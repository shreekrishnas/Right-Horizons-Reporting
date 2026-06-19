from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _service(creds: Credentials):
    return build("webmasters", "v3", credentials=creds, cache_discovery=False)


def get_summary(creds: Credentials, site_url: str, start: str, end: str) -> dict:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={"startDate": start, "endDate": end, "dimensions": [], "rowLimit": 1},
    ).execute()
    row = (resp.get("rows") or [{}])[0] if resp.get("rows") else {}
    return {
        "clicks": round(row.get("clicks", 0)),
        "impressions": round(row.get("impressions", 0)),
        "ctr": round(row.get("ctr", 0) * 100, 2),
        "position": round(row.get("position", 0), 1),
    }


def get_top_queries(creds: Credentials, site_url: str, start: str, end: str, limit: int = 10) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["query"], "rowLimit": limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        },
    ).execute()
    return [
        {
            "query": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_top_pages(creds: Credentials, site_url: str, start: str, end: str, limit: int = 10) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["page"], "rowLimit": limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        },
    ).execute()
    return [
        {
            "page": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_daily(creds: Credentials, site_url: str, start: str, end: str) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["date"], "rowLimit": 500,
            "orderBy": [{"fieldName": "date", "sortOrder": "ASCENDING"}],
        },
    ).execute()
    return [
        {
            "date": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def list_sites(creds: Credentials) -> list:
    svc = _service(creds)
    resp = svc.sites().list().execute()
    return [s["siteUrl"] for s in resp.get("siteEntry", [])]
