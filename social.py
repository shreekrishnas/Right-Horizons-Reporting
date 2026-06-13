import requests

BASE = "https://graph.facebook.com/v21.0"


def _get(path: str, token: str, params: dict = None) -> dict:
    params = params or {}
    params["access_token"] = token
    resp = requests.get(f"{BASE}{path}", params=params, timeout=30)
    if not resp.ok:
        try:
            err = resp.json().get("error", {})
            msg = err.get("message", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Meta API ({resp.status_code}): {msg}")
    return resp.json()


# ── Facebook Pages ───────────────────────────────────────────────────────────

def get_pages(token: str) -> list:
    data = _get("/me/accounts", token, {"fields": "id,name,fan_count,followers_count"})
    return data.get("data", [])


def get_page_insights(token: str, page_id: str, start: str, end: str) -> dict:
    metrics = "page_impressions,page_engaged_users,page_fans,page_views_total,page_post_engagements"
    data = _get(
        f"/{page_id}/insights", token,
        {"metric": metrics, "period": "total_over_range", "since": start, "until": end},
    )
    result = {}
    for item in data.get("data", []):
        val = item.get("values", [{}])[0].get("value", 0)
        result[item["name"]] = val
    return result


def get_page_posts(token: str, page_id: str, start: str, end: str, limit: int = 10) -> list:
    data = _get(
        f"/{page_id}/posts", token,
        {
            "fields": "id,message,created_time,shares,permalink_url",
            "since": start, "until": end, "limit": limit,
        },
    )
    posts = []
    for p in data.get("data", []):
        row = {
            "id": p["id"],
            "message": (p.get("message") or "")[:120],
            "created_time": p.get("created_time", ""),
            "permalink": p.get("permalink_url", ""),
            "shares": p.get("shares", {}).get("count", 0),
        }
        try:
            ins = _get(
                f"/{p['id']}/insights", token,
                {"metric": "post_impressions,post_engaged_users,post_clicks"},
            )
            for item in ins.get("data", []):
                val = item.get("values", [{}])[0].get("value", 0)
                row[item["name"]] = val
        except Exception:
            row.update({"post_impressions": 0, "post_engaged_users": 0, "post_clicks": 0})
        posts.append(row)
    return posts


# ── Instagram ────────────────────────────────────────────────────────────────

def get_ig_account(token: str, page_id: str) -> str | None:
    data = _get(f"/{page_id}", token, {"fields": "instagram_business_account"})
    ig = data.get("instagram_business_account")
    return ig["id"] if ig else None


def get_ig_profile(token: str, ig_id: str) -> dict:
    return _get(
        f"/{ig_id}", token,
        {"fields": "username,name,followers_count,follows_count,media_count"},
    )


def get_ig_insights(token: str, ig_id: str, start: str, end: str) -> dict:
    data = _get(
        f"/{ig_id}/insights", token,
        {
            "metric": "impressions,reach,accounts_engaged",
            "period": "day",
            "metric_type": "total_value",
            "since": start, "until": end,
        },
    )
    result = {}
    for item in data.get("data", []):
        val = item.get("total_value", {}).get("value", 0)
        result[item["name"]] = val
    return result


def get_ig_media(token: str, ig_id: str, limit: int = 10) -> list:
    data = _get(
        f"/{ig_id}/media", token,
        {"fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count", "limit": limit},
    )
    return data.get("data", [])
