"""
YouTube Channel Analytics
Analyzes channel performance, video stats, and provides insights.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from agent.config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, OUTPUT_DIR


def get_youtube_service():
    """Get YouTube API service (read-only, uses API key)."""
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def get_channel_stats(channel_id: str = None) -> dict:
    """Get overall channel statistics."""
    youtube = get_youtube_service()
    channel_id = channel_id or YOUTUBE_CHANNEL_ID

    response = youtube.channels().list(
        part="snippet,statistics,contentDetails,brandingSettings",
        id=channel_id,
    ).execute()

    if not response.get("items"):
        return {"error": "Channel not found"}

    channel = response["items"][0]
    stats = channel["statistics"]

    return {
        "channel_name": channel["snippet"]["title"],
        "description": channel["snippet"]["description"],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
        "created_at": channel["snippet"]["publishedAt"],
        "avg_views_per_video": (
            int(stats.get("viewCount", 0)) // max(int(stats.get("videoCount", 1)), 1)
        ),
    }


def get_recent_videos(channel_id: str = None, max_results: int = 20) -> list[dict]:
    """Get recent videos from the channel."""
    youtube = get_youtube_service()
    channel_id = channel_id or YOUTUBE_CHANNEL_ID

    # Get uploads playlist
    channel_response = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()

    if not channel_response.get("items"):
        return []

    uploads_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get videos from uploads playlist
    playlist_response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=uploads_id,
        maxResults=min(max_results, 50),
    ).execute()

    video_ids = [
        item["contentDetails"]["videoId"]
        for item in playlist_response.get("items", [])
    ]

    if not video_ids:
        return []

    # Get detailed stats for each video
    videos_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    videos = []
    for item in videos_response.get("items", []):
        stats = item["statistics"]
        videos.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "duration": item["contentDetails"]["duration"],
            "tags": item["snippet"].get("tags", []),
            "description": item["snippet"]["description"][:200],
        })

    return sorted(videos, key=lambda x: x["views"], reverse=True)


def analyze_performance(channel_id: str = None) -> dict:
    """Comprehensive channel performance analysis."""
    channel_stats = get_channel_stats(channel_id)
    recent_videos = get_recent_videos(channel_id, max_results=30)

    if not recent_videos:
        return {
            "channel": channel_stats,
            "analysis": "No videos found for analysis.",
        }

    # Calculate metrics
    total_views = sum(v["views"] for v in recent_videos)
    total_likes = sum(v["likes"] for v in recent_videos)
    total_comments = sum(v["comments"] for v in recent_videos)
    num_videos = len(recent_videos)

    avg_views = total_views // num_videos
    avg_likes = total_likes // num_videos
    avg_comments = total_comments // num_videos

    # Find best/worst performing
    best_video = max(recent_videos, key=lambda x: x["views"])
    worst_video = min(recent_videos, key=lambda x: x["views"])

    # Engagement rate
    engagement_rate = (
        (total_likes + total_comments) / max(total_views, 1) * 100
    )

    # Tag analysis - find most common tags
    all_tags = []
    for v in recent_videos:
        all_tags.extend(v.get("tags", []))
    tag_freq = {}
    for tag in all_tags:
        tag_freq[tag.lower()] = tag_freq.get(tag.lower(), 0) + 1
    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:20]

    analysis = {
        "channel": channel_stats,
        "performance": {
            "videos_analyzed": num_videos,
            "avg_views": avg_views,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "engagement_rate": round(engagement_rate, 2),
            "total_views_recent": total_views,
        },
        "best_video": {
            "title": best_video["title"],
            "views": best_video["views"],
            "video_id": best_video["video_id"],
        },
        "worst_video": {
            "title": worst_video["title"],
            "views": worst_video["views"],
            "video_id": worst_video["video_id"],
        },
        "top_tags": top_tags,
        "recommendations": generate_recommendations(
            avg_views, engagement_rate, best_video, recent_videos
        ),
    }

    # Save analysis
    analysis_path = OUTPUT_DIR / "channel_analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    return analysis


def generate_recommendations(
    avg_views: int, engagement_rate: float, best_video: dict, recent_videos: list
) -> list[str]:
    """Generate actionable recommendations based on analytics."""
    recs = []

    if avg_views < 100:
        recs.append("📈 Focus on SEO: Use trending keywords in titles and descriptions")
        recs.append("🏷️ Add more relevant tags (aim for 15-30 tags per video)")
        recs.append("📱 Share videos on social media platforms")

    if engagement_rate < 2:
        recs.append("💬 Add CTAs in videos asking viewers to like and comment")
        recs.append("❓ Include questions in descriptions to boost comments")

    if engagement_rate < 5:
        recs.append("🎯 Create more content similar to your best performer")
        recs.append(f"🌟 Your best video '{best_video['title']}' - make similar content")

    recs.append("📅 Maintain consistent upload schedule (daily is ideal)")
    recs.append("🖼️ Create eye-catching thumbnails with bright colors")
    recs.append("⏱️ Optimal video length for kids: 5-10 minutes")
    recs.append("🔄 Create video series to boost watch time")

    return recs


def get_competitor_analysis(competitor_channel_ids: list[str]) -> list[dict]:
    """Analyze competitor channels for benchmarking."""
    results = []
    for cid in competitor_channel_ids:
        try:
            stats = get_channel_stats(cid)
            top_videos = get_recent_videos(cid, max_results=10)
            results.append({
                "channel": stats,
                "top_videos": top_videos[:5],
            })
        except Exception as e:
            results.append({"channel_id": cid, "error": str(e)})

    return results


def print_analytics_report(analysis: dict):
    """Print a formatted analytics report."""
    ch = analysis.get("channel", {})
    perf = analysis.get("performance", {})

    print("\n" + "=" * 60)
    print(f"📊 CHANNEL ANALYTICS REPORT")
    print("=" * 60)
    print(f"📺 Channel: {ch.get('channel_name', 'N/A')}")
    print(f"👥 Subscribers: {ch.get('subscribers', 0):,}")
    print(f"👁️ Total Views: {ch.get('total_views', 0):,}")
    print(f"🎬 Total Videos: {ch.get('total_videos', 0):,}")
    print()
    print(f"📈 RECENT PERFORMANCE ({perf.get('videos_analyzed', 0)} videos)")
    print(f"   Avg Views: {perf.get('avg_views', 0):,}")
    print(f"   Avg Likes: {perf.get('avg_likes', 0):,}")
    print(f"   Avg Comments: {perf.get('avg_comments', 0):,}")
    print(f"   Engagement Rate: {perf.get('engagement_rate', 0)}%")
    print()

    best = analysis.get("best_video", {})
    print(f"🏆 Best Video: {best.get('title', 'N/A')} ({best.get('views', 0):,} views)")

    print("\n💡 RECOMMENDATIONS:")
    for rec in analysis.get("recommendations", []):
        print(f"   {rec}")

    print("=" * 60)
