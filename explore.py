"""Metric Builder backend: one flexible query over GA4 or Search Console.

The frontend sends the fields the user dragged onto the shelves (group-by
dimensions, values/metrics, filters) and gets back flat rows, totals and,
optionally, the same query for the previous period.
"""
import re
from datetime import date, timedelta

from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy,
    FilterExpression, FilterExpressionList, Filter, MetricAggregation,
)

import ga4
import gsc

# fmt: int | pct (already a %) | ratio (0-1 → shown as %) | sec | float | date | text
FIELDS = {
    "ga4": {
        "dimensions": [
            ("date", "Date", "date", "Time"),
            ("isoYearIsoWeek", "Week", "text", "Time"),
            ("yearMonth", "Month", "text", "Time"),
            ("dayOfWeekName", "Day of week", "text", "Time"),
            ("hour", "Hour of day", "text", "Time"),
            ("sessionDefaultChannelGroup", "Channel", "text", "Traffic source"),
            ("sessionSourceMedium", "Source / medium", "text", "Traffic source"),
            ("sessionSource", "Source", "text", "Traffic source"),
            ("sessionMedium", "Medium", "text", "Traffic source"),
            ("sessionCampaignName", "Campaign", "text", "Traffic source"),
            ("country", "Country", "text", "Location"),
            ("region", "Region / state", "text", "Location"),
            ("city", "City", "text", "Location"),
            ("deviceCategory", "Device", "text", "Technology"),
            ("browser", "Browser", "text", "Technology"),
            ("operatingSystem", "Operating system", "text", "Technology"),
            ("language", "Language", "text", "Technology"),
            ("landingPage", "Landing page", "text", "Content"),
            ("pagePath", "Page", "text", "Content"),
            ("pageTitle", "Page title", "text", "Content"),
            ("newVsReturning", "New vs returning", "text", "Audience"),
        ],
        "metrics": [
            ("sessions", "Sessions", "int"),
            ("totalUsers", "Users", "int"),
            ("newUsers", "New users", "int"),
            ("activeUsers", "Active users", "int"),
            ("screenPageViews", "Page views", "int"),
            ("engagedSessions", "Engaged sessions", "int"),
            ("engagementRate", "Engagement rate", "ratio"),
            ("bounceRate", "Bounce rate", "ratio"),
            ("averageSessionDuration", "Avg session duration", "sec"),
            ("screenPageViewsPerSession", "Pages per session", "float"),
            ("keyEvents", "Key events (conversions)", "int"),
            ("eventCount", "Events", "int"),
        ],
    },
    "gsc": {
        "dimensions": [
            ("date", "Date", "date", "Time"),
            ("query", "Search query", "text", "Search"),
            ("page", "Page", "text", "Search"),
            ("country", "Country", "text", "Location"),
            ("device", "Device", "text", "Technology"),
        ],
        "metrics": [
            ("clicks", "Clicks", "int"),
            ("impressions", "Impressions", "int"),
            ("ctr", "Click-through rate", "pct"),
            ("position", "Average position", "float"),
        ],
    },
}


def catalog() -> dict:
    out = {}
    for src, f in FIELDS.items():
        out[src] = {
            "label": "Google Analytics" if src == "ga4" else "Search Console",
            "dimensions": [{"id": i, "label": l, "fmt": fm, "group": g} for i, l, fm, g in f["dimensions"]],
            "metrics": [{"id": i, "label": l, "fmt": fm} for i, l, fm in f["metrics"]],
        }
    return out


def _valid(src, kind, ids):
    allowed = {x[0] for x in FIELDS[src][kind]}
    bad = [i for i in ids if i not in allowed]
    if bad:
        raise ValueError(f"Unknown {kind[:-1]}(s) for {src}: {', '.join(bad)}")
    return ids


# ── GA4 ──────────────────────────────────────────────────────────────────────

