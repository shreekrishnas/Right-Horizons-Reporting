"""
Google Trends integration — fetches trending & related keywords for Indian finance.
Returns empty string gracefully on any failure (rate limits, network, etc.).
"""
from __future__ import annotations


def _build_pytrends():
    try:
        from pytrends.request import TrendReq
        return TrendReq(hl='en-IN', tz=330, timeout=(5, 10))
    except Exception:
        return None


def trending_searches_india() -> str:
    pt = _build_pytrends()
    if not pt:
        return ""
    try:
        df = pt.trending_searches(pn='india')
        if df is None or df.empty:
            return ""
        items = df[0].tolist()[:15]
        return "Trending searches in India right now:\n" + "\n".join(f"- {t}" for t in items)
    except Exception:
        return ""


def related_topics(keyword: str) -> str:
    pt = _build_pytrends()
    if not pt:
        return ""
    try:
        pt.build_payload([keyword], cat=0, timeframe='now 7-d', geo='IN')
        data = pt.related_topics()
        if not data or keyword not in data:
            return ""
        parts = []
        rising = data[keyword].get("rising")
        if rising is not None and not rising.empty:
            topics = rising.head(8)["topic_title"].tolist()
            parts.append("Rising related topics: " + ", ".join(topics))
        top = data[keyword].get("top")
        if top is not None and not top.empty:
            topics = top.head(8)["topic_title"].tolist()
            parts.append("Top related topics: " + ", ".join(topics))
        return "\n".join(parts)
    except Exception:
        return ""


def related_queries(keyword: str) -> str:
    pt = _build_pytrends()
    if not pt:
        return ""
    try:
        pt.build_payload([keyword], cat=0, timeframe='now 7-d', geo='IN')
        data = pt.related_queries()
        if not data or keyword not in data:
            return ""
        parts = []
        rising = data[keyword].get("rising")
        if rising is not None and not rising.empty:
            queries = rising.head(10)["query"].tolist()
            parts.append("Rising searches: " + ", ".join(queries))
        top = data[keyword].get("top")
        if top is not None and not top.empty:
            queries = top.head(10)["query"].tolist()
            parts.append("Top searches: " + ", ".join(queries))
        return "\n".join(parts)
    except Exception:
        return ""


def interest_over_time(keywords: list[str]) -> str:
    pt = _build_pytrends()
    if not pt or not keywords:
        return ""
    try:
        kw_list = keywords[:5]
        pt.build_payload(kw_list, cat=0, timeframe='today 3-m', geo='IN')
        df = pt.interest_over_time()
        if df is None or df.empty:
            return ""
        latest = df.iloc[-1]
        parts = ["Search interest (last 3 months, India, 0-100 scale):"]
        for kw in kw_list:
            if kw in latest:
                parts.append(f"- {kw}: {int(latest[kw])}")
        return "\n".join(parts)
    except Exception:
        return ""


def finance_trends_context(topic: str = "") -> str:
    parts = []

    trending = trending_searches_india()
    if trending:
        parts.append(trending)

    seed = topic or "mutual funds India"
    queries = related_queries(seed)
    if queries:
        parts.append(f"\nRelated to '{seed}':\n{queries}")

    finance_keywords = ["PMS India", "NRI investment", "ESOP taxation", "SIP returns"]
    if topic and topic not in finance_keywords:
        finance_keywords = [topic] + finance_keywords[:3]
    interest = interest_over_time(finance_keywords)
    if interest:
        parts.append(f"\n{interest}")

    return "\n".join(parts)
