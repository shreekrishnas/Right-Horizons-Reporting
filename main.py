import io
import traceback
from datetime import date, timedelta, datetime, timezone
_IST = timezone(timedelta(hours=5, minutes=30))
def _today_ist() -> date:
    return datetime.now(_IST).date()

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles

from config import DOMAINS, META_MARKETING_TOKEN, META_SOCIAL_TOKEN, META_PAGE_ID, META_APP_ID, META_APP_SECRET, ADMIN_PASSWORD
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
from config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
from config import OPENROUTER_API_KEY, TAVILY_API_KEY, SE_RANKING_API_KEY
try:
    import web_search
except Exception:
    web_search = None
try:
    import google_trends
except Exception:
    google_trends = None
from google_auth import get_credentials, get_youtube_credentials
import gsc
import ga4
import meta
import social
import youtube
import linkedin
from exporter import build_report


def _meta_creds(domain: str = "rh"):
    """Resolve per-domain Meta social token and page ID."""
    d = DOMAINS.get(domain, DOMAINS["rh"])
    token = d.get("meta_social_token") or META_SOCIAL_TOKEN
    page_id = d.get("meta_page_id") or META_PAGE_ID
    return token, page_id

app = FastAPI(title="Right Horizons Reporting")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _dates(start: str, end: str):
    today = _today_ist()
    if not end:
        end = today.isoformat()
    if not start:
        start = (today - timedelta(days=27)).isoformat()
    return start, end


def _domain(key: str) -> dict:
    if key not in DOMAINS:
        raise HTTPException(400, f"Unknown domain: {key}")
    return DOMAINS[key]



# ── Health & Config ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    try:
        creds = get_credentials()
        return {"status": "ok", "google_auth": True, "meta_marketing": bool(META_MARKETING_TOKEN), "meta_social": bool(META_SOCIAL_TOKEN)}
    except Exception as e:
        return {"status": "degraded", "google_auth": False, "error": str(e), "meta_marketing": bool(META_MARKETING_TOKEN), "meta_social": bool(META_SOCIAL_TOKEN)}


