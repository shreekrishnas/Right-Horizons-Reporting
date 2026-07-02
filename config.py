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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "righthorizons@admin")

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

DOMAINS = {
    "rh": {
        "label": "Right Horizons",
        "short": "RH",
        "gsc_site": "https://www.righthorizons.com/",
        "ga4_property": os.getenv("GA4_PROPERTY_RH", "313861315"),
        "color": "#7C3AED",
        "url": "https://www.righthorizons.com",
        "meta_page_id": os.getenv("META_PAGE_ID", "296408333709162"),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_RH", "act_267691143342137"),
    },
    "pms": {
        "label": "Right Horizons PMS",
        "short": "PMS",
        "gsc_site": "sc-domain:righthorizonspms.com",
        "ga4_property": os.getenv("GA4_PROPERTY_PMS", "424731774"),
        "color": "#0EA5E9",
        "url": "https://righthorizonspms.com",
        "meta_page_id": os.getenv("META_PAGE_ID_PMS", "117532164550609"),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_PMS", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_PMS", ""),
    },
    "aif": {
        "label": "Right Horizons AIF",
        "short": "AIF",
        "gsc_site": "https://aif.righthorizonspms.com/",
        "ga4_property": os.getenv("GA4_PROPERTY_AIF", "534353483"),
        "color": "#10B981",
        "url": "https://aif.righthorizonspms.com",
        "meta_page_id": os.getenv("META_PAGE_ID_AIF", "1069286109601470"),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_AIF", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_AIF", ""),
    },
    "akeana": {
        "label": "Akeana",
        "short": "AKE",
        "gsc_site": os.getenv("GSC_SITE_AKEANA", "sc-domain:akeana.com"),
        "ga4_property": os.getenv("GA4_PROPERTY_AKEANA", "454994121"),
        "color": "#F59E0B",
        "url": os.getenv("AKEANA_URL", "https://www.akeana.com"),
        "meta_page_id": os.getenv("META_PAGE_ID_AKEANA", ""),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_AKEANA", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_AKEANA", ""),
    },
}