def _ga4_filter(f):
    field, op, vals = f["field"], f.get("op", "in"), f.get("values") or []
    if not vals:
        return None
    S = Filter.StringFilter.MatchType
    if op in ("in", "not_in"):
        expr = FilterExpression(filter=Filter(field_name=field, in_list_filter=Filter.InListFilter(values=[str(v) for v in vals])))
    elif op in ("gt", "lt", "gte", "lte"):
        N = Filter.NumericFilter.Operation
        opmap = {"gt": N.GREATER_THAN, "lt": N.LESS_THAN, "gte": N.GREATER_THAN_OR_EQUAL, "lte": N.LESS_THAN_OR_EQUAL}
        v = float(vals[0])
        nv = {"int64_value": int(v)} if v.is_integer() else {"double_value": v}
        expr = FilterExpression(filter=Filter(field_name=field, numeric_filter=Filter.NumericFilter(
            operation=opmap[op], value={**nv})))
    else:
        mt = {"contains": S.CONTAINS, "not_contains": S.CONTAINS, "starts_with": S.BEGINS_WITH,
              "ends_with": S.ENDS_WITH, "equals": S.EXACT, "not_equals": S.EXACT}[op]
        expr = FilterExpression(filter=Filter(field_name=field, string_filter=Filter.StringFilter(
            match_type=mt, value=str(vals[0]), case_sensitive=False)))
    if op.startswith("not_"):
        expr = FilterExpression(not_expression=expr)
    return expr


def _and(exprs):
    exprs = [e for e in exprs if e is not None]
    if not exprs:
        return None
    if len(exprs) == 1:
        return exprs[0]
    return FilterExpression(and_group=FilterExpressionList(expressions=exprs))


def _ga4_query(creds, prop, start, end, dims, mets, filters, limit, sort):
    metric_ids = {x[0] for x in FIELDS["ga4"]["metrics"]}
    dim_f = _and([_ga4_filter(f) for f in filters if f["field"] not in metric_ids])
    met_f = _and([_ga4_filter(f) for f in filters if f["field"] in metric_ids])
    order = []
    if sort and sort.get("field") in mets:
        order = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=sort["field"]), desc=sort.get("desc", True))]
    elif sort and sort.get("field") in dims:
        order = [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name=sort["field"]), desc=sort.get("desc", False))]
    elif dims and dims[0] in ("date", "isoYearIsoWeek", "yearMonth", "hour"):
        order = [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name=dims[0]))]
    elif mets:
        order = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=mets[0]), desc=True)]
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in mets],
        order_bys=order, limit=limit,
        metric_aggregations=[MetricAggregation.TOTAL] if dims else [],
    )
    if dim_f is not None:
        req.dimension_filter = dim_f
    if met_f is not None:
        req.metric_filter = met_f
    resp = ga4._client(creds).run_report(req)
    rows = []
    for r in resp.rows:
        row = {d: r.dimension_values[i].value for i, d in enumerate(dims)}
        for i, m in enumerate(mets):
            row[m] = float(r.metric_values[i].value or 0)
        rows.append(row)
    if dims and resp.totals:
        totals = {m: float(resp.totals[0].metric_values[i].value or 0) for i, m in enumerate(mets)}
    elif not dims and rows:
        totals = {m: rows[0][m] for m in mets}
    else:
        totals = {m: 0.0 for m in mets}
    for row in rows:
        if "date" in row and len(row["date"]) == 8:
            row["date"] = f"{row['date'][:4]}-{row['date'][4:6]}-{row['date'][6:]}"
        if "yearMonth" in row and len(row["yearMonth"]) == 6:
            row["yearMonth"] = f"{row['yearMonth'][:4]}-{row['yearMonth'][4:]}"
    return rows, totals, int(resp.row_count or len(rows))


# ── Search Console ───────────────────────────────────────────────────────────

