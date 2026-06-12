import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
SECRET_KEY           = os.getenv("SECRET_KEY", "dev-secret-change-me")

META_MARKETING_TOKEN = os.getenv("META_MARKETING_TOKEN", "")
META_SOCIAL_TOKEN    = os.getenv("META_SOCIAL_TOKEN", "")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
    "openid",
    "email",
    "profile",
]

DOMAINS = {
    "rh": {
        "label": "Right Horizons",
        "short": "RH",
        "gsc_site": "sc-domain:righthorizons.com",
        "ga4_property": os.getenv("GA4_PROPERTY_RH", ""),
        "color": "#7C3AED",
        "url": "https://www.righthorizons.com",
    },
    "pms": {
        "label": "Right Horizons PMS",
        "short": "PMS",
        "gsc_site": "sc-domain:righthorizonspms.com",
        "ga4_property": os.getenv("GA4_PROPERTY_PMS", ""),
        "color": "#0EA5E9",
        "url": "https://righthorizonspms.com",
    },
    "aif": {
        "label": "Right Horizons AIF",
        "short": "AIF",
        "gsc_site": "sc-domain:aif.righthorizonspms.com",
        "ga4_property": os.getenv("GA4_PROPERTY_AIF", ""),
        "color": "#10B981",
        "url": "https://aif.righthorizonspms.com",
    },
}
