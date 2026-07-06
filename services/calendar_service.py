# gets info from gcal like deadlines or meetings
#day 1 goal: Can I connect to Google Calendar and print upcoming events?
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
        redirect_uri="http://localhost:5000/oauth2callback"
    )

    return flow


def get_calendar_service(credentials):

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service