def _gsc_query(creds, site, start, end, dims, mets, filters, limit, sort):
    metric_ids = {x[0] for x in FIELDS["gsc"]["metrics"]}
    groups = []
    post = []
    for f in filters:
        vals = f.get("values") or []
        if not vals:
            continue
        if f["field"] in metric_ids:
            post.append(f)
            continue
        op = f.get("op", "in")
        if op in ("in", "not_in"):
            rx = "^(" + "|".join(re.escape(str(v)) for v in vals) + ")$"
            groups.append({"dimension": f["field"], "operator": "includingRegex" if op == "in" else "excludingRegex", "expression": rx})
        else:
            gop = {"contains": "contains", "not_contains": "notContains", "equals": "equals",
                   "not_equals": "notEquals", "starts_with": "includingRegex", "ends_with": "includingRegex"}[op]
            ex = str(vals[0])
            if op == "starts_with":
                ex = "^" + re.escape(ex)
            elif op == "ends_with":
                ex = re.escape(ex) + "$"
            groups.append({"dimension": f["field"], "operator": gop, "expression": ex})
    body = {"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": 25000 if post else limit}
    if groups:
        body["dimensionFilterGroups"] = [{"groupType": "and", "filters": groups}]
    svc = gsc._service(creds)
    resp = svc.searchanalytics().query(siteUrl=site, body=body).execute()

    def conv(r):
        row = {d: r["keys"][i] for i, d in enumerate(dims)} if dims else {}
        for m in mets:
            v = r.get(m, 0)
            row[m] = round(v * 100, 2) if m == "ctr" else v
        return row

    rows = [conv(r) for r in resp.get("rows", [])]
    for f in post:
        v = float(f["values"][0])
        op = f.get("op", "gt")
        cmp = {"gt": lambda x: x > v, "lt": lambda x: x < v, "gte": lambda x: x >= v, "lte": lambda x: x <= v}.get(op, lambda x: True)
        rows = [r for r in rows if cmp(r.get(f["field"], 0))]
    # totals from an undimensioned query with the same filters
    tbody = {k: v for k, v in body.items() if k not in ("dimensions", "rowLimit")}
    tresp = svc.searchanalytics().query(siteUrl=site, body={**tbody, "dimensions": [], "rowLimit": 1}).execute()
    trow = (tresp.get("rows") or [{}])[0] if tresp.get("rows") else {}
    totals = {m: (round(trow.get(m, 0) * 100, 2) if m == "ctr" else trow.get(m, 0)) for m in mets}
    if sort and sort.get("field") in (dims + mets):
        rows.sort(key=lambda r: r.get(sort["field"], 0), reverse=sort.get("desc", True))
    elif dims and dims[0] == "date":
        rows.sort(key=lambda r: r["date"])
    elif mets:
        rows.sort(key=lambda r: r.get(mets[0], 0), reverse=mets[0] != "position")
    return rows[:limit], totals, len(rows)


# ── Entry point ──────────────────────────────────────────────────────────────

def run(creds, domain_cfg: dict, q: dict) -> dict:
    src = q.get("source", "ga4")
    if src not in FIELDS:
        raise ValueError("source must be ga4 or gsc")
    dims = _valid(src, "dimensions", list(q.get("dimensions") or [])[:4])
    mets = _valid(src, "metrics", list(q.get("metrics") or [])[:8])
    if not mets:
        raise ValueError("Add at least one value (metric)")
    filters = [f for f in (q.get("filters") or []) if f.get("field")]
    for f in filters:
        _valid(src, "metrics" if f["field"] in {x[0] for x in FIELDS[src]["metrics"]} else "dimensions", [f["field"]])
    limit = max(1, min(int(q.get("limit") or 50), 500))
    start, end = q["start"], q["end"]
    sort = q.get("sort")
    if src == "ga4":
        target = domain_cfg.get("ga4_property")
        if not target:
            raise ValueError("Google Analytics isn't connected for this account")
        fn = _ga4_query
    else:
        target = domain_cfg.get("gsc_site")
        if not target:
            raise ValueError("Search Console isn't connected for this account")
        fn = _gsc_query
    rows, totals, row_count = fn(creds, target, start, end, dims, mets, filters, limit, sort)
    out = {"source": src, "dimensions": dims, "metrics": mets, "start": start, "end": end,
           "rows": rows, "totals": totals, "row_count": row_count}
    if q.get("compare"):
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        pe = s - timedelta(days=1)
        ps = pe - (e - s)
        prow, ptot, _ = fn(creds, target, ps.isoformat(), pe.isoformat(), dims, mets, filters, 500, sort)
        key = lambda r: tuple(r.get(d) for d in dims if d != "date")
        pmap = {key(r): r for r in prow}
        if dims and "date" not in dims:
            for r in rows:
                p = pmap.get(key(r))
                r["_prev"] = {m: p[m] for m in mets} if p else None
        out["compare"] = {"start": ps.isoformat(), "end": pe.isoformat(), "totals": ptot}
    return out


def field_values(creds, domain_cfg: dict, src: str, field: str, start: str, end: str, search: str = "") -> list:
    """Top values of one dimension, for the filter picker."""
    _valid(src, "dimensions", [field])
    filters = [{"field": field, "op": "contains", "values": [search]}] if search else []
    met = "sessions" if src == "ga4" else "impressions"
    r = run(creds, domain_cfg, {"source": src, "dimensions": [field], "metrics": [met], "filters": filters,
                                "start": start, "end": end, "limit": 100})
    return [{"value": row[field], "count": row[met]} for row in r["rows"]]
