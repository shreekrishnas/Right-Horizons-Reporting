from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy,
)
from google.oauth2.credentials import Credentials


def _client(creds: Credentials) -> BetaAnalyticsDataClient:
    return BetaAnalyticsDataClient(credentials=creds)


def get_summary(creds: Credentials, property_id: str, start: str, end: str) -> dict:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="screenPageViews"),
        ],
    ))
    if not resp.rows:
        return {"sessions": 0, "users": 0, "new_users": 0, "bounce_rate": 0, "avg_session": 0, "pageviews": 0}
    v = [m.value for m in resp.rows[0].metric_values]
    return {
        "sessions": int(float(v[0])),
        "users": int(float(v[1])),
        "new_users": int(float(v[2])),
        "bounce_rate": round(float(v[3]) * 100, 1),
        "avg_session": round(float(v[4])),
        "pageviews": int(float(v[5])),
    }


def get_top_pages(creds: Credentials, property_id: str, start: str, end: str, limit: int = 10) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="sessions"), Metric(name="averageSessionDuration")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=limit,
    ))
    return [
        {
            "page": r.dimension_values[0].value,
            "views": int(float(r.metric_values[0].value)),
            "sessions": int(float(r.metric_values[1].value)),
            "avg_dur": round(float(r.metric_values[2].value)),
        }
        for r in resp.rows
    ]


def get_traffic_sources(creds: Credentials, property_id: str, start: str, end: str) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    ))
    return [
        {
            "channel": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_organic_summary(creds: Credentials, property_id: str, start: str, end: str) -> dict:
    from google.analytics.data_v1beta.types import FilterExpression, Filter
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search"),
            )
        ),
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="keyEvents"),
        ],
    ))
    if not resp.rows:
        return {"organic_sessions": 0, "organic_users": 0, "bounce_rate": 0, "avg_session_duration": 0, "leads": 0}
    v = [m.value for m in resp.rows[0].metric_values]
    return {
        "organic_sessions": int(float(v[0])),
        "organic_users": int(float(v[1])),
        "bounce_rate": round(float(v[2]) * 100, 1),
        "avg_session_duration": round(float(v[3])),
        "leads": int(float(v[4])),
    }


def get_device_breakdown(creds: Credentials, property_id: str, start: str, end: str) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="totalUsers"), Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="totalUsers"), desc=True)],
        limit=10,
    ))
    return [
        {
            "deviceCategory": r.dimension_values[0].value,
            "users": int(float(r.metric_values[0].value)),
            "sessions": int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_age_breakdown(creds: Credentials, property_id: str, start: str, end: str) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="userAgeBracket")],
        metrics=[Metric(name="totalUsers"), Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="totalUsers"), desc=True)],
        limit=10,
    ))
    return [
        {
            "ageGroup": r.dimension_values[0].value,
            "users": int(float(r.metric_values[0].value)),
            "sessions": int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_city_breakdown(creds: Credentials, property_id: str, start: str, end: str, limit: int = 10) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="city")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    ))
    return [
        {
            "city": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_weekly_users(creds: Credentials, property_id: str, start: str, end: str) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="isoYearIsoWeek")],
        metrics=[Metric(name="totalUsers"), Metric(name="newUsers")],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="isoYearIsoWeek"))],
        limit=52,
    ))
    return [
        {
            "week": r.dimension_values[0].value,
            "totalUsers": int(float(r.metric_values[0].value)),
            "newUsers": int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_landing_pages(creds: Credentials, property_id: str, start: str, end: str, limit: int = 10) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    ))
    return [
        {
            "landingPage": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
        }
        for r in resp.rows
    ]


def get_daily(creds: Credentials, property_id: str, start: str, end: str) -> list:
    client = _client(creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="bounceRate"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        limit=500,
    ))
    return [
        {
            "date": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
            "new_users": int(float(r.metric_values[2].value)),
            "bounce_rate": float(r.metric_values[3].value),
            "pageviews": int(float(r.metric_values[4].value)),
            "avg_session": float(r.metric_values[5].value),
        }
        for r in resp.rows
    ]


