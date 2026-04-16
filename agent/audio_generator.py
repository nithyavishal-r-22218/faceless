"""
Audio Generator - Text-to-Speech using edge-tts
Generates narration audio for video scripts.
"""
from __future__ import annotations

import asyncio
import edge_tts
from pathlib import Path
from pydub import AudioSegment

from agent.config import TTS_VOICE, AUDIO_DIR


async def generate_narration(text: str, output_path: Path, voice: str = None) -> Path:
    """Generate TTS audio for narration text."""
    voice = voice or TTS_VOICE
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    return output_path


async def generate_scene_audio(scenes: list[dict], day_number: int) -> list[Path]:
    """Generate audio for each scene in a script."""
    audio_files = []
    day_dir = AUDIO_DIR / f"day_{day_number:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)

    for scene in scenes:
        scene_num = scene["scene_number"]
        narration = scene.get("narration", "")
        if not narration.strip():
            continue

        output_path = day_dir / f"scene_{scene_num:02d}.mp3"
        await generate_narration(narration, output_path)
        audio_files.append(output_path)
        print(f"  🔊 Scene {scene_num} audio generated")

    return audio_files


def combine_audio_files(audio_files: list[Path], output_path: Path, gap_ms: int = 500) -> Path:
    """Combine multiple audio files with gaps between them."""
    if not audio_files:
        raise ValueError("No audio files to combine")

    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=gap_ms)

    for i, audio_file in enumerate(audio_files):
        segment = AudioSegment.from_mp3(str(audio_file))
        combined += segment
        if i < len(audio_files) - 1:
            combined += silence

    combined.export(str(output_path), format="mp3")
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds."""
    audio = AudioSegment.from_file(str(audio_path))
    return len(audio) / 1000.0


async def generate_full_audio(script: dict, day_number: int) -> Path:
    """Generate complete audio for a full script."""
    scenes = script.get("scenes", [])
    scene_files = await generate_scene_audio(scenes, day_number)

    if not scene_files:
        raise ValueError("No audio generated from script scenes")

    full_audio_path = AUDIO_DIR / f"day_{day_number:02d}_full.mp3"
    combine_audio_files(scene_files, full_audio_path)
    print(f"  🎵 Full audio: {full_audio_path}")
    return full_audio_path


def run_generate_full_audio(script: dict, day_number: int) -> Path:
    """Synchronous wrapper for generate_full_audio."""
    return asyncio.run(generate_full_audio(script, day_number))
