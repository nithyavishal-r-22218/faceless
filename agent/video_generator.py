"""
Video Generator - Creates faceless videos from scripts with visuals and audio.
Uses MoviePy + Pillow for video compositing.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont

from agent.audio_generator import get_audio_duration, run_generate_full_audio
from agent.config import (
    ASSETS_DIR,
    KIDS_COLOR_PALETTES,
    THUMBNAILS_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_TEMPLATES,
    VIDEO_WIDTH,
    VIDEOS_DIR,
)


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def create_scene_image(
    visual_desc: str,
    text_overlay: str,
    bg_color: str,
    scene_num: int,
    day_number: int,
    characters: list = None,
) -> Path:
    """Create a scene image with text and colored background."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    # Draw decorative border
    border_color = "#FFFFFF"
    draw.rectangle(
        [20, 20, VIDEO_WIDTH - 20, VIDEO_HEIGHT - 20],
        outline=hex_to_rgb(border_color),
        width=4,
    )

    # Draw rounded inner frame
    draw.rectangle(
        [60, 60, VIDEO_WIDTH - 60, VIDEO_HEIGHT - 60],
        outline=hex_to_rgb("#FFFFFF80"),
        width=2,
    )

    # Add cute decorative circles in corners
    circle_colors = KIDS_COLOR_PALETTES["bright"]
    for i, (cx, cy) in enumerate([(100, 100), (VIDEO_WIDTH - 100, 100),
                                    (100, VIDEO_HEIGHT - 100), (VIDEO_WIDTH - 100, VIDEO_HEIGHT - 100)]):
        c = hex_to_rgb(circle_colors[i % len(circle_colors)])
        draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=c)

    # Add text overlay (main title text on screen)
    if text_overlay:
        wrapped = textwrap.fill(text_overlay, width=30)
        draw.multiline_text(
            (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 3),
            wrapped,
            font=title_font,
            fill=(255, 255, 255),
            anchor="mm",
            align="center",
            stroke_width=3,
            stroke_fill=(0, 0, 0),
        )

    # Add visual description as smaller text
    if visual_desc:
        short_desc = visual_desc[:120] + "..." if len(visual_desc) > 120 else visual_desc
        wrapped_desc = textwrap.fill(short_desc, width=50)
        draw.multiline_text(
            (VIDEO_WIDTH // 2, VIDEO_HEIGHT * 2 // 3),
            wrapped_desc,
            font=body_font,
            fill=(255, 255, 255),
            anchor="mm",
            align="center",
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )

    # Add character names if provided
    if characters:
        char_text = " | ".join(characters[:4])
        draw.text(
            (VIDEO_WIDTH // 2, VIDEO_HEIGHT - 80),
            f"🌟 {char_text} 🌟",
            font=small_font,
            fill=(255, 255, 200),
            anchor="mm",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )

    # Save
    scene_dir = VIDEOS_DIR / f"day_{day_number:02d}" / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    img_path = scene_dir / f"scene_{scene_num:02d}.png"
    img.save(str(img_path))
    return img_path


def create_scene_clip(
    scene: dict, day_number: int, audio_duration: float = None
) -> CompositeVideoClip:
    """Create a video clip for a single scene."""
    scene_num = scene["scene_number"]
    visual_desc = scene.get("visual_description", "")
    text_overlay = scene.get("text_overlay", "")
    bg_color = scene.get("background_color", "#4ECDC4")
    characters = scene.get("characters", [])
    duration = audio_duration or scene.get("duration_seconds", 10)

    # Generate scene image
    img_path = create_scene_image(
        visual_desc, text_overlay, bg_color, scene_num, day_number, characters
    )

    # Create image clip
    img_clip = ImageClip(str(img_path)).set_duration(duration)

    return img_clip


def create_intro_clip(title: str, duration: float = 5) -> CompositeVideoClip:
    """Create an intro clip with channel branding."""
    bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=hex_to_rgb("#FF6B6B"))
    bg = bg.set_duration(duration)

    # Create intro image
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), hex_to_rgb("#FF6B6B"))
    draw = ImageDraw.Draw(img)

    try:
        big_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
        sub_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except (OSError, IOError):
        try:
            big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except (OSError, IOError):
            big_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

    # Stars decoration
    for i, (x, y) in enumerate([(200, 200), (1700, 200), (960, 150), (300, 800), (1600, 800)]):
        draw.text((x, y), "⭐", font=big_font, fill=(255, 255, 200))

    wrapped_title = textwrap.fill(title, width=25)
    draw.multiline_text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2 - 50),
        wrapped_title,
        font=big_font,
        fill=(255, 255, 255),
        anchor="mm",
        align="center",
        stroke_width=4,
        stroke_fill=(0, 0, 0),
    )

    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2 + 120),
        "🎬 Kids Cartoon World 🎬",
        font=sub_font,
        fill=(255, 255, 200),
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )

    intro_path = VIDEOS_DIR / "intro_frame.png"
    img.save(str(intro_path))

    intro_clip = ImageClip(str(intro_path)).set_duration(duration)
    return intro_clip