def _mask(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return "****"
    return val[:4] + "*" * (len(val) - 8) + val[-4:]


@app.post("/api/admin/login")
def admin_login(password: str = ""):
    if not password or password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    return {"ok": True}


@app.post("/api/admin/credentials")
def admin_credentials(password: str = ""):
    if not password or password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    return {
        "google": {
            "client_id": _mask(GOOGLE_CLIENT_ID),
            "client_secret": _mask(GOOGLE_CLIENT_SECRET),
            "refresh_token": _mask(GOOGLE_REFRESH_TOKEN),
            "status": "Connected" if GOOGLE_REFRESH_TOKEN else "Not configured",
        },
        "youtube": {
            "client_id": _mask(YOUTUBE_CLIENT_ID),
            "client_secret": _mask(YOUTUBE_CLIENT_SECRET),
            "refresh_token": _mask(YOUTUBE_REFRESH_TOKEN),
            "status": "Connected" if YOUTUBE_REFRESH_TOKEN else "Not configured",
        },
        "meta": {
            "marketing_token": _mask(META_MARKETING_TOKEN),
            "social_token": _mask(META_SOCIAL_TOKEN),
            "app_id": _mask(META_APP_ID),
            "app_secret": _mask(META_APP_SECRET),
            "page_id": META_PAGE_ID,
            "status": "Connected" if META_MARKETING_TOKEN else "Not configured",
        },
        "openrouter": {
            "api_key": _mask(OPENROUTER_API_KEY),
            "status": "Connected" if OPENROUTER_API_KEY else "Not configured",
        },
        "se_ranking": {
            "api_key": _mask(SE_RANKING_API_KEY),
            "status": "Connected" if SE_RANKING_API_KEY else "Not configured",
        },
        "domains": {
            k: {
                "label": v["label"],
                "ga4_property": v.get("ga4_property", ""),
                "gsc_site": v.get("gsc_site", ""),
                "meta_page_id": v.get("meta_page_id", ""),
                "meta_ad_account": v.get("meta_ad_account", ""),
                "meta_social_token_set": bool(v.get("meta_social_token")),
            }
            for k, v in DOMAINS.items()
        },
    }


@app.post("/api/admin/history")
def admin_history(password: str = ""):
    if not password or password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    return {
        "calendar_levels": _generation_level,
        "calendar_history_counts": {k: len(v) for k, v in _calendar_history.items()},
        "ideas_history_counts": {k: len(v) for k, v in _ideas_history.items()},
        "calendar_recent": {k: v[-20:] for k, v in _calendar_history.items()},
        "ideas_recent": {k: v[-20:] for k, v in _ideas_history.items()},
    }


@app.post("/api/admin/reset-history")
def admin_reset_history(password: str = "", scope: str = "all"):
    if not password or password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    if scope in ("all", "calendar"):
        _calendar_history.clear()
    if scope in ("all", "ideas"):
        _ideas_history.clear()
    if scope == "all":
        _generation_level.clear()
    return {"ok": True, "scope": scope}


@app.get("/api/domains")
def get_domains():
    return {k: {kk: vv for kk, vv in v.items() if kk not in ("gsc_site", "ga4_property")} for k, v in DOMAINS.items()}


@app.get("/api/gsc/sites")
def gsc_sites():
    try:
        creds = get_credentials()
        return {"sites": gsc.list_sites(creds)}
    except Exception as e:
        raise HTTPException(502, f"GSC error: {e}")


# ── GSC Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/gsc/summary")
def gsc_summary(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    try:
        creds = get_credentials()
        return gsc.get_summary(creds, d["gsc_site"], start, end)
    except Exception as e:
        raise HTTPException(502, f"GSC error: {e}")


@app.get("/api/gsc/queries")
def gsc_queries(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    start, end = _dates(start, end)
    d = _domain(domain)
    try:
        creds = get_credentials()
        return gsc.get_top_queries(creds, d["gsc_site"], start, end, limit)
    except Exception as e:
        raise HTTPException(502, f"GSC error: {e}")


@app.get("/api/gsc/pages")
def gsc_pages(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    start, end = _dates(start, end)
    d = _domain(domain)
    try:
        creds = get_credentials()
        return gsc.get_top_pages(creds, d["gsc_site"], start, end, limit)
    except Exception as e:
        raise HTTPException(502, f"GSC error: {e}")


@app.get("/api/gsc/daily")
def gsc_daily(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    try:
        creds = get_credentials()
        return gsc.get_daily(creds, d["gsc_site"], start, end)
    except Exception as e:
        raise HTTPException(502, f"GSC error: {e}")


# ── GA4 Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/ga4/summary")
def ga4_summary(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    prop = d["ga4_property"]
    if not prop:
        raise HTTPException(400, f"GA4 property not configured for {domain}")
    try:
        creds = get_credentials()
        return ga4.get_summary(creds, prop, start, end)
    except Exception as e:
        raise HTTPException(502, f"GA4 error (property={prop}): {e}")


@app.get("/api/ga4/pages")
def ga4_pages(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    start, end = _dates(start, end)
    d = _domain(domain)
    prop = d["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    try:
        creds = get_credentials()
        return ga4.get_top_pages(creds, prop, start, end, limit)
    except Exception as e:
        raise HTTPException(502, f"GA4 error: {e}")


@app.get("/api/ga4/sources")
def ga4_sources(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    prop = d["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    try:
        creds = get_credentials()
        return ga4.get_traffic_sources(creds, prop, start, end)
    except Exception as e:
        raise HTTPException(502, f"GA4 error: {e}")


@app.get("/api/ga4/daily")
def ga4_daily(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    prop = d["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    try:
        creds = get_credentials()
        return ga4.get_daily(creds, prop, start, end)
    except Exception as e:
        raise HTTPException(502, f"GA4 error: {e}")


# ── Meta Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/meta/status")
def meta_status():
    return {"marketing": bool(META_MARKETING_TOKEN), "social": bool(META_SOCIAL_TOKEN)}


@app.get("/api/meta/campaigns")
def meta_campaigns(start: str = "", end: str = "", domain: str = "rh", status: str = "all"):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if not ad_account:
        raise HTTPException(400, "Meta Ads not configured for this domain")
    start, end = _dates(start, end)
    try:
        return meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end, status)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


@app.get("/api/meta/daily")
def meta_daily(start: str = "", end: str = "", domain: str = "rh"):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if not ad_account:
        raise HTTPException(400, "Meta Ads not configured for this domain")
    start, end = _dates(start, end)
    try:
        return meta.get_daily_spend(META_MARKETING_TOKEN, ad_account, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


@app.get("/api/meta/accounts")
def meta_accounts(domain: str = "rh"):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if not ad_account:
        raise HTTPException(400, "Meta Ads not configured for this domain")
    try:
        accounts = meta.get_ad_accounts(META_MARKETING_TOKEN)
        accounts = [a for a in accounts if a["id"] == ad_account]
        return accounts
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


# ── Social (Facebook + Instagram) ────────────────────────────────────────────

@app.get("/api/social/pages")
def social_pages(domain: str = "rh"):
    token, page_id = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if page_id:
        try:
            from social import _get
            page = _get(f"/{page_id}", token, {"fields": "id,name,fan_count,followers_count"})
            return [page]
        except Exception:
            return [{"id": page_id, "name": DOMAINS.get(domain, DOMAINS["rh"])["label"]}]
    try:
        return social.get_pages(token)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/diagnose")
def social_diagnose(token: str = ""):
    """Check Meta token access against every domain's page — shows the exact
    Graph API error when a page can't be read (e.g. token bound to another page).

    Pass ?token=... to test a specific token (instead of the configured env
    tokens) against every page, and to list which pages that token can manage.
    The token is never logged or stored."""
    out = {}
    if token:
        # Which pages does THIS token manage (each with its own page token)?
        try:
            from social import _get
            accts = _get("/me/accounts", token, {"fields": "id,name,access_token", "limit": 100})
            out["_token_manages_pages"] = [
                {"id": p.get("id"), "name": p.get("name")} for p in accts.get("data", [])
            ]
        except Exception as e:
            out["_token_manages_pages_error"] = str(e)[:300]
        try:
            me = _get("/me", token, {"fields": "id,name"})
            out["_token_identity"] = {"id": me.get("id"), "name": me.get("name")}
        except Exception as e:
            out["_token_identity_error"] = str(e)[:300]

    for dom_key in ("rh", "pms", "aif", "akeana"):
        cfg_token, page_id = _meta_creds(dom_key)
        use_token = token or cfg_token
        if not use_token or not page_id:
            out[dom_key] = {"skipped": "no token or page id configured"}
            continue
        out[dom_key] = social.diagnose_page_access(use_token, page_id)
    return out


@app.get("/api/social/fb-comprehensive")
def social_fb_comprehensive(start: str = "", end: str = "", domain: str = "rh"):
    token, page_id = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        raise HTTPException(400, "META_PAGE_ID not configured")
    start, end = _dates(start, end)
    try:
        result = social.get_fb_comprehensive(token, page_id, start, end)
        result["page_id"] = page_id
        return result
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/trend")
def social_trend(period: str = "weekly", periods: int = 5, domain: str = "rh", end_date: str = ""):
    token, page_id = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        raise HTTPException(400, "META_PAGE_ID not configured")

    anchor = date.fromisoformat(end_date) if end_date else _today_ist()
    days_per = 7 if period == "weekly" else 30
    ig_id = None
    try:
        ig_id = social.get_ig_account(token, page_id)
    except Exception:
        pass

    results = []
    for i in range(periods):
        p_end = anchor - timedelta(days=i * days_per)
        p_start = p_end - timedelta(days=days_per - 1)
        ps = p_start.isoformat()
        pe = p_end.isoformat()
        if period == "weekly":
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
        else:
            label = p_start.strftime('%B %Y')

        row = {"period": label, "start": ps, "end": pe, "period_start": p_start.strftime('%b %d'), "period_end": p_end.strftime('%b %d')}
        try:
            fb = social.get_fb_comprehensive(token, page_id, ps, pe)
            row["fb"] = fb
        except Exception:
            row["fb"] = {}
        if ig_id:
            try:
                ig = social.get_ig_comprehensive(token, ig_id, ps, pe)
                row["ig"] = ig
            except Exception:
                row["ig"] = {}
        else:
            row["ig"] = {}
        if row.get("fb") and isinstance(row["fb"], dict):
            row["fb"]["posts"] = row["fb"].get("posts_published", 0)
        if row.get("ig") and isinstance(row["ig"], dict):
            row["ig"]["posts"] = row["ig"].get("posts_published", 0)
        results.append(row)

    results.reverse()
    return results


@app.get("/api/social/ig-comprehensive")
def social_ig_comprehensive(start: str = "", end: str = "", domain: str = "rh"):
    token, page_id = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        raise HTTPException(400, "META_PAGE_ID not configured")
    start, end = _dates(start, end)
    try:
        ig_id = social.get_ig_account(token, page_id)
        if not ig_id:
            raise HTTPException(404, "No Instagram business account linked")
        return social.get_ig_comprehensive(token, ig_id, start, end)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/page-posts")
def social_page_posts(page_id: str = "", start: str = "", end: str = "", limit: int = 10, domain: str = "rh"):
    token, pid = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        page_id = pid
    if not page_id:
        raise HTTPException(400, "page_id required")
    start, end = _dates(start, end)
    try:
        return social.get_page_posts(token, page_id, start, end, limit)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-account")
def social_ig_account(page_id: str = "", domain: str = "rh"):
    token, pid = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        page_id = pid
    if not page_id:
        raise HTTPException(400, "page_id required")
    try:
        ig_id = social.get_ig_account(token, page_id)
        if not ig_id:
            raise HTTPException(404, "No Instagram business account linked to this page")
        return {"ig_id": ig_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-profile")
def social_ig_profile(ig_id: str, domain: str = "rh"):
    token, _ = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        return social.get_ig_profile(token, ig_id)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-insights")
def social_ig_insights(ig_id: str, start: str = "", end: str = "", domain: str = "rh"):
    token, _ = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _dates(start, end)
    try:
        return social.get_ig_insights(token, ig_id, start, end)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-media")
def social_ig_media(ig_id: str, limit: int = 10, domain: str = "rh"):
    token, _ = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        return social.get_ig_media(token, ig_id, limit)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


# ── SEO Trend ────────────────────────────────────────────────────────────────

@app.get("/api/seo/trend")
def seo_trend(domain: str = "rh", period: str = "weekly", periods: int = 5, end_date: str = ""):
    d = _domain(domain)
    try:
        creds = get_credentials()
    except Exception as e:
        raise HTTPException(502, f"Auth error: {e}")

    anchor = date.fromisoformat(end_date) if end_date else _today_ist()
    days_per = 7 if period == "weekly" else 30
    results = []
    for i in range(periods):
        p_end = anchor - timedelta(days=i * days_per)
        p_start = p_end - timedelta(days=days_per - 1)
        ws = p_start.isoformat()
        we = p_end.isoformat()
        if period == "weekly":
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
        else:
            label = p_start.strftime('%B %Y')

        row = {"period": label, "start": ws, "end": we, "period_start": p_start.strftime('%b %d'), "period_end": p_end.strftime('%b %d')}

        try:
            gs = gsc.get_summary(creds, d["gsc_site"], ws, we)
            row.update({
                "gsc_clicks": gs.get("clicks", 0),
                "gsc_impressions": gs.get("impressions", 0),
                "gsc_position": gs.get("position", 0),
            })
        except Exception:
            row.update({"gsc_clicks": 0, "gsc_impressions": 0, "gsc_position": 0})
        row["clicks"] = row.get("gsc_clicks", 0)
        row["impressions"] = row.get("gsc_impressions", 0)
        row["position"] = row.get("gsc_position", 0)

        prop = d.get("ga4_property")
        if prop:
            try:
                org = ga4.get_organic_summary(creds, prop, ws, we)
                row.update({
                    "organic_sessions": org.get("organic_sessions", 0),
                    "organic_users": org.get("organic_users", 0),
                    "bounce_rate": org.get("bounce_rate", 0),
                    "avg_session_duration": org.get("avg_session_duration", 0),
                    "leads": org.get("leads", 0),
                })
            except Exception:
                row.update({"organic_sessions": 0, "organic_users": 0, "bounce_rate": 0, "avg_session_duration": 0, "leads": 0})
        row["sessions"] = row.get("organic_sessions", 0)
        row["users"] = row.get("organic_users", 0)
        results.append(row)

    results.reverse()
    return results


# ── YouTube ──────────────────────────────────────────────────────────────────

@app.get("/api/youtube/channel")
def youtube_channel():
    try:
        creds = get_youtube_credentials()
        return youtube.get_channel_stats(creds)
    except Exception as e:
        raise HTTPException(502, f"YouTube error: {e}")


@app.get("/api/youtube/videos")
def youtube_videos(limit: int = 10):
    try:
        creds = get_youtube_credentials()
        return youtube.get_recent_videos(creds, limit)
    except Exception as e:
        raise HTTPException(502, f"YouTube error: {e}")


@app.post("/api/youtube/seo")
def youtube_seo(payload: dict = Body(...)):
    topic = payload.get("topic", "").strip()
    speaker = payload.get("speaker", "")
    transcript = payload.get("transcript", "")
    if not topic:
        raise HTTPException(400, "topic parameter required")
    return youtube.generate_seo_metadata(topic, speaker, transcript)


# ── SE Ranking ────────────────────────────────────────────────────────────────

try:
    import se_ranking as ser_mod
except Exception:
    ser_mod = None


@app.get("/api/se-ranking/dashboard")
def se_ranking_dashboard(domain: str = "akeana"):
    if not ser_mod or not SE_RANKING_API_KEY:
        raise HTTPException(503, "SE Ranking not configured")
    d = DOMAINS.get(domain, {})
    site_url = d.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    if not site_url:
        raise HTTPException(400, f"No URL configured for domain '{domain}'")
    source = d.get("se_ranking_source", "us")
    try:
        return ser_mod.full_dashboard(site_url, source)
    except Exception as e:
        raise HTTPException(502, f"SE Ranking error: {e}")


@app.get("/api/se-ranking/overview")
def se_ranking_overview(domain: str = "akeana", source: str = "us"):
    if not ser_mod or not SE_RANKING_API_KEY:
        raise HTTPException(503, "SE Ranking not configured")
    d = DOMAINS.get(domain, {})
    site_url = d.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    if not site_url:
        raise HTTPException(400, f"No URL configured for domain '{domain}'")
    try:
        return ser_mod.domain_overview(site_url, source)
    except Exception as e:
        raise HTTPException(502, f"SE Ranking error: {e}")


@app.get("/api/se-ranking/keywords")
def se_ranking_keywords(domain: str = "akeana", source: str = "us", limit: int = 50):
    if not ser_mod or not SE_RANKING_API_KEY:
        raise HTTPException(503, "SE Ranking not configured")
    d = DOMAINS.get(domain, {})
    site_url = d.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    if not site_url:
        raise HTTPException(400, f"No URL configured for domain '{domain}'")
    try:
        return {"keywords": ser_mod.domain_keywords(site_url, source, limit)}
    except Exception as e:
        raise HTTPException(502, f"SE Ranking error: {e}")


@app.get("/api/se-ranking/competitors")
def se_ranking_competitors(domain: str = "akeana", source: str = "us"):
    if not ser_mod or not SE_RANKING_API_KEY:
        raise HTTPException(503, "SE Ranking not configured")
    d = DOMAINS.get(domain, {})
    site_url = d.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    if not site_url:
        raise HTTPException(400, f"No URL configured for domain '{domain}'")
    try:
        return {"competitors": ser_mod.domain_competitors(site_url, source)}
    except Exception as e:
        raise HTTPException(502, f"SE Ranking error: {e}")


@app.get("/api/se-ranking/backlinks")
def se_ranking_backlinks(domain: str = "akeana"):
    if not ser_mod or not SE_RANKING_API_KEY:
        raise HTTPException(503, "SE Ranking not configured")
    d = DOMAINS.get(domain, {})
    site_url = d.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    if not site_url:
        raise HTTPException(400, f"No URL configured for domain '{domain}'")
    try:
        return {
            "summary": ser_mod.backlinks_summary(site_url),
            "authority": ser_mod.domain_authority(site_url),
            "top_backlinks": ser_mod.backlinks_top(site_url),
            "anchors": ser_mod.backlinks_anchors(site_url),
            "referring_domains": ser_mod.backlinks_ref_domains(site_url),
        }
    except Exception as e:
        raise HTTPException(502, f"SE Ranking error: {e}")


# ── LinkedIn (Excel upload) ─────────────────────────────────────────────────

@app.post("/api/linkedin/upload")
async def linkedin_upload(file: UploadFile = File(...), type: str = Query("analytics")):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    try:
        if type == "followers":
            return linkedin.parse_linkedin_followers(content, file.filename or "")
        return linkedin.parse_linkedin_analytics(content, file.filename or "")
    except Exception as e:
        raise HTTPException(422, f"Failed to parse file: {e}")


# ── Export ────────────────────────────────────────────────────────────────────

@app.get("/api/export")
def export_report(domain: str = "rh", start: str = "", end: str = ""):
    start, end = _dates(start, end)
    d = _domain(domain)
    try:
        creds = get_credentials()
    except Exception as e:
        raise HTTPException(502, f"Auth error: {e}")

    gsc_sum = gsc.get_summary(creds, d["gsc_site"], start, end)
    gsc_q = gsc.get_top_queries(creds, d["gsc_site"], start, end, 20)
    gsc_p = gsc.get_top_pages(creds, d["gsc_site"], start, end, 20)

    ga4_sum, ga4_p, ga4_src = {}, [], []
    prop = d["ga4_property"]
    if prop:
        try:
            ga4_sum = ga4.get_summary(creds, prop, start, end)
            ga4_p = ga4.get_top_pages(creds, prop, start, end, 20)
            ga4_src = ga4.get_traffic_sources(creds, prop, start, end)
        except Exception:
            pass

    meta_camps = None
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if META_MARKETING_TOKEN and ad_account:
        try:
            meta_camps = meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
        except Exception:
            pass

    xlsx = build_report(domain, d["label"], start, end, gsc_sum, gsc_q, gsc_p, ga4_sum, ga4_p, ga4_src, meta_camps)
    filename = f"Report_{d['short']}_{start}_{end}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Meta Token Exchange ─────────────────────────────────────────────────

@app.get("/api/meta/exchange-token")
def meta_exchange_token(token: str = ""):
    """Exchange a short-lived token for a 60-day long-lived token."""
    if not token:
        raise HTTPException(400, "token parameter required")
    if not META_APP_ID or not META_APP_SECRET:
        raise HTTPException(400, "META_APP_ID and META_APP_SECRET must be set in environment variables")
    import requests
    resp = requests.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "fb_exchange_token": token,
    }, timeout=30)
    if not resp.ok:
        raise HTTPException(502, f"Facebook error: {resp.text}")
    data = resp.json()
    long_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 0)

    page_token = ""
    if long_token:
        try:
            pr = requests.get(f"https://graph.facebook.com/v21.0/me/accounts", params={
                "access_token": long_token,
                "fields": "id,name,access_token",
            }, timeout=30)
            if pr.ok:
                for page in pr.json().get("data", []):
                    if page["id"] == META_PAGE_ID:
                        page_token = page.get("access_token", "")
                        break
        except Exception:
            pass

    return {
        "long_lived_token": long_token,
        "expires_in_seconds": expires_in,
        "expires_in_days": round(expires_in / 86400, 1) if expires_in else "unknown",
        "page_token": page_token,
        "page_token_note": "This page token never expires. Use it as META_SOCIAL_TOKEN." if page_token else "Could not get page token.",
        "instructions": "Update these in Vercel: META_MARKETING_TOKEN = long_lived_token, META_SOCIAL_TOKEN = page_token (or long_lived_token if no page_token)",
    }


# ── Reports & Analytics ─────────────────────────────────────────────────────

@app.get("/api/reports/generate")
def reports_generate(period: str = "weekly", domain: str = "rh", start: str = "", end: str = ""):
    today = _today_ist()
    if not end:
        end = today.isoformat()
    if not start:
        days = 7 if period == "weekly" else 30
        start = (today - timedelta(days=days - 1)).isoformat()
    d = _domain(domain)
    out = {"domain": domain, "label": d["label"], "period": period, "start": start, "end": end}
    try:
        creds = get_credentials()
        try:
            out["gsc"] = gsc.get_summary(creds, d["gsc_site"], start, end)
        except Exception as e:
            out["gsc"] = {"error": str(e)}
        prop = d.get("ga4_property")
        if prop:
            try:
                out["ga4"] = ga4.get_summary(creds, prop, start, end)
            except Exception as e:
                out["ga4"] = {"error": str(e)}
    except Exception as e:
        out["auth_error"] = str(e)
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if META_MARKETING_TOKEN and ad_account:
        try:
            camps = meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
            spend = sum(float(c.get("spend") or 0) for c in camps)
            clicks = sum(int(c.get("clicks") or 0) for c in camps)
            impressions = sum(int(c.get("impressions") or 0) for c in camps)
            out["meta"] = {"campaigns": len(camps), "spend": round(spend, 2), "clicks": clicks, "impressions": impressions}
        except Exception as e:
            out["meta"] = {"error": str(e)}
    s_token, s_page_id = _meta_creds(domain)
    if s_token and s_page_id:
        try:
            out["social_fb"] = social.get_fb_comprehensive(s_token, s_page_id, start, end)
        except Exception as e:
            out["social_fb"] = {"error": str(e)}
        try:
            ig_id = social.get_ig_account(s_token, s_page_id)
            if ig_id:
                out["social_ig"] = social.get_ig_comprehensive(s_token, ig_id, start, end)
        except Exception as e:
            out["social_ig"] = {"error": str(e)}
    return out


@app.get("/api/reports/export")
def reports_export(period: str = "weekly", domain: str = "rh", start: str = "", end: str = "", format: str = "excel", mode: str = "client", purpose: str = "client", sections: str = ""):
    today = _today_ist()
    if not end:
        end = today.isoformat()
    if not start:
        days = 7 if period == "weekly" else 30
        start = (today - timedelta(days=days - 1)).isoformat()
    d = _domain(domain)
    data = reports_generate(period, domain, start, end)
    fmt = format.lower()
    base = f"Report_{d['short']}_{period}_{start}_{end}"

    if fmt == "html" and domain == "akeana":
        import akeana_report
        try:
            creds = get_credentials()
        except Exception:
            creds = None
        ake_cfg = DOMAINS.get("akeana", {})
        ga4_data = {}
        gsc_data = {}
        ga4_extra = {}
        if creds:
            prop = ake_cfg.get("ga4_property")
            site = ake_cfg.get("gsc_site")
            if prop:
                try:
                    ga4_data["summary"] = ga4.get_summary(creds, prop, start, end)
                except Exception:
                    pass
                try:
                    ga4_extra["traffic_sources"] = ga4.get_traffic_sources(creds, prop, start, end)
                except Exception:
                    pass
                try:
                    ga4_extra["landing_pages"] = ga4.get_landing_pages(creds, prop, start, end, 10)
                except Exception:
                    pass
                try:
                    ga4_extra["cities"] = ga4.get_city_breakdown(creds, prop, start, end, 10)
                except Exception:
                    pass
                try:
                    ga4_extra["devices"] = ga4.get_device_breakdown(creds, prop, start, end)
                except Exception:
                    pass
                try:
                    ga4_extra["ages"] = ga4.get_age_breakdown(creds, prop, start, end)
                except Exception:
                    pass
                try:
                    ga4_extra["weekly_users"] = ga4.get_weekly_users(creds, prop, start, end)
                except Exception:
                    pass
            if site:
                try:
                    gsc_data["summary"] = gsc.get_summary(creds, site, start, end)
                except Exception:
                    pass
                try:
                    gsc_data["queries"] = gsc.get_top_queries(creds, site, start, end, 50)
                except Exception:
                    pass
        html_content = akeana_report.generate_akeana_report(ga4_data, gsc_data, ga4_extra, start, end)
        return StreamingResponse(
            io.BytesIO(html_content.encode("utf-8")),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{base}.html"'},
        )

    if fmt == "html":
        import html_report
        import json as _json
        report_domains = ["rh", "pms", "aif"]
        try:
            creds = get_credentials()
        except Exception:
            creds = None

        month_buckets = html_report._month_ranges(start, end)
        all_monthly_data = {}
        api_errors = []

        def _err(month, dom, source, e):
            msg = str(e)
            msg = msg.replace("\n", " ")[:120]
            api_errors.append(f"{month} · {dom.upper()} · {source}: {msg}")

        if not creds:
            api_errors.append("Google credentials unavailable — GSC and GA4 skipped for all months")

        # Resolve per-domain Meta page tokens + IG ids ONCE (not per month),
        # and the YouTube channel subscribers ONCE, to cut redundant calls.
        dom_meta = {}
        for dom_key in report_domains:
            dom_cfg = DOMAINS.get(dom_key, {})
            info = {"manual": dom_cfg.get("meta_manual", False), "ptoken": None, "pid": None, "ig_id": None}
            if not info["manual"]:
                h_token, h_page_id = _meta_creds(dom_key)
                if h_token and h_page_id:
                    info["pid"] = h_page_id
                    try:
                        info["ptoken"] = social.resolve_page_token(h_token, h_page_id)
                        info["ig_id"] = social.get_ig_account(info["ptoken"], h_page_id)
                    except Exception as e:
                        _err("setup", dom_key, "Meta page", e)
            dom_meta[dom_key] = info

        yt_creds = None
        yt_subs = None
        if YOUTUBE_REFRESH_TOKEN:
            try:
                yt_creds = get_youtube_credentials()
                yt_subs = youtube.get_channel_stats(yt_creds).get("subscribers")
            except Exception as e:
                _err("setup", "rh", "YouTube channel", e)

        def fetch_entity(month_label, m_start, m_end, dom_key):
            dom_cfg = DOMAINS.get(dom_key, {})
            entity_data = {}
            errs = []
            def le(src, e):
                errs.append((month_label, dom_key, src, e))
            if creds:
                try:
                    entity_data["gsc"] = gsc.get_summary(creds, dom_cfg["gsc_site"], m_start, m_end)
                except Exception as e:
                    le("GSC", e)
                prop = dom_cfg.get("ga4_property")
                if prop:
                    try:
                        ga4_sum = ga4.get_summary(creds, prop, m_start, m_end)
                        try:
                            org = ga4.get_organic_summary(creds, prop, m_start, m_end)
                            ga4_sum["organic_sessions"] = org.get("organic_sessions", 0)
                            ga4_sum["organic_users"] = org.get("organic_users", 0)
                        except Exception as e:
                            le("GA4 organic", e)
                        try:
                            devs = ga4.get_device_breakdown(creds, prop, m_start, m_end)
                            tot = sum(int(d.get("sessions") or 0) for d in devs)
                            mob = sum(int(d.get("sessions") or 0) for d in devs
                                      if (d.get("deviceCategory") or "").lower() == "mobile")
                            ga4_sum["mobile_traffic_pct"] = round(mob / tot * 100, 1) if tot else None
                        except Exception as e:
                            le("GA4 device", e)
                        entity_data["ga4"] = ga4_sum
                    except Exception as e:
                        le("GA4", e)

            info = dom_meta.get(dom_key, {})
            if not info.get("manual"):
                ad_account = dom_cfg.get("meta_ad_account", "")
                if META_MARKETING_TOKEN and ad_account:
                    try:
                        # Account-level total (1 call) instead of per-campaign loop
                        entity_data["meta_ads"] = [meta.get_account_summary(META_MARKETING_TOKEN, ad_account, m_start, m_end)]
                    except Exception as e:
                        le("Meta Ads", e)
                if info.get("ptoken") and info.get("pid"):
                    try:
                        entity_data["social_fb"] = social.get_fb_comprehensive(info["ptoken"], info["pid"], m_start, m_end)
                    except Exception as e:
                        le("Facebook", e)
                    if info.get("ig_id"):
                        try:
                            entity_data["social_ig"] = social.get_ig_comprehensive(info["ptoken"], info["ig_id"], m_start, m_end, fast=True)
                        except Exception as e:
                            le("Instagram", e)

            if dom_key == "rh" and yt_creds is not None:
                try:
                    yt = youtube.get_monthly_summary(yt_creds, m_start, m_end)
                    yt["subscribers"] = yt_subs
                    entity_data["youtube"] = yt
                except Exception as e:
                    le("YouTube", e)

            return (month_label, dom_key, entity_data, errs)

        tasks = [(ml, ms, me, dk) for (ml, ms, me) in month_buckets for dk in report_domains
                 if DOMAINS.get(dk)]
        for ml, _ms, _me in month_buckets:
            all_monthly_data[ml] = {}
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=8) as ex:
            for ml, dk, entity_data, errs in ex.map(lambda t: fetch_entity(*t), tasks):
                all_monthly_data[ml][dk] = entity_data
                for (m, d, s, e) in errs:
                    _err(m, d, s, e)

        manual_doms = [DOMAINS[k]["label"] for k in report_domains
                       if DOMAINS.get(k, {}).get("meta_manual")]
        if manual_doms:
            api_errors.append("Manual entry (by design): social & ads for "
                              + ", ".join(manual_doms) + " — use Edit Data to fill.")

        report_mode = mode or purpose or "client"
        sec_list = [s.strip() for s in sections.split(",") if s.strip()] if sections else None
        html_content = html_report.generate_html_report(all_monthly_data, start, end, report_mode=report_mode, api_status=api_errors, sections=sec_list)
        return StreamingResponse(
            io.BytesIO(html_content.encode("utf-8")),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{base}.html"'},
        )

    if fmt == "csv":
        import csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Section", "Metric", "Value"])
        for section in ("gsc", "ga4", "meta", "social_fb", "social_ig"):
            v = data.get(section)
            if not isinstance(v, dict):
                continue
            for k, val in v.items():
                w.writerow([section, k, val])
        return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="{base}.csv"'})

    if fmt == "pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            raise HTTPException(400, "PDF export requires reportlab. Use Excel or CSV instead.")
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"{d['label']} — {period.title()} Report", styles["Title"]),
                 Paragraph(f"Period: {start} to {end}", styles["Italic"]), Spacer(1, 12)]
        for section_key, label in [("gsc", "Search Console"), ("ga4", "Google Analytics"),
                                    ("meta", "Meta Ads"), ("social_fb", "Facebook"), ("social_ig", "Instagram")]:
            v = data.get(section_key)
            if not isinstance(v, dict) or "error" in v:
                continue
            story.append(Paragraph(label, styles["Heading2"]))
            rows = [["Metric", "Value"]] + [[str(k), str(val)] for k, val in v.items()]
            t = Table(rows, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))
        doc.build(story)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'})

    # excel default
    try:
        creds = get_credentials()
        gsc_sum = gsc.get_summary(creds, d["gsc_site"], start, end)
        gsc_q = gsc.get_top_queries(creds, d["gsc_site"], start, end, 20)
        gsc_p = gsc.get_top_pages(creds, d["gsc_site"], start, end, 20)
        ga4_sum, ga4_p, ga4_src = {}, [], []
        prop = d.get("ga4_property")
        if prop:
            try:
                ga4_sum = ga4.get_summary(creds, prop, start, end)
                ga4_p = ga4.get_top_pages(creds, prop, start, end, 20)
                ga4_src = ga4.get_traffic_sources(creds, prop, start, end)
            except Exception:
                pass
        meta_camps = None
        ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
        if META_MARKETING_TOKEN and ad_account:
            try:
                meta_camps = meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
            except Exception:
                pass
        xlsx = build_report(domain, d["label"], start, end, gsc_sum, gsc_q, gsc_p, ga4_sum, ga4_p, ga4_src, meta_camps)
        return StreamingResponse(io.BytesIO(xlsx),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{base}.xlsx"'})
    except Exception as e:
        raise HTTPException(502, f"Export error: {e}")


# ── Report Room ─────────────────────────────────────────────────────────────

def _compute_comparison_dates(start_str: str, end_str: str, compare: str):
    """Return (compare_start, compare_end) as ISO strings, or (None, None)."""
    if compare == "none":
        return None, None
    s = date.fromisoformat(start_str)
    e = date.fromisoformat(end_str)
    duration = (e - s).days + 1
    if compare == "previous_month":
        # Shift both dates back ~1 month (28 days keeps it simple, no dateutil)
        cs = s.replace(month=s.month - 1) if s.month > 1 else s.replace(year=s.year - 1, month=12)
        ce = e.replace(month=e.month - 1) if e.month > 1 else e.replace(year=e.year - 1, month=12)
        # Handle day overflow (e.g. March 31 -> Feb 28)
        import calendar
        for dt_name in ('cs', 'ce'):
            dt = cs if dt_name == 'cs' else ce
            max_day = calendar.monthrange(dt.year, dt.month)[1]
            if dt_name == 'cs':
                cs = dt.replace(day=min(s.day, max_day))
            else:
                ce = dt.replace(day=min(e.day, max_day))
        return cs.isoformat(), ce.isoformat()
    else:  # previous_period
        ce = s - timedelta(days=1)
        cs = ce - timedelta(days=duration - 1)
        return cs.isoformat(), ce.isoformat()


def _calc_delta(current_val, previous_val):
    """Calculate delta between two numeric values."""
    if previous_val is None or current_val is None:
        return None
    try:
        c = float(current_val)
        p = float(previous_val)
    except (TypeError, ValueError):
        return None
    diff = c - p
    pct = round((diff / p) * 100, 2) if p != 0 else (100.0 if c > 0 else 0.0)
    direction = "stable" if abs(pct) <= 5 else ("up" if diff > 0 else "down")
    return {"value": round(diff, 2), "pct": pct, "direction": direction}


def _calc_deltas(current: dict, previous: dict, keys: list):
    """Calculate deltas for a list of metric keys."""
    if not previous:
        return None
    return {k: _calc_delta(current.get(k, 0), previous.get(k, 0)) for k in keys}


def _fetch_gsc_channel(creds, d, start, end):
    site = d["gsc_site"]
    summary = gsc.get_summary(creds, site, start, end)
    top_queries = gsc.get_top_queries(creds, site, start, end, 20)
    top_pages = gsc.get_top_pages(creds, site, start, end, 20)
    current = {
        "clicks": summary.get("clicks", 0),
        "impressions": summary.get("impressions", 0),
        "ctr": summary.get("ctr", 0),
        "position": summary.get("position", 0),
    }
    return current, top_queries, top_pages


def _fetch_ga4_channel(creds, d, start, end):
    prop = d.get("ga4_property")
    if not prop:
        return None, [], []
    summary = ga4.get_summary(creds, prop, start, end)
    top_pages = ga4.get_top_pages(creds, prop, start, end, 20)
    sources = ga4.get_traffic_sources(creds, prop, start, end)
    current = {
        "sessions": summary.get("sessions", 0),
        "users": summary.get("users", 0),
        "pageviews": summary.get("pageviews", 0),
        "bounce_rate": summary.get("bounce_rate", 0),
    }
    return current, top_pages, sources


def _fetch_meta_channel(domain, start, end):
    ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
    if not META_MARKETING_TOKEN or not ad_account:
        return None, []
    camps = meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
    spend = sum(float(c.get("spend") or 0) for c in camps)
    clicks = sum(int(c.get("clicks") or 0) for c in camps)
    impressions = sum(int(c.get("impressions") or 0) for c in camps)
    leads = sum(int(c.get("leads") or c.get("results") or 0) for c in camps)
    ctr = round((clicks / impressions) * 100, 2) if impressions else 0
    cpl = round(spend / leads, 2) if leads else 0
    current = {
        "spend": round(spend, 2), "impressions": impressions,
        "clicks": clicks, "ctr": ctr, "leads": leads, "cpl": cpl,
    }
    return current, camps


def _fetch_social_channel(domain, start, end):
    s_token, s_page_id = _meta_creds(domain)
    if not s_token or not s_page_id:
        return None
    fb = social.get_fb_comprehensive(s_token, s_page_id, start, end)
    ig_data = {}
    try:
        ig_id = social.get_ig_account(s_token, s_page_id)
        if ig_id:
            ig_data = social.get_ig_comprehensive(s_token, ig_id, start, end)
    except Exception:
        pass
    return {"fb": fb, "ig": ig_data}


def _fetch_youtube_channel():
    creds = get_youtube_credentials()
    stats = youtube.get_channel_stats(creds)
    current = {
        "views": stats.get("views", stats.get("viewCount", 0)),
        "subscribers": stats.get("subscribers", stats.get("subscriberCount", 0)),
        "videos": stats.get("videos", stats.get("videoCount", 0)),
    }
    return current


def _build_highlights(channels_data: dict):
    """Scan all channel deltas and categorize metrics."""
    improved, dropped, stable = [], [], []
    label_map = {
        "gsc": "GSC", "ga4": "GA4", "meta": "Meta", "social": "Social", "youtube": "YouTube"
    }
    for ch_name, ch_data in channels_data.items():
        delta = ch_data.get("delta")
        current = ch_data.get("current")
        previous = ch_data.get("previous")
        if not delta or not previous:
            continue
        prefix = label_map.get(ch_name, ch_name.upper())
        for metric, d in delta.items():
            if not d or not isinstance(d, dict):
                continue
            entry = {
                "metric": f"{prefix} {metric.replace('_', ' ').title()}",
                "current": current.get(metric, 0) if isinstance(current, dict) else 0,
                "previous": previous.get(metric, 0) if isinstance(previous, dict) else 0,
                "change_pct": d.get("pct", 0),
            }
            direction = d.get("direction", "stable")
            if direction == "up":
                improved.append(entry)
            elif direction == "down":
                dropped.append(entry)
            else:
                stable.append(entry)
    improved.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    dropped.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return {"improved": improved, "dropped": dropped, "stable": stable}


def _generate_insights(channels_data: dict):
    """Generate automatic insights based on data patterns."""
    insights = []
    gsc_d = channels_data.get("gsc", {}).get("delta") or {}
    ga4_d = channels_data.get("ga4", {}).get("delta") or {}
    meta_d = channels_data.get("meta", {}).get("delta") or {}
    gsc_c = channels_data.get("gsc", {}).get("current") or {}

    # Impressions up but clicks down → CTR needs attention
    imp_d = gsc_d.get("impressions", {})
    click_d = gsc_d.get("clicks", {})
    if imp_d and click_d:
        if imp_d.get("direction") == "up" and click_d.get("direction") == "down":
            insights.append({"type": "warning", "title": "CTR needs attention",
                             "description": "Search impressions are up but clicks declined. Review title tags and meta descriptions for better click-through.", "severity": "medium"})

    # Clicks up but leads down
    meta_click_d = meta_d.get("clicks", {})
    meta_lead_d = meta_d.get("leads", {})
    if meta_click_d and meta_lead_d:
        if meta_click_d.get("direction") == "up" and meta_lead_d.get("direction") == "down":
            insights.append({"type": "warning", "title": "Landing page review needed",
                             "description": "Ad clicks are increasing but lead conversions dropped. Landing page experience may need optimization.", "severity": "medium"})

    # Spend similar but CPL up
    spend_d = meta_d.get("spend", {})
    cpl_d = meta_d.get("cpl", {})
    if spend_d and cpl_d:
        if spend_d.get("direction") in ("stable", "up") and cpl_d.get("direction") == "up":
            insights.append({"type": "warning", "title": "Audience fatigue possible",
                             "description": "Cost per lead is rising while spend is steady or increasing. Consider refreshing ad creatives or audiences.", "severity": "medium"})

    # High impressions but low CTR in SEO
    if gsc_c.get("impressions", 0) > 1000 and gsc_c.get("ctr", 0) < 2:
        insights.append({"type": "opportunity", "title": "Title/meta optimization opportunity",
                         "description": "High search impressions with low CTR suggest title tags and meta descriptions could be improved to drive more clicks.", "severity": "low"})

    # GA4 sessions up but bounce rate also up
    sess_d = ga4_d.get("sessions", {})
    bounce_d = ga4_d.get("bounce_rate", {})
    if sess_d and bounce_d:
        if sess_d.get("direction") == "up" and bounce_d.get("direction") == "up":
            insights.append({"type": "warning", "title": "Traffic quality concern",
                             "description": "Sessions are growing but bounce rate is also increasing. Review traffic sources for quality.", "severity": "medium"})

    # GA4 users down
    users_d = ga4_d.get("users", {})
    if users_d and users_d.get("direction") == "down" and abs(users_d.get("pct", 0)) > 15:
        insights.append({"type": "critical", "title": "Significant user decline",
                         "description": f"Users dropped by {abs(users_d.get('pct', 0))}%. Investigate traffic source changes.", "severity": "high"})

    # Meta spend up but impressions down
    meta_imp_d = meta_d.get("impressions", {})
    if spend_d and meta_imp_d:
        if spend_d.get("direction") == "up" and meta_imp_d.get("direction") == "down":
            insights.append({"type": "warning", "title": "Ad efficiency declining",
                             "description": "Ad spend is increasing but impressions are dropping. CPM may be rising due to competition or audience saturation.", "severity": "medium"})

    if not insights:
        insights.append({"type": "info", "title": "Stable performance",
                         "description": "No major anomalies detected. Performance is generally consistent with the comparison period.", "severity": "low"})
    return insights


@app.get("/api/reports/room")
def reports_room(
    domain: str = "rh",
    start: str = "",
    end: str = "",
    compare: str = "previous_period",
    channels: str = "gsc,ga4,meta,social,youtube",
):
    today = _today_ist()
    if not end:
        end = today.isoformat()
    if not start:
        start = (today - timedelta(days=29)).isoformat()
    if compare not in ("previous_period", "previous_month", "none"):
        raise HTTPException(400, "compare must be one of: previous_period, previous_month, none")

    d = _domain(domain)
    compare_start, compare_end = _compute_comparison_dates(start, end, compare)
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    channels_data = {}

    creds = None
    try:
        creds = get_credentials()
    except Exception:
        pass

    gsc_keys = ["clicks", "impressions", "ctr", "position"]
    ga4_keys = ["sessions", "users", "pageviews", "bounce_rate"]
    meta_keys = ["spend", "impressions", "clicks", "ctr", "leads", "cpl"]

    # GSC
    if "gsc" in channel_list and creds:
        try:
            current, top_queries, top_pages = _fetch_gsc_channel(creds, d, start, end)
            prev = None
            if compare_start:
                try:
                    prev, _, _ = _fetch_gsc_channel(creds, d, compare_start, compare_end)
                except Exception:
                    pass
            channels_data["gsc"] = {
                "current": current, "previous": prev,
                "delta": _calc_deltas(current, prev, gsc_keys),
                "top_queries": top_queries, "top_pages": top_pages,
            }
        except Exception as e:
            channels_data["gsc"] = {"error": str(e), "current": None, "previous": None, "delta": None}

    # GA4
    if "ga4" in channel_list and creds:
        try:
            current, top_pages, sources = _fetch_ga4_channel(creds, d, start, end)
            if current is None:
                channels_data["ga4"] = {"error": "No GA4 property configured", "current": None, "previous": None, "delta": None}
            else:
                prev = None
                if compare_start:
                    try:
                        prev, _, _ = _fetch_ga4_channel(creds, d, compare_start, compare_end)
                    except Exception:
                        pass
                channels_data["ga4"] = {
                    "current": current, "previous": prev,
                    "delta": _calc_deltas(current, prev, ga4_keys),
                    "top_pages": top_pages, "traffic_sources": sources,
                }
        except Exception as e:
            channels_data["ga4"] = {"error": str(e), "current": None, "previous": None, "delta": None}

    # Meta
    if "meta" in channel_list:
        try:
            current, campaigns = _fetch_meta_channel(domain, start, end)
            if current is None:
                channels_data["meta"] = {"error": "Meta not configured", "current": None, "previous": None, "delta": None}
            else:
                prev = None
                if compare_start:
                    try:
                        prev, _ = _fetch_meta_channel(domain, compare_start, compare_end)
                    except Exception:
                        pass
                channels_data["meta"] = {
                    "current": current, "previous": prev,
                    "delta": _calc_deltas(current, prev, meta_keys),
                    "campaigns": campaigns,
                }
        except Exception as e:
            channels_data["meta"] = {"error": str(e), "current": None, "previous": None, "delta": None}

    # Social
    if "social" in channel_list:
        try:
            current = _fetch_social_channel(domain, start, end)
            if current is None:
                channels_data["social"] = {"error": "Social not configured", "current": None, "previous": None, "delta": None}
            else:
                prev = None
                if compare_start:
                    try:
                        prev = _fetch_social_channel(domain, compare_start, compare_end)
                    except Exception:
                        pass
                channels_data["social"] = {
                    "current": current, "previous": prev, "delta": None,
                }
        except Exception as e:
            channels_data["social"] = {"error": str(e), "current": None, "previous": None, "delta": None}

    # YouTube
    if "youtube" in channel_list:
        try:
            current = _fetch_youtube_channel()
            # YouTube stats are typically lifetime/current, no date range comparison
            channels_data["youtube"] = {
                "current": current, "previous": None, "delta": None,
            }
        except Exception as e:
            channels_data["youtube"] = {"error": str(e), "current": None, "previous": None, "delta": None}

    highlights = _build_highlights(channels_data)
    insights = _generate_insights(channels_data)

    return {
        "domain": domain, "label": d["label"], "start": start, "end": end,
        "compare_start": compare_start, "compare_end": compare_end,
        "channels": channels_data,
        "highlights": highlights,
        "insights": insights,
    }


@app.post("/api/reports/room/summary")
def reports_room_summary(
    domain: str = "rh",
    start: str = "",
    end: str = "",
    compare: str = "previous_period",
    channels: str = "gsc,ga4,meta,social,youtube",
):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    room_data = reports_room(domain, start, end, compare, channels)
    sys_prompt = (
        "You are a senior digital marketing performance analyst for Indian financial services. "
        "Given the report data below, produce a sharp, insight-driven executive summary as JSON.\n\n"
        "ANALYSIS APPROACH:\n"
        "- Compare current period vs previous period — calculate % changes mentally\n"
        "- Identify the STORY behind the numbers, not just the numbers themselves\n"
        "- Flag anomalies: sudden spikes/drops, unusual patterns, seasonal effects\n"
        "- Connect dots across channels: did SEO gains correlate with social engagement?\n"
        "- Think about ACTIONABILITY: what can the team actually DO with each insight?\n\n"
        "JSON FIELDS (all required):\n"
        "- what_improved: specific metrics that improved with actual numbers and % changes\n"
        "- what_dropped: specific metrics that declined with actual numbers and % changes — include WHY if inferable\n"
        "- what_stable: metrics that held steady — note if stability is good (retention) or concerning (stagnation)\n"
        "- main_win: the single biggest positive takeaway — be specific about the metric, the magnitude, and the business impact\n"
        "- main_concern: the single biggest concern — include what could happen if unaddressed\n"
        "- key_opportunity: the highest-ROI action to take NOW — specific, not generic\n"
        "- recommended_focus: what to prioritize in the next reporting period — tie to a specific channel/metric\n"
        "- executive_summary: 2-3 sentence boardroom-ready summary — lead with the most important finding, quantify impact\n"
        "- confidence_score: integer 0-100 — overall digital marketing health. "
        "80+: strong momentum. 60-79: stable with opportunities. 40-59: needs attention. <40: urgent intervention.\n"
        "- channel_grades: object with keys for each active channel (seo, social, ads, youtube, email) — "
        "each is {grade: 'A'/'B'/'C'/'D'/'F', trend: 'improving'/'stable'/'declining', one_liner: string}\n"
        "- next_steps: array of 4-5 objects each with 'title', 'description', 'priority' (high/medium/low), "
        "'channel' (which channel this applies to), 'expected_impact' (what improvement to expect)\n"
        "- risks: array of 1-3 risks to monitor with 'risk' and 'mitigation' fields\n\n"
        "RULES:\n"
        "- Reference ACTUAL numbers from the data — never make up metrics\n"
        "- Use Indian Rupees (₹/INR) for all currency figures, never dollars\n"
        "- If data is missing for a channel, say 'Data not available for this period' — don't fabricate\n"
        "- Be a sharp analyst, not a cheerleader — call out problems clearly\n"
        "- Use em dash (—) for missing values, not zeros"
    )
    import json
    user_msg = f"Report room data for {room_data.get('label', domain)} ({start} to {end}):\n\n{json.dumps(room_data, default=str)}"

    if web_search:
        live = web_search.search_market_context()
        if live:
            user_msg += f"\n\nCURRENT MARKET CONTEXT (live — use to contextualize performance against market conditions):\n{live}\n"
        news = web_search.search_finance_news()
        if news:
            user_msg += f"\n\nLATEST FINANCE NEWS (use to add market context to the summary):\n{news}\n"

    try:
        summary = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=5000, temperature=0.6)
        return {"domain": domain, "label": room_data.get("label"), "start": start, "end": end, "summary": summary}
    except Exception as e:
        raise HTTPException(502, f"AI summary generation failed: {e}")


# ── Content Calendar ─────────────────────────────────────────────────────────

try:
    import ai as ai_mod
except Exception:
    ai_mod = None
from pydantic import BaseModel

_calendars: dict = {}  # key: f"{domain}:{month}" -> list of items
_ideas_state = {"last_check": 0, "available": 0}
_ideas_history: dict = {}  # key: domain -> list of past idea titles/descriptions
_calendar_history: dict = {}  # key: domain -> list of past post titles/captions
_generation_level: dict = {}  # key: domain -> int (increments each generation)


def _push_history(store: dict, domain: str, items: list, key_field: str = "title"):
    """Track up to last 200 items per domain to avoid repetition."""
    if domain not in store:
        store[domain] = []
    for it in items or []:
        if isinstance(it, dict):
            t = it.get(key_field) or it.get("caption") or it.get("description") or ""
            sw = it.get("swimlane", "")
            if t:
                store[domain].append({"title": str(t)[:200], "swimlane": sw})
    store[domain] = store[domain][-200:]


def _history_context(store: dict, domain: str, limit: int = 60) -> str:
    """Build a 'do NOT repeat' block from past items."""
    past = store.get(domain, [])[-limit:]
    if not past:
        return ""
    lines = []
    for p in past:
        sw = f" [{p['swimlane']}]" if p.get("swimlane") else ""
        lines.append(f"- {p['title']}{sw}")
    return "\n".join(lines)


def _level_up(domain: str) -> int:
    _generation_level[domain] = _generation_level.get(domain, 0) + 1
    return _generation_level[domain]


class CalendarRequest(BaseModel):
    domain: str = "rh"
    month: str = ""
    context: str = ""


def _unwrap_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "posts", "calendar", "ideas", "data", "result", "results"):
            v = data.get(key)
            if isinstance(v, list):
                return v
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


RH_CONTENT_DNA = """
RIGHT HORIZONS CONTENT DNA (learned from actual RH SM calendars Apr/May/Jun 2026)

FOUR CONTENT PILLARS ("Swimlanes") — every post must align to one:
1. Retirement Planning (35% of posts) — MOST IMPORTANT PILLAR
   Themes: Retirement at 50/55/60, corpus calculations (₹4-5 Cr typical), inflation
   doubling costs in 12 years, healthcare corpus (₹20-30L), SWP for tax-efficient
   income, equity allocation in 50s, PF/PPF gap analysis, post-retirement income
   planning, withdrawal strategies. Audience: pre-retirees, 45-60 age bracket.

2. NRI Wealth (27% of posts)
   Themes: NRI tax residency rules, Form 13 / Section 197 for lower TDS, GIFT City
   AIFs, DTAA benefits, repatriation, property sales taxation, Indian-sourced income
   (rent/dividends/interest), FEMA compliance, NRE/NRO accounts. Audience: NRIs with
   Indian assets/income above ₹15L.

3. ESOPs (15% of posts)
   Themes: Vesting strategies (3-5 year cliffs), ESOP tax planning at exercise &
   sale, concentration risk in employer stock, liquidity event planning, startup
   vs listed company ESOPs, perquisite tax vs capital gains. Audience: senior tech
   professionals, startup employees, CXOs.

4. Family Office (12% of posts)
   Themes: Family governance, family agreements (ownership/roles/exit strategies),
   multi-asset family portfolios, geopolitical impact (rupee/dollar), estate
   planning, generational wealth transfer, trustees, succession. Audience: UHNI
   business families, ₹50Cr+ AUM.

POST TYPES (in descending frequency):
- Carousel (42%): 4-5 slide deep dives. Slide 1 hook, Slide 2-4 substance with
  numbers/bullets, Final slide takeaway/CTA.
- Static Image (38%): Single image. Headline + 3-5 bullet points + brand handle.
- Reel (10%): Story-driven scenes ("Meet Mr. X — the busy professional..."),
  relatable working professional persona, emotional hook then financial insight.
- Poll (10%): Engagement-driven question with 2-4 options.

VOICE & TONE (NON-NEGOTIABLE):
- Advisory, not promotional. Never "buy now" or "limited offer".
- Data-driven with concrete numbers: "₹4-5 Cr corpus", "₹15L+ income",
  "12-year inflation doubling", "3-5 year vesting", "₹20-30L healthcare".
- Calm, mature, observational. Phrases like "tends to surface...", "a few
  financial realities apply...", "not as isolated topics, but as..."
- Educational disclaimer-friendly. NO returns guarantees, NO stock tips, NO
  market timing claims.
- Acknowledges complexity. Avoids hype words ("game-changing", "secret",
  "shocking", "you won't believe").
- Indian financial context throughout: SEBI, GIFT City, PMS, AIF, SWP, SIP,
  PPF, EPF, NPS, Form 13, Section 197, DTAA.

STRUCTURE PATTERNS FOR CAPTIONS:
- Carousel slides separated by "Slide 1: ... Slide 2: ..." headings
- Static image captions: Title line, then "- bullet - bullet - bullet"
- Reels: "[Scene 1: ...]" stage directions, dialogue, then financial takeaway

DESCRIPTION PATTERN (the longer caption posted with the visual):
- Opens with an observational statement, not a question
- Acknowledges the audience is already sophisticated
- Lists 2-3 areas the post covers (not as advice, as observations)
- No CTAs to "DM us" or "book a call" in body — handles/site only

HASHTAG PATTERN (12-15 tags, all educational/topical):
Must include: #RightHorizons + #WealthManagement + #FinancialPlanning + at
least one swimlane tag (#RetirementPlanning / #NRIInvesting / #ESOPs /
#FamilyOffice) + 4-6 topical hashtags. Never use generic hype hashtags
(#trending, #viral, #money goals).

DISCLAIMERS (when content discusses returns/products):
"This is for educational purposes only. Not investment advice. Consult a
SEBI-registered advisor before making decisions."
"""


CAL_SYSTEM = (
    "You are the Head of Content Strategy for Right Horizons (Indian wealth/PMS/AIF firm "
    "serving HNIs, NRIs, senior tech professionals, and UHNI business families). You write "
    "at CEO/CIO level — every post must read like it came from a Partner at the firm, not "
    "an intern. Vague, generic, or recycled advice is unacceptable.\n\n"
    + RH_CONTENT_DNA +
    "\n\nCALENDAR STRUCTURE (match the firm's actual operating cadence — DO NOT deviate):\n"
    "- Posts go on Mon/Wed/Fri primarily; occasional Tue/Thu. Sat = Case Study placeholder. "
    "Sun = OFF. Some Mondays = 'Leadership Quote/Video from RM' placeholder.\n"
    "- Target 12-14 active posts in the month + 3-4 'Case Study' placeholder rows + "
    "2-3 'Leadership Quote/Video from RM' placeholder rows.\n"
    "- For placeholders: set type='', swimlane='', caption='Case Study' or 'Leadership "
    "Quote/Video from RM', description=''. Still include the date and day.\n\n"
    "CAPTION QUALITY BAR (this is what separates basic from CEO-level — STUDY THESE PATTERNS):\n"
    "CAROUSEL captions MUST be written slide-by-slide with full slide text, e.g.:\n"
    "  'Slide 1: At 55, the plan that worked at 40 starts to quietly fail.\n"
    "   Slide 2: Equity allocation that felt aggressive at 40 now feels reckless. Three "
    "things change: time horizon shrinks, sequence-of-returns risk shows up, healthcare "
    "inflation compounds at 14%.\n"
    "   Slide 3: The 60/40 split everyone quotes assumes a US-style 4% withdrawal. In "
    "India, that math breaks. SWP-led 3.5% with a 5-year debt bucket holds up better.\n"
    "   Slide 4: A ₹4.2 Cr corpus at 55, structured right, produces ₹2.1L/month inflation-"
    "adjusted for 35 years. Same corpus, wrong structure — fails by year 22.\n"
    "   Slide 5: Three questions to ask your advisor this week.'\n\n"
    "STATIC IMAGE captions: Headline + 3-5 punchy supporting lines. Use specific numbers, "
    "named regulations (Form 13, Section 197, DTAA, FEMA), city/country specifics.\n\n"
    "REEL captions: Scene-by-scene with [Scene 1: ...] directions, dialogue, then the "
    "financial reveal. Build a relatable working professional persona.\n\n"
    "POLL captions: Sharp question + 3-4 options that themselves teach something.\n\n"
    "DESCRIPTION RULES (the longer post body, 80-150 words):\n"
    "- Opens with an OBSERVATION, never a question.\n"
    "- Cites a concrete data point (₹ amount, regulation reference, age bracket, year, %).\n"
    "- Acknowledges 2-3 sub-areas the post covers as observations, not advice.\n"
    "- Ends with a soft handle reference ('@righthorizons') — NEVER 'DM us' or 'book now'.\n\n"
    "HASHTAGS: 12-15 educational tags. Always include #RightHorizons + #WealthManagement + "
    "swimlane tag + 6-8 specific topical tags. NEVER #trending #viral #moneygoals.\n\n"
    "VARIETY MANDATE (CRITICAL — you must NOT produce a generic Indian-finance calendar):\n"
    "- For EACH post, choose a DIFFERENT narrative device: case study, myth-buster, "
    "regulatory deep-dive, mistake post-mortem, age-bracket walkthrough, before/after "
    "math, persona-driven scenario, contrarian take, framework introduction, FAQ format.\n"
    "- For EACH post, anchor in a SPECIFIC angle: a city (Dubai/Singapore/Bangalore), an "
    "age (52/58/63), a regulation just changed, a market event from this week, a number "
    "from a recent SEBI/RBI/CBDT circular, a profession (cardiologist, founder, CXO).\n"
    "- Use the LATEST MARKET CONTEXT, FINANCE NEWS, and GOOGLE TRENDS provided below to "
    "ground at least 3-4 posts in current events from this month.\n\n"
    "OUTPUT FORMAT (strict JSON array — match the firm's xlsx schema exactly):\n"
    "Each object: {\n"
    "  'date': 'YYYY-MM-DD',\n"
    "  'day': 'Monday/Tuesday/...',\n"
    "  'approval_status': 'Waiting for content approval' (for active posts) or '' (placeholders),\n"
    "  'type': 'Carousel' | 'Static Image' | 'Reel' | 'Poll' | 'Gif' | '' (for placeholders),\n"
    "  'swimlane': 'Retirement Planning' | 'NRI' | 'ESOPs' | 'Family Office' | '' (placeholders),\n"
    "  'caption': full slide-by-slide caption (for carousels) or headline+bullets (image) or "
    "scene script (reel) or question+options (poll) or 'Case Study'/'Leadership Quote/Video "
    "from RM' for placeholders,\n"
    "  'description': 80-150 word post body following the description rules above,\n"
    "  'hashtags': '#tag1 #tag2 ...' as a single string of 12-15 tags,\n"
    "  'design_notes': brief visual direction (e.g. 'Hero number ₹4.2 Cr centered, charcoal "
    "bg, mint accent on key stats'),\n"
    "  'references': any source URL or note for fact-checking (regulation, news article, "
    "trend keyword from the live context), or '' if none\n"
    "}\n\n"
    'RETURN: a JSON object {"items": [...]} where items is the array of 18-22 row objects '
    "covering the entire month (active posts + placeholders + off-day skips combined)."
)


@app.post("/api/calendar/generate")
def calendar_generate(req: CalendarRequest):
    if not ai_mod:
        raise HTTPException(500, "AI module failed to load")
    if not req.month:
        raise HTTPException(400, "month required (YYYY-MM)")
    domain_label = DOMAINS.get(req.domain, {}).get("label", req.domain)
    level = _level_up(req.domain)
    sys_prompt = CAL_SYSTEM.replace("{domain}", domain_label).replace("{month}", req.month)
    user = f"Generate the calendar for {domain_label}, month {req.month}.\n\n"
    user += f"GENERATION LEVEL: {level} (each level must go deeper / more specialized than the last)\n"
    user += "LEVEL-UP RULES:\n"
    user += "- Level 1-3: foundational topics (corpus basics, vesting basics, tax residency basics)\n"
    user += "- Level 4-7: intermediate angles (corpus vs SWP math, ESOP exit waterfalls, NRI DTAA optimization)\n"
    user += "- Level 8+: advanced/niche (estate freezes, GIFT City FoF structures, ESOP+RSU dual-track, family LLP vs Trust)\n"
    user += "Pick angles appropriate for current level. NEVER use the exact angle of any past item.\n\n"

    import random
    _devices = ["case study", "myth-buster", "regulatory deep-dive", "mistake post-mortem",
                "age-bracket walkthrough", "before/after math", "persona-driven scenario",
                "contrarian take", "framework introduction", "FAQ format", "checklist",
                "decision tree", "data-led explainer", "what-if scenario"]
    _personas = ["Bangalore CTO with vested ESOPs", "Dubai-based cardiologist returning to India",
                 "Mumbai founder post-exit", "Singapore-based banker with India property",
                 "Pune family office trustee", "Hyderabad startup CFO", "London-based NRI cardiologist",
                 "Chennai retired PSU executive", "Delhi second-generation business family",
                 "US-based tech VP with RSUs and ESOPs"]
    _angles = ["sequence-of-returns risk", "currency mismatch", "regulatory just-changed",
               "concentration risk", "tax timing", "estate transition", "withdrawal mechanics",
               "DTAA optimization", "liquidity event planning", "intergenerational gift structuring"]
    _devices_pick = random.sample(_devices, 6)
    _personas_pick = random.sample(_personas, 4)
    _angles_pick = random.sample(_angles, 4)
    user += "VARIETY SEED FOR THIS GENERATION (use these as starting points — do not repeat across posts):\n"
    user += f"- Narrative devices to lean on: {', '.join(_devices_pick)}\n"
    user += f"- Personas to weave in (at least 3 of these): {', '.join(_personas_pick)}\n"
    user += f"- Specific angles to anchor posts: {', '.join(_angles_pick)}\n\n"

    past = _history_context(_calendar_history, req.domain, limit=80)
    if past:
        user += "DO NOT REPEAT THESE PAST POSTS (vary the angle, the numbers, the specifics):\n"
        user += past + "\n\nProduce ALL-NEW angles. If a swimlane needs to be covered again, "
        user += "shift the sub-topic, audience segment, age bracket, or numerical example.\n"
    if req.context:
        user += f"\n\nAdditional context:\n{req.context}"

    if web_search:
        live = web_search.search_market_context()
        if live:
            user += f"\n\nLATEST MARKET CONTEXT (live web search — reference current events, rates, and indices):\n{live}\n"
        news = web_search.search_finance_news()
        if news:
            user += f"\n\nLATEST FINANCE NEWS (from Moneycontrol, ET Money, LiveMint — weave current events into posts):\n{news}\n"
    if google_trends:
        gt = google_trends.finance_trends_context()
        if gt:
            user += f"\n\nGOOGLE TRENDS — INDIA (align post topics with what people are actually searching):\n{gt}\n"

    if len(user) > 25000:
        user = user[:25000] + "\n\n[context trimmed for length]"

    try:
        items = ai_mod.chat_json(sys_prompt, user, max_tokens=12000, temperature=0.75)
        items = _unwrap_items(items)
        _calendars[f"{req.domain}:{req.month}"] = items
        _push_history(_calendar_history, req.domain, items if isinstance(items, list) else [], key_field="title")
        return {"items": items, "month": req.month, "domain": req.domain, "level": level}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.get("/api/calendar/get")
def calendar_get(domain: str = "rh", month: str = ""):
    return {"items": _calendars.get(f"{domain}:{month}", []), "domain": domain, "month": month}


@app.post("/api/calendar/save")
def calendar_save(payload: dict = Body(...)):
    domain = payload.get("domain", "rh")
    month = payload.get("month", "")
    items = payload.get("items", [])
    if not month:
        raise HTTPException(400, "month required")
    _calendars[f"{domain}:{month}"] = items
    return {"ok": True}


@app.get("/api/calendar/export.csv")
def calendar_export_csv(domain: str = "rh", month: str = ""):
    import csv
    items = _calendars.get(f"{domain}:{month}", [])
    if not items:
        raise HTTPException(404, "No calendar found for this domain/month — generate it first.")
    buf = io.StringIO()
    cols = ["DATE", "DAY", "Approval Status", "POST TYPE", "Aligned Swimlane",
            "CAPTION/Image Copy", "Design Notes", "DESCRIPTION", "HASHTAGS",
            "REFERENCES", "IMAGE", "CLIENT FEEDBACK"]
    w = csv.writer(buf)
    w.writerow(cols)
    for it in items:
        if not isinstance(it, dict):
            continue
        w.writerow([
            it.get("date", ""),
            it.get("day", ""),
            it.get("approval_status", ""),
            it.get("type", ""),
            it.get("swimlane", ""),
            it.get("caption", ""),
            it.get("design_notes", ""),
            it.get("description", ""),
            it.get("hashtags", ""),
            it.get("references", ""),
            "",  # IMAGE — filled by designer
            "",  # CLIENT FEEDBACK — filled later
        ])
    csv_text = buf.getvalue()
    label = DOMAINS.get(domain, {}).get("label", domain).replace(" ", "_")
    fname = f"RH_SM_Calendar_{label}_{month}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _parse_rh_calendar_xlsx(content: bytes) -> list:
    """Parse the RH SM Calendar Excel format with columns:
    DATE, DAY, Approval Status, POST TYPE, Aligned Swimlane, CAPTION/Image Copy,
    Design Notes, DESCRIPTION, HASHTAGS, REFERENCES, IMAGE, DESIGN NOTES, CLIENT FEEDBACK
    """
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c or "").strip().lower() for c in rows[0]]

    def col(*names):
        for n in names:
            for i, h in enumerate(header):
                if n.lower() in h:
                    return i
        return -1

    idx = {
        "date": col("date"),
        "day": col("day"),
        "status": col("approval"),
        "type": col("post type"),
        "swimlane": col("swimlane"),
        "caption": col("caption"),
        "design_notes": col("design notes"),
        "description": col("description"),
        "hashtags": col("hashtags"),
        "references": col("references"),
        "client_feedback": col("client feedback"),
    }

    items = []
    for r in rows[1:]:
        if not r or len(r) <= idx["date"]:
            continue
        d = r[idx["date"]] if idx["date"] >= 0 else None
        post_type = r[idx["type"]] if idx["type"] >= 0 else None
        if not post_type or not str(post_type).strip():
            continue

        date_str = ""
        if isinstance(d, (datetime, date)):
            date_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime) else d.isoformat()
        elif d:
            date_str = str(d).split(" ")[0]

        def g(k):
            i = idx.get(k, -1)
            if i < 0 or i >= len(r):
                return ""
            v = r[i]
            return str(v).strip() if v is not None else ""

        items.append({
            "date": date_str,
            "day": g("day"),
            "approval_status": g("status"),
            "type": str(post_type).strip(),
            "swimlane": g("swimlane"),
            "caption": g("caption"),
            "design_notes": g("design_notes"),
            "description": g("description"),
            "hashtags": g("hashtags"),
            "references": g("references"),
            "client_feedback": g("client_feedback"),
            "platforms": ["instagram", "facebook", "linkedin"],
        })
    return items


@app.post("/api/calendar/upload")
async def calendar_upload(file: UploadFile = File(...), domain: str = Query("rh"), month: str = Query("")):
    if not month:
        raise HTTPException(400, "month required")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    name = (file.filename or "").lower()

    # Structured Excel upload: parse directly, no AI
    if name.endswith(".xlsx") or name.endswith(".xls"):
        try:
            items = _parse_rh_calendar_xlsx(content)
        except Exception as e:
            raise HTTPException(422, f"Failed to parse Excel calendar: {e}")
        if items:
            _calendars[f"{domain}:{month}"] = items
            # Seed history so AI knows these were already published
            _push_history(_calendar_history, domain, [
                {"title": (it.get("caption") or "")[:200], "swimlane": it.get("swimlane", "")}
                for it in items
            ], key_field="title")
            return {"items": items, "month": month, "domain": domain, "source": "excel"}

    # Otherwise, fall back to AI-driven generation from PDF/DOCX/text
    text = ""
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        elif name.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(422, f"Failed to parse file: {e}")
    text = text[:8000]
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    sys_prompt = CAL_SYSTEM.replace("{domain}", domain_label).replace("{month}", month)
    user = f"Generate the calendar for {domain_label}, month {month}, using the following source document as context:\n\n{text}"
    try:
        items = ai_mod.chat_json(sys_prompt, user, max_tokens=8000)
        items = _unwrap_items(items)
        _calendars[f"{domain}:{month}"] = items
        return {"items": items, "month": month, "domain": domain, "source": "ai"}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


# ── Creative Ideas ───────────────────────────────────────────────────────────

IDEAS_SYSTEM = (
    "You are the content strategist for Right Horizons (Indian wealth/PMS/AIF firm). "
    "You produce ideas that are SPECIFIC, DATA-DRIVEN, and IMMEDIATELY ACTIONABLE.\n\n"
    + RH_CONTENT_DNA +
    "\n\nTASK: Generate 10 fresh content ideas for category '{category}'. Every idea "
    "MUST align to one of the four swimlanes (Retirement Planning / NRI / ESOPs / "
    "Family Office). Match the observational, data-driven tone — no hype, no clickbait. "
    "If the category is 'all', spread across all swimlanes following the 35/27/15/12 distribution.\n\n"
    "EACH IDEA MUST HAVE:\n"
    "- title: specific title with a number, ₹ amount, or audience callout — NEVER generic\n"
    "- type: 'Carousel' / 'Static Image' / 'Reel' / 'Poll'\n"
    "- swimlane: 'Retirement Planning' / 'NRI' / 'ESOPs' / 'Family Office'\n"
    "- description: 3-4 sentence production brief — the hook, the insight, the audience angle, the visual direction. "
    "Use the observational voice: 'A salaried professional turning 40 often discovers...', not 'Learn about...'\n"
    "- hook: the EXACT opening line for the post — scroll-stopping, uses a specific ₹ figure or surprising stat\n"
    "- hashtags: array of 12-15 educational hashtags including #RightHorizons + #WealthManagement + swimlane tag. "
    "No generic hype tags.\n"
    "- best_platform: 'LinkedIn' / 'Instagram' / 'Twitter/X' / 'YouTube' with a short WHY\n"
    "- audience_persona: one-sentence description of the exact person this is for (age, income in ₹, situation)\n"
    "- content_depth: 'foundational' / 'intermediate' / 'advanced' / 'niche'\n\n"
    "QUALITY RULES:\n"
    "- Every title must include a number, ₹ amount, or specific audience — 'Understanding wealth' is NOT acceptable, "
    "'Why your ₹50L FD earns less than inflation — a real-terms calculator' IS\n"
    "- Hooks must provoke curiosity or loss aversion — not generic statements\n"
    "- Each idea must be different in angle, format, and swimlane where possible\n"
    "- Reference 2024-2026 Indian financial context: new tax regime, LTCG at 12.5%, Budget changes, RBI rates"
)


@app.get("/api/ideas/generate")
def ideas_generate(domain: str = "rh", category: str = "all"):
    if not ai_mod:
        raise HTTPException(500, "AI module failed to load")
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    level = _level_up(f"ideas:{domain}")
    sys_prompt = IDEAS_SYSTEM.replace("{category}", category)
    user = f"Generate 10 fresh content ideas for {domain_label}, category: {category}.\n\n"
    user += f"GENERATION LEVEL: {level} (each batch must escalate in depth/specificity)\n"
    user += "LEVEL-UP RULES:\n"
    user += "- Level 1-3: foundational concepts\n"
    user += "- Level 4-7: intermediate strategies with concrete math\n"
    user += "- Level 8+: advanced/niche scenarios (cross-border, multi-entity, regulatory edge cases)\n\n"
    past = _history_context(_ideas_history, f"ideas:{domain}", limit=80)
    if past:
        user += "DO NOT REPEAT THESE PAST IDEAS (find a new angle, audience, or specific case):\n"
        user += past + "\n\nEvery idea must be NEW. Avoid the same titles, framings, or numerical examples.\n"
    try:
        items = ai_mod.chat_json(sys_prompt, user, max_tokens=5000, temperature=0.85)
        items = _unwrap_items(items)
        _ideas_state["available"] = len(items) if isinstance(items, list) else 0
        _push_history(_ideas_history, f"ideas:{domain}", items if isinstance(items, list) else [], key_field="title")
        return {"items": items, "domain": domain, "category": category, "level": level}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.get("/api/ideas/notifications")
def ideas_notifications():
    return {"new": _ideas_state.get("available", 0)}


@app.post("/api/ideas/seen")
def ideas_seen():
    _ideas_state["available"] = 0
    return {"ok": True}


@app.get("/api/ideas/lab/generate")
def ideas_lab_generate(
    domain: str = "rh",
    topic: str = "",
    audience: str = "",
    content_type: str = "LinkedIn carousel",
    goal: str = "Awareness",
    source: str = "Manual topic",
    context: str = "",
):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    d = DOMAINS.get(domain, {})
    domain_label = d.get("label", domain)
    entity_type = "Investment Advisory" if domain == "rh" else ("PMS" if domain == "pms" else "AIF")

    sys_prompt = (
        f"You are the head of content strategy at {domain_label}, a SEBI-registered Indian {entity_type} firm. "
        "You have deep expertise in Indian wealth management, tax planning, and investor psychology.\n\n"
        + RH_CONTENT_DNA +
        "\n\nYour job: generate 8 production-ready content idea cards as a JSON array.\n\n"
        "EACH IDEA MUST INCLUDE ALL OF THESE FIELDS:\n"
        "- title: specific, punchy, includes a number or ₹ figure or audience callout — NEVER generic\n"
        "- format: exact content format (LinkedIn carousel / Instagram Reel / Blog article / YouTube explainer / Email drip / Social static / Twitter thread / Webinar)\n"
        "- group: one of Social, Video, Blog, Seasonal\n"
        "- audience: hyper-specific Indian investor persona with income bracket in ₹ and life stage "
        "(e.g. 'Tech professionals 28-35 with ₹15-25L CTC and unexercised ESOPs', "
        "'NRI couples in UAE with ₹80L-2Cr in Indian FDs earning <3% real return', "
        "'Retired govt officers 60+ with ₹30L pension corpus worried about healthcare inflation')\n"
        "- hook: the EXACT opening line — scroll-stopping, uses a specific stat, question, or contrarian take. "
        "Must work as the first thing someone reads. Not a description of a hook — the actual words.\n"
        "- angle: one of Educational, Problem-solution, Myth-busting, Checklist, Expert opinion, Comparison, "
        "Mistakes to avoid, Data-backed, Case-study, Contrarian, Calculator, Framework\n"
        "- score: quality score 75-96 — vary realistically. A niche idea with small audience scores lower on 'Audience fit' but higher on 'Conversion potential'. Not every idea is 88+.\n"
        "- cta: specific, actionable CTA tied to a real Right Horizons offering — "
        "'Book a 15-min NRI tax review call (free)', 'Register: live webinar on ESOP tax planning — June 28', "
        "'Use our retirement corpus calculator at righthorizons.com/tools', 'Download the NRI repatriation checklist (PDF)'\n"
        "- visual_direction: precise design brief a designer can execute — specify: number of slides (for carousel), "
        "color palette (hex or description), typography hierarchy, chart types, imagery style, layout pattern, "
        "brand elements to include. Not vague — specific.\n"
        "- compliance_reminder: the SPECIFIC SEBI/finance compliance issue for THIS content — "
        "which disclaimer to use, which claims to avoid, which entity registration to display. "
        "Reference actual SEBI circular numbers or sections where relevant.\n"
        "- why_it_works: strategic rationale with psychological depth — name the cognitive bias or emotional trigger "
        "(loss aversion, social proof, authority bias, urgency, anchoring), explain the content gap this fills, "
        "and why this audience is underserved by current content.\n"
        "- slide_flow: array of 6-8 specific slide/section titles that a designer can directly use — "
        "not generic ('Introduction', 'Key points') but specific ('Slide 1: The ₹15L tax trap most NRIs walk into', "
        "'Slide 2: DTAA Article 4 — your residency shield')\n"
        "- scores: object with keys 'Audience fit' (how large/accessible), 'Clarity' (how easy to produce), "
        "'Platform fit' (how well it suits the format), 'Conversion potential' (likelihood of generating leads), "
        "'Compliance safety' (how easy to keep SEBI-safe) — each 68-96, VARIED per idea based on real tradeoffs\n"
        "- platform_notes: which platform(s) this works best on and WHY — posting time, algorithm considerations, "
        "format preferences (e.g. 'LinkedIn algorithm favors carousels with 8-12 slides posted Tue-Thu 8-10am IST')\n"
        "- content_pillar: which swimlane this maps to (Retirement Planning / NRI / ESOPs / Family Office)\n\n"
        "CREATIVITY RULES:\n"
        "- Each idea MUST have a different angle AND format — zero overlap in approach\n"
        "- At least 2 ideas must use contrarian or myth-busting angles\n"
        "- At least 1 idea must reference a CURRENT event or recent regulatory change (2024-2026)\n"
        "- At least 1 idea must be a calculator/framework/tool-based content\n"
        "- Hooks must provoke — use specific ₹ amounts, percentages, or surprising facts\n"
        "- Avoid bland corporate language — write like a sharp financial journalist, not a compliance officer\n"
        "- Every CTA must feel like a natural next step, not a sales push\n"
        "- Think about what content is MISSING in Indian fintech/wealth social media — fill gaps, don't repeat what everyone posts"
    )

    user_msg = (
        f"Client: {domain_label} ({entity_type})\n"
        f"Campaign goal: {goal}\nPreferred format: {content_type}\n"
        f"Topic source: {source}\nCore topic: {topic or '(open — pick the strongest angles)'}\n"
        f"Target audience: {audience or '(pick the most underserved segments for this topic)'}\n"
    )
    if context:
        user_msg += f"\nAdditional context from the user:\n{context}\n"

    past = _history_context(_ideas_history, f"ideas_lab:{domain}", limit=40)
    if past:
        user_msg += f"\nAVOID REPEATING these previously generated ideas — find fresh angles:\n{past}\n"

    if web_search:
        live = web_search.search_indian_finance(topic or "Indian wealth management trends")
        if live:
            user_msg += f"\n\nCURRENT MARKET CONTEXT (live web search — use for timely references, do NOT fabricate data):\n{live}\n"
        news = web_search.search_finance_news(topic or "")
        if news:
            user_msg += f"\n\nLATEST FINANCE NEWS (from Moneycontrol, ET Money, LiveMint — reference specific articles/data):\n{news}\n"
        trending = web_search.search_content_trends(topic or "")
        if trending:
            user_msg += f"\n\nTRENDING CONTENT IN FINANCE (use for timely angle inspiration):\n{trending}\n"
    if google_trends:
        gt = google_trends.finance_trends_context(topic or "mutual funds India")
        if gt:
            user_msg += f"\n\nGOOGLE TRENDS — INDIA (use trending keywords to make content timely and discoverable):\n{gt}\n"

    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=6000, temperature=0.85)
        items = _unwrap_items(items)
        _push_history(_ideas_history, f"ideas_lab:{domain}", items if isinstance(items, list) else [], key_field="title")
        return {"ideas": items, "domain": domain, "topic": topic}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.post("/api/ideas/lab/webinar")
def ideas_lab_webinar(body: dict = Body(...)):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    text = body.get("text", "")
    domain = body.get("domain", "rh")
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    sys_prompt = (
        f"You are a content repurposing expert at {domain_label}, an Indian SEBI-registered financial services firm. "
        "Your job: take ONE webinar and extract MAXIMUM value — turn it into a full content engine.\n\n"
        + RH_CONTENT_DNA +
        "\n\nANALYSIS FIRST: Before generating content, mentally extract from the webinar:\n"
        "- The 3-5 strongest data points or statistics mentioned\n"
        "- The most quotable statements from the speaker\n"
        "- The key audience pain points addressed\n"
        "- Any frameworks, models, or step-by-step processes described\n"
        "- Surprising or contrarian insights that would stop a scroll\n\n"
        "Generate 15-18 diverse, production-ready content pieces as a JSON array.\n\n"
        "CONTENT MIX (follow this distribution):\n"
        "- 3-4 LinkedIn posts: thought leadership, data highlights, myth-busting. Use the EXACT voice from Content DNA.\n"
        "- 3 carousels: step-by-step breakdowns (8-10 slides each), key stats visualized, checklists.\n"
        "- 3 short video/Reels (30-60 sec): speaker clips with on-screen stats, myth-bust moments, 'one thing you need to know'.\n"
        "- 2 blog articles: SEO-optimized with full H2/H3 structure, 1500-2000 words each.\n"
        "- 2 email sequences: not just subject lines — full nurture angle with 3-email arc.\n"
        "- 2 quote cards: exact quotes with visual treatment direction.\n\n"
        "EACH ITEM MUST HAVE:\n"
        "- title: specific, compelling title (not 'Webinar recap' — something a reader would click)\n"
        "- format: LinkedIn post / Carousel / Short video / Blog / Email sequence / Quote card\n"
        "- funnel_stage: TOFU (awareness) / MOFU (consideration) / BOFU (decision)\n"
        "- priority: high / medium / low — based on potential impact and ease of production\n"
        "- effort: quick (< 1 hour) / moderate (1-3 hours) / substantial (3+ hours)\n"
        "- description: detailed, actionable production brief (80+ words) including:\n"
        "  • Exact data points/quotes to use from the webinar\n"
        "  • Visual approach and design notes\n"
        "  • Platform-specific optimization tips\n"
        "  • CTA appropriate to the funnel stage\n"
        "- hook: the EXACT opening line — ready to copy-paste, not a description\n"
        "- key_insight: the core insight from the webinar this piece is built around\n"
        "- compliance_note: specific SEBI compliance consideration for this piece\n\n"
        "RULES:\n"
        "- All currency in ₹ (INR), Indian financial context exclusively\n"
        "- Extract SPECIFIC data points, speaker quotes, and insights — never genericize\n"
        "- Each piece must stand completely alone — someone who didn't watch the webinar should still find it valuable\n"
        "- Vary the emotional tone: some educational, some urgent, some aspirational, some myth-busting\n"
        "- Email sequences should have subject line A/B variants"
    )
    user_msg = f"Client: {domain_label}\n\nWebinar content to repurpose:\n{text[:8000]}"
    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=6000, temperature=0.8)
        items = _unwrap_items(items)
        return {"ideas": items, "domain": domain}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.post("/api/ideas/lab/seo")
