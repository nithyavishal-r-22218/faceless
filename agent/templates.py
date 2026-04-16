"""
Video Templates
Pre-built templates for different types of kids content.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent.config import KIDS_COLOR_PALETTES, VIDEO_TEMPLATES


# Pre-built script templates for quick content creation
STORY_TEMPLATE = {
    "title": "",
    "description": "",
    "tags": ["kids", "cartoon", "children", "story", "animated", "fun", "learning"],
    "category": "Moral Stories",
    "target_age": "3-10",
    "estimated_duration_seconds": 300,
    "thumbnail_text": "",
    "thumbnail_colors": KIDS_COLOR_PALETTES["bright"][:2],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 5,
            "visual_description": "Colorful intro screen with channel logo and sparkles",
            "narration": "Welcome to Kids Cartoon World! Today we have an amazing story for you!",
            "tone": "excited",
            "text_overlay": "",
            "background_color": "#FF6B6B",
            "sound_effects": ["sparkle", "whoosh"],
            "characters": [],
        },
        {
            "scene_number": 2,
            "duration_seconds": 30,
            "visual_description": "",
            "narration": "",
            "tone": "gentle",
            "text_overlay": "",
            "background_color": "#4ECDC4",
            "sound_effects": [],
            "characters": [],
        },
        # More scenes added dynamically
    ],
    "moral": "",
    "call_to_action": "Did you like this story? Subscribe and hit the bell! 🔔",
}

LEARNING_TEMPLATE = {
    "title": "",
    "description": "",
    "tags": ["kids learning", "educational", "abc", "numbers", "colors", "shapes", "preschool"],
    "category": "ABC & 123 Learning",
    "target_age": "3-6",
    "estimated_duration_seconds": 240,
    "thumbnail_text": "",
    "thumbnail_colors": KIDS_COLOR_PALETTES["rainbow"][:2],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 4,
            "visual_description": "Bright learning lab with cute animated characters",
            "narration": "Hey friends! Ready to learn something awesome today?",
            "tone": "excited",
            "text_overlay": "Let's Learn!",
            "background_color": "#FFD93D",
            "sound_effects": ["pop", "cheer"],
            "characters": ["Professor Bunny"],
        },
    ],
    "moral": "Learning is fun!",
    "call_to_action": "Great job learning today! Subscribe for more fun lessons! 🌟",
}

RHYME_TEMPLATE = {
    "title": "",
    "description": "",
    "tags": ["nursery rhymes", "kids songs", "baby songs", "toddler songs", "singing", "music"],
    "category": "Nursery Rhymes & Songs",
    "target_age": "2-6",
    "estimated_duration_seconds": 180,
    "thumbnail_text": "",
    "thumbnail_colors": KIDS_COLOR_PALETTES["pastel"][:2],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 3,
            "visual_description": "Musical intro with dancing notes and instruments",
            "narration": "Sing along with us! 🎵",
            "tone": "happy",
            "text_overlay": "🎵 Sing Along! 🎵",
            "background_color": "#FFB3BA",
            "sound_effects": ["music_intro"],
            "characters": [],
        },
    ],
    "moral": "",
    "call_to_action": "Wasn't that fun? Subscribe for more songs! 🎶",
}

FACTS_TEMPLATE = {
    "title": "",
    "description": "",
    "tags": ["fun facts", "kids facts", "did you know", "amazing facts", "science kids", "animals"],
    "category": "Fun Facts for Kids",
    "target_age": "5-10",
    "estimated_duration_seconds": 300,
    "thumbnail_text": "",
    "thumbnail_colors": KIDS_COLOR_PALETTES["ocean"][:2],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 4,
            "visual_description": "Space-themed intro with floating question marks",
            "narration": "Hey curious minds! Ready for some AMAZING facts?",
            "tone": "excited",
            "text_overlay": "🤯 Fun Facts!",
            "background_color": "#006994",
            "sound_effects": ["mind_blown", "whoosh"],
            "characters": ["Fact Fox"],
        },
    ],
    "moral": "The world is full of amazing things to discover!",
    "call_to_action": "Which fact was YOUR favorite? Tell us in the comments! Subscribe for more! 🦊",
}

ADVENTURE_TEMPLATE = {
    "title": "",
    "description": "",
    "tags": ["adventure", "kids adventure", "exploring", "cartoon adventure", "animated story"],
    "category": "Animal Adventures",
    "target_age": "4-10",
    "estimated_duration_seconds": 360,
    "thumbnail_text": "",
    "thumbnail_colors": KIDS_COLOR_PALETTES["nature"][:2],
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 5,
            "visual_description": "Map unrolling with compass and adventure gear",
            "narration": "Adventurers assemble! Today we're going on an incredible journey!",
            "tone": "dramatic",
            "text_overlay": "🗺️ Adventure Time!",
            "background_color": "#2D5016",
            "sound_effects": ["adventure_horn", "footsteps"],
            "characters": ["Explorer Bear", "Map Monkey"],
        },
    ],
    "moral": "Brave explorers always help their friends!",
    "call_to_action": "What adventure should we go on next? Comment below! 🌍",
}


TEMPLATES = {
    "story": STORY_TEMPLATE,
    "learning": LEARNING_TEMPLATE,
    "rhyme": RHYME_TEMPLATE,
    "facts": FACTS_TEMPLATE,
    "adventure": ADVENTURE_TEMPLATE,
}


def get_template(template_type: str) -> dict:
    """Get a copy of a template by type."""
    import copy
    template = TEMPLATES.get(template_type.lower(), STORY_TEMPLATE)
    return copy.deepcopy(template)


def list_templates() -> list[str]:
    """List all available template types."""
    return list(TEMPLATES.keys())


def apply_template(template_type: str, script: dict) -> dict:
    """Merge a generated script with a template's defaults."""
    template = get_template(template_type)

    # Use template defaults for missing fields
    for key, value in template.items():
        if key not in script or not script[key]:
            script[key] = value

    # Ensure tags include template tags
    template_tags = set(template.get("tags", []))
    script_tags = set(script.get("tags", []))
    script["tags"] = list(template_tags | script_tags)[:30]

    return script


def save_custom_template(name: str, template: dict, output_dir: Path = None):
    """Save a custom template for future use."""
    from agent.config import OUTPUT_DIR
    output_dir = output_dir or OUTPUT_DIR
    templates_dir = output_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    path = templates_dir / f"{name}_template.json"
    with open(path, "w") as f:
        json.dump(template, f, indent=2)
    print(f"💾 Template saved: {path}")
    return path


def load_custom_template(name: str, output_dir: Path = None) -> dict:
    """Load a custom template."""
    from agent.config import OUTPUT_DIR
    output_dir = output_dir or OUTPUT_DIR
    path = output_dir / "templates" / f"{name}_template.json"

    if not path.exists():
        raise FileNotFoundError(f"Template '{name}' not found at {path}")

    with open(path) as f:
        return json.load(f)
