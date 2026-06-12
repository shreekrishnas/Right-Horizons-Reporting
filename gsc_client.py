from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _service(creds_dict: dict):
    creds = Credentials(
        token=creds_dict["token"],
        refresh_token=creds_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_dict["client_id"],
        client_secret=creds_dict["client_secret"],
        scopes=creds_dict.get("scopes"),
    )
    return build("webmasters", "v3", credentials=creds, cache_discovery=False)


def get_summary(creds_dict: dict, site_url: str, start_date: str, end_date: str) -> dict:
    svc = _service(creds_dict)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": [],
        "rowLimit": 1,
    }
    resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    row = resp.get("rows", [{}])[0] if resp.get("rows") else {}
    return {
        "clicks":      round(row.get("clicks", 0)),
        "impressions": round(row.get("impressions", 0)),
        "ctr":         round(row.get("ctr", 0) * 100, 2),
        "position":    round(row.get("position", 0), 1),
    }


def get_top_queries(creds_dict: dict, site_url: str, start_date: str, end_date: str, limit: int = 10) -> list:
    svc = _service(creds_dict)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": limit,
        "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
    }
    resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return [
        {
            "query":       r["keys"][0],
            "clicks":      round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr":         round(r.get("ctr", 0) * 100, 2),
            "position":    round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_top_pages(creds_dict: dict, site_url: str, start_date: str, end_date: str, limit: int = 10) -> list:
    svc = _service(creds_dict)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": limit,
        "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
    }
    resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return [
        {
            "page":        r["keys"][0],
            "clicks":      round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr":         round(r.get("ctr", 0) * 100, 2),
            "position":    round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_daily_clicks(creds_dict: dict, site_url: str, start_date: str, end_date: str) -> list:
    svc = _service(creds_dict)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["date"],
        "rowLimit": 500,
        "orderBy": [{"fieldName": "date", "sortOrder": "ASCENDING"}],
    }
    resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return [
        {"date": r["keys"][0], "clicks": round(r.get("clicks", 0)), "impressions": round(r.get("impressions", 0))}
        for r in resp.get("rows", [])
    ]