def ideas_lab_seo(body: dict = Body(...)):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    keywords = body.get("keywords", "")
    domain = body.get("domain", "rh")
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    sys_prompt = (
        f"You are a senior SEO strategist at {domain_label}, an Indian SEBI-registered financial services firm "
        "(Investment Advisory, PMS, AIF). You combine deep SEO expertise with Indian financial domain knowledge.\n\n"
        + RH_CONTENT_DNA +
        "\n\nGiven SEO keywords, create a comprehensive content plan as a JSON array. For each keyword, create 2-3 ideas.\n\n"
        "EACH ITEM MUST HAVE:\n"
        "- title: SEO-optimized title with the keyword naturally included (55-65 chars for SERP)\n"
        "- format: one of Blog pillar page / Blog cluster article / Comparison guide / Calculator page / FAQ hub / "
        "LinkedIn carousel / YouTube explainer / Infographic / Tool/template page\n"
        "- keyword: the primary keyword this targets\n"
        "- search_intent: informational / transactional / commercial investigation / navigational\n"
        "- difficulty_tier: low (long-tail, <1K monthly searches) / medium (moderate competition, 1K-10K) / high (competitive, 10K+)\n"
        "- funnel_stage: TOFU / MOFU / BOFU\n"
        "- description: detailed production brief (100+ words) including:\n"
        "  • WHY this content will rank — what's the angle competitors are missing?\n"
        "  • Full H2/H3 structure (6-8 subheadings minimum)\n"
        "  • Specific ₹ calculations, tax sections, or regulatory references to include\n"
        "  • Featured snippet target — the exact format (table/list/paragraph/definition) and content\n"
        "  • 'People Also Ask' questions to answer inline\n"
        "  • Internal linking strategy — which Right Horizons pages to link TO and FROM\n"
        "  • Schema markup recommendation (FAQ, HowTo, Article, Calculator)\n"
        "  • Content differentiation — what makes this better than current Page 1 results\n"
        "- long_tail_keywords: array of 4-6 related keywords to naturally weave in\n"
        "- meta_description: ready-to-use meta description (150-155 chars)\n"
        "- cta: specific Right Horizons CTA appropriate to the search intent\n"
        "- estimated_word_count: target word count\n"
        "- content_pillar: which swimlane (Retirement / NRI / ESOPs / Family Office)\n\n"
        "STRATEGY RULES:\n"
        "- Think about TOPIC CLUSTERS — group keywords that should link to each other\n"
        "- For high-difficulty keywords, suggest a pillar page + 3-4 cluster articles strategy\n"
        "- All currency in ₹ (INR), Indian tax/regulatory context exclusively\n"
        "- Reference: Section 80C/80D/80CCD, LTCG (12.5%), STCG (20%), NRI DTAA, FEMA, SEBI circulars\n"
        "- Indian benchmarks: Nifty 50, Sensex, SBI FD rates, PPF rates, gold prices in ₹\n"
        "- Target Google India SERPs — what do the current top 3 results look like and how can we beat them?\n"
        "- Prioritize content that can earn backlinks naturally (data, calculators, definitive guides)"
    )
    user_msg = f"Client: {domain_label}\n\nTarget keywords:\n{keywords[:4000]}"
    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=6000, temperature=0.75)
        items = _unwrap_items(items)
        return {"ideas": items, "domain": domain}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.post("/api/ideas/lab/expand")
