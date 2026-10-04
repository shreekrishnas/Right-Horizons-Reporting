from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _service(creds: Credentials):
    return build("webmasters", "v3", credentials=creds, cache_discovery=False)


def get_summary(creds: Credentials, site_url: str, start: str, end: str) -> dict:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={"startDate": start, "endDate": end, "dimensions": [], "rowLimit": 1},
    ).execute()
    row = (resp.get("rows") or [{}])[0] if resp.get("rows") else {}
    return {
        "clicks": round(row.get("clicks", 0)),
        "impressions": round(row.get("impressions", 0)),
        "ctr": round(row.get("ctr", 0) * 100, 2),
        "position": round(row.get("position", 0), 1),
    }


def get_top_queries(creds: Credentials, site_url: str, start: str, end: str, limit: int = 10) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["query"], "rowLimit": limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        },
    ).execute()
    return [
        {
            "query": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_top_pages(creds: Credentials, site_url: str, start: str, end: str, limit: int = 10) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["page"], "rowLimit": limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        },
    ).execute()
    return [
        {
            "page": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def get_daily(creds: Credentials, site_url: str, start: str, end: str) -> list:
    svc = _service(creds)
    resp = svc.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start, "endDate": end,
            "dimensions": ["date"], "rowLimit": 500,
            "orderBy": [{"fieldName": "date", "sortOrder": "ASCENDING"}],
        },
    ).execute()
    return [
        {
            "date": r["keys"][0],
            "clicks": round(r.get("clicks", 0)),
            "impressions": round(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in resp.get("rows", [])
    ]


def list_sites(creds: Credentials) -> list:
    svc = _service(creds)
    resp = svc.sites().list().execute()
    return [s["siteUrl"] for s in resp.get("siteEntry", [])]


# Typical organic CTR by position (blended desktop+mobile benchmarks).
_EXPECTED_CTR = {1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.065, 6: 0.05, 7: 0.04, 8: 0.035, 9: 0.03, 10: 0.025}


def _exp_ctr(pos: float) -> float:
    p = max(1, min(10, round(pos)))
    return _EXPECTED_CTR[p] if pos <= 10.5 else 0.01


def _qp_rows(svc, site_url, start, end, dims, limit=5000):
    resp = svc.searchanalytics().query(siteUrl=site_url, body={
        "startDate": start, "endDate": end, "dimensions": dims, "rowLimit": limit,
    }).execute()
    return resp.get("rows", [])


def get_seo_opportunities(creds: Credentials, site_url: str, start: str, end: str,
                          prev_start: str, prev_end: str) -> dict:
    """Actionable SEO work list from Search Console:
    - striking_distance: queries at positions 4-20 with real demand (push to top 3)
    - low_ctr: page-1 rankings whose CTR is far below the benchmark (rewrite title/meta)
    - cannibalization: queries where 2+ of our pages compete
    - decaying_pages: pages that lost >=30% clicks vs the previous period
    - content_gaps: queries with demand where our best page ranks beyond 20 (needs new/better content)
    - rising_queries: queries gaining the most impressions vs previous period"""
    svc = _service(creds)
    qp = _qp_rows(svc, site_url, start, end, ["query", "page"])
    q_now = {r["keys"][0]: r for r in _qp_rows(svc, site_url, start, end, ["query"])}
    q_prev = {r["keys"][0]: r for r in _qp_rows(svc, site_url, prev_start, prev_end, ["query"])}
    p_now = {r["keys"][0]: r for r in _qp_rows(svc, site_url, start, end, ["page"])}
    p_prev = {r["keys"][0]: r for r in _qp_rows(svc, site_url, prev_start, prev_end, ["page"])}

    best_page = {}
    by_query = {}
    for r in qp:
        q, page = r["keys"]
        by_query.setdefault(q, []).append(r)
        if q not in best_page or r["impressions"] > best_page[q]["impressions"]:
            best_page[q] = r

    striking, low_ctr, gaps = [], [], []
    for q, r in q_now.items():
        imp, clk, pos, ctr = r["impressions"], r["clicks"], r["position"], r.get("ctr", 0)
        page = best_page.get(q, {}).get("keys", [None, ""])[1]
        if 3.5 < pos <= 20 and imp >= 30:
            gain = imp * _EXPECTED_CTR[3] - clk
            striking.append({"query": q, "page": page, "position": round(pos, 1), "impressions": int(imp),
                             "clicks": int(clk), "potential_extra_clicks": int(max(gain, 0))})
        if pos <= 10.5 and imp >= 50 and ctr < 0.5 * _exp_ctr(pos):
            low_ctr.append({"query": q, "page": page, "position": round(pos, 1), "impressions": int(imp),
                            "ctr": round(ctr * 100, 2), "benchmark_ctr": round(_exp_ctr(pos) * 100, 1),
                            "missed_clicks": int(imp * _exp_ctr(pos) - clk)})
        if pos > 20 and imp >= 40:
            gaps.append({"query": q, "best_page": page, "position": round(pos, 1), "impressions": int(imp)})

    cannibal = []
    for q, rows in by_query.items():
        rows = [x for x in rows if x["impressions"] >= 10]
        if len(rows) >= 2 and q_now.get(q, {}).get("impressions", 0) >= 30:
            cannibal.append({"query": q, "impressions": int(q_now[q]["impressions"]),
                             "pages": [{"page": x["keys"][1], "impressions": int(x["impressions"]),
                                        "position": round(x["position"], 1)}
                                       for x in sorted(rows, key=lambda x: -x["impressions"])[:4]]})

    decaying = []
    for page, pr in p_prev.items():
        before = pr["clicks"]
        now = p_now.get(page, {}).get("clicks", 0)
        if before >= 10 and now <= before * 0.7:
            nr = p_now.get(page, {})
            decaying.append({"page": page, "clicks_before": int(before), "clicks_now": int(now),
                             "change_pct": round((now - before) / before * 100),
                             "position_before": round(pr["position"], 1),
                             "position_now": round(nr.get("position", 0), 1) if nr else None,
                             "impressions_before": int(pr["impressions"]),
                             "impressions_now": int(nr.get("impressions", 0))})

    rising = []
    for q, r in q_now.items():
        before = q_prev.get(q, {}).get("impressions", 0)
        if r["impressions"] - before >= 30:
            rising.append({"query": q, "impressions_before": int(before), "impressions_now": int(r["impressions"]),
                           "position": round(r["position"], 1)})

    return {
        "period": {"start": start, "end": end, "previous_start": prev_start, "previous_end": prev_end},
        "striking_distance": sorted(striking, key=lambda x: -x["potential_extra_clicks"])[:40],
        "low_ctr": sorted(low_ctr, key=lambda x: -x["missed_clicks"])[:30],
        "cannibalization": sorted(cannibal, key=lambda x: -x["impressions"])[:20],
        "decaying_pages": sorted(decaying, key=lambda x: x["clicks_now"] - x["clicks_before"])[:20],
        "content_gaps": sorted(gaps, key=lambda x: -x["impressions"])[:30],
        "rising_queries": sorted(rising, key=lambda x: x["impressions_before"] - x["impressions_now"])[:20],
    }
