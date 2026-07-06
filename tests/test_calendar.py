from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CLIENT_SECRETS_FILE = "client_info.json"

REDIRECT_URI = "http://localhost:5000/oauth2callback"


def run_oauth_test():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes=True,
        prompt="consent"
    )

    print("\n👉 STEP 1: Open this URL in your browser:\n")
    print(auth_url)
    print("\n")

    code_url = input("👉 Paste FULL redirected URL here after login:\n")

    flow.fetch_token(authorization_response=code_url)

    credentials = flow.credentials

    print("\n✅ AUTH SUCCESS\n")

    service = build("calendar", "v3", credentials=credentials)

    now = "2026-01-01T00:00:00Z"

    events = service.events().list(
        calendarId="primary",
        maxResults=5,
        singleEvents=True,
        orderBy="startTime",
        timeMin=now
    ).execute()

    print("\n📅 Upcoming Events:\n")

    for event in events.get("items", []):
        print("-", event.get("summary", "No Title"))


if __name__ == "__main__":
    run_oauth_test()