def ideas_lab_expand(body: dict = Body(...)):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    idea = body.get("idea", {})
    output_type = body.get("output_type", "brief")
    domain = body.get("domain", "rh")
    domain_label = DOMAINS.get(domain, {}).get("label", domain)

    type_prompts = {
        "brief": (
            "Create a comprehensive production brief as a JSON object with keys:\n"
            "- overview: 2-3 sentence creative direction\n"
            "- target_audience: detailed persona description (age, income in ₹, location, pain points)\n"
            "- key_messages: array of 4-5 key messages to convey\n"
            "- content_structure: array of objects {heading, description, word_count} — full content outline\n"
            "- visual_mood: detailed visual/design direction (colors, typography, imagery style)\n"
            "- distribution: array of {channel, timing, format_notes} — where and when to publish\n"
            "- metrics: array of KPIs to track for this content\n"
            "- internal_links: array of Right Horizons pages/services to link to\n"
            "- seo_notes: target keywords, meta description, featured snippet opportunity\n"
            "- estimated_time: production time estimate"
        ),
        "carousel": (
            "Create a full carousel/slide deck as a JSON object with keys:\n"
            "- slide_count: number of slides\n"
            "- slides: array of objects {slide_number, headline, body_text, visual_note, speaker_note}\n"
            "  — body_text should be the ACTUAL text for each slide (not a description), 20-40 words per slide\n"
            "  — visual_note describes what the slide looks like\n"
            "- design_system: {primary_color, accent_color, font_pairing, layout_style}\n"
            "- caption: ready-to-post LinkedIn/Instagram caption (150-200 words) with hashtags\n"
            "All ₹ amounts, Indian context only."
        ),
        "blog": (
            "Create a full blog outline as a JSON object with keys:\n"
            "- meta_title: SEO title (60-70 chars)\n"
            "- meta_description: SEO meta description (150-160 chars)\n"
            "- word_count: target word count\n"
            "- sections: array of objects {heading, subheadings: [], key_points: [], word_count}\n"
            "- faq: array of {question, answer_outline} for FAQ schema\n"
            "- internal_links: suggested Right Horizons pages to link\n"
            "- cta_placement: where to place CTAs within the article\n"
            "- featured_snippet: the paragraph/list/table to target for position zero\n"
            "All ₹ amounts, Indian tax/financial context."
        ),
        "caption": (
            "Create ready-to-post social media captions as a JSON object with keys:\n"
            "- linkedin: {caption, hashtags} — professional tone, 150-250 words\n"
            "- instagram: {caption, hashtags} — engaging tone, 100-150 words with emoji\n"
            "- twitter: {tweets: []} — thread of 3-5 tweets, each under 280 chars\n"
            "- email_subject_lines: array of 3 A/B test subject lines\n"
            "All ₹ amounts, Indian context."
        ),
    }

    sys_prompt = (
        f"You are the head of content production at {domain_label}, an Indian SEBI-registered financial services firm. "
        "You produce content that is immediately usable — not outlines, but actual production-ready material.\n\n"
        + RH_CONTENT_DNA +
        "\n\n" + type_prompts.get(output_type, type_prompts['brief'])
    )
    user_msg = (
        f"Expand this idea into a full, production-ready {output_type}:\n\n"
        f"Title: {idea.get('title', '')}\nFormat: {idea.get('format', '')}\n"
        f"Target audience: {idea.get('audience', '')}\nOpening hook: {idea.get('hook', '')}\n"
        f"Content angle: {idea.get('angle', '')}\nCall to action: {idea.get('cta', '')}\n"
        f"Visual direction: {idea.get('visual', idea.get('visual_direction', ''))}\n"
        f"Content pillar: {idea.get('content_pillar', '')}\n"
        f"Why it works: {idea.get('why', idea.get('why_it_works', ''))}\n"
        f"Slide flow: {', '.join(idea.get('slides', idea.get('slide_flow', [])))}"
    )
    try:
        result = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=5000, temperature=0.8)
        return {"expanded": result, "output_type": output_type}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.get("/api/ideas/lab/seasonal")
