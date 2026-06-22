"""
Tavily web search integration — injects real-time context into AI prompts.
Returns empty string gracefully if TAVILY_API_KEY is not set.
"""
import requests
from config import TAVILY_API_KEY

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 5, topic: str = "general") -> str:
    if not TAVILY_API_KEY:
        return ""
    try:
        resp = requests.post(TAVILY_SEARCH_URL, json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "topic": topic,
            "include_answer": True,
        }, timeout=10)
        if not resp.ok:
            return ""
        data = resp.json()
        parts = []
        answer = data.get("answer")
        if answer:
            parts.append(f"Summary: {answer}")
        for r in (data.get("results") or [])[:max_results]:
            title = r.get("title", "")
            content = r.get("content", "")
            if title and content:
                parts.append(f"- {title}: {content[:300]}")
        return "\n".join(parts)
    except Exception:
        return ""


def search_indian_finance(topic: str) -> str:
    return search(
        f"{topic} India 2026 SEBI Indian investors INR",
        max_results=4,
        topic="news"
    )


def search_market_context() -> str:
    return search(
        "India stock market Nifty Sensex RBI repo rate SEBI latest 2026",
        max_results=4,
        topic="news"
    )


def search_seasonal_events(months: str) -> str:
    return search(
        f"Indian festivals tax deadlines financial events {months} 2026",
        max_results=5,
        topic="general"
    )
