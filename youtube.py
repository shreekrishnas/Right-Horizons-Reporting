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


def generate_seo_metadata(topic: str, speaker: str = "", transcript: str = "") -> dict:
    topic_clean = topic.strip()
    topic_lower = topic_clean.lower()
    speaker = speaker.strip()
    transcript = transcript.strip()

    topic_words = [w for w in topic_lower.split() if len(w) > 2]
    key_phrases = [topic_lower]
    if transcript:
        words = transcript.lower().split()
        freq = {}
        stop = {"the","a","an","is","are","was","were","be","been","being","have","has","had",
                "do","does","did","will","would","could","should","may","might","shall","can",
                "in","on","at","to","for","of","with","by","from","and","or","but","not","so",
                "this","that","these","those","it","its","we","you","i","he","she","they","our",
                "your","my","his","her","their","what","which","who","how","when","where","why",
                "about","into","than","then","also","just","very","more","most","some","any","all",
                "each","every","both","few","many","much","own","same","other","such","no","nor"}
        for w in words:
            w = ''.join(c for c in w if c.isalnum())
            if w and len(w) > 3 and w not in stop:
                freq[w] = freq.get(w, 0) + 1
        top_words = sorted(freq, key=freq.get, reverse=True)[:8]
        key_phrases.extend(top_words)

    seo_title_1 = f"{topic_clean} in India 2026 — Complete Guide for Smart Investors"
    seo_title_2 = f"{topic_clean}: Strategy, Returns & Risk Analysis | Expert Breakdown"
    if speaker:
        speaker_title = f"{topic_clean} with {speaker} | Right Horizons"
    else:
        speaker_title = f"{topic_clean} | Right Horizons Expert Analysis"

    titles = [
        {"type": "SEO Optimized", "title": seo_title_1},
        {"type": "SEO Optimized", "title": seo_title_2},
        {"type": "Speaker & Brand", "title": speaker_title},
    ]

    speaker_line = f" by {speaker}" if speaker else ""
    transcript_topics = ""
    if transcript:
        sentences = [s.strip() for s in transcript.replace('\n', '. ').split('.') if len(s.strip()) > 15]
        bullet_points = sentences[:5]
        transcript_topics = "\n".join(f"- {bp}" for bp in bullet_points)

    description = (
        f"{topic_clean}{speaker_line} — A deep-dive into {topic_lower} "
        f"covering key strategies, market outlook, and actionable insights for Indian investors.\n\n"
    )
    if speaker:
        description += (
            f"In this video, {speaker} from Right Horizons shares expert perspectives "
            f"on {topic_lower} and what it means for your portfolio in 2026.\n\n"
        )
    description += "Key topics covered in this video:\n"
    if transcript_topics:
        description += transcript_topics + "\n\n"
    else:
        description += (
            f"- What is {topic_lower} and why it matters now\n"
            f"- How {topic_lower} impacts your investment returns\n"
            f"- Strategies to maximize gains while managing risk\n"
            f"- Expert insights from Right Horizons research team\n\n"
        )
    description += (
        "About Right Horizons:\n"
        "Right Horizons is a SEBI-registered Portfolio Management Service (PMS) "
        "and Alternative Investment Fund (AIF) provider. With over 15 years of expertise, "
        "we help investors build sustainable, long-term wealth through research-driven strategies.\n\n"
        "Connect with us:\n"
        "Website: https://www.righthorizons.com\n"
        "PMS: https://righthorizonspms.com\n"
        "AIF: https://aif.righthorizonspms.com\n"
        "Email: info@righthorizons.com\n"
        "Phone: +91-80-4612 4612\n\n"
    )
    topic_tag = topic_clean.replace(' ', '')
    description += (
        f"#{topic_tag} #RightHorizons #Investment #WealthManagement "
        f"#PMS #AIF #StockMarketIndia #PortfolioManagement\n\n"
        "DISCLAIMER: This video is for educational and informational purposes only. "
        "It does not constitute investment advice. Please consult your financial advisor "
        "before making investment decisions."
    )

    base_tags = [
        "Right Horizons", "wealth management", "PMS India", "AIF India",
        "portfolio management services", "investment strategies India",
        "stock market India 2026", "financial planning", "SEBI registered PMS",
        "best PMS in India", topic_clean,
    ]
    if speaker:
        base_tags.append(speaker.split(',')[0].strip())
    extra = [w for w in key_phrases if w not in [t.lower() for t in base_tags]]
    tags = list(dict.fromkeys(base_tags + extra))[:25]

    hashtags = [
        f"#{topic_tag}", "#RightHorizons", "#Investment", "#WealthManagement",
        "#PMS", "#AIF", "#StockMarketIndia", "#Finance2026",
        "#PortfolioManagement", "#IndianStockMarket", "#SEBIRegistered",
        "#FinancialPlanning",
    ]

    return {
        "titles": titles,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }
