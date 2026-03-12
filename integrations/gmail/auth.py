from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]


def get_gmail_service(credentials_path: str, token_path: str):
    """
    OAuth2 flow:
    1. Première fois: ouvre le navigateur pour autorisation
    2. Sauvegarde le token dans token_path
    3. Rafraîchit automatiquement le token expiré
    """
    token_file = Path(token_path)
    creds_file = Path(credentials_path)
    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"Fichier OAuth introuvable: {creds_file}\n"
                    "Téléchargez-le depuis Google Cloud Console → API & Services → Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)
