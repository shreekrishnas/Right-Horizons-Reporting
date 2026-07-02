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


def get_ad_accounts(token: str) -> list:
    data = _get("/me/adaccounts", token, {"fields": "id,name,account_status"})
    return data.get("data", [])


def get_campaigns_summary(token: str, ad_account_id: str, start: str, end: str, status_filter: str = "all") -> list:
    statuses = '["ACTIVE"]' if status_filter == "active" else '["ACTIVE","PAUSED"]'
    data = _get(
        f"/{ad_account_id}/campaigns", token,
        {
            "fields": "name,status,objective",
            "filtering": '[{"field":"effective_status","operator":"IN","value":' + statuses + '}]',
            "limit": 100,
        },
    )
    campaigns = data.get("data", [])
    result = []
    for c in campaigns:
        insights = _get(
            f"/{c['id']}/insights", token,
            {
                "fields": "spend,impressions,reach,clicks,ctr,cpc,actions",
                "time_range": f'{{"since":"{start}","until":"{end}"}}',
            },
        )
        row = {"name": c["name"], "status": c.get("status", ""), "objective": c.get("objective", "")}
        if insights.get("data"):
            i = insights["data"][0]
            leads = 0
            for a in i.get("actions") or []:
                if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead", "leadgen_grouped"):
                    try:
                        leads += int(float(a.get("value") or 0))
                    except Exception:
                        pass
            row.update({
                "spend": float(i.get("spend", 0)),
                "impressions": int(i.get("impressions", 0)),
                "reach": int(i.get("reach", 0)),
                "clicks": int(i.get("clicks", 0)),
                "ctr": round(float(i.get("ctr", 0)), 2),
                "cpc": round(float(i.get("cpc", 0)), 2),
                "leads": leads,
            })
        else:
            row.update({"spend": 0, "impressions": 0, "reach": 0, "clicks": 0, "ctr": 0, "cpc": 0, "leads": 0})
        result.append(row)
    return result


def get_daily_spend(token: str, ad_account_id: str, start: str, end: str) -> list:
    data = _get(
        f"/{ad_account_id}/insights", token,
        {
            "fields": "spend,impressions,reach,clicks",
            "time_range": f'{{"since":"{start}","until":"{end}"}}',
            "time_increment": 1,
            "limit": 500,
        },
    )
    return [
        {
            "date": d.get("date_start", ""),
            "spend": float(d.get("spend", 0)),
            "impressions": int(d.get("impressions", 0)),
            "reach": int(d.get("reach", 0)),
            "clicks": int(d.get("clicks", 0)),
        }
        for d in data.get("data", [])
    ]


def get_page_summary(token: str, page_id: str, start: str, end: str) -> dict:
    metrics = "page_impressions,page_engaged_users,page_fans,page_views_total"
    data = _get(
        f"/{page_id}/insights", token,
        {"metric": metrics, "period": "total_over_range", "since": start, "until": end},
    )
    result = {}
    for item in data.get("data", []):
        name = item["name"]
        val = item.get("values", [{}])[0].get("value", 0)
        result[name] = val
    return result


def get_instagram_summary(token: str, ig_user_id: str, start: str, end: str) -> dict:
    data = _get(
        f"/{ig_user_id}/insights", token,
        {
            "metric": "impressions,reach,accounts_engaged,follows_and_unfollows",
            "period": "day",
            "metric_type": "total_value",
            "since": start,
            "until": end,
        },
    )
    result = {}
    for item in data.get("data", []):
        val = item.get("total_value", {}).get("value", 0)
        result[item["name"]] = val
    return result
