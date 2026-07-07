import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" 
from services.calendar_service import create_flow, get_upcoming_events
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
        return redirect(authorization_url)

    except Exception as e:
        flash(f"Authorization failed: {e}")
        return redirect(url_for("home"))


@app.route("/oauth2callback")
def oauth2callback():
    flow = create_flow()
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


@app.route("/meetings")
def meetings():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = Credentials(**session["credentials"])

    events = get_upcoming_events(credentials, max_results=10)

    return render_template("meetings.html", meetings=events)

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