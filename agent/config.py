import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# Content
CHANNEL_NICHE = os.getenv("CHANNEL_NICHE", "kids_cartoon")
TARGET_AUDIENCE = os.getenv("TARGET_AUDIENCE", "children")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# Video format presets
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 1920))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 1080))
SHORT_WIDTH = int(os.getenv("SHORT_WIDTH", 1080))
SHORT_HEIGHT = int(os.getenv("SHORT_HEIGHT", 1920))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", 24))
VIDEO_DURATION_MIN = int(os.getenv("VIDEO_DURATION_MIN", 30))
VIDEO_DURATION_MAX = int(os.getenv("VIDEO_DURATION_MAX", 600))

VIDEO_FORMATS = {
    "long": {
        "width": VIDEO_WIDTH,
        "height": VIDEO_HEIGHT,
        "aspect_ratio": "16:9",
    },
    "short": {
        "width": SHORT_WIDTH,
        "height": SHORT_HEIGHT,
        "aspect_ratio": "9:16",
    },
}

# TTS
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AnaNeural")

# Schedule
UPLOAD_TIME = os.getenv("UPLOAD_TIME", "10:00")
UPLOAD_TIMEZONE = os.getenv("UPLOAD_TIMEZONE", "Asia/Kolkata")

# Directories
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")
SCRIPTS_DIR = BASE_DIR / os.getenv("SCRIPTS_DIR", "output/scripts")
VIDEOS_DIR = BASE_DIR / os.getenv("VIDEOS_DIR", "output/videos")
AUDIO_DIR = BASE_DIR / os.getenv("AUDIO_DIR", "output/audio")
THUMBNAILS_DIR = BASE_DIR / os.getenv("THUMBNAILS_DIR", "output/thumbnails")
ASSETS_DIR = BASE_DIR / os.getenv("ASSETS_DIR", "assets")

# Create directories
for d in [OUTPUT_DIR, SCRIPTS_DIR, VIDEOS_DIR, AUDIO_DIR, THUMBNAILS_DIR, ASSETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Kids-safe content categories
KIDS_CATEGORIES = [
    "Moral Stories",
    "Nursery Rhymes & Songs",
    "Animal Adventures",
    "Fairy Tales",
    "Fun Facts for Kids",
    "ABC & 123 Learning",
    "Superhero Stories",
    "Bedtime Stories",
    "Cartoon Comedy",
    "Space & Science for Kids",
    "Dinosaur Adventures",
    "Friendship Stories",
    "Magic & Fantasy",
    "Nature & Wildlife",
    "Holiday Specials",
]

# Color palettes for kids content
KIDS_COLOR_PALETTES = {
    "bright": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#FFD93D"],
    "pastel": ["#FFB3BA", "#BAFFC9", "#BAE1FF", "#FFFFBA", "#E8BAFF", "#FFD1BA"],
    "rainbow": ["#FF0000", "#FF7700", "#FFFF00", "#00FF00", "#0000FF", "#8B00FF"],
    "nature": ["#2D5016", "#4A7C2E", "#7CB342", "#AED581", "#DCE775", "#FFF176"],
    "ocean": ["#006994", "#0099CC", "#33CCFF", "#66E0FF", "#99EEFF", "#CCF5FF"],
}

# YouTube categories
YOUTUBE_CATEGORY_EDUCATION = "27"
YOUTUBE_CATEGORY_ENTERTAINMENT = "24"
YOUTUBE_CATEGORY_FILM = "1"

# Video templates
VIDEO_TEMPLATES = {
    "story": {
        "intro_duration": 5,
        "scene_duration": 15,
        "outro_duration": 5,
        "bg_music_volume": 0.15,
        "narration_speed": 0.9,
    },
    "learning": {
        "intro_duration": 3,
        "scene_duration": 10,
        "outro_duration": 3,
        "bg_music_volume": 0.1,
        "narration_speed": 0.85,
    },
    "rhyme": {
        "intro_duration": 3,
        "scene_duration": 8,
        "outro_duration": 3,
        "bg_music_volume": 0.25,
        "narration_speed": 1.0,
    },
    "facts": {
        "intro_duration": 4,
        "scene_duration": 12,
        "outro_duration": 4,
        "bg_music_volume": 0.12,
        "narration_speed": 0.88,
    },
}

# Video generation provider
VIDEO_GENERATION_PROVIDER = os.getenv("VIDEO_GENERATION_PROVIDER", "veo")
REPLICATE_VIDEO_MODEL = os.getenv("REPLICATE_VIDEO_MODEL", "prunaai/p-video")
REPLICATE_VIDEO_RESOLUTION = os.getenv("REPLICATE_VIDEO_RESOLUTION", "720p")
REPLICATE_VIDEO_FPS = int(os.getenv("REPLICATE_VIDEO_FPS", "24"))
REPLICATE_VIDEO_DRAFT = os.getenv("REPLICATE_VIDEO_DRAFT", "false").lower() in {"1", "true", "yes", "on"}
REPLICATE_POLL_INTERVAL = float(os.getenv("REPLICATE_POLL_INTERVAL", "5"))
REPLICATE_TIMEOUT_SECONDS = int(os.getenv("REPLICATE_TIMEOUT_SECONDS", "420"))

# Google Veo video generation
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
VEO_PERSON_GENERATION = os.getenv("VEO_PERSON_GENERATION", "allow_all")
VEO_POLL_INTERVAL = float(os.getenv("VEO_POLL_INTERVAL", "10"))
VEO_TIMEOUT_SECONDS = int(os.getenv("VEO_TIMEOUT_SECONDS", "600"))
