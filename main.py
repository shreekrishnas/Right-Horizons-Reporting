import io
import traceback
from datetime import date, timedelta, datetime, timezone
_IST = timezone(timedelta(hours=5, minutes=30))
def _today_ist() -> date:
    return datetime.now(_IST).date()

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import DOMAINS, META_MARKETING_TOKEN, META_SOCIAL_TOKEN, META_PAGE_ID, META_APP_ID, META_APP_SECRET, ADMIN_PASSWORD
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
from config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
from config import OPENROUTER_API_KEY
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
def social_trend(period: str = "weekly", periods: int = 5, domain: str = "rh"):
    token, page_id = _meta_creds(domain)
    if not token:
        raise HTTPException(400, "Meta Social token not configured")
    if not page_id:
        raise HTTPException(400, "META_PAGE_ID not configured")

    today = _today_ist()
    days_per = 7 if period == "weekly" else 30
    ig_id = None
    try:
        ig_id = social.get_ig_account(token, page_id)
    except Exception:
        pass

    results = []
    for i in range(periods):
        p_end = today - timedelta(days=i * days_per)
        p_start = p_end - timedelta(days=days_per - 1)
        ps = p_start.isoformat()
        pe = p_end.isoformat()
        if period == "weekly":
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
        else:
            label = p_start.strftime('%B %Y')

        row = {"period": label, "start": ps, "end": pe}
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
def seo_trend(domain: str = "rh", period: str = "weekly", periods: int = 5):
    d = _domain(domain)
    try:
        creds = get_credentials()
    except Exception as e:
        raise HTTPException(502, f"Auth error: {e}")

    today = _today_ist()
    days_per = 7 if period == "weekly" else 30
    results = []
    for i in range(periods):
        p_end = today - timedelta(days=i * days_per)
        p_start = p_end - timedelta(days=days_per - 1)
        ws = p_start.isoformat()
        we = p_end.isoformat()
        if period == "weekly":
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%b %d')}"
        else:
            label = p_start.strftime('%B %Y')

        row = {"period": label, "start": ws, "end": we}

        try:
            gs = gsc.get_summary(creds, d["gsc_site"], ws, we)
            row.update({
                "gsc_clicks": gs.get("clicks", 0),
                "gsc_impressions": gs.get("impressions", 0),
                "gsc_position": gs.get("position", 0),
            })
        except Exception:
            row.update({"gsc_clicks": 0, "gsc_impressions": 0, "gsc_position": 0})

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


@app.get("/api/youtube/seo")
def youtube_seo(topic: str = "", speaker: str = "", transcript: str = ""):
    if not topic.strip():
        raise HTTPException(400, "topic parameter required")
    return youtube.generate_seo_metadata(topic, speaker, transcript)


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
def reports_export(period: str = "weekly", domain: str = "rh", start: str = "", end: str = "", format: str = "excel"):
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

    if fmt == "html":
        import html_report
        html_data = {}
        try:
            creds = get_credentials()
            gsc_sum = gsc.get_summary(creds, d["gsc_site"], start, end)
            gsc_sum["queries"] = gsc.get_top_queries(creds, d["gsc_site"], start, end, 20)
            gsc_sum["pages"] = gsc.get_top_pages(creds, d["gsc_site"], start, end, 20)
            html_data["gsc"] = gsc_sum
            prop = d.get("ga4_property")
            if prop:
                try:
                    ga4_sum = ga4.get_summary(creds, prop, start, end)
                    ga4_sum["pages"] = ga4.get_top_pages(creds, prop, start, end, 20)
                    ga4_sum["sources"] = ga4.get_traffic_sources(creds, prop, start, end)
                    try:
                        org = ga4.get_organic_summary(creds, prop, start, end)
                        ga4_sum["organic_sessions"] = org.get("organic_sessions", 0)
                        ga4_sum["organic_users"] = org.get("organic_users", 0)
                        ga4_sum["leads"] = org.get("leads", 0)
                    except Exception:
                        pass
                    html_data["ga4"] = ga4_sum
                except Exception:
                    pass
            try:
                html_data["seo_trend"] = seo_trend(domain, period, 5)
            except Exception:
                pass
        except Exception:
            pass
        ad_account = DOMAINS.get(domain, {}).get("meta_ad_account", "")
        if META_MARKETING_TOKEN and ad_account:
            try:
                html_data["meta_ads"] = meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
            except Exception:
                pass
        h_token, h_page_id = _meta_creds(domain)
        if h_token and h_page_id:
            try:
                html_data["social_fb"] = social.get_fb_comprehensive(h_token, h_page_id, start, end)
            except Exception:
                pass
            try:
                ig_id = social.get_ig_account(h_token, h_page_id)
                if ig_id:
                    html_data["social_ig"] = social.get_ig_comprehensive(h_token, ig_id, start, end)
            except Exception:
                pass
            try:
                html_data["social_trend"] = social_trend(period, 5, domain)
            except Exception:
                pass

        html_content = html_report.generate_html_report(html_data, start, end, d["label"])
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
        "You are a senior digital marketing analyst. Given the report room data below, "
        "produce an executive summary as JSON with these exact fields:\n"
        "- what_improved: string summarizing metrics that improved\n"
        "- what_dropped: string summarizing metrics that dropped\n"
        "- what_stable: string summarizing stable metrics\n"
        "- main_win: string describing the biggest positive takeaway\n"
        "- main_concern: string describing the biggest concern\n"
        "- key_opportunity: string describing the top opportunity to act on\n"
        "- recommended_focus: string describing what to prioritize next\n"
        "- executive_summary: string with a 2-3 sentence overall summary\n"
        "- confidence_score: integer 0-100 representing overall performance health\n"
        "- next_steps: array of 3-5 objects each with 'title' and 'description' fields\n"
        "Be concise, specific, and data-driven. Reference actual numbers where possible."
    )
    import json
    user_msg = f"Report room data for {room_data.get('label', domain)} ({start} to {end}):\n\n{json.dumps(room_data, default=str)}"
    try:
        summary = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=4000)
        return {"domain": domain, "label": room_data.get("label"), "start": start, "end": end, "summary": summary}
    except Exception as e:
        raise HTTPException(502, f"AI summary generation failed: {e}")


