import json
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

log = logging.getLogger(__name__)


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


def get_videos_in_range(creds: Credentials, start: str, end: str, max_scan: int = 200) -> list:
    """Videos published between start and end (YYYY-MM-DD), with view/like/comment stats.

    NOTE: YouTube's search API forbids combining forMine=true with
    publishedAfter/publishedBefore (returns HTTP 400), so we page through
    the newest videos ordered by date and filter to the range on our side.
    """
    yt = _service(creds)
    collected = []
    page_token = None
    scanned = 0
    while scanned < max_scan:
        kwargs = dict(forMine=True, type="video", order="date", part="snippet", maxResults=50)
        if page_token:
            kwargs["pageToken"] = page_token
        search = yt.search().list(**kwargs).execute()
        items = search.get("items", [])
        if not items:
            break
        scanned += len(items)
        stop = False
        for it in items:
            pub = it.get("snippet", {}).get("publishedAt", "")[:10]
            if pub and pub < start:
                stop = True  # results are newest-first; everything after is older
            if pub and start <= pub <= end:
                collected.append(it)
        page_token = search.get("nextPageToken")
        if not page_token or stop:
            break

    video_ids = [it["id"]["videoId"] for it in collected if it.get("id", {}).get("videoId")]
    if not video_ids:
        return []
    out = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        details = yt.videos().list(id=",".join(chunk), part="statistics,snippet").execute()
        for v in details.get("items", []):
            s = v.get("statistics", {})
            out.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"],
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            })
    return out


def get_monthly_summary(creds: Credentials, start: str, end: str) -> dict:
    """Aggregate YouTube activity for a date range: videos published + their stats."""
    vids = get_videos_in_range(creds, start, end)
    return {
        "videos_published": len(vids),
        "views": sum(v["views"] for v in vids),
        "likes": sum(v["likes"] for v in vids),
        "comments": sum(v["comments"] for v in vids),
    }