def ideas_lab_seasonal(domain: str = "rh", month: int = 0):
    if not ai_mod:
        raise HTTPException(503, "AI module not available")
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    today = _today_ist()
    current_month = month or today.month
    current_year = today.year
    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    current_name = month_names[current_month] if 1 <= current_month <= 12 else "this month"
    next1 = month_names[(current_month % 12) + 1] if current_month < 12 else "January"
    next2 = month_names[((current_month + 1) % 12) + 1] if current_month < 11 else month_names[((current_month + 1) % 12) + 1]

    sys_prompt = (
        f"You are a content calendar strategist at {domain_label}, an Indian SEBI-registered financial services firm "
        "(Investment Advisory, PMS, AIF). All currency in ₹ (INR).\n\n"
        + RH_CONTENT_DNA +
        f"\n\nToday is {today.strftime('%B %d, %Y')}. Generate 10 seasonal content ideas for "
        f"{current_name} {current_year}, {next1} {current_year}, and {next2} {current_year if current_month < 11 else current_year + 1}.\n\n"
        "SEASONAL TRIGGERS TO CONSIDER:\n"
        "- Indian festivals: Diwali, Holi, Dussehra, Ganesh Chaturthi, Onam, Pongal, Eid, Christmas, Dhanteras, Raksha Bandhan, Independence Day, Republic Day\n"
        "- Tax deadlines: March 31 (FY end), July 31 (ITR due), advance tax (Jun 15, Sep 15, Dec 15, Mar 15), TDS filing dates\n"
        "- Market events: Union Budget (Feb), RBI monetary policy (bi-monthly), quarterly results season, Nifty rebalancing\n"
        "- NRI-specific: Summer India visits (Jun-Aug), Diwali NRI return, academic year abroad, remittance peaks\n"
        "- Life events: appraisal season (Mar-Apr), bonus season, wedding season (Nov-Feb), new year financial resolutions\n"
        "- Regulatory: SEBI circular deadlines, AMFI changes, new tax regime transitions, GST deadlines\n\n"
        "EACH ITEM MUST HAVE:\n"
        "- title: specific, punchy title with ₹ amounts or numbers — not generic festival wishes\n"
        "- format: content format with platform (e.g. 'LinkedIn carousel + Instagram static', 'Blog + email sequence')\n"
        "- occasion: the exact seasonal trigger with approximate date\n"
        "- timing: exact publishing window (e.g. '2 weeks before March 31', 'Day of Budget announcement', 'Week after Diwali')\n"
        "- description: detailed production brief (80+ words) — angle, ₹ examples, specific investor audience, CTA, "
        "visual approach, and why this timing matters for engagement\n"
        "- audience: specific Indian investor segment with income/life stage\n"
        "- urgency: high (publish within 1-2 weeks) / medium (2-4 weeks runway) / low (plan ahead for next month)\n"
        "- content_pillar: Retirement Planning / NRI / ESOPs / Family Office\n\n"
        "RULES:\n"
        "- Don't just say 'Happy Diwali' — tie every festival to a FINANCIAL angle with specific ₹ math\n"
        "- Tax deadline content should include actual numbers (₹1.5L 80C, ₹50K NPS, ₹25K 80D)\n"
        "- NRI ideas should reference DTAA, Form 13, NRE/NRO, FEMA\n"
        "- Each idea must be content-led, not greeting-card style\n"
        "- Sort by urgency (high first)"
    )
    user_msg = f"Generate seasonal ideas for {current_name}-{next2} {current_year} for {domain_label}. Today is {today.isoformat()}."

    if web_search:
        live = web_search.search_seasonal_events(f"{current_name} {next1} {next2}")
        if live:
            user_msg += f"\n\nCURRENT EVENTS & DEADLINES (live web search — ground your ideas in these real events):\n{live}\n"
        news = web_search.search_finance_news("India financial events regulatory SEBI RBI")
        if news:
            user_msg += f"\n\nLATEST FINANCE NEWS (reference current regulatory/market developments):\n{news}\n"
    if google_trends:
        gt = google_trends.trending_searches_india()
        if gt:
            user_msg += f"\n\n{gt}\n"

    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=5000, temperature=0.8)
        items = _unwrap_items(items)
        return {"ideas": items, "month": current_name, "domain": domain}
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


