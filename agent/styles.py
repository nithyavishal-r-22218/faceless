"""
Art Styles & Visual Effects Engine
Multiple art styles for video generation - competing with FacelessReels.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import random
import textwrap
from pathlib import Path

from agent.config import KIDS_COLOR_PALETTES


# ── Art Style Definitions ────────────────────────────────────────
ART_STYLES = {
    "cartoon": {
        "name": "Cartoon",
        "description": "Bright, bold cartoon style with thick outlines",
        "bg_colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#FFD93D"],
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_scale": 1.0,
        "border_radius": 20,
        "effects": ["bold_outline", "sparkle"],
        "overlay_opacity": 0,
    },
    "anime": {
        "name": "Anime",
        "description": "Japanese anime-inspired visuals with vibrant colors",
        "bg_colors": ["#FF69B4", "#9370DB", "#4169E1", "#00CED1", "#FFD700", "#FF4500"],
        "text_color": "#FFFFFF",
        "stroke_color": "#1a1a2e",
        "stroke_width": 3,
        "font_scale": 0.95,
        "border_radius": 0,
        "effects": ["speed_lines", "glow"],
        "overlay_opacity": 20,
    },
    "watercolor": {
        "name": "Watercolor",
        "description": "Soft watercolor painting aesthetic",
        "bg_colors": ["#E8D5B7", "#F5E6D3", "#D4E6E1", "#E8E0F0", "#FDE8E0", "#E0F0E8"],
        "text_color": "#2C3E50",
        "stroke_color": "#7F8C8D",
        "stroke_width": 2,
        "font_scale": 0.9,
        "border_radius": 30,
        "effects": ["blur_edge", "texture"],
        "overlay_opacity": 30,
    },
    "neon": {
        "name": "Neon Glow",
        "description": "Dark background with neon glowing text and elements",
        "bg_colors": ["#0a0a0a", "#1a0a2e", "#0a1a2e", "#0a2e1a", "#2e0a1a", "#1a1a0a"],
        "text_color": "#00FF88",
        "stroke_color": "#FF00FF",
        "stroke_width": 3,
        "font_scale": 1.0,
        "border_radius": 15,
        "effects": ["neon_glow", "particles"],
        "overlay_opacity": 0,
    },
    "retro": {
        "name": "Retro Pop",
        "description": "Vintage retro-pop style with halftone effects",
        "bg_colors": ["#E74C3C", "#F39C12", "#27AE60", "#2980B9", "#8E44AD", "#D35400"],
        "text_color": "#FFF8DC",
        "stroke_color": "#2C3E50",
        "stroke_width": 5,
        "font_scale": 1.1,
        "border_radius": 0,
        "effects": ["halftone", "vintage"],
        "overlay_opacity": 15,
    },
    "minimalist": {
        "name": "Minimalist",
        "description": "Clean, modern minimalist design",
        "bg_colors": ["#FFFFFF", "#F8F9FA", "#E9ECEF", "#F0F4F8", "#FAFBFC", "#F5F5F5"],
        "text_color": "#212529",
        "stroke_color": "#ADB5BD",
        "stroke_width": 1,
        "font_scale": 0.85,
        "border_radius": 10,
        "effects": ["shadow", "line_accent"],
        "overlay_opacity": 0,
    },
    "pixel": {
        "name": "Pixel Art",
        "description": "8-bit pixel art retro gaming style",
        "bg_colors": ["#306230", "#0f380f", "#8bac0f", "#9bbc0f", "#306230", "#0f380f"],
        "text_color": "#9bbc0f",
        "stroke_color": "#0f380f",
        "stroke_width": 3,
        "font_scale": 1.0,
        "border_radius": 0,
        "effects": ["pixelate"],
        "overlay_opacity": 0,
    },
    "storybook": {
        "name": "Storybook",
        "description": "Children's storybook illustration style",
        "bg_colors": ["#FFEAA7", "#DCEDC1", "#A8E6CF", "#FFD3B6", "#FF8B94", "#C7CEEA"],
        "text_color": "#5D4037",
        "stroke_color": "#795548",
        "stroke_width": 3,
        "font_scale": 1.05,
        "border_radius": 25,
        "effects": ["paper_texture", "soft_border"],
        "overlay_opacity": 10,
    },
}

# ── Niche Definitions ────────────────────────────────────────────
NICHES = {
    "kids_cartoon": {
        "name": "Kids Cartoon",
        "description": "Fun, educational content for children",
        "default_art_style": "cartoon",
        "default_voice": "en-US-AnaNeural",
        "default_music": "upbeat",
        "categories": [
            "Moral Stories", "Nursery Rhymes", "Animal Adventures",
            "Fairy Tales", "Fun Facts", "ABC Learning", "Superhero Stories",
            "Bedtime Stories", "Cartoon Comedy", "Dinosaur Adventures",
        ],
        "prompt_prefix": "Create kid-safe, educational, fun content for children aged 3-10.",
        "made_for_kids": True,
    },
    "scary_stories": {
        "name": "Scary Stories",
        "description": "Creepy and mysterious horror stories",
        "default_art_style": "neon",
        "default_voice": "en-US-GuyNeural",
        "default_music": "dramatic",
        "categories": [
            "Urban Legends", "Ghost Stories", "Creepy History",
            "Mysterious Events", "Dark Tales", "Haunted Places",
        ],
        "prompt_prefix": "Create suspenseful, creepy storytelling content. Keep it PG-13.",
        "made_for_kids": False,
    },
    "history": {
        "name": "History",
        "description": "Fascinating historical events and figures",
        "default_art_style": "retro",
        "default_voice": "en-GB-RyanNeural",
        "default_music": "dramatic",
        "categories": [
            "Ancient Civilizations", "World Wars", "Famous Leaders",
            "Lost Empires", "Historical Mysteries", "Inventions",
        ],
        "prompt_prefix": "Create engaging, accurate historical content that educates and entertains.",
        "made_for_kids": False,
    },
    "motivation": {
        "name": "Motivation",
        "description": "Inspirational and motivational content",
        "default_art_style": "minimalist",
        "default_voice": "en-US-GuyNeural",
        "default_music": "calm",
        "categories": [
            "Success Stories", "Daily Motivation", "Life Lessons",
            "Mindset", "Productivity", "Goal Setting",
        ],
        "prompt_prefix": "Create powerful, uplifting motivational content.",
        "made_for_kids": False,
    },
    "science": {
        "name": "Science & Space",
        "description": "Mind-blowing science facts and space exploration",
        "default_art_style": "anime",
        "default_voice": "en-US-JennyNeural",
        "default_music": "upbeat",
        "categories": [
            "Space Facts", "Biology", "Physics", "Chemistry",
            "Earth Science", "Technology", "Future Tech",
        ],
        "prompt_prefix": "Create fascinating, accurate science content that makes learning fun.",
        "made_for_kids": False,
    },
    "mythology": {
        "name": "Mythology",
        "description": "Myths and legends from around the world",
        "default_art_style": "storybook",
        "default_voice": "en-GB-SoniaNeural",
        "default_music": "dramatic",
        "categories": [
            "Greek Mythology", "Norse Mythology", "Egyptian Myths",
            "Hindu Mythology", "Japanese Folklore", "Celtic Legends",
        ],
        "prompt_prefix": "Create vivid retellings of mythological stories.",
        "made_for_kids": False,
    },
    "finance": {
        "name": "Finance & Money",
        "description": "Personal finance tips and money education",
        "default_art_style": "minimalist",
        "default_voice": "en-US-GuyNeural",
        "default_music": "calm",
        "categories": [
            "Investing", "Saving Money", "Side Hustles",
            "Crypto", "Real Estate", "Financial Freedom",
        ],
        "prompt_prefix": "Create practical, actionable financial advice content.",
        "made_for_kids": False,
    },
    "animals": {
        "name": "Animals & Nature",
        "description": "Amazing animal facts and nature content",
        "default_art_style": "watercolor",
        "default_voice": "en-AU-NatashaNeural",
        "default_music": "calm",
        "categories": [
            "Wild Animals", "Ocean Life", "Birds", "Insects",
            "Endangered Species", "Animal Behavior",
        ],
        "prompt_prefix": "Create fascinating, educational content about animals and nature.",
        "made_for_kids": False,
    },
    "custom": {
        "name": "Custom Niche",
        "description": "Define your own niche and content style",
        "default_art_style": "cartoon",
        "default_voice": "en-US-JennyNeural",
        "default_music": "upbeat",
        "categories": [],
        "prompt_prefix": "",
        "made_for_kids": False,
    },
}

# ── Music Styles ─────────────────────────────────────────────────
MUSIC_STYLES = {
    "upbeat": {"name": "Upbeat & Fun", "bpm_range": (120, 140), "mood": "happy, energetic"},
    "calm": {"name": "Calm & Relaxing", "bpm_range": (60, 80), "mood": "peaceful, gentle"},
    "dramatic": {"name": "Dramatic & Epic", "bpm_range": (80, 100), "mood": "intense, cinematic"},
    "fun": {"name": "Playful & Quirky", "bpm_range": (110, 130), "mood": "silly, bouncy"},
    "mystery": {"name": "Mystery & Suspense", "bpm_range": (70, 90), "mood": "tense, eerie"},
    "none": {"name": "No Music", "bpm_range": (0, 0), "mood": "silent"},
}

# ── Available TTS Voices ─────────────────────────────────────────
TTS_VOICES = {
    "en-US-AnaNeural": {"name": "Ana", "gender": "female", "accent": "US", "age": "young", "best_for": "kids"},
    "en-US-JennyNeural": {"name": "Jenny", "gender": "female", "accent": "US", "age": "adult", "best_for": "general"},
    "en-US-GuyNeural": {"name": "Guy", "gender": "male", "accent": "US", "age": "adult", "best_for": "narration"},
    "en-GB-SoniaNeural": {"name": "Sonia", "gender": "female", "accent": "British", "age": "adult", "best_for": "stories"},
    "en-GB-RyanNeural": {"name": "Ryan", "gender": "male", "accent": "British", "age": "adult", "best_for": "documentary"},
    "en-AU-NatashaNeural": {"name": "Natasha", "gender": "female", "accent": "Australian", "age": "adult", "best_for": "fun"},
    "en-IN-NeerjaNeural": {"name": "Neerja", "gender": "female", "accent": "Indian", "age": "adult", "best_for": "educational"},
    "en-US-AriaNeural": {"name": "Aria", "gender": "female", "accent": "US", "age": "adult", "best_for": "professional"},
}


def get_art_style(style_name: str) -> dict:
    return ART_STYLES.get(style_name, ART_STYLES["cartoon"])


def get_niche(niche_name: str) -> dict:
    return NICHES.get(niche_name, NICHES["custom"])


def list_art_styles() -> list[dict]:
    return [{"id": k, **v} for k, v in ART_STYLES.items()]


def list_niches() -> list[dict]:
    return [{"id": k, **v} for k, v in NICHES.items()]


def list_voices() -> list[dict]:
    return [{"id": k, **v} for k, v in TTS_VOICES.items()]


def list_music_styles() -> list[dict]:
    return [{"id": k, **v} for k, v in MUSIC_STYLES.items()]


# ── Scene Renderer with Art Styles ───────────────────────────────
def render_scene_styled(
    width: int,
    height: int,
    text_main: str,
    text_sub: str,
    art_style: str = "cartoon",
    bg_color: str = None,
    scene_number: int = 1,
) -> Image.Image:
    """Render a scene image with the specified art style."""
    style = get_art_style(art_style)

    if bg_color is None:
        bg_color = random.choice(style["bg_colors"])

    bg_rgb = tuple(int(bg_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        title_size = int(72 * style["font_scale"])
        body_size = int(42 * style["font_scale"])
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", title_size)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", body_size)
    except (OSError, IOError):
        try:
            title_size = int(72 * style["font_scale"])
            body_size = int(42 * style["font_scale"])
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", body_size)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

    text_rgb = tuple(int(style["text_color"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    stroke_rgb = tuple(int(style["stroke_color"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Apply art style effects
    if "bold_outline" in style["effects"]:
        # Thick cartoon border
        draw.rectangle([15, 15, width-15, height-15], outline=stroke_rgb, width=6)

    if "speed_lines" in style["effects"]:
        # Anime speed lines from corners
        for i in range(0, width, 40):
            draw.line([(0, 0), (i, height)], fill=(*stroke_rgb, 30), width=1)
            draw.line([(width, 0), (width - i, height)], fill=(*stroke_rgb, 30), width=1)

    if "paper_texture" in style["effects"]:
        # Subtle paper dots
        for _ in range(200):
            x, y = random.randint(0, width), random.randint(0, height)
            r = random.randint(1, 3)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*stroke_rgb, 15))

    if "neon_glow" in style["effects"]:
        # Neon border
        for offset in range(5, 0, -1):
            alpha = 100 - offset * 15
            draw.rectangle(
                [20 - offset, 20 - offset, width - 20 + offset, height - 20 + offset],
                outline=(*text_rgb,), width=2
            )

    # Main text
    if text_main:
        max_chars = 20 if width < 1080 else 25
        wrapped = textwrap.fill(text_main, width=max_chars)
        draw.multiline_text(
            (width // 2, height // 3),
            wrapped,
            font=title_font,
            fill=text_rgb,
            anchor="mm",
            align="center",
            stroke_width=style["stroke_width"],
            stroke_fill=stroke_rgb,
        )

    # Sub text
    if text_sub:
        max_chars = 35 if width < 1080 else 45
        wrapped_sub = textwrap.fill(text_sub, width=max_chars)
        draw.multiline_text(
            (width // 2, height * 2 // 3),
            wrapped_sub,
            font=body_font,
            fill=text_rgb,
            anchor="mm",
            align="center",
            stroke_width=max(1, style["stroke_width"] - 1),
            stroke_fill=stroke_rgb,
        )

    # Post-processing effects
    if "pixelate" in style["effects"]:
        small = img.resize((width // 8, height // 8), Image.NEAREST)
        img = small.resize((width, height), Image.NEAREST)

    if "blur_edge" in style["effects"]:
        mask = Image.new("L", (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle([30, 30, width-30, height-30], fill=255)
        blurred = img.filter(ImageFilter.GaussianBlur(5))
        img = Image.composite(img, blurred, mask)

    if "vintage" in style["effects"]:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.7)

    return img