def _rows(resp, dims: list, mets: list) -> list:
    out = []
    for r in resp.rows:
        row = {d: r.dimension_values[i].value for i, d in enumerate(dims)}
        for i, (key, kind) in enumerate(mets):
            v = float(r.metric_values[i].value or 0)
            if kind == "pct":
                row[key] = round(v * 100, 1)
            elif kind == "sec":
                row[key] = round(v)
            elif kind == "float":
                row[key] = round(v, 2)
            else:
                row[key] = int(v)
        out.append(row)
    return out


_QUALITY_METRICS = [
    ("sessions", "int"), ("users", "int"), ("engaged_sessions", "int"),
    ("engagement_rate", "pct"), ("bounce_rate", "pct"),
    ("avg_session", "sec"), ("views_per_session", "float"), ("key_events", "int"),
]
_QUALITY_GA4 = ["sessions", "totalUsers", "engagedSessions", "engagementRate", "bounceRate",
                "averageSessionDuration", "screenPageViewsPerSession", "keyEvents"]


def _quality_report(creds, property_id, start, end, dims, limit):
    resp = _client(creds).run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in _QUALITY_GA4],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    ))
    return _rows(resp, dims, _QUALITY_METRICS)


def get_engagement_summary(creds: Credentials, property_id: str, start: str, end: str) -> dict:
    """Site-wide engagement quality: engaged sessions, engagement rate, views/session, key events."""
    rows = _quality_report(creds, property_id, start, end, [], 1)
    return rows[0] if rows else {k: 0 for k, _ in _QUALITY_METRICS}


def get_channel_quality(creds: Credentials, property_id: str, start: str, end: str) -> list:
    """Per-channel volume AND quality (engagement, avg session, key events)."""
    return _quality_report(creds, property_id, start, end, ["sessionDefaultChannelGroup"], 15)


def get_source_medium(creds: Credentials, property_id: str, start: str, end: str, limit: int = 20) -> list:
    return _quality_report(creds, property_id, start, end, ["sessionSourceMedium"], limit)


def get_country_breakdown(creds: Credentials, property_id: str, start: str, end: str, limit: int = 15) -> list:
    return _quality_report(creds, property_id, start, end, ["country"], limit)


def get_region_breakdown(creds: Credentials, property_id: str, start: str, end: str, limit: int = 20) -> list:
    return _quality_report(creds, property_id, start, end, ["country", "region"], limit)


def get_landing_page_quality(creds: Credentials, property_id: str, start: str, end: str, limit: int = 20) -> list:
    return _quality_report(creds, property_id, start, end, ["landingPagePlusQueryString"], limit)


# Cities that host major cloud data centres — traffic from here with near-zero
# engagement is usually crawlers, uptime monitors or scrapers, not people.
_DATACENTER_CITIES = {
    "ashburn", "boardman", "council bluffs", "the dalles", "san jose", "santa clara",
    "dublin", "frankfurt", "singapore", "moses lake", "quincy", "des moines",
    "north charleston", "columbus", "san antonio", "phoenix", "lenoir",
}


