"""
Database models for the Faceless Video Platform.
SQLAlchemy ORM models for users, series, videos, schedules, and platforms.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, default="")
    avatar_url = Column(String, default="")
    plan = Column(String, default="free")  # free, starter, pro, business
    videos_remaining = Column(Integer, default=3)  # monthly quota
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    series = relationship("Series", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    platforms = relationship("Platform", back_populates="user", cascade="all, delete-orphan")


class Series(Base):
    __tablename__ = "series"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    niche = Column(String, nullable=False)  # kids_cartoon, scary_stories, history, etc.
    description = Column(Text, default="")
    art_style = Column(String, default="cartoon")  # cartoon, anime, realistic, watercolor, 3d, pixel
    voice = Column(String, default="en-US-AnaNeural")
    music_style = Column(String, default="upbeat")  # upbeat, calm, dramatic, fun, none
    video_format = Column(String, default="short")  # short (9:16), long (16:9)
    video_duration_target = Column(Integer, default=60)  # seconds
    posting_frequency = Column(String, default="daily")  # daily, twice_daily, every_other_day, weekly
    posting_time = Column(String, default="10:00")
    posting_platforms = Column(JSON, default=list)  # ["youtube", "tiktok", "instagram"]
    is_active = Column(Boolean, default=True)
    auto_post = Column(Boolean, default=True)
    content_plan = Column(JSON, default=list)  # list of upcoming topics
    tags_default = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="series")
    videos = relationship("Video", back_populates="series", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    series_id = Column(String, ForeignKey("series.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    script = Column(JSON, default=dict)  # full script JSON
    tags = Column(JSON, default=list)
    status = Column(String, default="draft")  # draft, generating, ready, posting, posted, failed
    video_path = Column(String, default="")
    audio_path = Column(String, default="")
    thumbnail_path = Column(String, default="")
    duration_seconds = Column(Float, default=0)
    video_format = Column(String, default="short")  # short (9:16), long (16:9)
    art_style = Column(String, default="cartoon")
    niche = Column(String, default="")
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    post_results = Column(JSON, default=dict)  # {platform: {id, url, status}}
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    generation_progress = Column(Integer, default=0)  # 0-100
    generation_step = Column(String, default="")
    error_message = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="videos")
    series = relationship("Series", back_populates="videos")


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    platform_type = Column(String, nullable=False)  # youtube, tiktok, instagram
    account_name = Column(String, default="")
    is_connected = Column(Boolean, default=False)
    credentials = Column(JSON, default=dict)  # encrypted tokens
    channel_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="platforms")


class ScheduleJob(Base):
    __tablename__ = "schedule_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    series_id = Column(String, ForeignKey("series.id"), nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    platforms = Column(JSON, default=list)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
DATABASE_URL = "sqlite:///./faceless.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
