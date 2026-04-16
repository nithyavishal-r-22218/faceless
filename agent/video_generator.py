"""
Video Generator - cinematic faceless video rendering for YouTube.
Uses local scene assets when available and falls back to generated visuals.
"""
from __future__ import annotations

import math
import os
import re
import textwrap
import time
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import requests
import numpy as np

from agent.audio_generator import run_generate_audio_package
from agent.config import (
    ASSETS_DIR,
    GEMINI_API_KEY,
    REPLICATE_API_TOKEN,
    REPLICATE_POLL_INTERVAL,
    REPLICATE_TIMEOUT_SECONDS,
    REPLICATE_VIDEO_DRAFT,
    REPLICATE_VIDEO_FPS,
    REPLICATE_VIDEO_MODEL,
    REPLICATE_VIDEO_RESOLUTION,
    SHORT_HEIGHT,
    SHORT_WIDTH,
    THUMBNAILS_DIR,
    VEO_MODEL,
    VEO_PERSON_GENERATION,
    VEO_POLL_INTERVAL,
    VEO_TIMEOUT_SECONDS,
    VIDEO_FPS,
    VIDEO_FORMATS,
    VIDEO_GENERATION_PROVIDER,
    VIDEOS_DIR,
)

FOOTAGE_DIR = ASSETS_DIR / "footage"
IMAGE_DIR = ASSETS_DIR / "images"
AI_IMAGE_DIR = VIDEOS_DIR / "ai_frames"
GENERATED_VIDEO_DIR = VIDEOS_DIR / "generated_scenes"

VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
BRAND_NAME = "Faceless"
TRANSITION_DURATION = 0.35
POLLINATIONS_BASE_URL = os.getenv("POLLINATIONS_BASE_URL", "https://image.pollinations.ai/prompt")
POLLINATIONS_STYLE = os.getenv(
    "POLLINATIONS_STYLE",
    "ultra realistic cinematic still, film lighting, natural detail, depth of field, high quality",
)
REPLICATE_API_BASE = "https://api.replicate.com/v1"

