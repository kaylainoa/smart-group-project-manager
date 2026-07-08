# gets info from gcal like deadlines or meetings

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timezone

#tells google "I only want permission to read the user's calendar."
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]

CLIENT_SECRETS_FILE = "client_info.json"


def create_flow():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://127.0.0.1:5000/oauth2callback"
    )

    return flow


def get_calendar_service(credentials):

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service
# gets upcoming meetings/events from Google Calendar
def get_upcoming_events(credentials, max_results=10):
    """
    Returns a list of upcoming Google Calendar events.

    Args:
        credentials: Google OAuth credentials.
        max_results (int): Number of events to return.

    Returns:
        List of dictionaries containing event information.
    """

    service = get_calendar_service(credentials)

    now = datetime.now(timezone.utc).isoformat()

    results = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = results.get("items", [])

    meeting_list = []

    for event in events:
        start = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        meeting_list.append(
            {
                "id": event.get("id"),
                "title": event.get("summary", "No Title"),
                "start": start,
                "location": event.get("location", ""),
                "description": event.get("description", "")
            }
        )

    return meeting_list

def get_project_deadlines(credentials, max_results=10):
    events = get_upcoming_events(credentials, max_results)

    deadlines = []

    for event in events:
        title = event["title"].lower()
        description = event["description"].lower()

        if "deadline" in title or "due" in title or "deadline" in description or "due" in description:
            deadlines.append(event)

    return deadlines