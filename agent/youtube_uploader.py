"""
YouTube Uploader & Scheduler
Handles OAuth2 authentication, video upload, and scheduled publishing.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import schedule
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from agent.config import (
    BASE_DIR,
    UPLOAD_TIME,
    UPLOAD_TIMEZONE,
    YOUTUBE_API_KEY,
    YOUTUBE_CATEGORY_EDUCATION,
    YOUTUBE_CHANNEL_ID,
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.readonly"]

TOKEN_FILE = BASE_DIR / "token.json"
CLIENT_SECRETS_FILE = BASE_DIR / "client_secret.json"


def get_authenticated_service():
    """Get authenticated YouTube API service."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                # Create client secrets from env vars
                client_config = {
                    "installed": {
                        "client_id": YOUTUBE_CLIENT_ID,
                        "client_secret": YOUTUBE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"],
                    }
                }
                with open(CLIENT_SECRETS_FILE, "w") as f:
                    json.dump(client_config, f)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: str = None,
    category_id: str = YOUTUBE_CATEGORY_EDUCATION,
    privacy: str = "private",
    publish_at: str = None,
    made_for_kids: bool = True,
) -> str:
    """Upload a video to YouTube.

    Returns the video ID on success.
    """
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": description[:5000],  # YouTube desc limit
            "tags": tags[:30],  # YouTube tags limit
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": True,
            "publicStatsViewable": True,
        },
    }

    # Schedule for later if publish_at provided
    if publish_at and privacy == "private":
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    print(f"📤 Uploading: {title}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"✅ Uploaded! Video ID: {video_id}")

    # Set thumbnail if provided
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
            ).execute()
            print(f"🖼️ Thumbnail set for {video_id}")
        except Exception as e:
            print(f"⚠️ Thumbnail upload failed: {e}")

    return video_id


def schedule_upload(
    video_path: str,
    script: dict,
    thumbnail_path: str = None,
    publish_date: str = None,
    publish_time: str = None,
) -> str:
    """Schedule a video upload for a specific date/time."""
    title = script.get("title", "Kids Video")
    description = script.get("description", "")

    # Add SEO description if available
    if "seo" in script:
        description = script["seo"].get("description_seo", description)

    tags = script.get("tags", [])
    if "seo" in script:
        tags = script["seo"].get("tags_enhanced", tags)

    # Build publish datetime
    if publish_date and publish_time:
        publish_at = f"{publish_date}T{publish_time}:00.000Z"
    elif publish_date:
        publish_at = f"{publish_date}T{UPLOAD_TIME}:00.000Z"
    else:
        # Upload now as private
        publish_at = None

    video_id = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=thumbnail_path,
        privacy="private" if publish_at else "public",
        publish_at=publish_at,
        made_for_kids=True,
    )

    return video_id


def batch_schedule_uploads(upload_queue: list[dict]) -> list[dict]:
    """Upload and schedule multiple videos.

    upload_queue: list of dicts with keys:
        - video_path, script, thumbnail_path, publish_date, publish_time
    """
    results = []
    for item in upload_queue:
        try:
            video_id = schedule_upload(
                video_path=item["video_path"],
                script=item["script"],
                thumbnail_path=item.get("thumbnail_path"),
                publish_date=item.get("publish_date"),
                publish_time=item.get("publish_time"),
            )
            results.append({
                "day": item.get("day"),
                "video_id": video_id,
                "status": "uploaded",
                "title": item["script"].get("title"),
            })
        except Exception as e:
            results.append({
                "day": item.get("day"),
                "status": "failed",
                "error": str(e),
                "title": item["script"].get("title"),
            })
            print(f"❌ Upload failed for day {item.get('day')}: {e}")

    return results


def run_scheduler(upload_fn, daily_time: str = None):
    """Run a background scheduler that triggers uploads at set times."""
    daily_time = daily_time or UPLOAD_TIME

    schedule.every().day.at(daily_time).do(upload_fn)
    print(f"⏰ Scheduler started. Will run daily at {daily_time}")

    while True:
        schedule.run_pending()
        time.sleep(60)
