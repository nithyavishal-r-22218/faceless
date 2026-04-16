"""
Script Generator using Google Gemini Pro API
Generates kids-friendly cartoon video scripts with scenes, narration, and visuals.
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import google.generativeai as genai

from agent.config import (
    GEMINI_API_KEY,
    KIDS_CATEGORIES,
    SCRIPTS_DIR,
    VIDEO_DURATION_MIN,
    VIDEO_DURATION_MAX,
    TARGET_AUDIENCE,
)

genai.configure(api_key=GEMINI_API_KEY)


def get_model():
    return genai.GenerativeModel("gemini-2.5-flash")


def generate_with_retry(model, prompt, max_retries=3):
    """Generate content with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 15
                print(f"Rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise


SCRIPT_SYSTEM_PROMPT = """You are a professional kids' cartoon YouTube scriptwriter with 30+ years of experience.
You create engaging, educational, and entertaining scripts for children aged 3-10.

RULES:
- Content must be 100% child-safe (no violence, scary content, or inappropriate themes)
- Use simple, clear language appropriate for young children
- Include fun sound effects descriptions in brackets [sound effect]
- Each scene must have a visual description for animation/image generation
- Stories should have a moral or learning outcome
- Keep narration engaging with varied tone instructions (excited, gentle, curious, etc.)
- Include interactive elements like "Can you count with me?" or "What color is that?"

OUTPUT FORMAT (strict JSON):
{
    "title": "Video Title (catchy, kid-friendly, SEO-optimized)",
    "description": "YouTube description with keywords",
    "tags": ["tag1", "tag2", ...],
    "category": "content category",
    "target_age": "3-10",
    "estimated_duration_seconds": 300,
    "thumbnail_text": "Short text for thumbnail",
    "thumbnail_colors": ["#color1", "#color2"],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 15,
            "visual_description": "Detailed description of what should appear on screen",
            "narration": "The actual narration text to be spoken",
            "tone": "excited/gentle/curious/happy/dramatic",
            "text_overlay": "Optional text to show on screen",
            "background_color": "#hex_color",
            "sound_effects": ["effect1", "effect2"],
            "characters": ["character names appearing"]
        }
    ],
    "moral": "The lesson or moral of the story",
    "call_to_action": "Subscribe prompt for kids"
}"""


def generate_script(topic: str, category: str = None, duration_target: int = None) -> dict:
    """Generate a single video script using Gemini Pro."""
    if category is None:
        category = random.choice(KIDS_CATEGORIES)

    if duration_target is None:
        duration_target = random.randint(VIDEO_DURATION_MIN, VIDEO_DURATION_MAX)

    model = get_model()

    prompt = f"""{SCRIPT_SYSTEM_PROMPT}

Create a complete video script for:
- Topic: {topic}
- Category: {category}
- Target Duration: {duration_target} seconds (~{duration_target // 60} minutes)
- Target Audience: {TARGET_AUDIENCE} (ages 3-10)
- Style: Colorful, animated, cartoon-style visuals
- Must include: intro, main content (multiple scenes), and outro with subscribe CTA

Make it fun, educational, and engaging! Use bright colors and lovable characters.
Return ONLY valid JSON, no markdown formatting."""

    response = generate_with_retry(model, prompt)
    text = response.text.strip()

    # Clean potential markdown wrapping
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:]

    script = json.loads(text.strip())
    return script


def generate_30_day_plan(channel_name: str = "Kids Cartoon World") -> list[dict]:
    """Generate a complete 30-day content plan with scripts."""
    model = get_model()

    plan_prompt = f"""{SCRIPT_SYSTEM_PROMPT}

You are planning a 30-day content calendar for a kids' cartoon YouTube channel called "{channel_name}".

Create a JSON array of 30 video ideas, one for each day. Mix different categories to keep content fresh.
Each entry should have:
{{
    "day": 1,
    "date": "YYYY-MM-DD",
    "topic": "Video topic/title idea",
    "category": "One of the categories",
    "description_brief": "One-line description",
    "duration_target": 300,
    "priority": "high/medium/low",
    "hashtags": ["#tag1", "#tag2"]
}}

Categories to use: {json.dumps(KIDS_CATEGORIES)}

Start date: {datetime.now().strftime('%Y-%m-%d')}
Mix categories well. Include 2-3 trending/seasonal ideas. Ensure variety.
Return ONLY valid JSON array, no markdown."""

    response = generate_with_retry(model, plan_prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:]

    plan = json.loads(text.strip())

    # Save the plan
    plan_path = SCRIPTS_DIR / "30_day_plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)

    return plan


def generate_scripts_batch(plan: list[dict], days: list[int] = None) -> list[dict]:
    """Generate full scripts for specified days in the plan."""
    if days is None:
        days = list(range(1, 31))

    scripts = []
    for entry in plan:
        if entry["day"] in days:
            try:
                script = generate_script(
                    topic=entry["topic"],
                    category=entry["category"],
                    duration_target=entry.get("duration_target", 300),
                )
                script["day"] = entry["day"]
                script["date"] = entry.get("date", "")

                # Save individual script
                script_path = SCRIPTS_DIR / f"day_{entry['day']:02d}_script.json"
                with open(script_path, "w") as f:
                    json.dump(script, f, indent=2)

                scripts.append(script)
                print(f"✅ Day {entry['day']}: {script.get('title', entry['topic'])}")
            except Exception as e:
                print(f"❌ Day {entry['day']}: Failed - {e}")
                scripts.append({"day": entry["day"], "error": str(e)})

    return scripts


def enhance_script_seo(script: dict) -> dict:
    """Enhance a script's SEO elements using Gemini."""
    model = get_model()

    seo_prompt = f"""You are a YouTube SEO expert for kids' content channels.
Enhance the following video metadata for maximum discoverability:

Title: {script.get('title', '')}
Description: {script.get('description', '')}
Tags: {json.dumps(script.get('tags', []))}

Return JSON with:
{{
    "title_options": ["title1", "title2", "title3"],
    "description_seo": "Full SEO-optimized description with keywords, timestamps, and hashtags",
    "tags_enhanced": ["tag1", "tag2", ...up to 30 tags],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
}}

Focus on kids content SEO. Include popular search terms kids and parents use.
Return ONLY valid JSON."""

    response = model.generate_content(seo_prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:]

    seo_data = json.loads(text.strip())
    script["seo"] = seo_data
    return script
