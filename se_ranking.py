"""
SE Ranking API integration for domain analytics, keyword rankings, backlinks, and site audit.
"""
import requests
import logging
from config import SE_RANKING_API_KEY

log = logging.getLogger(__name__)

BASE = "https://api.seranking.com/v1"


def _headers():
    return {"Authorization": f"Bearer {SE_RANKING_API_KEY}"}


def _get(path: str, params: dict = None) -> dict | list:
    resp = requests.get(f"{BASE}{path}", headers=_headers(), params=params or {}, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"SE Ranking API ({resp.status_code}): {resp.text[:500]}")
    return resp.json()


def domain_overview(domain: str, source: str = "us") -> dict:
    try:
        data = _get("/research/overview/domain", {"domain": domain, "source": source, "type": "organic"})
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("SE Ranking domain overview failed: %s", e)
        return {}


def domain_keywords(domain: str, source: str = "us", limit: int = 50) -> list:
    try:
        data = _get("/research/keywords/domain", {
            "domain": domain, "source": source, "type": "organic",
            "limit": limit, "order_by": "traffic,desc",
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking domain keywords failed: %s", e)
        return []


def domain_competitors(domain: str, source: str = "us", limit: int = 20) -> list:
    try:
        data = _get("/research/competitors/domain", {
            "domain": domain, "source": source, "type": "organic", "limit": limit,
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking competitors failed: %s", e)
        return []


def backlinks_summary(domain: str) -> dict:
    try:
        data = _get("/backlinks/metrics", {"target": domain, "target_type": "domain"})
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("SE Ranking backlinks summary failed: %s", e)
        return {}


def backlinks_top(domain: str, limit: int = 30) -> list:
    try:
        data = _get("/backlinks/backlinks", {
            "target": domain, "target_type": "domain",
            "limit": limit, "order_by": "inlink_rank,desc",
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking top backlinks failed: %s", e)
        return []


def backlinks_anchors(domain: str, limit: int = 30) -> list:
    try:
        data = _get("/backlinks/anchors", {
            "target": domain, "target_type": "domain", "limit": limit,
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking anchors failed: %s", e)
        return []


def backlinks_ref_domains(domain: str, limit: int = 30) -> list:
    try:
        data = _get("/backlinks/ref-domains", {
            "target": domain, "target_type": "domain", "limit": limit,
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking ref domains failed: %s", e)
        return []


def domain_authority(domain: str) -> dict:
    try:
        data = _get("/backlinks/authority", {"target": domain, "target_type": "domain"})
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("SE Ranking domain authority failed: %s", e)
        return {}


def keyword_metrics(keywords: list, source: str = "us") -> list:
    try:
        data = _get("/research/keywords/metrics", {
            "keywords": ",".join(keywords[:20]), "source": source,
        })
        return data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("SE Ranking keyword metrics failed: %s", e)
        return []


def full_dashboard(domain: str, source: str = "us") -> dict:
    overview = domain_overview(domain, source)
    keywords = domain_keywords(domain, source, limit=50)
    competitors = domain_competitors(domain, source, limit=15)
    bl_summary = backlinks_summary(domain)
    authority = domain_authority(domain)
    bl_top = backlinks_top(domain, limit=20)
    bl_anchors = backlinks_anchors(domain, limit=20)
    bl_ref = backlinks_ref_domains(domain, limit=20)

    return {
        "overview": overview,
        "keywords": keywords,
        "competitors": competitors,
        "backlinks": {
            "summary": bl_summary,
            "authority": authority,
            "top_backlinks": bl_top,
            "anchors": bl_anchors,
            "referring_domains": bl_ref,
        },
    }
