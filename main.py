import json
import os
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import io

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_SCOPES, DOMAINS, META_MARKETING_TOKEN, META_SOCIAL_TOKEN, GOOGLE_REFRESH_TOKEN
import gsc_client
import ga4_client
import meta_client
from exporter import build_report

# Allow HTTP for local dev
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

app = FastAPI(title="Right Horizons Reports")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Simple in-process token store (single-user tool — no DB needed)
_token_store: dict = {}


def _flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


def _creds() -> Optional[dict]:
    c = _token_store.get("creds")
    if c:
        return c
    if GOOGLE_REFRESH_TOKEN:
        return {
            "token":         None,
            "refresh_token": GOOGLE_REFRESH_TOKEN,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "scopes":        GOOGLE_SCOPES,
        }
    return None


def _require_creds():
    c = _creds()
    if not c:
        raise HTTPException(status_code=401, detail="Not authenticated. Visit /auth/google first.")
    return c


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/auth/google")
def auth_google():
    flow = _flow()
    flow.oauth2session.compliance_hook.add(lambda r: r)
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return RedirectResponse(url)


@app.get("/auth/google/callback")
def auth_callback(code: str, request: Request):
    flow = _flow()
    flow.fetch_token(code=code)
    creds: Credentials = flow.credentials
    _token_store["creds"] = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "client_id":     GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "scopes":        list(creds.scopes or GOOGLE_SCOPES),
    }
    return RedirectResponse("/?connected=1")


@app.get("/auth/status")
def auth_status():
    return {"connected": bool(_creds()), "mode": "refresh_token" if (not _token_store.get("creds") and GOOGLE_REFRESH_TOKEN) else "oauth"}


@app.post("/auth/disconnect")
def auth_disconnect():
    _token_store.clear()
    return {"ok": True}


# ── Domain config ─────────────────────────────────────────────────────────────

@app.get("/api/domains")
def get_domains():
    return {k: {kk: vv for kk, vv in v.items() if kk != "gsc_site"} for k, v in DOMAINS.items()}


# ── GSC ───────────────────────────────────────────────────────────────────────

@app.get("/api/debug/token")
def debug_token():
    c = _token_store.get("creds")
    if not c:
        return {"stored": False, "message": "No token in memory. Visit /auth/google first."}
    return {"stored": True, "refresh_token": c.get("refresh_token"), "token_prefix": (c.get("token") or "")[:20]}


@app.get("/api/debug/gsc")
def debug_gsc():
    import traceback
    creds = _creds()
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        c = Credentials(
            token=creds.get("token") if creds else None,
            refresh_token=creds.get("refresh_token") if creds else None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds.get("client_id") if creds else None,
            client_secret=creds.get("client_secret") if creds else None,
            scopes=creds.get("scopes") if creds else None,
        )
        c.refresh(Request())
        return {"ok": True, "token_prefix": c.token[:20] if c.token else None, "valid": c.valid}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


