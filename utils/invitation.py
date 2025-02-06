import os
import pickle
import datetime
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# Define the API scope for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to your downloaded credentials.json file
CLIENT_SECRET_FILE = 'client_secret_575701819091-bu3aitbj73b3c7df63440tga3v8itdn5.apps.googleusercontent.com.json'
# CLIENT_SECRET_FILE = '/Users/anz-davar/Downloads/client_secret_575701819091-bu3aitbj73b3c7df63440tga3v8itdn5.apps.googleusercontent.com.json'
API_NAME = 'calendar'
API_VERSION = 'v3'
REDIRECT_URI = 'http://localhost:8080/'


# Authenticate the user and get the credentials
def get_credentials():
    creds = None
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there's no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES, redirect_uri=REDIRECT_URI)
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


# Create and send a Google Calendar event invitation
def create_event(service):
    event = {
        'summary': 'Test Meeting',
        'location': 'Somewhere',
        'description': 'A chance to discuss important topics.',
        'start': {
            'dateTime': '2025-01-25T09:00:00-07:00',  # Start time in RFC3339 format
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2025-01-25T10:00:00-07:00',  # End time in RFC3339 format
            'timeZone': 'America/Los_Angeles',
        },
        'attendees': [
            {'email': 'avrdvir@gmail.com'},
            # {'email': 'oiluridze@gmail.com'},
            # {'email': 'javakhishviliannabelle@gmail.com'},
        ],
        'reminders': {
            'useDefault': True,
        },
    }

    try:
        event_result = service.events().insert(
            calendarId='primary', body=event).execute()
        print(f"Event created: {event_result.get('htmlLink')}")
    except HttpError as error:
        print(f"An error occurred: {error}")


# Main function to run the script
def main():
    # Get the credentials and create a service object
    creds = get_credentials()
    service = build(API_NAME, API_VERSION, credentials=creds)

    # Create the event and send invitations
    create_event(service)


if __name__ == '__main__':
    main()

# from google.oauth2.service_account import Credentials
# from googleapiclient.discovery import build
#
# # Service account credentials file
# SERVICE_ACCOUNT_FILE = "credentials.json"
# SCOPES = ["https://www.googleapis.com/auth/calendar"]
#
# # Calendar ID (use 'primary' for your default calendar)
# CALENDAR_ID = "primary"
# def create_event():
#     # Authenticate with the Google Calendar API
#     credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     service = build("calendar", "v3", credentials=credentials)
#
#     # Event details
#     event = {
#         "summary": "Project Discussion",
#         "location": "Google Meet link: https://meet.google.com/xyz-abc-def",
#         "description": "Let's discuss project updates and next steps.",
#         "start": {
#             "dateTime": "2025-01-20T10:00:00",
#             "timeZone": "UTC",
#         },
#         "end": {
#             "dateTime": "2025-01-20T11:00:00",
#             "timeZone": "UTC",
#         },
#         "attendees": [
#             {"email": "recipient1@example.com"},
#             {"email": "recipient2@example.com"},
#         ],
#         "reminders": {
#             "useDefault": False,
#             "overrides": [
#                 {"method": "email", "minutes": 24 * 60},  # 1 day before
#                 {"method": "popup", "minutes": 10},       # 10 minutes before
#             ],
#         },
#         "conferenceData": {
#             "createRequest": {
#                 "requestId": "sample123",
#                 "conferenceSolutionKey": {"type": "hangoutsMeet"},
#             },
#         },
#     }
#
#     # Insert the event into the calendar
#     event = service.events().insert(
#         calendarId=CALENDAR_ID,
#         body=event,
#         conferenceDataVersion=1,
#         sendUpdates="all",  # Sends notifications to attendees
#     ).execute()
#
#     print(f"Event created: {event.get('htmlLink')}")
#
# if __name__ == "__main__":
#     create_event()