def create_outro_clip(duration: float = 5) -> CompositeVideoClip:
    """Create an outro clip with subscribe CTA."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), hex_to_rgb("#45B7D1"))
    draw = ImageDraw.Draw(img)

    try:
        big_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        sub_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    except (OSError, IOError):
        try:
            big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        except (OSError, IOError):
            big_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 3),
        "Thanks for Watching! 🎉",
        font=big_font,
        fill=(255, 255, 255),
        anchor="mm",
        stroke_width=3,
        stroke_fill=(0, 0, 0),
    )

    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2),
        "👆 SUBSCRIBE & Hit the 🔔",
        font=sub_font,
        fill=(255, 255, 0),
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )

    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT * 2 // 3),
        "More Fun Videos Coming Soon! 🚀",
        font=sub_font,
        fill=(255, 255, 255),
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )

    outro_path = VIDEOS_DIR / "outro_frame.png"
    img.save(str(outro_path))

    outro_clip = ImageClip(str(outro_path)).set_duration(duration)
    return outro_clip


def create_video(script: dict, day_number: int) -> Path:
    """Create a complete video from a script with audio."""
    title = script.get("title", f"Day {day_number} Video")
    scenes = script.get("scenes", [])
    template_name = script.get("category", "story").lower()

    # Get template settings
    template = VIDEO_TEMPLATES.get(template_name, VIDEO_TEMPLATES["story"])

    print(f"🎬 Creating video: {title}")

    # Step 1: Generate audio
    print("  📢 Generating narration audio...")
    audio_path = run_generate_full_audio(script, day_number)
    total_audio_duration = get_audio_duration(audio_path)

    # Calculate per-scene duration based on audio
    num_scenes = len(scenes)
    if num_scenes > 0:
        avg_scene_duration = total_audio_duration / num_scenes
    else:
        avg_scene_duration = 10

    # Step 2: Create scene clips
    print("  🖼️ Creating scene visuals...")
    scene_clips = []

    # Intro
    intro_clip = create_intro_clip(title, template["intro_duration"])
    scene_clips.append(intro_clip)

    # Main scenes
    for scene in scenes:
        scene_duration = scene.get("duration_seconds", avg_scene_duration)
        clip = create_scene_clip(scene, day_number, scene_duration)
        scene_clips.append(clip)

    # Outro
    outro_clip = create_outro_clip(template["outro_duration"])
    scene_clips.append(outro_clip)

    # Step 3: Concatenate all clips
    print("  🔗 Compositing video...")
    final_video = concatenate_videoclips(scene_clips, method="compose")

    # Step 4: Add audio
    audio_clip = AudioFileClip(str(audio_path))

    # Match video duration to audio (plus intro/outro)
    video_duration = final_video.duration
    if audio_clip.duration < video_duration:
        audio_clip = audio_clip.set_duration(video_duration)

    final_video = final_video.set_audio(audio_clip.set_duration(final_video.duration))

    # Step 5: Export
    output_path = VIDEOS_DIR / f"day_{day_number:02d}_{_sanitize(title)}.mp4"
    print(f"  💾 Exporting to {output_path}...")
    final_video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        bitrate="5000k",
    )

    # Cleanup
    final_video.close()
    audio_clip.close()
    for clip in scene_clips:
        clip.close()

    print(f"  ✅ Video created: {output_path}")
    return output_path


def create_thumbnail(script: dict, day_number: int) -> Path:
    """Create an eye-catching thumbnail for the video."""
    title = script.get("title", "Fun Video")
    thumb_text = script.get("thumbnail_text", title[:30])
    thumb_colors = script.get("thumbnail_colors", ["#FF6B6B", "#4ECDC4"])

    img = Image.new("RGB", (1280, 720), hex_to_rgb(thumb_colors[0]))
    draw = ImageDraw.Draw(img)

    # Gradient-ish effect with second color
    if len(thumb_colors) > 1:
        for y in range(360, 720):
            ratio = (y - 360) / 360
            r1, g1, b1 = hex_to_rgb(thumb_colors[0])
            r2, g2, b2 = hex_to_rgb(thumb_colors[1])
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (1280, y)], fill=(r, g, b))

    try:
        big_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except (OSError, IOError):
        try:
            big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except (OSError, IOError):
            big_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    # Border
    draw.rectangle([10, 10, 1270, 710], outline=(255, 255, 255), width=6)

    # Stars
    for x, y in [(100, 80), (1180, 80), (100, 640), (1180, 640)]:
        draw.text((x, y), "⭐", font=small_font, fill=(255, 255, 0), anchor="mm")

    # Main text
    wrapped = textwrap.fill(thumb_text, width=18)
    draw.multiline_text(
        (640, 320),
        wrapped,
        font=big_font,
        fill=(255, 255, 255),
        anchor="mm",
        align="center",
        stroke_width=5,
        stroke_fill=(0, 0, 0),
    )

    # "NEW" badge
    draw.rounded_rectangle([50, 50, 220, 120], radius=15, fill=(255, 0, 0))
    draw.text((135, 85), "NEW!", font=small_font, fill=(255, 255, 255), anchor="mm")

    thumb_path = THUMBNAILS_DIR / f"day_{day_number:02d}_thumb.png"
    img.save(str(thumb_path), quality=95)
    print(f"  🖼️ Thumbnail: {thumb_path}")
    return thumb_path


def _sanitize(text: str) -> str:
    """Sanitize text for use in filenames."""
    return "".join(c if c.isalnum() or c in " -_" else "" for c in text)[:50].strip().replace(" ", "_")
