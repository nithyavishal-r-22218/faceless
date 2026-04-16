"""
Multi-platform video posting - YouTube, TikTok, Instagram Reels.
Handles auto-posting to all connected platforms.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from agent.config import BASE_DIR, YOUTUBE_API_KEY


class YouTubePoster:
    """Post videos to YouTube / YouTube Shorts."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def upload(self, video_path: str, title: str, description: str, tags: list,
               thumbnail_path: str = None, is_short: bool = True,
               made_for_kids: bool = True, scheduled_time: str = None) -> dict:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials.from_authorized_user_info(self.credentials)
        youtube = build("youtube", "v3", credentials=creds)

        # Add #Shorts tag for YouTube Shorts
        if is_short and "#Shorts" not in tags:
            tags.append("#Shorts")
        if is_short and "#shorts" not in title.lower():
            title = f"{title} #Shorts"

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": "24",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private" if scheduled_time else "public",
                "selfDeclaredMadeForKids": made_for_kids,
                "embeddable": True,
            },
        }

        if scheduled_time:
            body["status"]["publishAt"] = scheduled_time

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )

        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
                ).execute()
            except Exception:
                pass

        return {
            "platform": "youtube",
            "video_id": video_id,
            "url": f"https://youtube.com/shorts/{video_id}" if is_short else f"https://youtu.be/{video_id}",
            "status": "posted",
        }


class TikTokPoster:
    """Post videos to TikTok via their API."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def upload(self, video_path: str, title: str, description: str, tags: list,
               scheduled_time: str = None) -> dict:
        """Upload video to TikTok using the TikTok Content Posting API."""
        import httpx

        access_token = self.credentials.get("access_token", "")
        open_id = self.credentials.get("open_id", "")

        if not access_token:
            return {"platform": "tiktok", "status": "failed", "error": "No access token"}

        # Step 1: Initialize upload
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        hashtag_str = " ".join(f"#{t.strip('#')}" for t in tags[:5])
        caption = f"{title} {hashtag_str}"[:150]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        file_size = os.path.getsize(video_path)
        init_body = {
            "post_info": {
                "title": caption,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": min(file_size, 10 * 1024 * 1024),
                "total_chunk_count": 1,
            },
        }

        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(init_url, json=init_body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                upload_url = data.get("data", {}).get("upload_url", "")
                publish_id = data.get("data", {}).get("publish_id", "")

                if upload_url:
                    with open(video_path, "rb") as f:
                        upload_resp = client.put(
                            upload_url,
                            content=f.read(),
                            headers={"Content-Type": "video/mp4"},
                        )

                return {
                    "platform": "tiktok",
                    "publish_id": publish_id,
                    "status": "posted",
                }
        except Exception as e:
            return {"platform": "tiktok", "status": "failed", "error": str(e)}


class InstagramPoster:
    """Post Reels to Instagram via Graph API."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def upload(self, video_path: str, title: str, description: str, tags: list,
               thumbnail_path: str = None, scheduled_time: str = None) -> dict:
        """Upload Reel to Instagram."""
        import httpx

        access_token = self.credentials.get("access_token", "")
        ig_user_id = self.credentials.get("instagram_user_id", "")

        if not access_token or not ig_user_id:
            return {"platform": "instagram", "status": "failed", "error": "Missing credentials"}

        hashtag_str = " ".join(f"#{t.strip('#')}" for t in tags[:20])
        caption = f"{title}\n\n{description[:500]}\n\n{hashtag_str}"

        # For Instagram Reels, we need a public URL for the video
        # In production, upload to a CDN first, then provide the URL
        # For local dev, this simulates the flow
        try:
            with httpx.Client(timeout=120) as client:
                # Step 1: Create media container
                create_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
                create_resp = client.post(create_url, params={
                    "media_type": "REELS",
                    "video_url": video_path,  # Must be a public URL
                    "caption": caption[:2200],
                    "share_to_feed": "true",
                    "access_token": access_token,
                })
                create_data = create_resp.json()
                container_id = create_data.get("id")

                if not container_id:
                    return {"platform": "instagram", "status": "failed",
                            "error": create_data.get("error", {}).get("message", "Unknown error")}

                # Step 2: Publish
                publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
                publish_resp = client.post(publish_url, params={
                    "creation_id": container_id,
                    "access_token": access_token,
                })
                publish_data = publish_resp.json()

                return {
                    "platform": "instagram",
                    "media_id": publish_data.get("id"),
                    "status": "posted",
                }
        except Exception as e:
            return {"platform": "instagram", "status": "failed", "error": str(e)}


class MultiPlatformPoster:
    """Orchestrates posting to all connected platforms."""

    def __init__(self, platforms: dict):
        """platforms: {platform_type: credentials_dict}"""
        self.posters = {}
        for p_type, creds in platforms.items():
            if p_type == "youtube" and creds:
                self.posters["youtube"] = YouTubePoster(creds)
            elif p_type == "tiktok" and creds:
                self.posters["tiktok"] = TikTokPoster(creds)
            elif p_type == "instagram" and creds:
                self.posters["instagram"] = InstagramPoster(creds)

    def post_to_all(self, video_path: str, title: str, description: str,
                    tags: list, thumbnail_path: str = None,
                    target_platforms: list = None,
                    made_for_kids: bool = True,
                    scheduled_time: str = None) -> dict:
        """Post video to all (or specified) connected platforms."""
        results = {}
        targets = target_platforms or list(self.posters.keys())

        for platform in targets:
            poster = self.posters.get(platform)
            if not poster:
                results[platform] = {"status": "skipped", "error": "Not connected"}
                continue

            try:
                if platform == "youtube":
                    results[platform] = poster.upload(
                        video_path, title, description, tags,
                        thumbnail_path=thumbnail_path,
                        is_short=True,
                        made_for_kids=made_for_kids,
                        scheduled_time=scheduled_time,
                    )
                elif platform == "tiktok":
                    results[platform] = poster.upload(
                        video_path, title, description, tags,
                        scheduled_time=scheduled_time,
                    )
                elif platform == "instagram":
                    results[platform] = poster.upload(
                        video_path, title, description, tags,
                        thumbnail_path=thumbnail_path,
                        scheduled_time=scheduled_time,
                    )
            except Exception as e:
                results[platform] = {"status": "failed", "error": str(e)}

        return results
