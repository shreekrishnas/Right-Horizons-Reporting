from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _service(creds: Credentials):
    return build("youtube", "v3", credentials=creds)


def get_channel_stats(creds: Credentials) -> dict:
    yt = _service(creds)
    resp = yt.channels().list(mine=True, part="snippet,statistics").execute()
    items = resp.get("items", [])
    if not items:
        return {}
    ch = items[0]
    stats = ch.get("statistics", {})
    return {
        "title": ch["snippet"]["title"],
        "description": ch["snippet"].get("description", ""),
        "thumbnail": ch["snippet"].get("thumbnails", {}).get("default", {}).get("url", ""),
        "subscribers": int(stats.get("subscriberCount", 0)),
        "views": int(stats.get("viewCount", 0)),
        "videos": int(stats.get("videoCount", 0)),
    }


def get_recent_videos(creds: Credentials, max_results: int = 10) -> list:
    yt = _service(creds)
    search = yt.search().list(
        forMine=True, type="video", order="date",
        part="snippet", maxResults=max_results,
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search.get("items", [])]
    if not video_ids:
        return []

    details = yt.videos().list(
        id=",".join(video_ids), part="statistics,snippet",
    ).execute()

    results = []
    for v in details.get("items", []):
        s = v.get("statistics", {})
        results.append({
            "id": v["id"],
            "title": v["snippet"]["title"],
            "published": v["snippet"]["publishedAt"],
            "thumbnail": v["snippet"].get("thumbnails", {}).get("medium", {}).get("url", ""),
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
        })
    return results


def generate_seo_metadata(topic: str) -> dict:
    topic_clean = topic.strip()
    topic_lower = topic_clean.lower()

    base_tags = [
        "Right Horizons", "wealth management", "PMS", "AIF",
        "portfolio management", "investment", "mutual funds",
        "stock market India", "financial planning", "SEBI registered",
    ]

    topic_tags = [w.strip() for w in topic_clean.split() if len(w.strip()) > 2]

    titles = [
        f"{topic_clean} | Right Horizons",
        f"{topic_clean} — Expert Analysis | Right Horizons",
        f"Understanding {topic_clean} in 2026 | Investment Guide",
        f"{topic_clean}: What Every Investor Should Know",
        f"Right Horizons Explains: {topic_clean}",
    ]

    description = (
        f"{topic_clean} — In this video, Right Horizons breaks down everything you need to know "
        f"about {topic_lower}.\n\n"
        f"Right Horizons is a SEBI-registered Portfolio Management Service (PMS) and "
        f"Alternative Investment Fund (AIF) provider helping investors build long-term wealth.\n\n"
        f"Topics covered:\n"
        f"- What is {topic_lower}?\n"
        f"- How does it impact your portfolio?\n"
        f"- Key takeaways for investors\n\n"
        f"Learn more: https://www.righthorizons.com\n"
        f"Contact: info@righthorizons.com\n\n"
        f"#RightHorizons #Investment #{topic_clean.replace(' ', '')} #WealthManagement"
    )

    hashtags = [
        f"#{topic_clean.replace(' ', '')}",
        "#RightHorizons", "#Investment", "#WealthManagement",
        "#PMS", "#AIF", "#StockMarket", "#Finance",
        "#PortfolioManagement", "#IndianStockMarket",
    ]

    tags = list(set(base_tags + topic_tags + [topic_clean]))[:20]

    return {
        "suggested_titles": titles,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }
