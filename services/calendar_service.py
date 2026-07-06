# gets info from gcal like deadlines or meetings
#day 1 goal: Can I connect to Google Calendar and print upcoming events?
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone

#tells google "I only want permission to read the user's calendar."
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_info.json",
        SCOPES
    )

    credentials = flow.run_local_server(port=5001)

    return credentials

def get_calendar_service():
    credentials = authenticate()

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service

def get_upcoming_events():

    service = get_calendar_service()

    now = datetime.now(timezone.utc).isoformat()

    events = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events.get("items", [])