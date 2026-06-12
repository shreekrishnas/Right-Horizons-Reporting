import httpx
from datetime import date, timedelta

GRAPH = "https://graph.facebook.com/v19.0"


def _get(path: str, token: str, params: dict = None) -> dict:
    p = {"access_token": token, **(params or {})}
    r = httpx.get(f"{GRAPH}/{path}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Marketing API ─────────────────────────────────────────────────────────────

def get_ad_accounts(token: str) -> list:
    data = _get("me/adaccounts", token, {"fields": "id,name,currency,account_status"})
    return data.get("data", [])


def get_campaigns_summary(token: str, since: str, until: str) -> dict:
    accounts = get_ad_accounts(token)
    if not accounts:
        return {"spend": 0, "impressions": 0, "clicks": 0, "reach": 0, "cpc": 0, "ctr": 0, "campaigns": []}

    total = {"spend": 0.0, "impressions": 0, "clicks": 0, "reach": 0}
    campaigns = []

    for acc in accounts:
        acc_id = acc["id"]
        try:
            ins = _get(f"{acc_id}/insights", token, {
                "fields": "campaign_name,spend,impressions,clicks,reach,cpc,ctr",
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "level": "campaign",
                "limit": 20,
            })
            for row in ins.get("data", []):
                total["spend"]       += float(row.get("spend", 0))
                total["impressions"] += int(row.get("impressions", 0))
                total["clicks"]      += int(row.get("clicks", 0))
                total["reach"]       += int(row.get("reach", 0))
                campaigns.append({
                    "name":        row.get("campaign_name", ""),
                    "spend":       round(float(row.get("spend", 0)), 2),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks":      int(row.get("clicks", 0)),
                    "reach":       int(row.get("reach", 0)),
                    "cpc":         round(float(row.get("cpc", 0)), 2),
                    "ctr":         round(float(row.get("ctr", 0)), 2),
                })
        except Exception:
            continue

    cpc = round(total["spend"] / total["clicks"], 2) if total["clicks"] else 0
    ctr = round(total["clicks"] / total["impressions"] * 100, 2) if total["impressions"] else 0
    return {
        "spend":       round(total["spend"], 2),
        "impressions": total["impressions"],
        "clicks":      total["clicks"],
        "reach":       total["reach"],
        "cpc":         cpc,
        "ctr":         ctr,
        "campaigns":   campaigns,
    }


def get_daily_spend(token: str, since: str, until: str) -> list:
    accounts = get_ad_accounts(token)
    if not accounts:
        return []
    daily: dict = {}
    for acc in accounts:
        try:
            ins = _get(f"{acc['id']}/insights", token, {
                "fields": "spend,impressions,clicks",
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "time_increment": "1",
                "limit": 90,
            })
            for row in ins.get("data", []):
                d = row.get("date_start", "")
                if d not in daily:
                    daily[d] = {"date": d, "spend": 0.0, "impressions": 0, "clicks": 0}
                daily[d]["spend"]       += float(row.get("spend", 0))
                daily[d]["impressions"] += int(row.get("impressions", 0))
                daily[d]["clicks"]      += int(row.get("clicks", 0))
        except Exception:
            continue
    result = sorted(daily.values(), key=lambda x: x["date"])
    for r in result:
        r["spend"] = round(r["spend"], 2)
    return result


# ── Social / Graph API ────────────────────────────────────────────────────────

def get_pages(token: str) -> list:
    data = _get("me/accounts", token, {"fields": "id,name,fan_count,followers_count,category"})
    return data.get("data", [])


def get_page_summary(token: str, since: str, until: str) -> dict:
    pages = get_pages(token)
    if not pages:
        return {"followers": 0, "impressions": 0, "reach": 0, "engagement": 0, "posts": 0, "pages": []}

    summary = {"followers": 0, "impressions": 0, "reach": 0, "engagement": 0, "posts": 0, "pages": []}

    for page in pages:
        pid = page["id"]
        page_token_data = _get(f"{pid}", token, {"fields": "access_token,fan_count,followers_count,name"})
        pt = page_token_data.get("access_token", token)
        fans = page_token_data.get("fan_count", 0)
        summary["followers"] += fans

        try:
            ins = _get(f"{pid}/insights", pt, {
                "metric": "page_impressions,page_reach,page_engaged_users",
                "since": since,
                "until": until,
                "period": "day",
            })
            for metric in ins.get("data", []):
                name = metric.get("name", "")
                vals = sum(v.get("value", 0) for v in metric.get("values", []))
                if name == "page_impressions":
                    summary["impressions"] += vals
                elif name == "page_reach":
                    summary["reach"] += vals
                elif name == "page_engaged_users":
                    summary["engagement"] += vals
        except Exception:
            pass

        try:
            posts_data = _get(f"{pid}/posts", pt, {
                "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
                "since": since,
                "until": until,
                "limit": 20,
            })
            posts = posts_data.get("data", [])
            summary["posts"] += len(posts)
            summary["pages"].append({
                "name":      page.get("name", ""),
                "followers": fans,
                "posts":     len(posts),
                "top_posts": [
                    {
                        "message":  p.get("message", "")[:80],
                        "likes":    p.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares":   p.get("shares", {}).get("count", 0) if p.get("shares") else 0,
                        "date":     p.get("created_time", "")[:10],
                    }
                    for p in posts[:5]
                ],
            })
        except Exception:
            pass

    return summary


def get_instagram_summary(token: str, since: str, until: str) -> dict:
    try:
        pages = get_pages(token)
        if not pages:
            return {"followers": 0, "impressions": 0, "reach": 0, "profile_views": 0, "accounts": []}

        result = {"followers": 0, "impressions": 0, "reach": 0, "profile_views": 0, "accounts": []}

        for page in pages:
            pid = page["id"]
            page_token_data = _get(f"{pid}", token, {"fields": "access_token,instagram_business_account"})
            pt = page_token_data.get("access_token", token)
            ig = page_token_data.get("instagram_business_account")
            if not ig:
                continue
            ig_id = ig["id"]

            ig_data = _get(f"{ig_id}", pt, {
                "fields": "name,username,followers_count,media_count,profile_picture_url"
            })
            result["followers"] += ig_data.get("followers_count", 0)

            try:
                ins = _get(f"{ig_id}/insights", pt, {
                    "metric": "impressions,reach,profile_views",
                    "period": "day",
                    "since": since,
                    "until": until,
                })
                for metric in ins.get("data", []):
                    name = metric.get("name", "")
                    vals = sum(v.get("value", 0) for v in metric.get("values", []))
                    if name == "impressions":
                        result["impressions"] += vals
                    elif name == "reach":
                        result["reach"] += vals
                    elif name == "profile_views":
                        result["profile_views"] += vals
            except Exception:
                pass

            result["accounts"].append({
                "username":  ig_data.get("username", ""),
                "followers": ig_data.get("followers_count", 0),
                "posts":     ig_data.get("media_count", 0),
            })

        return result
    except Exception as e:
        return {"followers": 0, "impressions": 0, "reach": 0, "profile_views": 0, "accounts": [], "error": str(e)}
