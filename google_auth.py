from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN


def get_credentials() -> Credentials:
    if not GOOGLE_REFRESH_TOKEN:
        raise RuntimeError("GOOGLE_REFRESH_TOKEN not set")
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    creds.refresh(Request())
    return creds
