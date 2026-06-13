from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy,
)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def _client(creds_dict: dict) -> BetaAnalyticsDataClient:
    creds = Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_dict["client_id"],
        client_secret=creds_dict["client_secret"],
        scopes=creds_dict.get("scopes"),
    )
    if not creds.valid:
        creds.refresh(Request())
    return BetaAnalyticsDataClient(credentials=creds)


def get_summary(creds_dict: dict, property_id: str, start_date: str, end_date: str) -> dict:
    client = _client(creds_dict)
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="screenPageViews"),
        ],
    )
    resp = client.run_report(req)
    if not resp.rows:
        return {"sessions": 0, "users": 0, "new_users": 0, "bounce_rate": 0, "avg_session": 0, "pageviews": 0}
    vals = [v.value for v in resp.rows[0].metric_values]
    return {
        "sessions":    int(float(vals[0])),
        "users":       int(float(vals[1])),
        "new_users":   int(float(vals[2])),
        "bounce_rate": round(float(vals[3]) * 100, 1),
        "avg_session": round(float(vals[4])),
        "pageviews":   int(float(vals[5])),
    }


def get_top_pages(creds_dict: dict, property_id: str, start_date: str, end_date: str, limit: int = 10) -> list:
    client = _client(creds_dict)
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="sessions"), Metric(name="averageSessionDuration")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(req)
    return [
        {
            "page":     r.dimension_values[0].value,
            "views":    int(float(r.metric_values[0].value)),
            "sessions": int(float(r.metric_values[1].value)),
            "avg_dur":  round(float(r.metric_values[2].value)),
        }
        for r in resp.rows
    ]


def get_traffic_sources(creds_dict: dict, property_id: str, start_date: str, end_date: str) -> list:
    client = _client(creds_dict)
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    )
    resp = client.run_report(req)
    return [
        {
            "channel":  r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users":    int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]


def get_daily_sessions(creds_dict: dict, property_id: str, start_date: str, end_date: str) -> list:
    client = _client(creds_dict)
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        limit=500,
    )
    resp = client.run_report(req)
    return [
        {
            "date":     r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users":    int(float(r.metric_values[1].value)),
        }
        for r in resp.rows
    ]
