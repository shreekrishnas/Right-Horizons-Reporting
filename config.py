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
SE_RANKING_API_KEY = os.getenv("SE_RANKING_API_KEY", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "righthorizons@admin")

ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_FUND_THRESHOLD = int(os.getenv("ALERT_FUND_THRESHOLD", "10000"))

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
        # Token now has PMS page access, so social auto-fetches. Set
        # META_MANUAL_PMS=1 to force manual entry again.
        "meta_manual": os.getenv("META_MANUAL_PMS", "0") == "1",
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
        # Token now has AIF page access, so social auto-fetches. Set
        # META_MANUAL_AIF=1 to force manual entry again.
        "meta_manual": os.getenv("META_MANUAL_AIF", "0") == "1",
    },
    "akeana": {
        "label": "Akeana",
        "short": "AKE",
        "gsc_site": os.getenv("GSC_SITE_AKEANA", "https://www.akeana.com/"),
        "ga4_property": os.getenv("GA4_PROPERTY_AKEANA", "454994121"),
        "color": "#F59E0B",
        "url": os.getenv("AKEANA_URL", "https://www.akeana.com"),
        "meta_page_id": os.getenv("META_PAGE_ID_AKEANA", ""),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_AKEANA", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_AKEANA", ""),
    },
    "nextwealth": {
        "label": "NextWealth",
        "short": "NW",
        "gsc_site": os.getenv("GSC_SITE_NEXTWEALTH", "https://www.nextwealth.com/"),
        "ga4_property": os.getenv("GA4_PROPERTY_NEXTWEALTH", "313815408"),
        "color": "#E11D48",
        "url": os.getenv("NEXTWEALTH_URL", "https://www.nextwealth.com"),
        "meta_page_id": os.getenv("META_PAGE_ID_NEXTWEALTH", ""),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_NEXTWEALTH", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_NEXTWEALTH", ""),
    },
    "hoya": {
        "label": "Hoya Vision India",
        "short": "HOYA",
        "gsc_site": os.getenv("GSC_SITE_HOYA", "https://www.hoyavision.com/in/"),
        "ga4_property": os.getenv("GA4_PROPERTY_HOYA", "255658156"),
        "color": "#0057B8",
        "url": os.getenv("HOYA_URL", "https://www.hoyavision.com/in/"),
        "meta_page_id": os.getenv("META_PAGE_ID_HOYA", ""),
        "meta_social_token": os.getenv("META_SOCIAL_TOKEN_HOYA", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_HOYA", ""),
    },
}

# Accounts not currently being worked on: hidden from the dashboard, chat,
# reports and alerts. Override with the PAUSED_DOMAINS env var ("" = none).
PAUSED_DOMAINS = {k.strip() for k in os.getenv("PAUSED_DOMAINS", "rh,pms,aif").split(",") if k.strip()}

# Business context the AI assistant uses to interpret each domain's numbers.
DOMAIN_KNOWLEDGE = {
    "rh": "Right Horizons — Indian wealth management / investment advisory firm (Bangalore HQ). "
          "Audience: HNIs, NRIs, pre-retirees, senior tech professionals, UHNI families. "
          "Content pillars: Retirement Planning, NRI wealth, ESOPs, Family Office. Conversions = enquiries/consultation leads.",
    "pms": "Right Horizons PMS — SEBI-registered Portfolio Management Service (min ticket ₹50L). "
           "Audience: HNI investors evaluating PMS strategies. Traffic is niche and high-intent; low volume is normal.",
    "aif": "Right Horizons AIF — Alternative Investment Fund (min ticket ₹1Cr). Audience: UHNIs, family offices, "
           "NRIs (incl. GIFT City). Very niche, low-volume, high-value traffic.",
    "akeana": "Akeana — US-based RISC-V processor IP / semiconductor company. Audience: chip architects, SoC design "
              "teams, engineers, investors, job seekers. Primary market is US/global, not India.",
    "nextwealth": "NextWealth (nextwealth.com) — Bangalore-based B2B AI/ML data services company: human-in-the-loop "
                  "data annotation & labeling, GenAI/LLM data (RLHF, evaluation), computer vision, document/content "
                  "operations and digital ops. Known for 'impact sourcing' via delivery centres in Tier-2/3 Indian towns. "
                  "Audience: AI/ML, data-science and operations leaders at enterprises & AI-first companies, mostly in "
                  "the US/Europe; India traffic often includes job seekers and employees. Conversions = 'Contact us' / "
                  "demo / RFP enquiries; careers pages draw high but non-buyer traffic — separate them when judging lead quality. "
                  "Long sales cycles: judge quality by engaged sessions, time on service/case-study pages and US/EU share, not raw volume.",
    "hoya": "Hoya Vision Care India (hoyavision.com/in) — Indian arm of HOYA, the Japanese optical-technology company making "
            "spectacle lenses (MiyoSmart myopia-control lenses for children, progressive/varifocal lenses such as Hoyalux iD, "
            "single-vision, blue-light/screen and photochromic Sensity lenses, Hi-Vision coatings). Sold through optical "
            "stores/opticians, not direct online. Audiences: parents of myopic children, working professionals with screen "
            "strain, presbyopes 40+, and optometrists/opticians (B2B). Work here is mainly social media (creatives, content) "
            "with some SEO. Conversions = store-locator use, 'find an optician' and enquiry forms; India traffic is the target.",
}
