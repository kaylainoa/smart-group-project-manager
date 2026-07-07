from flask import Flask, render_template, redirect, url_for, flash
from services.calendar_service import get_upcoming_events
from services.slack_service import send_progress_report
import database


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


# placeholder/hard coded slack message
@app.route("/send-update-to-slack", methods=["POST"])
def send_update_to_slack():
    report = {
        "team_name": "Smart Group Project Manager",
        "period": "This Week",
        "completed": ["Set up GitHub sync"],
        "in_progress": ["Building Slack integration"],
        "blockers": [],
    }

    success, error = send_progress_report(report)

    if success:
        flash("Update sent to Slack!")
    else:
        flash(f"Failed to send update to Slack: {error}")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)