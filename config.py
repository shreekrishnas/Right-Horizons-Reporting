import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")

META_MARKETING_TOKEN = os.getenv("META_MARKETING_TOKEN", "")
META_SOCIAL_TOKEN = os.getenv("META_SOCIAL_TOKEN", "")
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_PAGE_ID = os.getenv("META_PAGE_ID", "296408333709162")
META_AD_ACCOUNT = os.getenv("META_AD_ACCOUNT", "act_267691143342137")

DOMAINS = {
    "rh": {
        "label": "Right Horizons",
        "short": "RH",
        "gsc_site": "https://www.righthorizons.com/",
        "ga4_property": os.getenv("GA4_PROPERTY_RH", "6639050"),
        "color": "#7C3AED",
        "url": "https://www.righthorizons.com",
    },
    "pms": {
        "label": "Right Horizons PMS",
        "short": "PMS",
        "gsc_site": "sc-domain:righthorizonspms.com",
        "ga4_property": os.getenv("GA4_PROPERTY_PMS", "424731774"),
        "color": "#0EA5E9",
        "url": "https://righthorizonspms.com",
    },
    "aif": {
        "label": "Right Horizons AIF",
        "short": "AIF",
        "gsc_site": "https://aif.righthorizonspms.com/",
        "ga4_property": os.getenv("GA4_PROPERTY_AIF", "534353483"),
        "color": "#10B981",
        "url": "https://aif.righthorizonspms.com",
    },
}