# ── Content Calendar ─────────────────────────────────────────────────────────

try:
    import ai as ai_mod
except Exception:
    ai_mod = None
from fastapi import Body
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
    "You are the content strategist for Right Horizons (Indian wealth/PMS/AIF firm). "
    "You must produce content that matches the firm's established voice exactly.\n\n"
    + RH_CONTENT_DNA +
    "\n\nTASK: Generate a monthly content calendar for {domain} for {month}. Produce "
    "12-15 posts (not 20-30) matching the swimlane distribution above (5-6 Retirement, "
    "3-4 NRI, 2 ESOPs, 1-2 Family Office). Follow the post-type mix (more Carousels & "
    "Static Images, occasional Reels/Polls). Captions and descriptions MUST follow the "
    "voice rules — observational, data-driven, no hype. Each post must include a swimlane.\n\n"
    "Output ONLY valid JSON: an array of "
    "{date: 'YYYY-MM-DD', platform, type ('Carousel'/'Static Image'/'Reel'/'Poll'), "
    "swimlane ('Retirement Planning'/'NRI'/'ESOPs'/'Family Office'), title, caption, "
    "description, hashtags: []}."
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
    past = _history_context(_calendar_history, req.domain, limit=80)
    if past:
        user += "DO NOT REPEAT THESE PAST POSTS (vary the angle, the numbers, the specifics):\n"
        user += past + "\n\nProduce ALL-NEW angles. If a swimlane needs to be covered again, "
        user += "shift the sub-topic, audience segment, age bracket, or numerical example.\n"
    if req.context:
        user += f"\n\nAdditional context:\n{req.context}"
    try:
        items = ai_mod.chat_json(sys_prompt, user, max_tokens=8000)
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
    "You are the content strategist for Right Horizons (Indian wealth/PMS/AIF firm).\n\n"
    + RH_CONTENT_DNA +
    "\n\nTASK: Generate 10 fresh content ideas for category '{category}'. Every idea "
    "MUST align to one of the four swimlanes (Retirement Planning / NRI / ESOPs / "
    "Family Office). Match the observational, data-driven tone — no hype, no clickbait. "
    "Include specific numbers and Indian financial context. If the category is 'all', "
    "spread across all four swimlanes following the 35/27/15/12 distribution.\n\n"
    "Output ONLY valid JSON array of "
    "{title, type ('Carousel'/'Static Image'/'Reel'/'Poll'), swimlane, description "
    "(2-3 sentence observational hook), hashtags: [12-15 educational tags including "
    "#RightHorizons + #WealthManagement + swimlane tag], best_platform}."
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
        items = ai_mod.chat_json(sys_prompt, user, max_tokens=4000)
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
    domain_label = DOMAINS.get(domain, {}).get("label", domain)
    sys_prompt = (
        "You are a senior content strategist for a financial services firm. "
        "Generate 6 structured content idea cards as a JSON array. Each idea must have these exact fields:\n"
        "- title: clear content idea title\n"
        "- format: content format (e.g. LinkedIn carousel, Blog, Short video, YouTube video, Email, Social post, Ad creative)\n"
        "- group: one of Social, Video, Blog, Seasonal\n"
        "- audience: target audience\n"
        "- hook: opening hook line that a writer can use immediately\n"
        "- angle: content angle (e.g. Educational, Problem-solution, Myth-busting, Checklist, Expert opinion, Comparison, Mistakes to avoid)\n"
        "- score: quality score 78-95\n"
        "- cta: suggested call to action\n"
        "- visual_direction: specific visual/design direction for the design team\n"
        "- compliance_reminder: finance compliance caution\n"
        "- why_it_works: why this idea is effective for the audience\n"
        "- slide_flow: array of 5-6 slide/section titles\n"
        "- scores: object with keys 'Audience fit', 'Clarity', 'Platform fit', 'Conversion potential', 'Compliance safety' each 75-95\n"
        "Make ideas specific and actionable, not generic. Each idea should be strong enough for a content writer to start working immediately."
    )
    user_msg = (
        f"Client: {domain_label}\nGoal: {goal}\nContent type: {content_type}\n"
        f"Topic source: {source}\nTopic: {topic}\nAudience: {audience}\n"
    )
    if context:
        user_msg += f"Extra context: {context}\n"
    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=4000)
        items = _unwrap_items(items)
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
        "You are a content repurposing expert. Given a webinar transcript or key points, "
        "generate a content repurposing pack as a JSON array. Create diverse content pieces:\n"
        "- 3-5 LinkedIn posts\n- 2-3 carousel ideas\n- 3-5 short video/Shorts ideas\n"
        "- 1-2 blog ideas\n- 2-3 email subject lines\n- 3-5 quote card ideas\n\n"
        "Each item must have: title, format (LinkedIn post/Carousel/Short video/Blog/Email/Quote card), "
        "description (actionable direction), hook (if applicable).\n"
        "Make each piece specific and usable, not generic."
    )
    user_msg = f"Client: {domain_label}\n\nWebinar content:\n{text[:6000]}"
    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=4000)
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
        "You are an SEO content strategist. Given a list of SEO keywords, "
        "generate content ideas as a JSON array. For each keyword, create 1-2 ideas.\n"
        "Each item must have: title, format (Blog/Carousel/Short video/LinkedIn post/FAQ), "
        "description (actionable direction including search intent, internal linking angle, and CTA suggestion).\n"
        "Focus on search intent and topical authority."
    )
    user_msg = f"Client: {domain_label}\n\nKeywords:\n{keywords[:3000]}"
    try:
        items = ai_mod.chat_json(sys_prompt, user_msg, max_tokens=4000)
        items = _unwrap_items(items)
        return {"ideas": items, "domain": domain}
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
    "You are a senior content reviewer for Right Horizons (Indian wealth/PMS/AIF).\n\n"
    "Review against BOTH the brand guidelines AND the content DNA below.\n\n"
    "=== BRAND GUIDELINES ===\n" + _RH_BRAND_GUIDELINES +
    "\n\n" + RH_CONTENT_DNA +
    "\n\nCHECKS TO PERFORM:\n"
    "1. SEBI compliance: correct entity disclaimer, SEBI reg number, no assured returns.\n"
    "2. Swimlane alignment: does the content fit one of the 4 pillars cleanly?\n"
    "3. Voice match: observational vs promotional? Concrete numbers used?\n"
    "4. Hype words to flag: 'game-changing', 'secret', 'shocking', 'guaranteed',\n"
    "   'limited time', 'don't miss', 'buy now', 'best returns', 'risk-free'.\n"
    "5. Hashtag quality: 12-15 educational tags including #RightHorizons, swimlane tag?\n"
    "6. Structure match for type (Carousel slides / Static bullets / Reel scenes).\n"
    "7. Grammar, clarity, Indian financial context (SEBI/GIFT City/SWP/AIF lingo).\n"
    "Output ONLY valid JSON: {score: 0-100, entity_detected: 'RH'|'PMS'|'AIF'|'unknown', "
    "swimlane_detected: 'Retirement Planning'|'NRI'|'ESOPs'|'Family Office'|'unclear', "
    "voice_match_score: 0-100, hype_words_found: [], "
    "compliance_issues: [{issue, severity: 'critical'|'warning'|'info', guideline_ref}], "
    "voice_issues: [{issue, suggestion}], grammar_issues: [{issue, suggestion}], "
    "strengths: [], weaknesses: [], recommendations: [], missing_info: [], "
    "publish_ready: boolean, summary: string}."
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
        return ai_mod.chat_json(VALIDATOR_TEXT_SYSTEM, f"Review this content:\n\n{content}", max_tokens=2500)
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
