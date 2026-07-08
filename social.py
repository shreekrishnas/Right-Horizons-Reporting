import requests
import logging

log = logging.getLogger(__name__)

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


def _get_paged(path: str, token: str, params: dict, max_items: int = 500) -> list:
    """Follow cursor pagination until max_items collected or pages run out."""
    items = []
    after = None
    while len(items) < max_items:
        p = dict(params)
        if after:
            p["after"] = after
        data = _get(path, token, p)
        batch = data.get("data", [])
        if not batch:
            break
        items.extend(batch)
        after = data.get("paging", {}).get("cursors", {}).get("after")
        if not after or not data.get("paging", {}).get("next"):
            break
    return items[:max_items]


# ── Facebook Pages ───────────────────────────────────────────────────────────

def get_pages(token: str) -> list:
    data = _get("/me/accounts", token, {"fields": "id,name,fan_count,followers_count"})
    return data.get("data", [])


def resolve_page_token(token: str, page_id: str) -> str:
    """Exchange a user/admin token for a page-specific access token.

    A page access token only works for its own page. When the shared token
    belongs to a user who admins multiple pages (RH, PMS, AIF), asking the
    target page for its access_token yields a token that works for that
    page's insights. Falls back to the original token on any failure.
    """
    try:
        data = _get(f"/{page_id}", token, {"fields": "access_token"})
        return data.get("access_token") or token
    except Exception as e:
        log.debug("resolve_page_token failed for %s: %s", page_id, e)
        return token


def diagnose_page_access(token: str, page_id: str) -> dict:
    """Report whether the token can read the page and its insights."""
    out = {"page_id": page_id, "page_ok": False, "insights_ok": False, "ig_linked": False}
    try:
        page = _get(f"/{page_id}", token, {"fields": "name,followers_count"})
        out["page_ok"] = True
        out["page_name"] = page.get("name", "")
    except Exception as e:
        out["error"] = str(e)[:300]
        return out
    p_token = resolve_page_token(token, page_id)
    out["page_token_resolved"] = p_token != token

    # Probe a focused set of FB page-insight metrics and report which are
    # actually valid on this API version — deprecations vary by version.
    # THROTTLED: small delay between calls + trimmed candidate list, so this
    # does not look like a burst and re-trip Meta's "unusual activity" guard.
    import datetime as _dt, time as _time
    until = _dt.date.today()
    since = until - _dt.timedelta(days=30)
    fb_candidates = [
        "page_impressions", "page_impressions_unique",
        "page_post_engagements", "page_fan_adds_unique",
        "page_daily_follows_unique", "page_views_total",
    ]
    valid, invalid = [], {}
    for m in fb_candidates:
        try:
            _get(f"/{page_id}/insights", p_token, {
                "metric": m, "period": "day",
                "since": since.isoformat(), "until": until.isoformat(),
            })
            valid.append(m)
        except Exception as e:
            invalid[m] = str(e)[:120]
        _time.sleep(0.4)
    out["fb_valid_metrics"] = valid
    out["fb_invalid_metrics"] = list(invalid.keys())
    out["insights_ok"] = bool(valid)

    try:
        ig = _get(f"/{page_id}", p_token, {"fields": "instagram_business_account"})
        ig_acct = ig.get("instagram_business_account")
        out["ig_linked"] = bool(ig_acct)
        if ig_acct:
            ig_id = ig_acct["id"]
            ig_candidates = ["reach", "views", "accounts_engaged", "total_interactions", "follows_and_unfollows", "follower_count"]
            ig_valid, ig_invalid = [], []
            for m in ig_candidates:
                try:
                    _get(f"/{ig_id}/insights", p_token, {
                        "metric": m, "period": "day", "metric_type": "total_value",
                        "since": since.isoformat(), "until": until.isoformat(),
                    })
                    ig_valid.append(m)
                except Exception:
                    ig_invalid.append(m)
                _time.sleep(0.4)
            out["ig_valid_metrics"] = ig_valid
            out["ig_invalid_metrics"] = ig_invalid
    except Exception as e:
        out["ig_error"] = str(e)[:300]
    return out


