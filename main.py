import io
import traceback
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import DOMAINS, META_MARKETING_TOKEN, META_SOCIAL_TOKEN
from google_auth import get_credentials
import gsc
import ga4
import meta
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
        return meta.get_ad_accounts(META_MARKETING_TOKEN)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


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