# ── Content Validator ────────────────────────────────────────────────────────

_RH_BRAND_GUIDELINES = """
=== BRAND GUIDELINES: RIGHT HORIZONS GROUP ===

1. RIGHT HORIZONS (Investment Advisory)
   - Email: contactus@righthorizons.com
   - Website: http://www.righthorizons.com
   - Phone: 91 80505 74007
   - SEBI Registration: Investment Adviser — INA200002601
   - BSE Enlistment: 1730
   - Mandatory Disclaimer: "Investment in securities market are subject to market risks. Read all the related documents carefully before investing."
   - Additional Disclaimer: "Registration granted by SEBI, enlistment as IA with Exchange and certification from National Institute of Securities Markets (NISM) in no way guarantee performance of the intermediary provide any assurance of returns to investors."

2. RIGHT HORIZONS PMS (Portfolio Management Services)
   - Email: rhpmscare@righthorizons.com
   - Website: http://www.righthorizonspms.com
   - Phone: 91 80505 93006
   - SEBI Registration: INP000004359
   - Mandatory Disclaimer: "Investments under Portfolio Management Services by Right Horizons Portfolio Management Private Limited are subject to market risks, and past performance does not guarantee future returns. Investors should read the Disclosure Document carefully, understand all risks, and consult tax advisors before investing. No assured returns are offered, and SEBI has not verified performance data."

3. RIGHT HORIZONS AIF (Alternative Investment Funds)
   - Email: aifsupport@righthorizons.com
   - Phone: 91 80505 93006
   - SEBI Registration: IN/AIF3/25-26/2114
   - Mandatory Disclaimer: "Investments in AIFs are subject to market risks, including potential loss of capital. Past performance of the sponsor/investment manager does not guarantee future returns. Please read the Private Placement Memorandum (PPM) carefully and consult your advisors before investing."

=== COMPLIANCE RULES ===
- Every creative MUST include the correct disclaimer for the entity it represents.
- SEBI registration number MUST be displayed.
- Contact details (email, phone, website) should be present or referenced.
- No guaranteed/assured returns language is permitted.
- Past performance disclaimers are mandatory when showing returns data.
- "Mutual fund investments are subject to market risks" type disclaimers must match the entity type (IA/PMS/AIF).
"""

