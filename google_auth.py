import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

_cached_creds = None
_cached_at = 0


def get_credentials() -> Credentials:
    global _cached_creds, _cached_at
    if _cached_creds and _cached_creds.valid and (time.time() - _cached_at) < 1800:
        return _cached_creds
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
    _cached_creds = creds
    _cached_at = time.time()
    return creds
