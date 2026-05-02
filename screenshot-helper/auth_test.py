from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDS_PATH = os.path.expanduser('~/workspace/design-research/screenshot-helper/credentials.json')
TOKEN_PATH = os.path.expanduser('~/workspace/design-research/screenshot-helper/token.json')

def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    return creds

creds = authenticate()
service = build('drive', 'v3', credentials=creds)
result = service.files().list(pageSize=1).execute()
print('✅ Google Drive 연결 성공!')