VALIDATOR_TEXT_SYSTEM = (
    "You are the chief content quality officer at Right Horizons. You review EVERY piece before it goes live. "
    "You are meticulous, thorough, and specific. Your reviews save the brand from compliance violations and weak content.\n\n"
    "Review against BOTH the brand guidelines AND the content DNA below.\n\n"
    "=== BRAND GUIDELINES ===\n" + _RH_BRAND_GUIDELINES +
    "\n\n" + RH_CONTENT_DNA +
    "\n\nPERFORM THESE CHECKS IN ORDER:\n"
    "1. SEBI COMPLIANCE (critical — can result in regulatory action):\n"
    "   - Correct entity disclaimer present? Match disclaimer text EXACTLY to the entity (RH/PMS/AIF)\n"
    "   - SEBI registration number displayed?\n"
    "   - No assured/guaranteed returns language? (even indirect: 'proven', 'consistently outperforming')\n"
    "   - No forward-looking statements without disclaimers?\n"
    "   - Past performance disclaimer when showing returns data?\n"
    "   - No specific stock/fund recommendations without IA disclaimer?\n"
    "2. SWIMLANE ALIGNMENT: does the content cleanly fit one of 4 pillars? Mixed/unclear hurts brand positioning.\n"
    "3. VOICE & TONE MATCH:\n"
    "   - Observational vs promotional? (RH voice is advisory, never salesy)\n"
    "   - Concrete ₹ numbers used? (not vague 'significant returns')\n"
    "   - Acknowledges complexity vs oversimplifies?\n"
    "   - Calm, mature language vs hype/clickbait?\n"
    "4. HYPE WORD SCAN: flag ALL instances of: 'game-changing', 'secret', 'shocking', 'guaranteed', "
    "'risk-free', 'limited time', 'don't miss', 'buy now', 'best returns', 'huge returns', "
    "'massive growth', 'once in a lifetime', 'sureshot', 'jackpot', '100% safe', 'double your money'.\n"
    "5. HASHTAG QUALITY: 12-15 educational tags? Includes #RightHorizons + #WealthManagement + swimlane tag? "
    "No generic hype tags (#trending, #viral, #moneygoals)?\n"
    "6. STRUCTURE MATCH: Does the format match the type? Carousel has numbered slides? Static has bullets? Reel has scene directions?\n"
    "7. GRAMMAR & CLARITY: Spelling, punctuation, sentence clarity. Indian English conventions.\n"
    "8. ENGAGEMENT POTENTIAL: Will this actually perform? Is the hook strong? Is the CTA clear?\n\n"
    "Output ONLY valid JSON: {\n"
    "  score: 0-100 (overall publish-readiness),\n"
    "  entity_detected: 'RH'|'PMS'|'AIF'|'unknown',\n"
    "  swimlane_detected: 'Retirement Planning'|'NRI'|'ESOPs'|'Family Office'|'unclear',\n"
    "  voice_match_score: 0-100 (how closely it matches RH Content DNA voice),\n"
    "  engagement_score: 0-100 (predicted engagement potential),\n"
    "  hype_words_found: [exact words found],\n"
    "  compliance_issues: [{issue: string, severity: 'critical'|'warning'|'info', guideline_ref: string, fix: string}],\n"
    "  voice_issues: [{issue: string, suggestion: string, example_rewrite: string}],\n"
    "  grammar_issues: [{issue: string, suggestion: string}],\n"
    "  strengths: [specific things done well],\n"
    "  weaknesses: [specific things to improve],\n"
    "  recommendations: [actionable improvements, ordered by impact],\n"
    "  missing_info: [what's missing — disclaimers, SEBI reg, contact details, hashtags],\n"
    "  rewrite_suggestions: [{original: string, suggested: string, reason: string}] (top 3 sentences to rewrite),\n"
    "  publish_ready: boolean,\n"
    "  summary: string (2-3 sentence verdict)\n"
    "}."
)

