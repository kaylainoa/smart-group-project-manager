import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" 
from services.calendar_service import create_flow, get_upcoming_events, get_project_deadlines
from services.slack_service import send_progress_report
from services.gemini_service import project_summary
import database
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, session, request
from google.oauth2.credentials import Credentials

load_dotenv()


app = Flask(__name__)
app.secret_key = "your-secret-key"

database.init_db()

@app.route("/")
def home():
    logs = database.get_notification_logs()
    return render_template("dashboard.html", logs=logs)

@app.route("/authorize")
def authorize():
    try:
        flow = create_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
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

    return redirect(url_for("meetings"))

@app.route("/meetings", methods=["GET", "POST"])
def meetings():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = Credentials(**session["credentials"])

    events = get_upcoming_events(credentials, max_results=10)

    for event in events:
        database.save_meeting(event)

    meetings_from_db = database.get_meetings()

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

    deadline_events = get_project_deadlines(credentials, max_results=20)

    for deadline in deadline_events:
        database.save_deadline(deadline)

    deadlines_from_db = database.get_deadlines()

    return render_template("deadlines.html", deadlines=deadlines_from_db)


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
    app.run(debug=True, port=8080)