"""
Run this first to see all calendars available on your Google account.
Copy the IDs of the ones you want into generate.py.
"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DIR = os.path.dirname(os.path.abspath(__file__))


def get_credentials(token_file='token.json'):
    token_path = os.path.join(DIR, token_file)
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(DIR, 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds


creds = get_credentials()
service = build('calendar', 'v3', credentials=creds)

print("\nCalendars available on your account:\n")
result = service.calendarList().list().execute()
for cal in result.get('items', []):
    print(f"  Name : {cal['summary']}")
    print(f"  ID   : {cal['id']}")
    print()

print("Copy the IDs you want into CALENDAR_IDS in generate.py")