_SEO_SYSTEM = """You are the YouTube SEO strategist for Right Horizons (Indian SEBI-registered PMS & AIF firm).

You produce professional YouTube descriptions, titles, timestamps, and tags that match the firm's
established format EXACTLY. Study these two real examples of Right Horizons YouTube descriptions:

--- EXAMPLE 1 ---
Looking to invest beyond mutual funds, PMS, and stocks? In this Right FinTalk Live webinar, Anil Rego (Founder & CIO of Right Horizons) explains Alternative Investment Funds (AIF), how they manage risk via market hedging, and who should consider them for portfolio diversification.

Timestamp:
00:00 - Introduction & Portfolio Diversification
02:08 - Audience Poll: What is an Alternative Investment Fund (AIF)?
04:03 - Why Consider AIFs? Low Market Correlation & Hedging Explained
08:09 - What is an Alternative Investment Fund? Mutual Funds vs. PMS vs. AIF
11:24 - AIF Categories Explained: Cat 1, Cat 2, and Cat 3 Funds
15:51 - Asset Allocation: How HNIs & Family Offices Structure Portfolios
21:30 - Small Cap & Mid Cap Market Cycle Outlook (20-Year Data)
28:44 - The Right Horizons $10 Trillion India Growth Opportunity Strategy
33:32 - AIF Fund Structure: Staggered Drawdowns, Lock-ins, and Taxation
39:12 - Global Opportunity Strategy: International Diversification with ETFs

Key topics covered:
✅ What is an Alternative Investment Fund and how it differs from Mutual Funds and PMS
✅ Why low market correlation matters for portfolio risk
✅ How AIFs use F&O for both hedging and growth
✅ Asymmetric return potential and downside protection
✅ The Right Horizons AIF and the India opportunity
✅ Introduction to global fund of funds investing
✅ Who should consider AIFs and why

📢 Watch now to understand how AIFs can add a new dimension to your investment portfolio
🔔 Like, Share & Subscribe for more insights from Right Horizons

For more information about Right Horizons, connect with us:
Facebook: https://facebook.com/Righthorizonsfinancialspvtltd/
LinkedIn: https://linkedin.com/in/right-horizons-3b8a2240/
Instagram: https://instagram.com/_righthorizons_/
Website: https://www.righthorizons.com
Website: https://righthorizonspms.com/

#AlternativeInvestments #AIFFund #RightHorizons #AnilRego #WealthManagement #PortfolioManagement #HNIInvestors #InvestmentStrategy #AssetAllocation #IndiaGrowthStory #AlternativeAssets #FinancialPlanning #RightFinTalk #SmartInvesting #BeyondMutualFunds

Disclaimer: Investments in securities markets are subject to market risks. Read all scheme-related documents carefully before investing. Past performance is not indicative of future results.

--- EXAMPLE 2 ---
Looking to understand where India's markets may be headed and how investors can approach opportunities beyond traditional investment products?

In this Right Horizons webinar, Shakthi Prabhu, Assistant Fund Manager at Right Horizons, shares insights on India's structural growth story, the current macro environment, FII sentiment, small and mid-cap opportunities, and the role of Alternative Investment Funds in long-term wealth creation.

Key topics covered:
✅ India's long-term structural growth opportunity
✅ Current market environment and macroeconomic indicators
✅ FII flows, currency stability and global capital rotation
✅ Why small and mid-caps can create long-term wealth
✅ How AIFs differ from traditional investment products
✅ RH Rising India Opportunities AIF strategy and structure

📢 Watch now to understand how India's growth story, small-cap opportunities and AIF strategies can support long-term wealth creation.
🔔 Like, Share & Subscribe for more insights from Right Horizons.

For more information about Right Horizons, connect with us:
Facebook: https://facebook.com/Righthorizonsfinancialspvtltd/
LinkedIn: https://linkedin.com/in/right-horizons-3b8a2240/
Instagram: https://instagram.com/_righthorizons_/
Website: https://www.righthorizons.com
Website: https://righthorizonspms.com/

#RightHorizons #AIF #AlternativeInvestmentFund #RHWebinar #ShakthiPrabhu #WealthManagement #SmallCaps #MidCaps #IndiaGrowthStory #InvestmentStrategy #PortfolioManagement #HNIInvestors #MarketOutlook #AssetAllocation #RiskManagement #FinancialPlanning #LongTermInvesting #SmartInvesting #AlternativeInvestments

Disclaimer: Investments in securities markets are subject to market risks. Read all scheme-related documents carefully before investing. Past performance is not indicative of future results.

--- END EXAMPLES ---

RULES FOR GENERATING OUTPUT:
1. DESCRIPTION must follow the EXACT structure:
   - Opening hook paragraph (1-2 sentences, question or statement that pulls the viewer in)
   - Speaker intro paragraph ("In this Right Horizons webinar, [Speaker Name], [Title] at Right Horizons, shares insights on...")
   - Timestamp section (if transcript is provided — generate realistic timestamps from the transcript content, formatted as "Timestamp:\\n00:00 - Topic\\n02:15 - Topic...")
   - "Key topics covered:" section with ✅ bullet points (5-8 points, specific not generic)
   - 📢 CTA line ("Watch now to understand...")
   - 🔔 Subscribe line
   - Social links block (ALWAYS include these exact links):
     Facebook: https://facebook.com/Righthorizonsfinancialspvtltd/
     LinkedIn: https://linkedin.com/in/right-horizons-3b8a2240/
     Instagram: https://instagram.com/_righthorizons_/
     Website: https://www.righthorizons.com
     Website: https://righthorizonspms.com/
   - Hashtags line (15-20 hashtags, always include #RightHorizons, speaker name hashtag, topic-specific tags)
   - Disclaimer: "Investments in securities markets are subject to market risks. Read all scheme-related documents carefully before investing. Past performance is not indicative of future results."

2. TITLES: Generate 4-5 title options:
   - SEO-optimized titles with year, numbers, and power words
   - Speaker & brand title with speaker name
   - Curiosity-driven title
   - Each under 100 characters for YouTube best practices

3. TAGS: Generate 25-30 YouTube tags (NOT hashtags — these go in YouTube's tag field):
   - Mix of broad (wealth management, investment) and specific (topic-related)
   - Include "Right Horizons", speaker name, topic variations
   - Include India-specific investing terms
   - Include trending finance YouTube search terms
   - Long-tail keywords (3-5 word phrases that people actually search)

4. HASHTAGS: Generate 15-20 hashtags for the description:
   - Always start with topic-specific tags
   - Always include #RightHorizons
   - Include speaker name as hashtag
   - Mix of broad financial + specific topic tags
   - Never use generic hype tags (#trending, #viral)

Return JSON: {
  "titles": [{"type": "SEO Optimized"|"Speaker & Brand"|"Curiosity", "title": "..."}],
  "description": "full description following the exact structure above",
  "tags": ["tag1", "tag2", ...],
  "hashtags": ["#Tag1", "#Tag2", ...]
}"""


