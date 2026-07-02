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
