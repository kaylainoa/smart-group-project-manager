# gets info from gcal like deadlines or meetings

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timezone

#tells google "I only want permission to read the user's calendar."
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
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


# grabs the logged-in user's email so we can keep everyone's meetings/deadlines
# separate in the db instead of one big shared list for the whole team
def get_user_email(credentials):
    service = build("oauth2", "v2", credentials=credentials)
    return service.userinfo().get().execute()["email"]


# used on first login to show someone the list of calendars they can pick from
def list_calendars(credentials):
    service = get_calendar_service(credentials)
    calendars = service.calendarList().list().execute().get("items", [])
    return [
        {"id": calendar["id"], "name": calendar.get("summary", calendar["id"])}
        for calendar in calendars
    ]


# gets upcoming meetings/events from Google Calendar
def get_upcoming_events(credentials, calendar_id, max_results=10):
    """
    Returns a list of upcoming events from one specific Google Calendar.

    Args:
        credentials: Google OAuth credentials.
        calendar_id (str): Which calendar to pull events from.
        max_results (int): Number of events to return.

    Returns:
        List of dictionaries containing event information.
    """

    service = get_calendar_service(credentials)

    now = datetime.now(timezone.utc).isoformat()

    results = (
        service.events()
        .list(
            calendarId=calendar_id,
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

# just a simple keyword check on the title/description to guess whether an
# event is a deadline vs. a regular meeting - no fancy NLP, just string matching
def _is_deadline_event(event):
    title = event["title"].lower()
    description = event["description"].lower()
    return "deadline" in title or "due" in title or "deadline" in description or "due" in description


# same calendar events as above, but only the ones that look like deadlines
def get_project_deadlines(credentials, calendar_id, max_results=10):
    events = get_upcoming_events(credentials, calendar_id, max_results)
    return [event for event in events if _is_deadline_event(event)]


# same calendar events, but excludes deadlines so /meetings and /deadlines
# don't show the same events twice
def get_meeting_events(credentials, calendar_id, max_results=10):
    events = get_upcoming_events(credentials, calendar_id, max_results)
    return [event for event in events if not _is_deadline_event(event)]