def generate_seo_metadata(topic: str, speaker: str = "", transcript: str = "") -> dict:
    try:
        import ai as ai_mod
    except ImportError:
        ai_mod = None

    if not ai_mod:
        return _fallback_seo(topic, speaker, transcript)

    user_msg = f"VIDEO TOPIC: {topic}\n"
    if speaker:
        user_msg += f"SPEAKER: {speaker}\n"
    if transcript:
        user_msg += f"\nTRANSCRIPT / KEY POINTS:\n{transcript[:15000]}\n"
    user_msg += "\nGenerate the complete YouTube SEO package following the structure and quality of the examples."

    try:
        result = ai_mod.chat_json(_SEO_SYSTEM, user_msg, max_tokens=5000, temperature=0.6)
        if isinstance(result, dict):
            items = result.get("items")
            if isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict):
                result = items[0]
            elif isinstance(items, dict):
                result = items
        for key in ("titles", "description", "tags", "hashtags"):
            if key not in result:
                result[key] = [] if key != "description" else ""
        return result
    except Exception as e:
        log.warning("AI SEO generation failed, using fallback: %s", e)
        return _fallback_seo(topic, speaker, transcript)


def _fallback_seo(topic: str, speaker: str = "", transcript: str = "") -> dict:
    topic_clean = topic.strip()
    topic_tag = topic_clean.replace(' ', '')
    speaker_line = f", {speaker}," if speaker else ""

    description = (
        f"Looking to understand {topic_clean.lower()} and how it fits into your investment strategy?\n\n"
        f"In this Right Horizons webinar{speaker_line} shares insights on {topic_clean.lower()}, "
        f"key strategies, market outlook, and actionable takeaways for Indian investors.\n\n"
        "Key topics covered:\n"
        f"✅ What is {topic_clean.lower()} and why it matters now\n"
        f"✅ How {topic_clean.lower()} impacts your investment portfolio\n"
        "✅ Strategies to maximize returns while managing risk\n"
        "✅ Expert insights from Right Horizons research team\n\n"
        f"📢 Watch now to understand how {topic_clean.lower()} can support your wealth creation goals.\n"
        "🔔 Like, Share & Subscribe for more insights from Right Horizons.\n\n"
        "For more information about Right Horizons, connect with us:\n"
        "Facebook: https://facebook.com/Righthorizonsfinancialspvtltd/\n"
        "LinkedIn: https://linkedin.com/in/right-horizons-3b8a2240/\n"
        "Instagram: https://instagram.com/_righthorizons_/\n"
        "Website: https://www.righthorizons.com\n"
        "Website: https://righthorizonspms.com/\n\n"
        f"#{topic_tag} #RightHorizons #WealthManagement #Investment #PortfolioManagement "
        "#HNIInvestors #InvestmentStrategy #FinancialPlanning #SmartInvesting\n\n"
        "Disclaimer: Investments in securities markets are subject to market risks. "
        "Read all scheme-related documents carefully before investing. "
        "Past performance is not indicative of future results."
    )

    titles = [
        {"type": "SEO Optimized", "title": f"{topic_clean} in India 2026 — Complete Guide for Smart Investors"},
        {"type": "SEO Optimized", "title": f"{topic_clean}: Strategy, Returns & Risk Analysis | Expert Breakdown"},
    ]
    if speaker:
        titles.append({"type": "Speaker & Brand", "title": f"{topic_clean} with {speaker} | Right Horizons"})
    else:
        titles.append({"type": "Speaker & Brand", "title": f"{topic_clean} | Right Horizons Expert Analysis"})

    tags = [
        "Right Horizons", "wealth management", "PMS India", "AIF India",
        "portfolio management services", "investment strategies India",
        "stock market India 2026", "financial planning", "SEBI registered PMS",
        "best PMS in India", topic_clean,
    ]
    if speaker:
        tags.append(speaker.split(',')[0].strip())

    hashtags = [
        f"#{topic_tag}", "#RightHorizons", "#WealthManagement", "#Investment",
        "#PortfolioManagement", "#HNIInvestors", "#InvestmentStrategy",
        "#FinancialPlanning", "#SmartInvesting", "#IndiaGrowthStory",
    ]

    return {
        "titles": titles,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }
