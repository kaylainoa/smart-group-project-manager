from flask import Flask, render_template
from services.calendar_service import get_upcoming_events


app = Flask(__name__)
app.secret_key = "your-secret-key"

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/meetings")
def meetings():

    events = get_upcoming_events()

    for event in events:
        print(event["summary"], event["start"]["dateTime"], event["end"]["dateTime"])

    return "Check your terminal!"

if __name__ == "__main__":
    app.run(debug=True)