def get_bot_traffic(creds: Credentials, property_id: str, start: str, end: str) -> dict:
    """Heuristic bot/spam estimate. GA4 has no 'bot' dimension, so we score
    country+city+browser+channel segments on behaviour: almost no time on site,
    ~1 page, ~all new users, low engagement, data-centre locations, (not set)
    geo. Returns totals, % of traffic, suspect segments and 'clean' metrics."""
    dims = ["country", "city", "browser", "sessionDefaultChannelGroup"]
    resp = _client(creds).run_report(RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in ("sessions", "totalUsers", "newUsers", "engagedSessions",
                                          "averageSessionDuration", "screenPageViewsPerSession", "keyEvents")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=1000,
    ))
    total = {"sessions": 0, "users": 0, "engaged": 0, "dur": 0.0, "key_events": 0}
    bot = {"sessions": 0, "users": 0, "engaged": 0, "dur": 0.0}
    suspects = []
    for r in resp.rows:
        country, city, browser, channel = (v.value for v in r.dimension_values)
        s, u, nu, eng, dur, vps, ke = (float(m.value or 0) for m in r.metric_values)
        total["sessions"] += s; total["users"] += u; total["engaged"] += eng
        total["dur"] += dur * s; total["key_events"] += ke
        if s < 5 or ke > 0:
            continue
        er = eng / s if s else 0
        reasons, score = [], 0
        if dur < 5:
            score += 2; reasons.append(f"avg session {dur:.0f}s")
        elif dur < 10:
            score += 1; reasons.append(f"avg session {dur:.0f}s")
        if er < 0.3:
            score += 1; reasons.append(f"engagement {er*100:.0f}%")
        if u and nu / u > 0.95 and s >= 10:
            score += 1; reasons.append("~100% new users")
        if vps <= 1.05:
            score += 1; reasons.append("single page")
        if city.lower() in _DATACENTER_CITIES:
            score += 1; reasons.append(f"data-centre city ({city})")
        if city in ("(not set)", "") or country in ("(not set)", ""):
            score += 1; reasons.append("location not set")
        if s and u / s > 0.97 and s >= 20 and dur < 10:
            score += 1; reasons.append("1 session per user")
        if score >= 4:
            bot["sessions"] += s; bot["users"] += u; bot["engaged"] += eng; bot["dur"] += dur * s
            suspects.append({"country": country, "city": city, "browser": browser, "channel": channel,
                             "sessions": int(s), "users": int(u), "avg_session": round(dur),
                             "engagement_rate": round(er * 100, 1), "score": score, "reasons": reasons})
    # Segment rows double-count users/sessions that span several cities or
    # browsers, so take the real totals from an undimensioned query and
    # subtract the suspected bots from those.
    t = get_engagement_summary(creds, property_id, start, end)
    total = {"sessions": t["sessions"], "users": t["users"], "engaged": t["engaged_sessions"],
             "dur": t["avg_session"] * t["sessions"], "key_events": t["key_events"]}
    ts, bs = total["sessions"], bot["sessions"]
    hs = max(ts - bs, 0)
    by_country, by_channel = {}, {}
    for x in suspects:
        by_country[x["country"]] = by_country.get(x["country"], 0) + x["sessions"]
        by_channel[x["channel"]] = by_channel.get(x["channel"], 0) + x["sessions"]
    return {
        "method": "heuristic estimate — GA4 does not label bots; segments scored on near-zero time, single page, "
                  "~100% new users, low engagement, data-centre/unknown location; segments with key events are never flagged",
        "total_sessions": int(ts),
        "total_users": int(total["users"]),
        "suspected_bot_sessions": int(bs),
        "suspected_bot_users": int(bot["users"]),
        "bot_share_pct": round(bs / ts * 100, 1) if ts else 0,
        "by_country": dict(sorted(by_country.items(), key=lambda kv: -kv[1])),
        "by_channel": dict(sorted(by_channel.items(), key=lambda kv: -kv[1])),
        "top_suspect_segments": sorted(suspects, key=lambda x: -x["sessions"])[:15],
        "clean": {
            "sessions": int(hs),
            "users": int(max(total["users"] - bot["users"], 0)),
            "engagement_rate": round(max(total["engaged"] - bot["engaged"], 0) / hs * 100, 1) if hs else 0,
            "avg_session": round(max(total["dur"] - bot["dur"], 0) / hs) if hs else 0,
            "key_events": int(total["key_events"]),
        },
        "reported": {
            "engagement_rate": round(total["engaged"] / ts * 100, 1) if ts else 0,
            "avg_session": round(total["dur"] / ts) if ts else 0,
        },
    }
