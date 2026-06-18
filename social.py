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

    # Try each metric individually with total_over_range
    _metrics_total = [
        "page_post_engagements",
        "page_views_total",
        "page_video_views",
        "page_impressions",
        "page_impressions_unique",   # unique reach (replaces deprecated page_reach)
        "page_consumptions",          # link/content clicks
        "page_consumptions_unique",
    ]
    for metric in _metrics_total:
        try:
            data = _get(f"/{page_id}/insights", token, {
                "metric": metric, "period": "total_over_range",
                "since": start, "until": end,
            })
            for item in data.get("data", []):
                val = item.get("values", [{}])[0].get("value", 0)
                result[item["name"]] = val if not isinstance(val, dict) else sum(val.values())
        except Exception:
            pass

    # page_fan_adds: day period, sum daily values
    try:
        data = _get(f"/{page_id}/insights", token, {
            "metric": "page_fan_adds", "period": "day",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            result["page_fan_adds"] = sum(v.get("value", 0) for v in item.get("values", []))
    except Exception:
        result.setdefault("page_fan_adds", 0)

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

    # Reach: unique impressions is the closest v21.0 equivalent to reach
    reach = (
        result.get("page_impressions_unique") or
        result.get("page_impressions") or
        0
    )
    eng = result.get("page_post_engagements", 0)
    new_followers = result.get("page_fan_adds", 0)
    link_clicks = (
        result.get("page_consumptions_unique") or
        result.get("page_consumptions") or
        0
    )

    result["engagement_rate"] = round((eng / reach * 100), 2) if reach > 0 else 0
    result["new_followers"] = new_followers
    result["reach"] = reach
    result["engagements"] = eng
    result["views"] = result.get("page_views_total", 0)
    result["video_views"] = result.get("page_video_views", 0)
    result["link_clicks"] = link_clicks
    result["profile_visits"] = result.get("page_views_total", 0)
    result["saves_shares"] = 0

    return result


def get_page_posts(token: str, page_id: str, start: str, end: str, limit: int = 10) -> list:
    data = _get(
        f"/{page_id}/posts", token,
        {
            "fields": "id,message,created_time,shares,permalink_url,"
                       "likes.summary(true).limit(0),"
                       "comments.summary(true).limit(0),"
                       "reactions.summary(true).limit(0)",
            "since": start, "until": end, "limit": limit,
        },
    )
    posts = []
    for p in data.get("data", []):
        likes = p.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
        reactions = p.get("reactions", {}).get("summary", {}).get("total_count", 0)
        shares = p.get("shares", {}).get("count", 0)
        row = {
            "id": p["id"],
            "message": (p.get("message") or "")[:120],
            "created_time": p.get("created_time", ""),
            "permalink": p.get("permalink_url", ""),
            "shares": shares,
            "post_impressions": reactions + shares,
            "post_engaged_users": likes + comments + shares,
            "post_clicks": reactions,
        }
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

    _ig_metrics = [
        "impressions", "reach", "accounts_engaged",
        "follows_and_unfollows", "profile_views", "website_clicks",
    ]
    for metric in _ig_metrics:
        try:
            data = _get(f"/{ig_id}/insights", token, {
                "metric": metric, "period": "day",
                "metric_type": "total_value",
                "since": start, "until": end,
            })
            for item in data.get("data", []):
                tv = item.get("total_value", {})
                val = tv.get("value", 0)
                if metric == "follows_and_unfollows":
                    # value may be net int, or breakdowns may contain follows/unfollows
                    follows = unfollows = 0
                    for bd in tv.get("breakdowns", []):
                        for r in bd.get("results", []):
                            dims = r.get("dimension_values", [])
                            v = r.get("value", 0)
                            if "FOLLOW" in dims:
                                follows += v
                            elif "UNFOLLOW" in dims:
                                unfollows += v
                    if follows or unfollows:
                        result["new_followers"] = follows - unfollows
                    elif isinstance(val, dict):
                        result["new_followers"] = val.get("follows", 0) - val.get("unfollows", 0)
                    else:
                        result["new_followers"] = val
                else:
                    result[item["name"]] = val if not isinstance(val, dict) else 0
        except Exception:
            if metric == "follows_and_unfollows":
                result.setdefault("new_followers", 0)
            else:
                result.setdefault(metric, 0)

    all_media = _safe(lambda: _get(f"/{ig_id}/media", token, {
        "fields": "id,timestamp,media_type,like_count,comments_count",
        "limit": 100,
    }).get("data", []), [])
    media = [m for m in all_media if start <= m.get("timestamp", "")[:10] <= end]

    result["posts_published"] = len(media)
    video_media = [m for m in media if m.get("media_type") in ("VIDEO", "REELS", "REEL")]
    result["reels_stories"] = len(video_media)
    total_likes = sum(m.get("like_count", 0) for m in media)
    total_comments = sum(m.get("comments_count", 0) for m in media)
    result["engagements"] = result.get("accounts_engaged", 0) or (total_likes + total_comments)

    reach = result.get("reach", 0)
    impressions = result.get("impressions", 0)

    # views = impressions if available, otherwise reach (both measure content visibility)
    result["views"] = impressions if impressions > 0 else reach
    # video_views: use impressions proportional to video posts, or reels count as proxy
    result["video_views"] = impressions if (impressions > 0 and len(video_media) > 0) else 0
    result["link_clicks"] = result.get("website_clicks", 0)
    result["saves_shares"] = 0

    eng = result.get("engagements", 0)
    result["engagement_rate"] = round((eng / reach * 100), 2) if reach > 0 else 0
    result["reach"] = reach

    return result


def get_ig_media(token: str, ig_id: str, limit: int = 10) -> list:
    data = _get(
        f"/{ig_id}/media", token,
        {"fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count", "limit": limit},
    )
    return data.get("data", [])
