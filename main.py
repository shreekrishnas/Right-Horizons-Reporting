import io
import traceback
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import DOMAINS, META_MARKETING_TOKEN, META_SOCIAL_TOKEN, META_PAGE_ID, META_AD_ACCOUNT
from google_auth import get_credentials
import gsc
import ga4
import meta
import social
import youtube
import linkedin
from exporter import build_report

app = FastAPI(title="Right Horizons Reporting")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _dates(start: str, end: str):
    today = date.today()
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
        raise HTTPException(502, f"GA4 error: {e}")


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
def meta_campaigns(start: str = "", end: str = "", ad_account: str = ""):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    if not ad_account:
        raise HTTPException(400, "ad_account parameter required")
    start, end = _dates(start, end)
    try:
        return meta.get_campaigns_summary(META_MARKETING_TOKEN, ad_account, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


@app.get("/api/meta/daily")
def meta_daily(start: str = "", end: str = "", ad_account: str = ""):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    if not ad_account:
        raise HTTPException(400, "ad_account parameter required")
    start, end = _dates(start, end)
    try:
        return meta.get_daily_spend(META_MARKETING_TOKEN, ad_account, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


@app.get("/api/meta/accounts")
def meta_accounts():
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    try:
        accounts = meta.get_ad_accounts(META_MARKETING_TOKEN)
        if META_AD_ACCOUNT:
            accounts = [a for a in accounts if a["id"] == META_AD_ACCOUNT]
        return accounts
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


# ── Social (Facebook + Instagram) ────────────────────────────────────────────

@app.get("/api/social/pages")
def social_pages():
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        pages = social.get_pages(META_SOCIAL_TOKEN)
        if META_PAGE_ID:
            pages = [p for p in pages if p["id"] == META_PAGE_ID]
        return pages
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/page-insights")
def social_page_insights(page_id: str, start: str = "", end: str = ""):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _dates(start, end)
    try:
        return social.get_page_insights(META_SOCIAL_TOKEN, page_id, start, end)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/page-posts")
def social_page_posts(page_id: str, start: str = "", end: str = "", limit: int = 10):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _dates(start, end)
    try:
        return social.get_page_posts(META_SOCIAL_TOKEN, page_id, start, end, limit)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-account")
def social_ig_account(page_id: str):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        ig_id = social.get_ig_account(META_SOCIAL_TOKEN, page_id)
        if not ig_id:
            raise HTTPException(404, "No Instagram business account linked to this page")
        return {"ig_id": ig_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-profile")
def social_ig_profile(ig_id: str):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        return social.get_ig_profile(META_SOCIAL_TOKEN, ig_id)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-insights")
def social_ig_insights(ig_id: str, start: str = "", end: str = ""):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _dates(start, end)
    try:
        return social.get_ig_insights(META_SOCIAL_TOKEN, ig_id, start, end)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


@app.get("/api/social/ig-media")
def social_ig_media(ig_id: str, limit: int = 10):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    try:
        return social.get_ig_media(META_SOCIAL_TOKEN, ig_id, limit)
    except Exception as e:
        raise HTTPException(502, f"Social API error: {e}")


# ── YouTube ──────────────────────────────────────────────────────────────────

@app.get("/api/youtube/channel")
def youtube_channel():
    try:
        creds = get_credentials()
        return youtube.get_channel_stats(creds)
    except Exception as e:
        raise HTTPException(502, f"YouTube error: {e}")


@app.get("/api/youtube/videos")
def youtube_videos(limit: int = 10):
    try:
        creds = get_credentials()
        return youtube.get_recent_videos(creds, limit)
    except Exception as e:
        raise HTTPException(502, f"YouTube error: {e}")


@app.get("/api/youtube/seo")
def youtube_seo(topic: str = ""):
    if not topic.strip():
        raise HTTPException(400, "topic parameter required")
    return youtube.generate_seo_metadata(topic)


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
    if META_MARKETING_TOKEN:
        try:
            accounts = meta.get_ad_accounts(META_MARKETING_TOKEN)
            if accounts:
                meta_camps = meta.get_campaigns_summary(META_MARKETING_TOKEN, accounts[0]["id"], start, end)
        except Exception:
            pass

    xlsx = build_report(domain, d["label"], start, end, gsc_sum, gsc_q, gsc_p, ga4_sum, ga4_p, ga4_src, meta_camps)
    filename = f"Report_{d['short']}_{start}_{end}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
