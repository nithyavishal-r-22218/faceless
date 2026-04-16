"""
Audio Generator - narration, background music, and sound effect mixing.
Creates a YouTube-ready master track while preserving scene timing metadata.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment
from pydub.generators import Sine

from agent.config import ASSETS_DIR, AUDIO_DIR, TTS_VOICE

MUSIC_DIR = ASSETS_DIR / "music"
SFX_DIR = ASSETS_DIR / "sfx"
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".ogg")

DEFAULT_MUSIC_LEVEL_DB = -24
DEFAULT_SFX_LEVEL_DB = -12
DEFAULT_GAP_MS = 350


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _load_audio(path: Path) -> AudioSegment:
    return AudioSegment.from_file(str(path))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _find_asset(directory: Path, names: list[str]) -> Path | None:
    if not directory.exists():
        return None

    seen: set[str] = set()
    for name in names:
        slug = _slugify(name)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        for ext in AUDIO_EXTENSIONS:
            candidate = directory / f"{slug}{ext}"
            if candidate.exists():
                return candidate

    normalized_names = {_slugify(name) for name in names if _slugify(name)}
    for candidate in sorted(directory.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in AUDIO_EXTENSIONS:
            if _slugify(candidate.stem) in normalized_names:
                return candidate
    return None


def _music_profile(style: str) -> tuple[int, int, int]:
    style = (style or "ambient").lower()
    profiles = {
        "upbeat": (180, 240, 360),
        "calm": (174, 220, 261),
        "dramatic": (130, 164, 196),
        "fun": (220, 277, 330),
        "mystery": (146, 174, 220),
        "ambient": (160, 196, 247),
        "none": (0, 0, 0),
    }
    return profiles.get(style, profiles["ambient"])


def _generate_music_bed(duration_ms: int, style: str) -> AudioSegment:
    if style == "none":
        return AudioSegment.silent(duration=duration_ms)

    low, mid, high = _music_profile(style)
    if not low:
        return AudioSegment.silent(duration=duration_ms)

    base = (
        Sine(low).to_audio_segment(duration=duration_ms).apply_gain(-31)
        .overlay(Sine(mid).to_audio_segment(duration=duration_ms).apply_gain(-34))
        .overlay(Sine(high).to_audio_segment(duration=duration_ms).apply_gain(-37))
    )
    pulse = Sine(high * 2).to_audio_segment(duration=max(duration_ms // 8, 1000)).apply_gain(-40)
    cursor = AudioSegment.silent(duration=duration_ms)
    step = max(duration_ms // 6, 2200)
    for offset in range(0, duration_ms, step):
        cursor = cursor.overlay(pulse, position=offset)

    return base.overlay(cursor).fade_in(1200).fade_out(1800)


def _generate_effect_fallback(effect_name: str) -> AudioSegment:
    name = (effect_name or "").lower()
    if any(token in name for token in ("whoosh", "swoosh", "swish")):
        return Sine(720).to_audio_segment(duration=220).fade_out(180).apply_gain(-12)
    if any(token in name for token in ("sparkle", "magic", "twinkle", "chime")):
        return (
            Sine(880).to_audio_segment(duration=160).apply_gain(-15)
            .overlay(Sine(1320).to_audio_segment(duration=120).apply_gain(-18), position=40)
            .fade_out(120)
        )
    if any(token in name for token in ("pop", "click", "tap")):
        return Sine(520).to_audio_segment(duration=90).fade_out(80).apply_gain(-10)
    if any(token in name for token in ("boom", "hit", "dramatic")):
        return Sine(110).to_audio_segment(duration=260).fade_out(220).apply_gain(-10)
    return Sine(660).to_audio_segment(duration=120).fade_out(100).apply_gain(-18)


async def generate_narration(text: str, output_path: Path, voice: str = None) -> Path:
    """Generate TTS audio for narration text."""
    voice = voice or TTS_VOICE
    _ensure_parent(output_path)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    return output_path


async def generate_scene_audio(scenes: list[dict], day_number: int, voice: str = None) -> list[dict]:
    """Generate narration audio for each scene and return timing metadata."""
    audio_files: list[dict] = []
    day_dir = AUDIO_DIR / f"day_{day_number:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)

    offset_ms = 0
    for scene in scenes:
        scene_num = scene["scene_number"]
        narration = scene.get("narration", "")
        if not narration.strip():
            continue

        output_path = day_dir / f"scene_{scene_num:02d}.mp3"
        await generate_narration(narration, output_path, voice=voice)
        duration_ms = len(AudioSegment.from_mp3(str(output_path)))
        audio_files.append(
            {
                "scene_number": scene_num,
                "path": output_path,
                "duration_ms": duration_ms,
                "offset_ms": offset_ms,
            }
        )
        offset_ms += duration_ms + DEFAULT_GAP_MS
        print(f"  🔊 Scene {scene_num} audio generated")

    return audio_files


def combine_audio_files(audio_files: list[dict], output_path: Path, gap_ms: int = DEFAULT_GAP_MS) -> Path:
    """Combine per-scene narration files into a single narration track."""
    if not audio_files:
        raise ValueError("No audio files to combine")

    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=gap_ms)

    for i, entry in enumerate(audio_files):
        segment = AudioSegment.from_mp3(str(entry["path"]))
        combined += segment
        if i < len(audio_files) - 1:
            combined += silence

    _ensure_parent(output_path)
    combined.export(str(output_path), format="mp3")
    return output_path


def build_background_music(duration_ms: int, music_style: str, output_path: Path, volume_db: int = DEFAULT_MUSIC_LEVEL_DB) -> Path:
    """Create or loop a background music bed."""
    asset = _find_asset(MUSIC_DIR, [music_style, "default", "ambient"])
    if asset:
        music = _load_audio(asset)
        if len(music) < duration_ms:
            loops = (duration_ms // max(len(music), 1)) + 1
            music = music * loops
        music = music[:duration_ms]
    else:
        music = _generate_music_bed(duration_ms, music_style)

    music = music.apply_gain(volume_db).fade_in(1200).fade_out(1800)
    _ensure_parent(output_path)
    music.export(str(output_path), format="mp3")
    return output_path


def build_sound_effects_track(
    scenes: list[dict],
    scene_audio: list[dict],
    duration_ms: int,
    output_path: Path,
    volume_db: int = DEFAULT_SFX_LEVEL_DB,
) -> Path:
    """Create a sound effects layer aligned with scene starts."""
    effect_track = AudioSegment.silent(duration=duration_ms)
    timing_map = {entry["scene_number"]: entry for entry in scene_audio}

    for scene in scenes:
        timing = timing_map.get(scene.get("scene_number"))
        if not timing:
            continue

        base_position = timing["offset_ms"]
        effects = scene.get("sound_effects", []) or []
        for index, effect_name in enumerate(effects[:3]):
            asset = _find_asset(SFX_DIR, [effect_name])
            effect = _load_audio(asset) if asset else _generate_effect_fallback(effect_name)
            effect = effect.apply_gain(volume_db - (index * 2))
            effect_track = effect_track.overlay(effect, position=base_position + index * 260)

    _ensure_parent(output_path)
    effect_track.export(str(output_path), format="mp3")
    return output_path


def mix_audio_package(
    script: dict,
    day_number: int,
    scene_audio: list[dict],
    narration_path: Path,
    music_style: str | None = None,
) -> dict:
    """Create mastered audio outputs for the video."""
    narration = AudioSegment.from_file(str(narration_path))
    total_duration_ms = len(narration)
    mix_dir = AUDIO_DIR / f"day_{day_number:02d}"
    mix_dir.mkdir(parents=True, exist_ok=True)

    music_style = music_style or script.get("music_style") or "ambient"
    music_path = mix_dir / "background_music.mp3"
    sfx_path = mix_dir / "sound_effects.mp3"
    master_path = AUDIO_DIR / f"day_{day_number:02d}_full.mp3"

    build_background_music(total_duration_ms, music_style, music_path)
    build_sound_effects_track(script.get("scenes", []), scene_audio, total_duration_ms, sfx_path)

    music = AudioSegment.from_file(str(music_path))
    sound_fx = AudioSegment.from_file(str(sfx_path))

    mastered = music.overlay(sound_fx).overlay(narration)
    mastered = mastered.normalize(headroom=1.5).fade_in(400).fade_out(800)
    mastered.export(str(master_path), format="mp3")

    return {
        "master_path": master_path,
        "narration_path": narration_path,
        "music_path": music_path,
        "sfx_path": sfx_path,
        "scene_audio": scene_audio,
        "duration_ms": total_duration_ms,
    }


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds."""
    audio = AudioSegment.from_file(str(audio_path))
    return len(audio) / 1000.0


