"""
Trending Video Finder
Discovers trending topics and videos in kids/cartoon niche using YouTube API and Gemini.
"""
from __future__ import annotations

import json
from datetime import datetime

import google.generativeai as genai
from googleapiclient.discovery import build

from agent.config import GEMINI_API_KEY, YOUTUBE_API_KEY, KIDS_CATEGORIES, OUTPUT_DIR

genai.configure(api_key=GEMINI_API_KEY)


def get_youtube_service():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def find_trending_kids_videos(max_results: int = 25) -> list[dict]:
    """Find currently trending kids/cartoon videos on YouTube."""
    youtube = get_youtube_service()

    search_queries = [
        "kids cartoon new",
        "children story animated",
        "nursery rhymes 2024",
        "kids learning videos",
        "cartoon for kids",
        "bedtime stories for children",
        "funny cartoons kids",
        "animal stories for kids",
        "superhero cartoon kids",
        "fairy tales animated",
    ]

    all_videos = []
    seen_ids = set()

    for query in search_queries:
        try:
            response = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                order="viewCount",
                publishedAfter=_get_recent_date(),
                maxResults=5,
                videoCategoryId="24",  # Entertainment
                relevanceLanguage="en",
                safeSearch="strict",
            ).execute()

            for item in response.get("items", []):
                vid = item["id"]["videoId"]
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    all_videos.append({
                        "video_id": vid,
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "published_at": item["snippet"]["publishedAt"],
                        "description": item["snippet"]["description"][:200],
                        "search_query": query,
                    })
        except Exception as e:
            print(f"⚠️ Search failed for '{query}': {e}")

    # Get view counts for found videos
    if all_videos:
        video_ids = [v["video_id"] for v in all_videos[:50]]
        stats_response = youtube.videos().list(
            part="statistics,contentDetails",
            id=",".join(video_ids),
        ).execute()

        stats_map = {}
        for item in stats_response.get("items", []):
            stats_map[item["id"]] = {
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
                "duration": item["contentDetails"]["duration"],
            }

        for v in all_videos:
            if v["video_id"] in stats_map:
                v.update(stats_map[v["video_id"]])

    # Sort by views
    all_videos.sort(key=lambda x: x.get("views", 0), reverse=True)
    return all_videos[:max_results]


def analyze_trends_with_gemini(trending_videos: list[dict]) -> dict:
    """Use Gemini to analyze trends and suggest content ideas."""
    model = genai.GenerativeModel("gemini-pro")

    video_summaries = []
    for v in trending_videos[:15]:
        video_summaries.append(
            f"- \"{v['title']}\" by {v['channel']} ({v.get('views', 0):,} views)"
        )

    prompt = f"""You are a kids' cartoon YouTube content strategist with 30+ years experience.

Analyze these currently trending kids videos:
{chr(10).join(video_summaries)}

Based on these trends, provide:
1. Top 5 trending themes/topics in kids content right now
2. 10 specific video ideas we should create (title + brief description)
3. Best keywords to target
4. Content gaps we can fill (underserved topics)
5. Recommended video formats (duration, style)
6. Thumbnail trends (what's working)

Return as JSON:
{{
    "trending_themes": ["theme1", "theme2", ...],
    "video_ideas": [
        {{"title": "...", "description": "...", "category": "...", "priority": "high/medium/low"}}
    ],
    "keywords": ["keyword1", "keyword2", ...],
    "content_gaps": ["gap1", "gap2", ...],
    "format_recommendations": {{
        "optimal_duration": "5-8 minutes",
        "best_styles": ["style1", "style2"],
        "upload_frequency": "daily"
    }},
    "thumbnail_trends": ["trend1", "trend2", ...]
}}

Return ONLY valid JSON."""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:]

    analysis = json.loads(text.strip())
    return analysis


def get_trending_report() -> dict:
    """Generate complete trending report with videos and AI analysis."""
    print("🔍 Finding trending kids videos...")
    trending = find_trending_kids_videos()

    print(f"📊 Found {len(trending)} trending videos")
    print("🤖 Analyzing trends with Gemini...")
    analysis = analyze_trends_with_gemini(trending)

    report = {
        "generated_at": datetime.now().isoformat(),
        "trending_videos": trending,
        "ai_analysis": analysis,
    }

    # Save report
    report_path = OUTPUT_DIR / "trending_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"📄 Report saved to {report_path}")
    return report


def print_trending_report(report: dict):
    """Print formatted trending report."""
    analysis = report.get("ai_analysis", {})

    print("\n" + "=" * 60)
    print("🔥 TRENDING CONTENT REPORT")
    print("=" * 60)

    print("\n📈 TRENDING THEMES:")
    for i, theme in enumerate(analysis.get("trending_themes", []), 1):
        print(f"   {i}. {theme}")

    print("\n💡 VIDEO IDEAS TO CREATE:")
    for idea in analysis.get("video_ideas", []):
        priority = idea.get("priority", "medium")
        icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        print(f"   {icon} {idea['title']}")
        print(f"      └─ {idea.get('description', '')}")

    print("\n🏷️ TOP KEYWORDS:")
    keywords = analysis.get("keywords", [])
    print(f"   {', '.join(keywords[:15])}")

    print("\n🕳️ CONTENT GAPS:")
    for gap in analysis.get("content_gaps", []):
        print(f"   • {gap}")

    fmt = analysis.get("format_recommendations", {})
    print(f"\n⏱️ OPTIMAL DURATION: {fmt.get('optimal_duration', 'N/A')}")
    print(f"📅 UPLOAD FREQUENCY: {fmt.get('upload_frequency', 'N/A')}")

    print("\n🖼️ THUMBNAIL TRENDS:")
    for trend in analysis.get("thumbnail_trends", []):
        print(f"   • {trend}")

    print("=" * 60)


def _get_recent_date() -> str:
    """Get ISO date string for 30 days ago."""
    from datetime import timezone
    d = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=30)
    return d.strftime("%Y-%m-%dT00:00:00Z")
