import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
from datetime import datetime, timezone, timedelta
from services.calendar_service import create_flow, get_meeting_events, get_project_deadlines, get_user_email, list_calendars
from services.slack_service import send_progress_report
from services.gemini_service import project_summary
import database
from database import generate_tasks_from_notes
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, session, request
from google.oauth2.credentials import Credentials
from services.github_service import get_repo_info, get_recent_commits
load_dotenv()


app = Flask(__name__)
app.secret_key = "your-secret-key"


# lets templates do {{ some_date | pretty_date }} to turn the raw ISO timestamp
# google gives us into something readable, like "July 10 2026"
@app.template_filter("pretty_date")
def pretty_date(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%B %d %Y")
    except (ValueError, AttributeError):
        return value


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

    return render_template(
        "dashboard.html",
        logs=logs,
        meetings=meetings_from_db,
        deadlines=deadlines_from_db,
        show_picker=show_picker,
        available_calendars=available_calendars
    )

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
# the notes form on /meetings is, so we just save it as a "General Note"
@app.route("/notes", methods=["POST"])
def add_note():
    notes = request.form["notes"]

    note_id = database.save_meeting_notes(
        None,
        "General Note",
        datetime.now(timezone.utc).isoformat(),
        notes
    )

    generated_tasks = generate_tasks_from_notes(notes)

    for task in generated_tasks:
        database.save_task(note_id, task)

    flash("Note saved and tasks generated.")
    return redirect(url_for("home"))


@app.route("/reports")
def reports():
    logs = database.get_notification_logs()
    return render_template("reports.html", logs=logs)


@app.route("/test-gemini", methods=["POST"])
def send_update_to_slack():
    raw_notes = "Discussed dashboard layout. John finished GitHub connection. Need to fix database bugs."
    raw_commits = ["feat: linked github service", "fix: resolved connection pool leak"]
    raw_deadlines = ["Milestone 2 due Friday at 5 PM"]

    ai_summary = project_summary(raw_notes, raw_commits, raw_deadlines)
    
    report = {
        "text": ai_summary 
    }

    success, error = send_progress_report(report)

    if success:
        flash("AI-generated update sent to Slack!")
    else:
        flash(f"Failed to send update to Slack: {error}")

    return redirect(url_for("home"))


if __name__ == "__main__":
    # app.run(debug=True, port=8080)
    app.run(host="0.0.0.0", port=8080, debug=True)
