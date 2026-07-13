import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
import math
from datetime import datetime, timezone, timedelta
from services.calendar_service import create_flow, get_meeting_events, get_project_deadlines, get_user_email, list_calendars
from services.slack_service import send_progress_report
from services.gemini_service import categorize_update
import database
from database import generate_tasks_from_notes
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, session, request
from google.oauth2.credentials import Credentials
from services.github_service import get_project_activity
load_dotenv()


app = Flask(__name__)
app.secret_key = "your-secret-key"

class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix:
            environ["SCRIPT_NAME"] = self.prefix
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(self.prefix):
                environ["PATH_INFO"] = path_info[len(self.prefix):]
        return self.app(environ, start_response)


proxy_prefix = os.environ.get("USE_PROXY_PREFIX", "")
if proxy_prefix:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=proxy_prefix)

# lets templates do {{ some_date | pretty_date }} to turn the raw ISO timestamp
# google gives us into something readable, like "July 10 2026"
@app.template_filter("pretty_date")
def pretty_date(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%B %d %Y")
    except (ValueError, AttributeError):
        return value


# "2pm" instead of "02:00 PM" / "2:30pm" if it's not on the hour - no leading
# zero, lowercase am/pm
def _short_time(dt):
    hour12 = dt.strftime("%I").lstrip("0") or "12"
    ampm = dt.strftime("%p").lower()
    if dt.minute == 0:
        return f"{hour12}{ampm}"
    return f"{hour12}:{dt.minute:02d}{ampm}"


# lets templates do {{ meeting | meeting_schedule }} - same "Month Day Year"
# format as pretty_date, plus a time range like "11am-2pm" for events that
# actually have a time (all-day events just get the date, same as deadlines)
@app.template_filter("meeting_schedule")
def meeting_schedule(meeting):
    start_raw = meeting.get("start_time")
    if not start_raw:
        return start_raw

    try:
        start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return start_raw

    date_part = start_dt.strftime("%B %d %Y")

    # all-day events come back as a bare date ("2026-07-18") with no "T" in
    # it - there's no time to show for those
    if "T" not in start_raw:
        return date_part

    end_raw = meeting.get("end_time")
    end_dt = None
    if end_raw:
        try:
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            end_dt = None

    if end_dt:
        return f"{date_part}, {_short_time(start_dt)}-{_short_time(end_dt)}"
    return f"{date_part}, {_short_time(start_dt)}"


database.init_db()


# figures out who's logged in. caches it in the session after the first lookup
# so we're not hitting the Google API on every single request just for an email
def get_current_user_email(credentials):
    if "user_email" in session:
        return session["user_email"]
    try:
        email = get_user_email(credentials)
    except Exception:
        return None
    session["user_email"] = email
    return email


# used to trim the dashboard's meeting list down to just today + the next 2 days,
# so it's not a huge wall of every meeting for the rest of the semester
def _within_next_three_days(start_time):
    try:
        event_date = datetime.fromisoformat(start_time.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return False
    today = datetime.now(timezone.utc).date()
    return today <= event_date <= today + timedelta(days=2)


# pulls fresh events from Google, saves any new ones to the db, then reads back
# out of the db - this way /meetings, /deadlines, and the dashboard all show
# the same data without three different copies of this fetch-save-read logic
def refresh_meetings(credentials, user_email, calendar_id):
    events = get_meeting_events(credentials, calendar_id, max_results=50)
    for event in events:
        database.save_meeting(event, user_email, calendar_id)
    return database.get_meetings(user_email, calendar_id)


def refresh_deadlines(credentials, user_email, calendar_id):
    deadline_events = get_project_deadlines(credentials, calendar_id, max_results=50)
    for deadline in deadline_events:
        database.save_deadline(deadline, user_email, calendar_id)
    return database.get_deadlines(user_email, calendar_id)


# pastel tints of the same 8-hue categorical order the dataviz palette
# validates - fixed order, never regenerated. yellow/magenta are held back
# from the tint since they're already near the top of the lightness band;
# re-validated with scripts/validate_palette.js against our card surface
# (#fffdf8) before shipping. anything past slot 7 folds into "Other" (muted
# gray) instead of a synthesized 9th hue
PIE_COLORS = ["#5090dd", "#44bd92", "#eda305", "#2e992e", "#6b5db7", "#e86a69", "#ea88ad", "#ef8359"]
PIE_OTHER_COLOR = "#898781"


# turns [{"login", "contributions"}, ...] into SVG pie wedges (path + color +
# label + percent) the template can just loop over and draw
def build_pie_chart(contributors, cx=100, cy=100, r=90):
    if not contributors:
        return []

    top = contributors[:7]
    rest = contributors[7:]

    slice_data = [(c["login"], c["contributions"]) for c in top]
    if rest:
        slice_data.append(("Other", sum(c["contributions"] for c in rest)))

    total = sum(count for _, count in slice_data)
    if total == 0:
        return []

    slices = []
    angle = 0.0

    for i, (label, count) in enumerate(slice_data):
        fraction = count / total
        start_angle = angle
        end_angle = angle + fraction * 2 * math.pi
        color = PIE_OTHER_COLOR if label == "Other" else PIE_COLORS[i % len(PIE_COLORS)]

        if len(slice_data) == 1:
            # a single slice is the whole circle - the arc math below is
            # degenerate at exactly 360 degrees, so draw a plain circle instead
            path = None
        else:
            x1 = cx + r * math.sin(start_angle)
            y1 = cy - r * math.cos(start_angle)
            x2 = cx + r * math.sin(end_angle)
            y2 = cy - r * math.cos(end_angle)
            large_arc = 1 if (end_angle - start_angle) > math.pi else 0
            path = f"M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z"

        slices.append({
            "label": label,
            "count": count,
            "percent": round(fraction * 100),
            "color": color,
            "path": path
        })

        angle = end_angle

    return slices


# turns raw note text into the {"team_name", "period", "completed", "in_progress",
# "blockers"} shape send_progress_report expects, using Gemini to sort the note
# into buckets and pulling in real deadlines + real GitHub commits for context
def build_slack_report(notes_text, user_email):
    raw_commits = []
    repo_url = database.get_github_repo_url()
    if repo_url:
        activity = get_project_activity(repo_url, limit=5)
        if activity:
            raw_commits = [f"{c['author']}: {c['message']}" for c in activity["commits"]]

    raw_deadlines = []
    if user_email:
        selection = database.get_calendar_selection(user_email)
        if selection:
            deadlines = database.get_deadlines(user_email, selection["calendar_id"])
            raw_deadlines = [f"{d['title']} - due {d['due_time']}" for d in deadlines]

    categorized = categorize_update(notes_text, raw_commits, raw_deadlines)

    # this week's Monday through Friday, for the "period" line
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    period = f"{monday.strftime('%B %d')} - {friday.strftime('%B %d, %Y')}"

    return {
        "team_name": f"Update sent from {user_email or 'Unknown user'}",
        "period": period,
        "completed": categorized["completed"],
        "in_progress": categorized["in_progress"],
        "blockers": categorized["blockers"]
    }


@app.route("/")
def home():
    logs = database.get_notification_logs()

    meetings_from_db = []
    deadlines_from_db = []
    available_calendars = []
    show_picker = False

    if "credentials" in session:
        credentials = Credentials(**session["credentials"])
        user_email = get_current_user_email(credentials)

        if user_email is None:
            session.clear()
        else:
            selection = database.get_calendar_selection(user_email)

            # first time logging in, no calendar picked yet - show the picker
            # instead of the normal dashboard content
            if selection is None:
                show_picker = True
                available_calendars = list_calendars(credentials)
            else:
                calendar_id = selection["calendar_id"]
                meetings_from_db = [
                    m for m in refresh_meetings(credentials, user_email, calendar_id)
                    if _within_next_three_days(m["start_time"])
                ]
                deadlines_from_db = refresh_deadlines(credentials, user_email, calendar_id)

    github_repo_url = database.get_github_repo_url()
    github_activity = None
    pie_slices = []

    if github_repo_url:
        github_activity = get_project_activity(github_repo_url, limit=3)
        if github_activity:
            pie_slices = build_pie_chart(github_activity["contributors"])

    return render_template(
        "dashboard.html",
        logs=logs,
        meetings=meetings_from_db,
        deadlines=deadlines_from_db,
        show_picker=show_picker,
        available_calendars=available_calendars,
        saved_notes=database.get_general_notes(),
        github_repo_url=github_repo_url,
        github_activity=github_activity,
        pie_slices=pie_slices
    )


# saves (or updates) which GitHub repo the dashboard/Slack reports pull
# activity from - a project-wide setting, so anyone can set/change it
@app.route("/settings/github", methods=["POST"])
def set_github_repo():
    repo_url = request.form.get("repo_url", "").strip()
    if not repo_url:
        flash("Enter a GitHub repo URL first.")
        return redirect(url_for("home"))

    activity = get_project_activity(repo_url)
    if activity is None:
        flash("Couldn't find that repo - check the URL and try again.")
        return redirect(url_for("home"))

    database.save_github_repo_url(repo_url)
    flash(f"Now tracking \"{activity['repo']['name']}\".")
    return redirect(url_for("home"))

@app.route("/authorize")
def authorize():
    try:
        flow = create_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account consent"
        )

        session["state"] = state
        session["code_verifier"] = flow.code_verifier
        return redirect(authorization_url)

    except Exception as e:
        flash(f"Authorization failed: {e}")
        return redirect(url_for("home"))


@app.route("/oauth2callback")
def oauth2callback():
    flow = create_flow()
    flow.code_verifier = session.get("code_verifier")
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    return redirect(url_for("home"))


# handles the picker form from the dashboard. once someone has picked a
# calendar this just bounces them back home - the choice is permanent
@app.route("/select-calendar", methods=["POST"])
def select_calendar():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = Credentials(**session["credentials"])

    user_email = get_current_user_email(credentials)
    if user_email is None:
        session.clear()
        return redirect(url_for("authorize"))

    if database.get_calendar_selection(user_email) is not None:
        return redirect(url_for("home"))

    chosen_id = request.form.get("calendar_id")
    if not chosen_id:
        flash("Pick a calendar.")
        return redirect(url_for("home"))

    available = list_calendars(credentials)
    chosen = next((c for c in available if c["id"] == chosen_id), None)
    if chosen is None:
        flash("That calendar could not be found. Please pick again.")
        return redirect(url_for("home"))

    database.save_calendar_selection(user_email, chosen["id"], chosen["name"])
    flash(f"Now pulling from \"{chosen['name']}\".")
    return redirect(url_for("home"))


@app.route("/meetings", methods=["GET", "POST"])
def meetings():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = Credentials(**session["credentials"])

    user_email = get_current_user_email(credentials)
    if user_email is None:
        session.clear()
        return redirect(url_for("authorize"))

    selection = database.get_calendar_selection(user_email)
    if selection is None:
        return redirect(url_for("home"))

    meetings_from_db = refresh_meetings(credentials, user_email, selection["calendar_id"])

    if request.method == "POST":
        meeting_id = request.form["meeting_id"]
        meeting_title = request.form["meeting_title"]
        meeting_time = request.form["meeting_time"]
        notes = request.form["notes"]

        note_id = database.save_meeting_notes(
            meeting_id,
            meeting_title,
            meeting_time,
            notes
        )

        generated_tasks = generate_tasks_from_notes(notes)

        for task in generated_tasks:
            database.save_task(note_id, task)

        flash("Meeting notes saved and tasks generated.")
        return redirect(url_for("meetings"))

    notes = database.get_meeting_notes()
    tasks = database.get_tasks()

    return render_template(
        "meetings.html",
        meetings=meetings_from_db,
        notes=notes,
        tasks=tasks
    )

@app.route("/deadlines")
def deadlines():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = Credentials(**session["credentials"])

    user_email = get_current_user_email(credentials)
    if user_email is None:
        session.clear()
        return redirect(url_for("authorize"))

    selection = database.get_calendar_selection(user_email)
    if selection is None:
        return redirect(url_for("home"))

    deadlines_from_db = refresh_deadlines(credentials, user_email, selection["calendar_id"])

    return render_template("deadlines.html", deadlines=deadlines_from_db)

@app.route("/github")
def github():
    repo_info = get_repo_info()
    commits = get_recent_commits()
    return render_template("github.html", repo_info=repo_info, commits=commits)

# the "Enter Notes" box on the dashboard - not tied to a specific meeting like
# the notes form on /meetings is, so we just save it as a "General Note".
# each saved note gets its own card + Send button (see send_note_to_slack
# below) instead of generating a Slack report right here
@app.route("/notes", methods=["POST"])
def add_note():
    notes = request.form["notes"]
    title = request.form.get("title", "").strip() or "General Note"

    note_id = database.save_meeting_notes(
        None,
        title,
        datetime.now(timezone.utc).isoformat(),
        notes
    )

    generated_tasks = generate_tasks_from_notes(notes)

    for task in generated_tasks:
        database.save_task(note_id, task)

    flash("Note saved.")
    return redirect(url_for("home"))


# wipes the whole "Saved Notes" column
@app.route("/notes/clear", methods=["POST"])
def clear_notes():
    database.clear_general_notes()
    flash("Saved notes cleared.")
    return redirect(url_for("home"))


# the Send button on an individual note card - generates the Gemini report
# from just that note's text and posts it right away
@app.route("/notes/<int:note_id>/send", methods=["POST"])
def send_note_to_slack(note_id):
    note = database.get_note_by_id(note_id)
    if note is None:
        flash("That note could not be found.")
        return redirect(url_for("home"))

    user_email = None
    if "credentials" in session:
        credentials = Credentials(**session["credentials"])
        user_email = get_current_user_email(credentials)

    report = build_slack_report(note["notes"], user_email)
    success, error = send_progress_report(report)

    if success:
        database.mark_note_sent(note_id)
        flash("Update sent to Slack!")
    else:
        flash(f"Failed to send update to Slack: {error}")

    return redirect(url_for("home"))


@app.route("/reports")
def reports():
    logs = database.get_notification_logs()
    return render_template("reports.html", logs=logs)




if __name__ == "__main__":
    # app.run(debug=True, port=8080)
    app.run(host="0.0.0.0", port=5000, debug=True)