THEME_PRESETS = {
    "default": {
        "primary": "#0f172a",
        "secondary": "#2563eb",
        "overlay": (7, 10, 18),
        "accent": (96, 165, 250),
        "caption_fill": (0, 0, 0, 122),
        "caption_text": (255, 255, 255, 240),
        "intro_tag": "Cinematic faceless video",
        "outro_headline": "Thanks for watching",
        "outro_subline": "Subscribe for more faceless videos",
    },
    "story": {
        "primary": "#1e293b",
        "secondary": "#7c3aed",
        "overlay": (11, 15, 31),
        "accent": (196, 181, 253),
        "caption_fill": (8, 10, 20, 128),
        "caption_text": (250, 250, 255, 240),
        "intro_tag": "Story-driven faceless video",
        "outro_headline": "Thanks for joining the story",
        "outro_subline": "Come back for the next chapter",
    },
    "motivation": {
        "primary": "#111827",
        "secondary": "#ea580c",
        "overlay": (10, 10, 12),
        "accent": (251, 191, 36),
        "caption_fill": (12, 10, 8, 126),
        "caption_text": (255, 250, 245, 240),
        "intro_tag": "High-impact motivational video",
        "outro_headline": "Keep moving forward",
        "outro_subline": "Subscribe for more daily momentum",
    },
    "history": {
        "primary": "#1f2937",
        "secondary": "#92400e",
        "overlay": (18, 15, 10),
        "accent": (245, 158, 11),
        "caption_fill": (16, 12, 8, 132),
        "caption_text": (255, 248, 240, 240),
        "intro_tag": "Historical faceless documentary",
        "outro_headline": "History never really stops",
        "outro_subline": "Subscribe for more untold stories",
    },
    "facts": {
        "primary": "#082f49",
        "secondary": "#0f766e",
        "overlay": (4, 16, 22),
        "accent": (45, 212, 191),
        "caption_fill": (4, 18, 20, 128),
        "caption_text": (240, 253, 250, 240),
        "intro_tag": "Fast, clean facts video",
        "outro_headline": "More facts coming soon",
        "outro_subline": "Subscribe for your next quick insight",
    },
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_video_dimensions(video_format: str = "long") -> tuple[int, int]:
    """Resolve the output dimensions for a video format."""
    preset = VIDEO_FORMATS.get(video_format, VIDEO_FORMATS["long"])
    return preset["width"], preset["height"]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _load_font(size: int, bold: bool = False):
    system_fonts = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for font_path in system_fonts:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _find_matching_asset(scene: dict, day_number: int, directories: list[Path], extensions: tuple[str, ...]) -> Path | None:
    scene_num = scene.get("scene_number", 0)
    names = [
        f"scene_{scene_num:02d}",
        _slugify(scene.get("text_overlay", "")),
        _slugify(scene.get("visual_description", ""))[:48],
    ]
    day_folders = [f"day_{day_number:02d}", f"day_{day_number}"]

    for directory in directories:
        search_roots = [directory, *[directory / folder for folder in day_folders]]
        for root in search_roots:
            if not root.exists():
                continue
            for name in names:
                if not name:
                    continue
                for ext in extensions:
                    candidate = root / f"{name}{ext}"
                    if candidate.exists():
                        return candidate
            fallback = next((p for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in extensions and p.stem.startswith(f"scene_{scene_num:02d}")), None)
            if fallback:
                return fallback
    return None


def _create_brand_badge(width: int) -> Image.Image:
    badge = Image.new("RGBA", (260 if width > 1200 else 220, 56), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle([0, 0, badge.width, badge.height], radius=18, fill=(7, 11, 20, 136))
    draw.rounded_rectangle([10, 10, 46, 46], radius=12, fill=(255, 255, 255, 42))
    font = _load_font(24, bold=True)
    draw.text((60, 15), BRAND_NAME, font=font, fill=(255, 255, 255, 218))
    return badge


def _clean_copy(text: str, limit: int) -> str:
    text = " ".join((text or "").replace("\n", " ").split())
    return text[:limit].rstrip()


def _aspect_ratio_for_format(video_format: str) -> str:
    return "9:16" if video_format == "short" else "16:9"


def _download_binary(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=180, stream=True)
    response.raise_for_status()
    with open(destination, "wb") as fh:
        for chunk in response.iter_content(8192):
            if chunk:
                fh.write(chunk)
    return destination


def _extract_replicate_output_url(output) -> str | None:
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str):
                return item
            if isinstance(item, dict):
                for key in ("url", "output", "video"):
                    value = item.get(key)
                    if isinstance(value, str):
                        return value
    if isinstance(output, dict):
        for key in ("url", "output", "video"):
            value = output.get(key)
            if isinstance(value, str):
                return value
    return None


def _wait_for_replicate_prediction(prediction: dict) -> dict:
    get_url = prediction.get("urls", {}).get("get") or f"{REPLICATE_API_BASE}/predictions/{prediction['id']}"
    headers = {"Authorization": f"Bearer {REPLICATE_API_TOKEN}"}
    deadline = time.time() + REPLICATE_TIMEOUT_SECONDS

    while time.time() < deadline:
        status = prediction.get("status")
        if status == "succeeded":
            return prediction
        if status in {"failed", "canceled"}:
            error = prediction.get("error") or f"Replicate prediction {status}"
            raise RuntimeError(error)
        time.sleep(REPLICATE_POLL_INTERVAL)
        response = requests.get(get_url, headers=headers, timeout=60)
        response.raise_for_status()
        prediction = response.json()

    raise TimeoutError(f"Replicate prediction timed out after {REPLICATE_TIMEOUT_SECONDS}s")


def _generate_replicate_scene_video(
    scene: dict,
    script: dict,
    day_number: int,
    video_format: str,
    duration: float,
    theme: dict,
) -> Path | None:
    if VIDEO_GENERATION_PROVIDER != "replicate" or not REPLICATE_API_TOKEN:
        return None

    model = REPLICATE_VIDEO_MODEL
    if "/" not in model:
        raise ValueError("REPLICATE_VIDEO_MODEL must be in the form 'owner/model'")
    owner, model_name = model.split("/", 1)

    scene_num = scene.get("scene_number", 0)
    output_path = GENERATED_VIDEO_DIR / f"day_{day_number:02d}_scene_{scene_num:02d}.mp4"
    if output_path.exists():
        return output_path

    prompt = _build_ai_prompt(scene, script, theme)
    payload = {
        "input": {
            "prompt": prompt,
            "duration": max(1, min(int(round(duration)), 10)),
            "aspect_ratio": _aspect_ratio_for_format(video_format),
            "resolution": REPLICATE_VIDEO_RESOLUTION,
            "fps": REPLICATE_VIDEO_FPS,
            "draft": REPLICATE_VIDEO_DRAFT,
            "prompt_upsampling": True,
            "seed": max(day_number * 100 + scene_num, 1),
        }
    }
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        print(f"    🎬 Generating video scene {scene_num} via Replicate...")
        response = requests.post(
            f"{REPLICATE_API_BASE}/models/{owner}/{model_name}/predictions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        prediction = _wait_for_replicate_prediction(response.json())
        output_url = _extract_replicate_output_url(prediction.get("output"))
        if not output_url:
            raise RuntimeError("Replicate prediction did not return a downloadable output URL")
        return _download_binary(output_url, output_path)
    except Exception as exc:
        print(f"    ⚠ Replicate video generation failed for scene {scene_num}: {exc}")
        return None


def _generate_veo_scene_video(
    scene: dict,
    script: dict,
    day_number: int,
    video_format: str,
    duration: float,
    theme: dict,
) -> Path | None:
    if VIDEO_GENERATION_PROVIDER != "veo" or not GEMINI_API_KEY:
        return None

    from google import genai
    from google.genai import types

    scene_num = scene.get("scene_number", 0)
    GENERATED_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = GENERATED_VIDEO_DIR / f"day_{day_number:02d}_scene_{scene_num:02d}.mp4"
    if output_path.exists():
        return output_path

    prompt = _build_ai_prompt(scene, script, theme)
    aspect_ratio = _aspect_ratio_for_format(video_format)

    try:
        print(f"    🎬 Generating video scene {scene_num} via Veo 3.1...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        operation = client.models.generate_videos(
            model=VEO_MODEL,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                person_generation=VEO_PERSON_GENERATION,
                aspect_ratio=aspect_ratio,
            ),
        )

        deadline = time.time() + VEO_TIMEOUT_SECONDS
        while not operation.done:
            if time.time() > deadline:
                raise TimeoutError(f"Veo video generation timed out after {VEO_TIMEOUT_SECONDS}s")
            time.sleep(VEO_POLL_INTERVAL)
            operation = client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            raise RuntimeError("Veo did not return any generated videos")

        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save(str(output_path))
        print(f"    ✅ Veo scene {scene_num} saved to {output_path}")
        return output_path
    except Exception as exc:
        print(f"    ⚠ Veo video generation failed for scene {scene_num}: {exc}")
        return None


def _build_ai_prompt(scene: dict, script: dict, theme: dict) -> str:
    visual = _clean_copy(scene.get("visual_description", ""), 220)
    narration = _clean_copy(scene.get("narration", ""), 160)
    characters = ", ".join(scene.get("characters", [])[:4])
    niche = _clean_copy(script.get("niche", ""), 60)
    title = _clean_copy(script.get("title", ""), 80)
    tone = _clean_copy(scene.get("tone", ""), 40)

    parts = [part for part in [visual, narration, characters, niche, title, tone] if part]
    prompt_core = ". ".join(parts) if parts else "cinematic scene for a faceless YouTube video"
    return f"{prompt_core}. {POLLINATIONS_STYLE}. mood colors inspired by {theme['primary']} and {theme['secondary']}"


def _generate_ai_scene_image(scene: dict, script: dict, day_number: int, video_format: str, theme: dict) -> Path | None:
    width, height = get_video_dimensions(video_format)
    scene_num = scene.get("scene_number", 0)
    prompt = _build_ai_prompt(scene, script, theme)
    safe_prompt = requests.utils.quote(prompt)
    seed = max(day_number * 100 + scene_num, 1)
    url = f"{POLLINATIONS_BASE_URL}/{safe_prompt}?width={width}&height={height}&seed={seed}&nologo=true"

    AI_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AI_IMAGE_DIR / f"day_{day_number:02d}_scene_{scene_num:02d}.jpg"
    if output_path.exists():
        return output_path

    try:
        print(f"    🎨 Generating AI scene {scene_num}...")
        response = requests.get(url, timeout=90, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return output_path
    except Exception as exc:
        print(f"    ⚠ AI image generation failed for scene {scene_num}: {exc}")
        return None


def _get_theme(script: dict) -> dict:
    niche = _slugify(script.get("niche", ""))
    category = _slugify(script.get("category", ""))
    title = _slugify(script.get("title", ""))

    if any(token in niche or token in category or token in title for token in ("motivation", "success", "mindset")):
        return THEME_PRESETS["motivation"]
    if any(token in niche or token in category or token in title for token in ("history", "myth", "legend", "documentary")):
        return THEME_PRESETS["history"]
    if any(token in niche or token in category or token in title for token in ("fact", "science", "space", "animal")):
        return THEME_PRESETS["facts"]
    if any(token in niche or token in category or token in title for token in ("story", "bedtime", "fairy", "adventure")):
        return THEME_PRESETS["story"]
    return THEME_PRESETS["default"]


def _create_gradient_background(width: int, height: int, primary: str, secondary: str) -> Image.Image:
    img = Image.new("RGB", (width, height), hex_to_rgb(primary))
    px = img.load()
    r1, g1, b1 = hex_to_rgb(primary)
    r2, g2, b2 = hex_to_rgb(secondary)
    for y in range(height):
        y_ratio = y / max(height - 1, 1)
        for x in range(width):
            x_ratio = x / max(width - 1, 1)
            blend = min(1.0, 0.15 + (0.85 * (0.6 * y_ratio + 0.4 * x_ratio)))
            px[x, y] = (
                int(r1 + (r2 - r1) * blend),
                int(g1 + (g2 - g1) * blend),
                int(b1 + (b2 - b1) * blend),
            )
    return img


def _split_caption_chunks(text: str, max_words: int = 3) -> list[str]:
    words = [w for w in text.split() if w]
    if not words:
        return []
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def _apply_ken_burns(img_path: Path, duration: float, width: int, height: int, scene_num: int):
    image = Image.open(img_path).convert("RGB")
    source_width, source_height = image.size

    scale = max(width / source_width, height / source_height)
    base_width = max(int(source_width * scale * 1.08), width + 2)
    base_height = max(int(source_height * scale * 1.08), height + 2)
    prepared = image.resize((base_width, base_height), Image.LANCZOS)
    image_array = np.array(prepared)

    pan_direction = -1 if scene_num % 2 == 0 else 1
    zoom_start = 1.0
    zoom_end = 1.09 if width > height else 1.13
    pan_limit_x = max(base_width - width, 1)
    pan_limit_y = max(base_height - height, 1)

    def make_frame(t: float):
        progress = 0 if duration <= 0 else min(max(t / duration, 0), 1)
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        current_width = max(int(base_width * zoom), width + 2)
        current_height = max(int(base_height * zoom), height + 2)
        frame = np.array(Image.fromarray(image_array).resize((current_width, current_height), Image.LANCZOS))

        x_travel = max(current_width - width, 1)
        y_travel = max(current_height - height, 1)
        x_offset = int((0.5 + 0.25 * pan_direction * progress) * x_travel)
        y_offset = int((0.45 + 0.1 * ((scene_num % 3) - 1) * progress) * y_travel)
        x_offset = max(0, min(x_offset, x_travel))
        y_offset = max(0, min(y_offset, y_travel))
        return frame[y_offset:y_offset + height, x_offset:x_offset + width]

    return VideoClip(make_frame, duration=duration).with_fps(VIDEO_FPS)


def create_scene_image(
    scene: dict,
    day_number: int,
    video_format: str = "long",
    theme: dict | None = None,
) -> Path:
    """Create a cinematic fallback scene frame."""
    width, height = get_video_dimensions(video_format)
    scene_num = scene.get("scene_number", 0)
    theme = theme or THEME_PRESETS["default"]
    primary = scene.get("background_color", theme["primary"])
    secondary = scene.get("accent_color", theme["secondary"])
    text_overlay = _clean_copy(scene.get("text_overlay") or scene.get("title") or "", 90)
    visual_desc = _clean_copy(scene.get("visual_description", ""), 180)
    narration = _clean_copy(scene.get("narration", ""), 180)

    image = _create_gradient_background(width, height, primary, secondary).convert("RGBA")
    draw = ImageDraw.Draw(image)

    overlay = Image.new("RGBA", (width, height), (5, 10, 20, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse([-width * 0.1, -height * 0.2, width * 0.65, height * 0.75], fill=(255, 255, 255, 22))
    overlay_draw.ellipse([width * 0.45, height * 0.15, width * 1.1, height * 1.05], fill=(0, 0, 0, 60))
    overlay = overlay.filter(ImageFilter.GaussianBlur(28))
    image = Image.alpha_composite(image, overlay)

    title_font = _load_font(82 if video_format == "long" else 72, bold=True)
    body_font = _load_font(34 if video_format == "long" else 38)
    small_font = _load_font(24)

    draw.rounded_rectangle([42, 42, width - 42, height - 42], radius=32, outline=(255, 255, 255, 44), width=1)

    wrapped_title = textwrap.fill(text_overlay or "Visual Storytelling", width=18 if video_format == "short" else 20)
    title_position = (width * 0.08, height * 0.15)
    draw.multiline_text(
        title_position,
        wrapped_title,
        font=title_font,
        fill=(255, 255, 255, 240),
        spacing=10,
        stroke_width=2,
        stroke_fill=(8, 15, 28, 220),
    )

    details = visual_desc or narration
    details = textwrap.fill(details[:180], width=24 if video_format == "short" else 44)
    details_box = [int(width * 0.08), int(height * 0.66), int(width * 0.84), int(height * 0.84)]
    draw.rounded_rectangle(details_box, radius=24, fill=(10, 15, 28, 124))
    draw.multiline_text(
        (details_box[0] + 30, details_box[1] + 24),
        details,
        font=body_font,
        fill=(236, 241, 248, 224),
        spacing=8,
    )

    accent = theme["accent"]
    draw.line(
        [(int(width * 0.08), int(height * 0.13)), (int(width * 0.24), int(height * 0.13))],
        fill=accent,
        width=5,
    )

    badge = _create_brand_badge(width)
    image.alpha_composite(badge, dest=(width - badge.width - 42, 42))

    scene_dir = VIDEOS_DIR / f"day_{day_number:02d}" / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    output_path = scene_dir / f"scene_{scene_num:02d}_fallback.png"
    image.convert("RGB").save(str(output_path), quality=95)
    return output_path


def _create_caption_image(text: str, width: int, height: int, video_format: str, theme: dict) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    panel_height = int(height * (0.145 if video_format == "short" else 0.12))
    panel_top = height - panel_height - 26
    panel_width = int(width * 0.78) if video_format == "long" else width - 44
    panel = [22, panel_top, panel_width, height - 18]
    draw.rounded_rectangle(panel, radius=24, fill=theme["caption_fill"])

    font = _load_font(38 if video_format == "short" else 30, bold=True)
    wrapped = textwrap.fill(_clean_copy(text, 72), width=18 if video_format == "short" else 28)
    draw.multiline_text(
        (panel[0] + 24, panel[1] + 18),
        wrapped,
        font=font,
        fill=theme["caption_text"],
        spacing=6,
        stroke_width=0,
        stroke_fill=(0, 0, 0, 200),
    )
    accent = theme["accent"]
    draw.rounded_rectangle([panel[0], panel[1] - 10, panel[0] + 120, panel[1] - 2], radius=4, fill=accent)
    return canvas


def _create_scene_overlay_path(text: str, scene_num: int, day_number: int, video_format: str, theme: dict, idx: int = 0) -> Path:
    width, height = get_video_dimensions(video_format)
    overlay = _create_caption_image(text, width, height, video_format, theme)
    overlay_dir = VIDEOS_DIR / f"day_{day_number:02d}" / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    path = overlay_dir / f"scene_{scene_num:02d}_caption_{idx:02d}.png"
    overlay.save(str(path))
    return path


def _build_timed_caption_clips(scene: dict, day_number: int, video_format: str, duration: float, theme: dict) -> list[ImageClip]:
    narration = _clean_copy(scene.get("narration") or scene.get("caption") or scene.get("text_overlay") or "", 180)
    if not narration:
        narration = _clean_copy(scene.get("visual_description", ""), 120)
    chunks = _split_caption_chunks(narration, max_words=2 if video_format == "short" else 3)
    if not chunks:
        return []

    total_chars = sum(max(len(chunk), 1) for chunk in chunks)
    elapsed = 0.0
    clips: list[ImageClip] = []
    for idx, chunk in enumerate(chunks):
        share = max(len(chunk), 1) / max(total_chars, 1)
        chunk_duration = max(duration * share, 0.45)
        if idx == len(chunks) - 1:
            chunk_duration = max(duration - elapsed, 0.4)
        elif elapsed + chunk_duration > duration:
            chunk_duration = max(duration - elapsed, 0.4)
        path = _create_scene_overlay_path(chunk, scene.get("scene_number", 0), day_number, video_format, theme, idx=idx)
        clip = ImageClip(str(path)).with_start(elapsed).with_duration(chunk_duration)
        clips.append(clip)
        elapsed += chunk_duration
        if elapsed >= duration:
            break
    return clips


def _prepare_video_asset_clip(path: Path, duration: float, width: int, height: int):
    clip = VideoFileClip(str(path))
    if clip.duration > duration:
        clip = clip.subclipped(0, duration)
    elif clip.duration < duration and clip.duration > 0:
        loops = math.ceil(duration / clip.duration)
        clip = concatenate_videoclips([clip] * loops, method="compose").subclipped(0, duration)
    return clip.resized((width, height)).with_duration(duration)


def _prepare_image_asset_clip(path: Path, duration: float, width: int, height: int):
    return ImageClip(str(path)).resized((width, height)).with_duration(duration)


def create_scene_clip(
    scene: dict,
    script: dict,
    day_number: int,
    video_format: str = "long",
    audio_duration: float | None = None,
    theme: dict | None = None,
) -> CompositeVideoClip:
    """Create a cinematic scene clip from local footage, programmatic video, or generated imagery."""
    width, height = get_video_dimensions(video_format)
    duration = max(audio_duration or scene.get("duration_seconds", 6), 1.0)
    theme = theme or THEME_PRESETS["default"]

    footage_asset = _find_matching_asset(scene, day_number, [FOOTAGE_DIR], VIDEO_EXTENSIONS)
    image_asset = _find_matching_asset(scene, day_number, [IMAGE_DIR], IMAGE_EXTENSIONS)

    generated_video_asset = None
    if VIDEO_GENERATION_PROVIDER == "veo":
        generated_video_asset = _generate_veo_scene_video(scene, script, day_number, video_format, duration, theme)
    elif VIDEO_GENERATION_PROVIDER == "replicate":
        generated_video_asset = _generate_replicate_scene_video(scene, script, day_number, video_format, duration, theme)

    if footage_asset:
        base_clip = _prepare_video_asset_clip(footage_asset, duration, width, height)
    elif generated_video_asset:
        base_clip = _prepare_video_asset_clip(generated_video_asset, duration, width, height)
    else:
        ai_image_path = image_asset or _generate_ai_scene_image(scene, script, day_number, video_format, theme)
        image_path = ai_image_path or create_scene_image(scene, day_number, video_format=video_format, theme=theme)
        base_clip = _apply_ken_burns(image_path, duration, width, height, scene.get("scene_number", 0))

    tint = ColorClip(size=(width, height), color=theme["overlay"]).with_opacity(0.10).with_duration(duration)
    vignette = ColorClip(size=(width, height), color=(0, 0, 0)).with_opacity(0.04).with_duration(duration)
    caption_clips = _build_timed_caption_clips(scene, day_number, video_format, duration, theme)

    return CompositeVideoClip(
        [base_clip, tint, vignette, *caption_clips],
        size=(width, height),
    ).with_duration(duration)


def create_intro_clip(title: str, duration: float = 2.8, video_format: str = "long", theme: dict | None = None) -> CompositeVideoClip:
    """Create a cleaner YouTube-style intro clip."""
    width, height = get_video_dimensions(video_format)
    theme = theme or THEME_PRESETS["default"]
    intro_image = _create_gradient_background(width, height, theme["primary"], theme["secondary"]).convert("RGBA")
    draw = ImageDraw.Draw(intro_image)

    title_font = _load_font(82 if video_format == "long" else 72, bold=True)
    subtitle_font = _load_font(28, bold=False)
    wrapped_title = textwrap.fill(_clean_copy(title, 90), width=16 if video_format == "short" else 22)
    draw.multiline_text((width * 0.08, height * 0.26), wrapped_title, font=title_font, fill=(255, 255, 255), spacing=8)
    draw.text((width * 0.08, height * 0.72), theme["intro_tag"], font=subtitle_font, fill=theme["accent"])
    draw.line([(int(width * 0.08), int(height * 0.18)), (int(width * 0.24), int(height * 0.18))], fill=theme["accent"], width=5)

    badge = _create_brand_badge(width)
    intro_image.alpha_composite(badge, dest=(int(width * 0.08), int(height * 0.08)))

    intro_path = VIDEOS_DIR / "intro_frame.png"
    intro_image.convert("RGB").save(str(intro_path), quality=95)
    return ImageClip(str(intro_path)).with_duration(duration)


def create_outro_clip(duration: float = 2.5, video_format: str = "long", theme: dict | None = None) -> CompositeVideoClip:
    """Create a compact CTA outro clip."""
    width, height = get_video_dimensions(video_format)
    theme = theme or THEME_PRESETS["default"]
    outro_image = _create_gradient_background(width, height, theme["primary"], theme["secondary"]).convert("RGBA")
    draw = ImageDraw.Draw(outro_image)

    title_font = _load_font(64 if video_format == "long" else 56, bold=True)
    body_font = _load_font(28, bold=False)
    draw.multiline_text((width * 0.09, height * 0.3), theme["outro_headline"], font=title_font, fill=(255, 255, 255), spacing=8)
    draw.text((width * 0.09, height * 0.58), theme["outro_subline"], font=body_font, fill=(226, 232, 240))
    draw.line([(int(width * 0.09), int(height * 0.22)), (int(width * 0.23), int(height * 0.22))], fill=theme["accent"], width=5)

    outro_path = VIDEOS_DIR / "outro_frame.png"
    outro_image.convert("RGB").save(str(outro_path), quality=95)
    return ImageClip(str(outro_path)).with_duration(duration)


def create_video(script: dict, day_number: int, video_format: str = "long") -> Path:
    """Create a YouTube-ready faceless video with narration, music, and scene timing sync."""
    title = script.get("title", f"Day {day_number} Video")
    scenes = script.get("scenes", [])
    voice = script.get("voice")
    music_style = script.get("music_style") or "ambient"
    theme = _get_theme(script)

    print(f"🎬 Creating video: {title}")
    print("  📢 Generating mastered audio...")
    audio_package = run_generate_audio_package(script, day_number, voice=voice, music_style=music_style)
    master_audio_path = audio_package["master_path"]
    scene_audio = audio_package["scene_audio"]

    scene_timing = {entry["scene_number"]: entry for entry in scene_audio}
    print("  🖼️ Building cinematic scenes...")

    clips = [create_intro_clip(title, video_format=video_format, theme=theme)]
    for scene in scenes:
        timing = scene_timing.get(scene.get("scene_number"))
        duration = (timing["duration_ms"] / 1000.0) if timing else scene.get("duration_seconds", 6)
        clips.append(create_scene_clip(scene, script, day_number, video_format=video_format, audio_duration=duration, theme=theme))
    clips.append(create_outro_clip(video_format=video_format, theme=theme))

    print("  🔗 Compositing master timeline...")
    final_video = concatenate_videoclips(clips, method="compose", padding=-TRANSITION_DURATION)
    audio_clip = AudioFileClip(str(master_audio_path))
    target_duration = min(final_video.duration, audio_clip.duration)
    final_video = final_video.subclipped(0, target_duration)
    final_video = final_video.with_audio(audio_clip.with_duration(target_duration))

    output_path = VIDEOS_DIR / f"day_{day_number:02d}_{_sanitize(title)}.mp4"
    print(f"  💾 Exporting to {output_path}...")
    final_video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        bitrate="6000k",
    )

    final_video.close()
    audio_clip.close()
    for clip in clips:
        clip.close()

    print(f"  ✅ Video created: {output_path}")
    return output_path


def create_thumbnail(script: dict, day_number: int) -> Path:
    """Create a YouTube thumbnail."""
    return create_thumbnail_for_format(script, day_number, video_format="long")


def create_thumbnail_for_format(script: dict, day_number: int, video_format: str = "long") -> Path:
    """Create a thumbnail or vertical cover image using local assets when available."""
    title = script.get("title", "Video")
    thumb_text = script.get("thumbnail_text", title[:42])
    scene = (script.get("scenes") or [{}])[0]
    theme = _get_theme(script)

    if video_format == "short":
        width, height = SHORT_WIDTH, SHORT_HEIGHT
        wrap = 14
    else:
        width, height = 1280, 720
        wrap = 18

    image_asset = _find_matching_asset(scene, day_number, [IMAGE_DIR], IMAGE_EXTENSIONS)
    if image_asset:
        base = Image.open(image_asset).convert("RGBA").resize((width, height))
    else:
        ai_image_path = _generate_ai_scene_image(scene, script, day_number, video_format, theme)
        if ai_image_path:
            base = Image.open(ai_image_path).convert("RGBA").resize((width, height))
        else:
            primary = scene.get("background_color", theme["primary"])
            secondary = scene.get("accent_color", theme["secondary"])
            base = _create_gradient_background(width, height, primary, secondary).convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (4, 8, 18, 110))
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)

    title_font = _load_font(86 if video_format == "long" else 82, bold=True)
    wrapped = textwrap.fill(_clean_copy(thumb_text, 60), width=wrap)

    draw.rounded_rectangle([34, 34, width - 34, height - 34], radius=26, outline=(255, 255, 255, 180), width=3)
    text_panel = [44, int(height * 0.56), int(width * 0.86), height - 46]
    draw.rounded_rectangle(text_panel, radius=24, fill=(0, 0, 0, 136))
    draw.multiline_text((text_panel[0] + 24, text_panel[1] + 22), wrapped, font=title_font, fill=(255, 255, 255), spacing=8)
    draw.line([(text_panel[0] + 24, text_panel[1] - 12), (text_panel[0] + 156, text_panel[1] - 12)], fill=theme["accent"], width=5)

    brand = _create_brand_badge(width)
    base.alpha_composite(brand, dest=(width - brand.width - 34, 34))

    suffix = "_short" if video_format == "short" else ""
    output_path = THUMBNAILS_DIR / f"day_{day_number:02d}_thumb{suffix}.png"
    base.convert("RGB").save(str(output_path), quality=95)
    print(f"  🖼️ Thumbnail: {output_path}")
    return output_path


def _sanitize(text: str) -> str:
    """Sanitize text for use in filenames."""
    return "".join(c if c.isalnum() or c in " -_" else "" for c in text)[:50].strip().replace(" ", "_")
