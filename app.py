import os
from flask import Flask, render_template, redirect, url_for, flash
from services.calendar_service import get_upcoming_events
from services.slack_service import send_progress_report
from services.gemini_service import project_summary
import database
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "your-secret-key"

database.init_db()

@app.route("/")
def home():
    logs = database.get_notification_logs()
    return render_template("dashboard.html", logs=logs)


@app.route("/meetings")
def meetings():
    events = get_upcoming_events()
    for event in events:
        print(event["summary"], event["start"]["dateTime"], event["end"]["dateTime"])
    return "Check your terminal!"


@app.route("/reports")
def reports():
    logs = database.get_notification_logs()
    return render_template("reports.html", logs=logs)


@app.route("/send-update-to-slack", methods=["POST"])
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
    app.run(debug=True)