VALIDATOR_IMAGE_SYSTEM = (
    "You are a senior creative reviewer for Right Horizons (Indian wealth/PMS/AIF).\n\n"
    "Review against BOTH the brand guidelines AND the content DNA below.\n\n"
    "=== BRAND GUIDELINES ===\n" + _RH_BRAND_GUIDELINES +
    "\n\n" + RH_CONTENT_DNA +
    "\n\nCHECKS TO PERFORM:\n"
    "1. SEBI compliance: visible disclaimer matching entity, SEBI reg number, no assured returns.\n"
    "2. Swimlane alignment: does the visual fit Retirement/NRI/ESOPs/Family Office?\n"
    "3. Design quality: hierarchy, readability of overlays, white-space, brand handles.\n"
    "4. Voice match in any visible copy: observational, not promotional.\n"
    "5. Logo, contact details, brand color usage (purple #7C3AED accent acceptable).\n"
    "Output ONLY valid JSON: {score: 0-100, entity_detected: 'RH'|'PMS'|'AIF'|'unknown', "
    "swimlane_detected: 'Retirement Planning'|'NRI'|'ESOPs'|'Family Office'|'unclear', "
    "voice_match_score: 0-100, hype_words_found: [], "
    "compliance_issues: [{issue, severity: 'critical'|'warning'|'info', guideline_ref}], "
    "voice_issues: [{issue, suggestion}], grammar_issues: [{issue, suggestion}], "
    "strengths: [], weaknesses: [], recommendations: [], missing_info: [], "
    "publish_ready: boolean, summary: string}."
)


@app.post("/api/validator/text")
def validator_text(payload: dict = Body(...)):
    content = (payload or {}).get("content", "").strip()
    if not content:
        raise HTTPException(400, "content required")
    try:
        return ai_mod.chat_json(VALIDATOR_TEXT_SYSTEM, f"Review this content thoroughly:\n\n{content}", max_tokens=4000, temperature=0.5)
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.post("/api/validator/image")
async def validator_image(file: UploadFile = File(...)):
    import base64
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    mime = file.content_type or "image/png"
    b64 = base64.b64encode(raw).decode()
    data_url = f"data:{mime};base64,{b64}"
    try:
        return ai_mod.chat_vision_json(VALIDATOR_IMAGE_SYSTEM,
            "Review this visual creative for a financial services brand.", data_url, max_tokens=2500)
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")


@app.post("/api/validator/video")
async def validator_video(file: UploadFile = File(...)):
    return {"message": "Video analysis: extract first frame and submit as image, or paste description"}


# ── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
