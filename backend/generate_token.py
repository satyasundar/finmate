from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def generate_token():
    creds = None
    if os.path.exists("token.json"):
        print("Token already exists.")
        return

    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials for future use
    with open("token.json", "w") as token:
        token.write(creds.to_json())
    print("Token saved.")

if __name__ == "__main__":
    generate_token()
