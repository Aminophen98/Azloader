import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DATA_DIR = os.getenv("DATA_DIR", "/data")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")


def has_credentials_file() -> bool:
    return os.path.exists(CREDENTIALS_PATH)


def is_authorized() -> bool:
    creds = get_credentials()
    return creds is not None and creds.valid


def get_credentials() -> Credentials | None:
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        return creds if creds.valid else None
    except Exception:
        return None


def _save_token(creds: Credentials):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


# We store the flow in memory between /auth/start and /auth/code
_pending_flow: Flow | None = None


def start_auth_flow() -> str:
    global _pending_flow
    _pending_flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = _pending_flow.authorization_url(
        prompt="consent", access_type="offline"
    )
    return auth_url


def complete_auth_flow(code: str) -> bool:
    global _pending_flow
    if _pending_flow is None:
        raise RuntimeError("No pending auth flow. Call /auth/start first.")
    _pending_flow.fetch_token(code=code.strip())
    _save_token(_pending_flow.credentials)
    _pending_flow = None
    return True


def upload_file(filepath: str, filename: str, folder_id: str | None = None) -> dict:
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Not authorized with Google Drive.")
    service = build("drive", "v3", credentials=creds)

    file_metadata: dict = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(filepath, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,name,webViewLink")
        .execute()
    )
    return file