@app.get("/api/gsc/summary")
def gsc_summary(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    if domain not in DOMAINS:
        raise HTTPException(400, "Unknown domain key")
    start, end = _resolve_dates(start, end)
    return gsc_client.get_summary(creds, DOMAINS[domain]["gsc_site"], start, end)


@app.get("/api/gsc/queries")
def gsc_queries(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    creds = _require_creds()
    start, end = _resolve_dates(start, end)
    return gsc_client.get_top_queries(creds, DOMAINS[domain]["gsc_site"], start, end, limit)


@app.get("/api/gsc/pages")
def gsc_pages(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    creds = _require_creds()
    start, end = _resolve_dates(start, end)
    return gsc_client.get_top_pages(creds, DOMAINS[domain]["gsc_site"], start, end, limit)


@app.get("/api/gsc/daily")
def gsc_daily(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    start, end = _resolve_dates(start, end)
    return gsc_client.get_daily_clicks(creds, DOMAINS[domain]["gsc_site"], start, end)


# ── GA4 ───────────────────────────────────────────────────────────────────────

@app.get("/api/ga4/summary")
def ga4_summary(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    prop = DOMAINS[domain]["ga4_property"]
    if not prop:
        raise HTTPException(400, f"GA4 property ID not configured for '{domain}'. Set GA4_PROPERTY_{domain.upper()} in .env")
    start, end = _resolve_dates(start, end)
    return ga4_client.get_summary(creds, prop, start, end)


@app.get("/api/ga4/pages")
def ga4_pages(domain: str = "rh", start: str = "", end: str = "", limit: int = 10):
    creds = _require_creds()
    prop = DOMAINS[domain]["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    start, end = _resolve_dates(start, end)
    return ga4_client.get_top_pages(creds, prop, start, end, limit)


@app.get("/api/ga4/sources")
def ga4_sources(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    prop = DOMAINS[domain]["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    start, end = _resolve_dates(start, end)
    return ga4_client.get_traffic_sources(creds, prop, start, end)


@app.get("/api/ga4/daily")
def ga4_daily(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    prop = DOMAINS[domain]["ga4_property"]
    if not prop:
        raise HTTPException(400, "GA4 property not configured")
    start, end = _resolve_dates(start, end)
    return ga4_client.get_daily_sessions(creds, prop, start, end)


# ── Meta Marketing API ───────────────────────────────────────────────────────

@app.get("/api/meta/status")
def meta_status():
    return {
        "marketing": bool(META_MARKETING_TOKEN),
        "social":    bool(META_SOCIAL_TOKEN),
    }

@app.get("/api/meta/campaigns")
def meta_campaigns(start: str = "", end: str = ""):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    start, end = _resolve_dates(start, end)
    try:
        return meta_client.get_campaigns_summary(META_MARKETING_TOKEN, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")

@app.get("/api/meta/daily")
def meta_daily(start: str = "", end: str = ""):
    if not META_MARKETING_TOKEN:
        raise HTTPException(400, "Meta Marketing token not configured")
    start, end = _resolve_dates(start, end)
    try:
        return meta_client.get_daily_spend(META_MARKETING_TOKEN, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")

@app.get("/api/meta/pages")
def meta_pages(start: str = "", end: str = ""):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _resolve_dates(start, end)
    try:
        return meta_client.get_page_summary(META_SOCIAL_TOKEN, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")

@app.get("/api/meta/instagram")
def meta_instagram(start: str = "", end: str = ""):
    if not META_SOCIAL_TOKEN:
        raise HTTPException(400, "Meta Social token not configured")
    start, end = _resolve_dates(start, end)
    try:
        return meta_client.get_instagram_summary(META_SOCIAL_TOKEN, start, end)
    except Exception as e:
        raise HTTPException(502, f"Meta API error: {e}")


# ── Export ────────────────────────────────────────────────────────────────────

@app.get("/api/export")
def export_report(domain: str = "rh", start: str = "", end: str = ""):
    creds = _require_creds()
    if domain not in DOMAINS:
        raise HTTPException(400, "Unknown domain key")
    start, end = _resolve_dates(start, end)
    d = DOMAINS[domain]
    prop = d["ga4_property"]

    gsc_sum  = gsc_client.get_summary(creds, d["gsc_site"], start, end)
    gsc_q    = gsc_client.get_top_queries(creds, d["gsc_site"], start, end, 20)
    gsc_p    = gsc_client.get_top_pages(creds, d["gsc_site"], start, end, 20)
    ga4_sum  = ga4_client.get_summary(creds, prop, start, end) if prop else {}
    ga4_p    = ga4_client.get_top_pages(creds, prop, start, end, 20) if prop else []
    ga4_src  = ga4_client.get_traffic_sources(creds, prop, start, end) if prop else []

    xlsx = build_report(domain, d["label"], start, end, gsc_sum, gsc_q, gsc_p, ga4_sum, ga4_p, ga4_src)
    filename = f"RH_Report_{domain.upper()}_{start}_{end}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        return f.read()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_dates(start: str, end: str):
    today = date.today()
    if not end:
        end = today.isoformat()
    if not start:
        start = (today - timedelta(days=27)).isoformat()
    return start, end


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
