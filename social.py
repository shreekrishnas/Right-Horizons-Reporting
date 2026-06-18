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


def _safe(fn, default=0):
    try:
        return fn()
    except Exception:
        return default


# ── Facebook Pages ───────────────────────────────────────────────────────────

def get_pages(token: str) -> list:
    data = _get("/me/accounts", token, {"fields": "id,name,fan_count,followers_count"})
    return data.get("data", [])


def get_fb_comprehensive(token: str, page_id: str, start: str, end: str) -> dict:
    page = _get(f"/{page_id}", token, {"fields": "name,fan_count,followers_count"})
    result = {
        "page_name": page.get("name", ""),
        "followers": page.get("followers_count", 0),
        "page_likes": page.get("fan_count", 0),
    }

    # v21.0 valid metrics — try each individually to get what works
    _metrics_total = [
        ("page_post_engagements", "total_over_range"),
        ("page_views_total", "total_over_range"),
        ("page_video_views", "total_over_range"),
        ("page_fan_adds", "total_over_range"),
        ("page_impressions", "total_over_range"),
        ("page_reach", "total_over_range"),
    ]
    for metric, period in _metrics_total:
        try:
            data = _get(f"/{page_id}/insights", token, {
                "metric": metric, "period": period,
                "since": start, "until": end,
            })
            for item in data.get("data", []):
                val = item.get("values", [{}])[0].get("value", 0)
                result[item["name"]] = val if not isinstance(val, dict) else sum(val.values())
        except Exception:
            pass

    try:
        posts_data = _get(f"/{page_id}/posts", token, {
            "fields": "id", "since": start, "until": end, "limit": 100,
        })
        result["posts_published"] = len(posts_data.get("data", []))
    except Exception:
        result["posts_published"] = 0

    try:
        vids = _get(f"/{page_id}/videos", token, {
            "fields": "id", "since": start, "until": end, "limit": 100, "type": "uploaded",
        })
        result["reels_stories"] = len(vids.get("data", []))
    except Exception:
        result["reels_stories"] = 0

    reach = result.get("page_reach") or result.get("page_impressions", 0)
    eng = result.get("page_post_engagements", 0)
    new_followers = result.get("page_fan_adds", 0)

    result["engagement_rate"] = round((eng / reach * 100), 2) if reach > 0 else 0
    result["new_followers"] = new_followers
    result["reach"] = reach
    result["engagements"] = eng
    result["views"] = result.get("page_views_total", 0)
    result["video_views"] = result.get("page_video_views", 0)
    result["link_clicks"] = result.get("page_consumptions", 0)
    result["profile_visits"] = result.get("page_views_total", 0)
    result["saves_shares"] = 0

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


def get_ig_comprehensive(token: str, ig_id: str, start: str, end: str) -> dict:
    profile = _get(f"/{ig_id}", token, {
        "fields": "username,name,followers_count,follows_count,media_count",
    })
    result = {
        "username": profile.get("username", ""),
        "name": profile.get("name", ""),
        "followers": profile.get("followers_count", 0),
        "follows": profile.get("follows_count", 0),
        "total_media": profile.get("media_count", 0),
    }

    try:
        data = _get(f"/{ig_id}/insights", token, {
            "metric": "impressions,reach,accounts_engaged",
            "period": "day", "metric_type": "total_value",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            result[item["name"]] = item.get("total_value", {}).get("value", 0)
    except Exception:
        result.update({"impressions": 0, "reach": 0, "accounts_engaged": 0})

    try:
        data = _get(f"/{ig_id}/insights", token, {
            "metric": "follows_and_unfollows",
            "period": "day", "metric_type": "total_value",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            val = item.get("total_value", {}).get("value", 0)
            if isinstance(val, dict):
                result["new_followers"] = val.get("follows", 0) - val.get("unfollows", 0)
            else:
                result["new_followers"] = val
    except Exception:
        result["new_followers"] = 0

    try:
        data = _get(f"/{ig_id}/insights", token, {
            "metric": "profile_views,website_clicks",
            "period": "day", "metric_type": "total_value",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            result[item["name"]] = item.get("total_value", {}).get("value", 0)
    except Exception:
        result.setdefault("profile_views", 0)
        result.setdefault("website_clicks", 0)

    media = _safe(lambda: _get(f"/{ig_id}/media", token, {
        "fields": "id,timestamp,media_type,like_count,comments_count",
        "since": start, "until": end, "limit": 100,
    }).get("data", []), [])

    result["posts_published"] = len(media)
    result["reels_stories"] = sum(1 for m in media if m.get("media_type") in ("VIDEO", "REELS"))
    total_likes = sum(m.get("like_count", 0) for m in media)
    total_comments = sum(m.get("comments_count", 0) for m in media)
    result["engagements"] = result.get("accounts_engaged", 0) or (total_likes + total_comments)
    result["video_views"] = result.get("impressions", 0)
    result["link_clicks"] = result.get("website_clicks", 0)
    result["saves_shares"] = 0

    reach = result.get("reach", 0)
    eng = result.get("engagements", 0)
    result["engagement_rate"] = round((eng / reach * 100), 2) if reach > 0 else 0
    result["views"] = result.get("impressions", 0)

    return result


def get_ig_media(token: str, ig_id: str, limit: int = 10) -> list:
    data = _get(
        f"/{ig_id}/media", token,
        {"fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count", "limit": limit},
    )
    return data.get("data", [])
