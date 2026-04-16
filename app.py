"""
FastAPI Web Application - Faceless Video Automation Platform
The main web server that powers the dashboard, API, and video generation pipeline.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent.auth import create_access_token, decode_access_token, hash_password, verify_password
from agent.config import BASE_DIR, OUTPUT_DIR, VIDEOS_DIR, THUMBNAILS_DIR, SCRIPTS_DIR
from agent.database import SessionLocal, init_db, User, Series, Video, Platform, ScheduleJob
from agent.styles import ART_STYLES, NICHES, MUSIC_STYLES, TTS_VOICES

app = FastAPI(title="Faceless Video Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# WebSocket connections for real-time progress
active_connections: dict[str, WebSocket] = {}

init_db()


# ── Dependencies ─────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


# ── Pydantic Models ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class SeriesCreate(BaseModel):
    name: str
    niche: str = "kids_cartoon"
    art_style: str = "cartoon"
    voice: str = "en-US-AnaNeural"
    music_style: str = "upbeat"
    video_format: str = "short"
    video_duration_target: int = 60
    posting_frequency: str = "daily"
    posting_time: str = "10:00"
    posting_platforms: list[str] = ["youtube"]
    auto_post: bool = True
    tags_default: list[str] = []

class VideoCreate(BaseModel):
    series_id: str = ""
    topic: str = ""
    niche: str = "kids_cartoon"
    art_style: str = "cartoon"
    video_format: str = "short"
    duration_target: int = 60

class ScheduleCreate(BaseModel):
    video_id: str
    scheduled_time: str
    platforms: list[str] = ["youtube"]


# ── Auth Routes ──────────────────────────────────────────────────
@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        name=req.name or req.email.split("@")[0],
        plan="free",
        videos_remaining=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "plan": user.plan}}


@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.id})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "plan": user.plan}}


@app.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "email": user.email, "name": user.name,
        "plan": user.plan, "videos_remaining": user.videos_remaining,
    }


# ── Series Routes ────────────────────────────────────────────────
@app.post("/api/series")
def create_series(req: SeriesCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    series = Series(
        user_id=user.id,
        name=req.name,
        niche=req.niche,
        art_style=req.art_style,
        voice=req.voice,
        music_style=req.music_style,
        video_format=req.video_format,
        video_duration_target=req.video_duration_target,
        posting_frequency=req.posting_frequency,
        posting_time=req.posting_time,
        posting_platforms=req.posting_platforms,
        auto_post=req.auto_post,
        tags_default=req.tags_default,
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    return _series_to_dict(series)


@app.get("/api/series")
def list_series(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    series_list = db.query(Series).filter(Series.user_id == user.id).all()
    return [_series_to_dict(s) for s in series_list]


@app.get("/api/series/{series_id}")
def get_series(series_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    series = db.query(Series).filter(Series.id == series_id, Series.user_id == user.id).first()
    if not series:
        raise HTTPException(404, "Series not found")
    return _series_to_dict(series)


@app.delete("/api/series/{series_id}")
def delete_series(series_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    series = db.query(Series).filter(Series.id == series_id, Series.user_id == user.id).first()
    if not series:
        raise HTTPException(404, "Series not found")
    db.delete(series)
    db.commit()
    return {"status": "deleted"}


# ── Video Routes ─────────────────────────────────────────────────
@app.post("/api/videos/generate")
async def generate_video(req: VideoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.videos_remaining <= 0 and user.plan == "free":
        raise HTTPException(403, "Video limit reached. Upgrade your plan.")

    video = Video(
        user_id=user.id,
        series_id=req.series_id or None,
        title="Generating...",
        niche=req.niche,
        art_style=req.art_style,
        video_format=req.video_format,
        status="generating",
        generation_progress=0,
        generation_step="Starting...",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Launch background generation
    asyncio.create_task(_generate_video_pipeline(video.id, req, user.id))

    return {"video_id": video.id, "status": "generating"}


@app.get("/api/videos")
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    videos = db.query(Video).filter(Video.user_id == user.id).order_by(Video.created_at.desc()).all()
    return [_video_to_dict(v) for v in videos]


@app.get("/api/videos/{video_id}")
def get_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    return _video_to_dict(video)


@app.get("/api/videos/{video_id}/download")
def download_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not video or not video.video_path:
        raise HTTPException(404, "Video not found")
    return FileResponse(video.video_path, media_type="video/mp4", filename=f"{video.title}.mp4")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    db.delete(video)
    db.commit()
    return {"status": "deleted"}


# ── Schedule Routes ──────────────────────────────────────────────
@app.post("/api/schedule")
def schedule_video(req: ScheduleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == req.video_id, Video.user_id == user.id).first()
    if not video:
        raise HTTPException(404, "Video not found")

    job = ScheduleJob(
        video_id=req.video_id,
        series_id=video.series_id,
        scheduled_time=datetime.fromisoformat(req.scheduled_time),
        platforms=req.platforms,
        status="pending",
    )
    db.add(job)
    video.scheduled_at = job.scheduled_time
    video.status = "scheduled"
    db.commit()
    return {"job_id": job.id, "status": "scheduled"}


@app.get("/api/schedule")
def list_scheduled(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = (
        db.query(ScheduleJob)
        .join(Video)
        .filter(Video.user_id == user.id)
        .order_by(ScheduleJob.scheduled_time)
        .all()
    )
    return [
        {
            "id": j.id, "video_id": j.video_id, "scheduled_time": j.scheduled_time.isoformat(),
            "platforms": j.platforms, "status": j.status,
        }
        for j in jobs
    ]


# ── Platform/Social Connection Routes ────────────────────────────
@app.get("/api/platforms")
def list_platforms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    platforms = db.query(Platform).filter(Platform.user_id == user.id).all()
    return [
        {"id": p.id, "platform_type": p.platform_type, "account_name": p.account_name, "is_connected": p.is_connected}
        for p in platforms
    ]


@app.post("/api/platforms/connect")
def connect_platform(platform_type: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # In production, this would redirect to OAuth flow for each platform
    platform = Platform(user_id=user.id, platform_type=platform_type)
    db.add(platform)
    db.commit()
    return {"id": platform.id, "platform_type": platform_type, "status": "pending_auth"}


# ── Config/Options Routes ────────────────────────────────────────
@app.get("/api/config/niches")
def get_niches():
    return [{"id": k, "name": v["name"], "description": v["description"],
             "default_art_style": v["default_art_style"], "categories": v.get("categories", [])}
            for k, v in NICHES.items()]


@app.get("/api/config/art-styles")
def get_art_styles():
    return [{"id": k, "name": v["name"], "description": v["description"]}
            for k, v in ART_STYLES.items()]


@app.get("/api/config/voices")
def get_voices():
    return [{"id": k, **v} for k, v in TTS_VOICES.items()]


@app.get("/api/config/music")
def get_music():
    return [{"id": k, "name": v["name"], "mood": v["mood"]} for k, v in MUSIC_STYLES.items()]


# ── Analytics Routes ─────────────────────────────────────────────
@app.get("/api/analytics/dashboard")
def get_dashboard_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_videos = db.query(Video).filter(Video.user_id == user.id).count()
    posted_videos = db.query(Video).filter(Video.user_id == user.id, Video.status == "posted").count()
    total_views = sum(
        v.views for v in db.query(Video).filter(Video.user_id == user.id).all()
    )
    total_likes = sum(
        v.likes for v in db.query(Video).filter(Video.user_id == user.id).all()
    )
    active_series = db.query(Series).filter(Series.user_id == user.id, Series.is_active == True).count()

    return {
        "total_videos": total_videos,
        "posted_videos": posted_videos,
        "total_views": total_views,
        "total_likes": total_likes,
        "active_series": active_series,
        "videos_remaining": user.videos_remaining,
        "plan": user.plan,
    }


@app.get("/api/analytics/trending")
async def get_trending():
    try:
        from agent.trending import get_trending_report
        report = get_trending_report()
        return report
    except Exception as e:
        return {"error": str(e), "trending_videos": [], "ai_analysis": {}}


# ── WebSocket for Real-time Progress ─────────────────────────────
@app.websocket("/ws/progress/{video_id}")
async def websocket_progress(websocket: WebSocket, video_id: str):
    await websocket.accept()
    active_connections[video_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.pop(video_id, None)


async def notify_progress(video_id: str, progress: int, step: str, status: str = "generating"):
    ws = active_connections.get(video_id)
    if ws:
        try:
            await ws.send_json({"progress": progress, "step": step, "status": status})
        except Exception:
            active_connections.pop(video_id, None)


# ── Video Generation Pipeline ────────────────────────────────────
async def _generate_video_pipeline(video_id: str, req: VideoCreate, user_id: str):
    """Background task: full video generation pipeline."""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        # Step 1: Generate script with Gemini
        await notify_progress(video_id, 10, "Generating script with AI...", "generating")
        video.generation_progress = 10
        video.generation_step = "Generating script..."
        db.commit()

        from agent.script_generator import generate_script
        from agent.styles import get_niche

        niche = get_niche(req.niche)
        topic = req.topic or "auto-generate based on trending content"

        script = generate_script(
            topic=topic,
            category=niche["categories"][0] if niche["categories"] else "General",
            duration_target=req.duration_target,
        )

        video.title = script.get("title", "Untitled")
        video.description = script.get("description", "")
        video.script = script
        video.tags = script.get("tags", [])
        video.generation_progress = 30
        video.generation_step = "Script ready. Generating audio..."
        db.commit()
        await notify_progress(video_id, 30, "Script ready. Generating audio...")

        # Step 2: Generate audio
        from agent.audio_generator import run_generate_full_audio

        day_num = hash(video_id) % 9999
        audio_path = run_generate_full_audio(script, day_num)
        video.audio_path = str(audio_path)
        video.generation_progress = 55
        video.generation_step = "Audio ready. Creating visuals..."
        db.commit()
        await notify_progress(video_id, 55, "Audio ready. Creating visuals...")

        # Step 3: Create video with art style
        from agent.video_generator import create_video, create_thumbnail

        video_path = create_video(script, day_num)
        video.video_path = str(video_path)
        video.generation_progress = 85
        video.generation_step = "Video ready. Creating thumbnail..."
        db.commit()
        await notify_progress(video_id, 85, "Video ready. Creating thumbnail...")

        # Step 4: Create thumbnail
        thumb_path = create_thumbnail(script, day_num)
        video.thumbnail_path = str(thumb_path)
        video.generation_progress = 100
        video.generation_step = "Complete!"
        video.status = "ready"
        db.commit()
        await notify_progress(video_id, 100, "Complete!", "ready")

        # Decrement user quota
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.plan == "free":
            user.videos_remaining = max(0, user.videos_remaining - 1)
            db.commit()

    except Exception as e:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "failed"
            video.error_message = str(e)
            video.generation_step = f"Failed: {str(e)[:200]}"
            db.commit()
        await notify_progress(video_id, 0, f"Failed: {str(e)[:100]}", "failed")
    finally:
        db.close()


# ── Helper Functions ─────────────────────────────────────────────
def _series_to_dict(s: Series) -> dict:
    return {
        "id": s.id, "name": s.name, "niche": s.niche, "art_style": s.art_style,
        "voice": s.voice, "music_style": s.music_style, "video_format": s.video_format,
        "video_duration_target": s.video_duration_target, "posting_frequency": s.posting_frequency,
        "posting_time": s.posting_time, "posting_platforms": s.posting_platforms,
        "auto_post": s.auto_post, "is_active": s.is_active,
        "tags_default": s.tags_default, "created_at": s.created_at.isoformat(),
        "video_count": len(s.videos),
    }


def _video_to_dict(v: Video) -> dict:
    return {
        "id": v.id, "title": v.title, "description": v.description[:200] if v.description else "",
        "status": v.status, "niche": v.niche, "art_style": v.art_style,
        "video_format": v.video_format, "duration_seconds": v.duration_seconds,
        "video_path": v.video_path, "thumbnail_path": v.thumbnail_path,
        "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None,
        "posted_at": v.posted_at.isoformat() if v.posted_at else None,
        "post_results": v.post_results, "views": v.views, "likes": v.likes,
        "generation_progress": v.generation_progress, "generation_step": v.generation_step,
        "error_message": v.error_message, "created_at": v.created_at.isoformat(),
        "tags": v.tags,
    }


# ── Serve Frontend ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>Faceless Video Platform</h1><p>Frontend not found. Place index.html in /static/</p>")