def get_fb_light(token: str, page_id: str, start: str, end: str) -> dict:
    """Fast Facebook snapshot for a window — batched insights, no post
    pagination. Used to fetch several time windows for the AI assistant."""
    tok = resolve_page_token(token, page_id)
    res = {}
    try:
        page = _get(f"/{page_id}", tok, {"fields": "fan_count,followers_count"})
        res["followers"] = page.get("followers_count", 0)
        res["page_likes"] = page.get("fan_count", 0)
    except Exception:
        pass
    try:
        data = _get(f"/{page_id}/insights", tok, {
            "metric": "page_post_engagements,page_views_total",
            "period": "total_over_range", "since": start, "until": end,
        })
        for item in data.get("data", []):
            v = item.get("values", [{}])[0].get("value", 0)
            res[item["name"]] = v if not isinstance(v, dict) else sum(v.values())
    except Exception:
        pass
    res["new_followers"] = None
    try:
        data = _get(f"/{page_id}/insights", tok, {
            "metric": "page_daily_follows_unique", "period": "day",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            res["new_followers"] = sum(x.get("value", 0) for x in item.get("values", []))
    except Exception:
        pass
    eng = res.get("page_post_engagements", 0)
    foll = res.get("followers", 0) or res.get("page_likes", 0)
    res["engagements"] = eng
    res["views"] = res.get("page_views_total", 0)
    res["engagement_rate_pct"] = round(eng / foll * 100, 2) if foll else 0
    return res


def get_ig_light(token: str, ig_id: str, start: str, end: str) -> dict:
    """Fast Instagram snapshot for a window — batched insights, no media
    pagination. Used for multi-window fetches for the AI assistant."""
    res = {}
    try:
        prof = _get(f"/{ig_id}", token, {"fields": "followers_count,media_count"})
        res["followers"] = prof.get("followers_count", 0)
        res["total_media"] = prof.get("media_count", 0)
    except Exception:
        pass
    try:
        data = _get(f"/{ig_id}/insights", token, {
            "metric": "reach,views,accounts_engaged,total_interactions",
            "period": "day", "metric_type": "total_value", "since": start, "until": end,
        })
        for item in data.get("data", []):
            v = item.get("total_value", {}).get("value", 0)
            res[item["name"]] = v if not isinstance(v, dict) else 0
    except Exception:
        pass
    res["new_followers"] = None
    try:
        data = _get(f"/{ig_id}/insights", token, {
            "metric": "follows_and_unfollows", "period": "day",
            "metric_type": "total_value", "breakdown": "follow_type",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            f = u = 0
            for bd in item.get("total_value", {}).get("breakdowns", []):
                for r in bd.get("results", []):
                    dims = " ".join(str(x).upper() for x in r.get("dimension_values", []))
                    val = r.get("value", 0)
                    if "NON_FOLLOWER" in dims:
                        u += val
                    elif "FOLLOWER" in dims:
                        f += val
            if f or u:
                res["new_followers"] = f - u
    except Exception:
        pass
    reach = res.get("reach", 0)
    eng = res.get("total_interactions", 0) or res.get("accounts_engaged", 0)
    res["engagements"] = eng
    res["views"] = res.get("views", 0) or reach
    res["engagement_rate_pct"] = round(eng / reach * 100, 2) if reach else 0
    return res


def get_fb_comprehensive(token: str, page_id: str, start: str, end: str) -> dict:
    token = resolve_page_token(token, page_id)
    page = _get(f"/{page_id}", token, {"fields": "name,fan_count,followers_count"})
    result = {
        "page_name": page.get("name", ""),
        "followers": page.get("followers_count", 0),
        "page_likes": page.get("fan_count", 0),
    }

    # Only metrics confirmed valid on the current Graph API version (diagnose
    # probe): page_post_engagements, page_views_total. Meta deprecated
    # page_impressions / page_impressions_unique (reach) and page_consumptions.
    _metrics_total = [
        "page_post_engagements",
        "page_views_total",
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
        except Exception as e:
            log.debug("FB metric %s failed: %s", metric, e)

    # New followers: page_daily_follows_unique (page_fan_adds is deprecated)
    # new_followers stays None (→ "—") unless the API genuinely returns it.
    result["new_followers_raw"] = None
    try:
        data = _get(f"/{page_id}/insights", token, {
            "metric": "page_daily_follows_unique", "period": "day",
            "since": start, "until": end,
        })
        for item in data.get("data", []):
            result["new_followers_raw"] = sum(v.get("value", 0) for v in item.get("values", []))
    except Exception as e:
        log.debug("FB page_daily_follows_unique failed: %s", e)

    # Fetch posts (paginated + de-duped by id, filtered strictly to the range)
    try:
        posts_list = _get_paged(f"/{page_id}/posts", token, {
            "fields": "id,created_time,shares",
            "since": start, "until": end, "limit": 100,
        })
        seen, uniq = set(), []
        for p in posts_list:
            pid = p.get("id")
            d = p.get("created_time", "")[:10]
            if pid and pid not in seen and (not d or start <= d <= end):
                seen.add(pid)
                uniq.append(p)
        result["posts_published"] = len(uniq)
        result["total_shares"] = sum(p.get("shares", {}).get("count", 0) for p in uniq)
    except Exception:
        result["posts_published"] = 0
        result["total_shares"] = 0

    try:
        vids = _get(f"/{page_id}/videos", token, {
            "fields": "id", "since": start, "until": end, "limit": 100, "type": "uploaded",
        })
        result["reels_stories"] = len(vids.get("data", []))
    except Exception:
        result["reels_stories"] = 0

    eng = result.get("page_post_engagements", 0)
    followers = result.get("followers", 0) or result.get("page_likes", 0)
    # FB page reach/impressions are no longer exposed by the API, so engagement
    # rate is measured against total followers (a standard alternate definition).
    result["engagement_rate"] = round((eng / followers * 100), 2) if followers > 0 else 0
    result["new_followers"] = result.get("new_followers_raw")  # None if unavailable
    result["reach"] = None            # not available on current Graph API
    result["engagements"] = eng
    result["views"] = result.get("page_views_total", 0)
    result["video_views"] = None      # page_video_views deprecated
    result["link_clicks"] = None      # page_consumptions deprecated
    result["profile_visits"] = result.get("page_views_total", 0)
    result["saves_shares"] = result.get("total_shares", 0)

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
    token = resolve_page_token(token, page_id)
    data = _get(f"/{page_id}", token, {"fields": "instagram_business_account"})
    ig = data.get("instagram_business_account")
    return ig["id"] if ig else None


def get_ig_profile(token: str, ig_id: str) -> dict:
    return _get(f"/{ig_id}", token, {
        "fields": "username,name,followers_count,follows_count,media_count,biography,website,profile_picture_url",
    })


def get_ig_insights(token: str, ig_id: str, start: str, end: str) -> dict:
    return get_ig_comprehensive(token, ig_id, start, end)


def get_ig_comprehensive(token: str, ig_id: str, start: str, end: str, fast: bool = False) -> dict:
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

    # Valid on current Graph API (diagnose probe): reach, views,
    # accounts_engaged, total_interactions. 'impressions' is deprecated
    # (replaced by 'views'). The remaining ones are kept in the per-metric
    # try/except so they populate where still supported and skip otherwise.
    _ig_metrics = [
        "reach", "views", "accounts_engaged", "total_interactions",
        "follows_and_unfollows", "profile_views", "website_clicks",
    ]
    # new_followers stays None (→ "—") unless the API genuinely returns it.
    result["new_followers"] = None
    for metric in _ig_metrics:
        try:
            params = {
                "metric": metric, "period": "day",
                "metric_type": "total_value",
                "since": start, "until": end,
            }
            # follows_and_unfollows needs the follow_type breakdown to return data
            if metric == "follows_and_unfollows":
                params["breakdown"] = "follow_type"
            data = _get(f"/{ig_id}/insights", token, params)
            for item in data.get("data", []):
                tv = item.get("total_value", {})
                val = tv.get("value", 0)
                if metric == "follows_and_unfollows":
                    follows = unfollows = 0
                    for bd in tv.get("breakdowns", []):
                        for r in bd.get("results", []):
                            # Instagram returns follow_type = "FOLLOWER" (accounts
                            # that followed = gains) and "NON_FOLLOWER" (accounts
                            # that unfollowed = losses). Check NON_FOLLOWER/UNFOLLOW
                            # first since both contain the substring "FOLLOW".
                            dims = " ".join(str(x).upper() for x in r.get("dimension_values", []))
                            v = r.get("value", 0)
                            if "NON_FOLLOWER" in dims or "UNFOLLOW" in dims:
                                unfollows += v
                            elif "FOLLOWER" in dims or "FOLLOW" in dims:
                                follows += v
                    if follows or unfollows:
                        result["new_followers"] = follows - unfollows
                    elif isinstance(val, dict):
                        result["new_followers"] = val.get("follows", 0) - val.get("unfollows", 0)
                    elif isinstance(val, (int, float)):
                        result["new_followers"] = val
                else:
                    result[item["name"]] = val if not isinstance(val, dict) else 0
        except Exception as e:
            log.debug("IG metric %s failed: %s", metric, e)
            if metric != "follows_and_unfollows":
                result.setdefault(metric, 0)

    # Fetch ALL media, then filter strictly by date — deterministic, so
    # collaboration posts (which carry the original post date and can appear
    # out of order) are counted the same way every run.
    def _fetch_media():
        collected = []
        after = None
        past_pages = 0
        for _ in range(8):  # bounded for serverless speed
            p = {"fields": "id,timestamp,media_type,media_product_type,like_count,comments_count", "limit": 100}
            if after:
                p["after"] = after
            data = _get(f"/{ig_id}/media", token, p)
            batch = data.get("data", [])
            collected.extend(batch)
            # Stop once a whole page predates the range; one extra page as a
            # safety net for out-of-order collaboration posts.
            newest = batch[0].get("timestamp", "")[:10] if batch else ""
            if newest and newest < start:
                past_pages += 1
            after = data.get("paging", {}).get("cursors", {}).get("after")
            if not after or not batch or past_pages >= 1:
                break
        return collected
    all_media = _safe(_fetch_media, [])
    # De-dupe by id (collab posts can appear twice) and filter to the range
    seen_ids = set()
    media = []
    for m in all_media:
        mid = m.get("id")
        d = m.get("timestamp", "")[:10]
        if mid and mid not in seen_ids and start <= d <= end:
            seen_ids.add(mid)
            media.append(m)

    result["posts_published"] = len(media)
    video_media = [m for m in media if m.get("media_type") in ("VIDEO", "REELS", "REEL")]
    result["reels_stories"] = len(video_media)
    total_likes = sum(m.get("like_count", 0) for m in media)
    total_comments = sum(m.get("comments_count", 0) for m in media)
    # Prefer total_interactions (valid), then accounts_engaged, then computed
    result["engagements"] = (result.get("total_interactions", 0)
                             or result.get("accounts_engaged", 0)
                             or (total_likes + total_comments))

    reach = result.get("reach", 0)
    views = result.get("views", 0)  # Meta's replacement for 'impressions'

    result["views"] = views if views > 0 else reach
    result["video_views"] = views if (views > 0 and len(video_media) > 0) else 0
    result["link_clicks"] = result.get("website_clicks", 0)

    # Saves require one insights call PER post (slow). Skip in fast mode
    # (the report doesn't use saves_shares) to avoid serverless timeouts.
    total_saves = 0
    if not fast:
        for m in media[:50]:
            try:
                mi = _get(f"/{m['id']}/insights", token, {"metric": "saved"})
                for item in mi.get("data", []):
                    vals = item.get("values", [])
                    if vals:
                        total_saves += vals[0].get("value", 0)
            except Exception:
                pass
    result["saves_shares"] = total_saves

    eng = result.get("engagements", 0)
    result["engagement_rate"] = round((eng / reach * 100), 2) if reach > 0 else 0
    result["reach"] = reach
    result["profile_visits"] = result.get("profile_views", 0)
    # CTR = website clicks / views (impressions equivalent)
    clicks = result.get("website_clicks", 0) or 0
    denom = result.get("views", 0) or reach
    result["ctr"] = round((clicks / denom * 100), 2) if denom else 0

    return result


def get_ig_media(token: str, ig_id: str, limit: int = 10) -> list:
    data = _get(
        f"/{ig_id}/media", token,
        {"fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count", "limit": limit},
    )
    return data.get("data", [])