async def generate_full_audio_package(
    script: dict,
    day_number: int,
    voice: str = None,
    music_style: str | None = None,
) -> dict:
    """Generate narration plus mastered music/sfx mix for a full script."""
    scenes = script.get("scenes", [])
    scene_audio = await generate_scene_audio(scenes, day_number, voice=voice)

    if not scene_audio:
        raise ValueError("No audio generated from script scenes")

    narration_path = AUDIO_DIR / f"day_{day_number:02d}_narration.mp3"
    combine_audio_files(scene_audio, narration_path)
    package = mix_audio_package(script, day_number, scene_audio, narration_path, music_style=music_style)
    print(f"  🎵 Master audio: {package['master_path']}")
    return package


async def generate_full_audio(script: dict, day_number: int) -> Path:
    """Backwards-compatible wrapper returning the mastered audio path."""
    package = await generate_full_audio_package(script, day_number)
    return package["master_path"]


def run_generate_audio_package(
    script: dict,
    day_number: int,
    voice: str = None,
    music_style: str | None = None,
) -> dict:
    """Synchronous wrapper that returns full audio package metadata."""
    coroutine = generate_full_audio_package(script, day_number, voice=voice, music_style=music_style)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coroutine).result()
    return asyncio.run(coroutine)


def run_generate_full_audio(script: dict, day_number: int) -> Path:
    """Synchronous wrapper preserving the previous public API."""
    return run_generate_audio_package(script, day_number)["master_path"]
