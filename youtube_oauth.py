"""
One-time helper to generate a YOUTUBE_REFRESH_TOKEN that includes the
YouTube Analytics scope (needed for accurate per-month views / new subscribers).

Run LOCALLY on a machine with a browser (not on Vercel):

    pip install google-auth-oauthlib
    export YOUTUBE_CLIENT_ID="...."
    export YOUTUBE_CLIENT_SECRET="...."
    python youtube_oauth.py

A browser window opens → sign in with the Google account that owns the
Right Horizons YouTube channel → approve. The script prints a refresh token.
Paste that value into Vercel as YOUTUBE_REFRESH_TOKEN and redeploy.

Prereq: in Google Cloud Console the OAuth client must be a "Desktop app"
(or have http://localhost listed as an authorized redirect URI), and both the
YouTube Data API v3 and the YouTube Analytics API must be enabled.
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def main():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET env vars first.")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token is returned
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    print("\n============================================================")
    print("YOUTUBE_REFRESH_TOKEN =")
    print(creds.refresh_token)
    print("============================================================")
    print("Paste the value above into Vercel as YOUTUBE_REFRESH_TOKEN, then redeploy.")


if __name__ == "__main__":
    main()
