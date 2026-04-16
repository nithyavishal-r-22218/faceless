#!/usr/bin/env python3
"""
🎬 Faceless YouTube Automation Agent
Main orchestrator - CLI interface for all automation features.

Usage:
    python main.py plan          - Generate 30-day content plan
    python main.py script <day>  - Generate script for a specific day
    python main.py video <day>   - Generate video for a specific day
    python main.py upload <day>  - Upload video for a specific day
    python main.py analytics     - Analyze channel performance
    python main.py trending      - Find trending content
    python main.py full <day>    - Full pipeline: script → video → upload
    python main.py batch <start> <end>  - Batch process multiple days
    python main.py scheduler     - Start auto-upload scheduler
    python main.py templates     - List available templates
    python main.py status        - Show pipeline status
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from agent.config import (
    GEMINI_API_KEY,
    OUTPUT_DIR,
    SCRIPTS_DIR,
    VIDEOS_DIR,
    THUMBNAILS_DIR,
    UPLOAD_TIME,
    YOUTUBE_API_KEY,
    YOUTUBE_CHANNEL_ID,
)

console = Console()


def banner():
    console.print(Panel.fit(
        "[bold magenta]🎬 Faceless YouTube Automation Agent[/]\n"
        "[cyan]Kids Cartoon Channel • Fully Automated Pipeline[/]\n"
        "[dim]Script → Audio → Video → Thumbnail → Upload → Schedule[/]",
        border_style="bright_magenta",
    ))


def check_config():
    """Verify required configuration."""
    issues = []
    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY not set in .env")
    if not YOUTUBE_API_KEY:
        issues.append("YOUTUBE_API_KEY not set in .env (needed for analytics/trending)")
    if not YOUTUBE_CHANNEL_ID:
        issues.append("YOUTUBE_CHANNEL_ID not set in .env (needed for analytics)")
    return issues


# ── Plan ─────────────────────────────────────────────────────────
def cmd_plan():
    """Generate 30-day content plan."""
    from agent.script_generator import generate_30_day_plan

    console.print("\n[bold green]📅 Generating 30-Day Content Plan...[/]")

    plan = generate_30_day_plan()

    table = Table(title="30-Day Content Plan", show_lines=True)
    table.add_column("Day", style="bold cyan", width=5)
    table.add_column("Date", style="dim", width=12)
    table.add_column("Topic", style="bold white", width=40)
    table.add_column("Category", style="green", width=20)
    table.add_column("Priority", width=8)

    for entry in plan:
        priority_color = {
            "high": "red", "medium": "yellow", "low": "green"
        }.get(entry.get("priority", "medium"), "white")

        table.add_row(
            str(entry["day"]),
            entry.get("date", ""),
            entry["topic"],
            entry.get("category", ""),
            f"[{priority_color}]{entry.get('priority', 'medium')}[/]",
        )

    console.print(table)
    console.print(f"\n[green]✅ Plan saved to {SCRIPTS_DIR / '30_day_plan.json'}[/]")


# ── Script ───────────────────────────────────────────────────────
def cmd_script(day: int):
    """Generate script for a specific day."""
    from agent.script_generator import generate_script, enhance_script_seo
    from agent.templates import apply_template

    plan_path = SCRIPTS_DIR / "30_day_plan.json"
    if not plan_path.exists():
        console.print("[red]❌ No content plan found. Run 'plan' first.[/]")
        return

    with open(plan_path) as f:
        plan = json.load(f)

    day_entry = next((e for e in plan if e["day"] == day), None)
    if not day_entry:
        console.print(f"[red]❌ Day {day} not found in plan.[/]")
        return

    console.print(f"\n[bold green]📝 Generating script for Day {day}: {day_entry['topic']}[/]")

    script = generate_script(
        topic=day_entry["topic"],
        category=day_entry.get("category"),
        duration_target=day_entry.get("duration_target", 300),
    )

    # Apply template
    category_map = {
        "Moral Stories": "story",
        "Fairy Tales": "story",
        "Bedtime Stories": "story",
        "Friendship Stories": "story",
        "Nursery Rhymes & Songs": "rhyme",
        "ABC & 123 Learning": "learning",
        "Fun Facts for Kids": "facts",
        "Space & Science for Kids": "facts",
        "Animal Adventures": "adventure",
        "Dinosaur Adventures": "adventure",
    }
    template_type = category_map.get(day_entry.get("category", ""), "story")
    script = apply_template(template_type, script)

    # Enhance SEO
    console.print("  🔍 Enhancing SEO...")
    script = enhance_script_seo(script)

    script["day"] = day
    script["date"] = day_entry.get("date", "")

    script_path = SCRIPTS_DIR / f"day_{day:02d}_script.json"
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)

    console.print(f"[green]✅ Script saved: {script_path}[/]")
    console.print(f"   Title: [bold]{script.get('title', 'N/A')}[/]")
    console.print(f"   Scenes: {len(script.get('scenes', []))}")
    console.print(f"   Duration: ~{script.get('estimated_duration_seconds', 0) // 60} min")


# ── Video ────────────────────────────────────────────────────────
def cmd_video(day: int):
    """Generate video for a specific day."""
    from agent.video_generator import create_video, create_thumbnail

    script_path = SCRIPTS_DIR / f"day_{day:02d}_script.json"
    if not script_path.exists():
        console.print(f"[red]❌ No script for Day {day}. Run 'script {day}' first.[/]")
        return

    with open(script_path) as f:
        script = json.load(f)

    console.print(f"\n[bold green]🎬 Creating video for Day {day}: {script.get('title', '')}[/]")

    video_format = script.get("video_format", "long")
    video_path = create_video(script, day, video_format=video_format)
    if video_format == "short":
        from agent.video_generator import create_thumbnail_for_format
        thumb_path = create_thumbnail_for_format(script, day, video_format=video_format)
    else:
        thumb_path = create_thumbnail(script, day)

    console.print(f"[green]✅ Video: {video_path}[/]")
    console.print(f"[green]✅ Thumbnail: {thumb_path}[/]")


# ── Upload ───────────────────────────────────────────────────────
def cmd_upload(day: int, publish_date: str = None):
    """Upload video for a specific day."""
    from agent.youtube_uploader import schedule_upload

    script_path = SCRIPTS_DIR / f"day_{day:02d}_script.json"
    if not script_path.exists():
        console.print(f"[red]❌ No script for Day {day}.[/]")
        return

    with open(script_path) as f:
        script = json.load(f)

    # Find video file
    video_files = list(VIDEOS_DIR.glob(f"day_{day:02d}_*.mp4"))
    if not video_files:
        console.print(f"[red]❌ No video for Day {day}. Run 'video {day}' first.[/]")
        return

    video_path = str(video_files[0])
    thumb_files = list(THUMBNAILS_DIR.glob(f"day_{day:02d}_*.png"))
    thumb_path = str(thumb_files[0]) if thumb_files else None

    if not publish_date:
        publish_date = script.get("date")

    console.print(f"\n[bold green]📤 Uploading Day {day}: {script.get('title', '')}[/]")

    video_id = schedule_upload(
        video_path=video_path,
        script=script,
        thumbnail_path=thumb_path,
        publish_date=publish_date,
        publish_time=UPLOAD_TIME,
    )

    console.print(f"[green]✅ Uploaded! Video ID: {video_id}[/]")


# ── Full Pipeline ────────────────────────────────────────────────
def cmd_full(day: int):
    """Run full pipeline for a single day: script → video → upload."""
    console.print(f"\n[bold magenta]🚀 Full Pipeline - Day {day}[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating script...", total=4)

        cmd_script(day)
        progress.update(task, advance=1, description="Creating video...")

        cmd_video(day)
        progress.update(task, advance=1, description="Uploading...")

        cmd_upload(day)
        progress.update(task, advance=1, description="Done!")

        progress.update(task, advance=1)

    console.print(f"\n[bold green]🎉 Day {day} complete! Full pipeline finished.[/]")


# ── Batch ────────────────────────────────────────────────────────
def cmd_batch(start_day: int, end_day: int):
    """Run full pipeline for a range of days."""
    console.print(f"\n[bold magenta]📦 Batch Processing Days {start_day}-{end_day}[/]")

    for day in range(start_day, end_day + 1):
        try:
            console.print(f"\n{'─' * 50}")
            console.print(f"[bold cyan]Day {day}/{end_day}[/]")
            cmd_script(day)
            cmd_video(day)
            console.print(f"[green]✅ Day {day} complete[/]")
        except Exception as e:
            console.print(f"[red]❌ Day {day} failed: {e}[/]")

    console.print(f"\n[bold green]📦 Batch complete! Days {start_day}-{end_day} processed.[/]")


# ── Analytics ────────────────────────────────────────────────────
def cmd_analytics():
    """Run channel analytics."""
    from agent.analytics import analyze_performance, print_analytics_report

    console.print("\n[bold green]📊 Analyzing channel performance...[/]")
    analysis = analyze_performance()
    print_analytics_report(analysis)


# ── Trending ─────────────────────────────────────────────────────
def cmd_trending():
    """Find trending content."""
    from agent.trending import get_trending_report, print_trending_report

    console.print("\n[bold green]🔥 Finding trending kids content...[/]")
    report = get_trending_report()
    print_trending_report(report)


# ── Templates ────────────────────────────────────────────────────
def cmd_templates():
    """List available templates."""
    from agent.templates import TEMPLATES

    table = Table(title="Available Video Templates")
    table.add_column("Template", style="bold cyan")
    table.add_column("Category", style="green")
    table.add_column("Target Age", style="yellow")
    table.add_column("Duration", style="dim")
    table.add_column("Tags", style="dim", width=40)

    for name, tmpl in TEMPLATES.items():
        table.add_row(
            name,
            tmpl.get("category", ""),
            tmpl.get("target_age", ""),
            f"{tmpl.get('estimated_duration_seconds', 0) // 60} min",
            ", ".join(tmpl.get("tags", [])[:5]),
        )

    console.print(table)


# ── Scheduler ────────────────────────────────────────────────────
def cmd_scheduler():
    """Start the auto-upload scheduler."""
    from agent.youtube_uploader import run_scheduler

    console.print(f"\n[bold green]⏰ Starting scheduler (daily at {UPLOAD_TIME})...[/]")
    console.print("[dim]Press Ctrl+C to stop[/]")

    day_counter_path = OUTPUT_DIR / "scheduler_state.json"
    if day_counter_path.exists():
        with open(day_counter_path) as f:
            state = json.load(f)
        current_day = state.get("next_day", 1)
    else:
        current_day = 1

    def daily_upload():
        nonlocal current_day
        try:
            console.print(f"\n[cyan]⏰ Scheduled run - Day {current_day}[/]")
            cmd_full(current_day)
            current_day += 1
            with open(day_counter_path, "w") as f:
                json.dump({"next_day": current_day, "last_run": datetime.now().isoformat()}, f)
        except Exception as e:
            console.print(f"[red]❌ Scheduled run failed: {e}[/]")

    run_scheduler(daily_upload, UPLOAD_TIME)


# ── Status ───────────────────────────────────────────────────────
def cmd_status():
    """Show current pipeline status."""
    table = Table(title="Pipeline Status")
    table.add_column("Day", style="cyan", width=5)
    table.add_column("Script", width=8)
    table.add_column("Video", width=8)
    table.add_column("Thumbnail", width=10)
    table.add_column("Title", style="white", width=40)

    for day in range(1, 31):
        script_exists = (SCRIPTS_DIR / f"day_{day:02d}_script.json").exists()
        video_exists = bool(list(VIDEOS_DIR.glob(f"day_{day:02d}_*.mp4")))
        thumb_exists = bool(list(THUMBNAILS_DIR.glob(f"day_{day:02d}_*.png")))

        title = ""
        if script_exists:
            with open(SCRIPTS_DIR / f"day_{day:02d}_script.json") as f:
                title = json.load(f).get("title", "")[:40]

        table.add_row(
            str(day),
            "[green]✅[/]" if script_exists else "[red]❌[/]",
            "[green]✅[/]" if video_exists else "[red]❌[/]",
            "[green]✅[/]" if thumb_exists else "[red]❌[/]",
            title,
        )

    console.print(table)

    # Config check
    issues = check_config()
    if issues:
        console.print("\n[yellow]⚠️ Configuration Issues:[/]")
        for issue in issues:
            console.print(f"  [red]• {issue}[/]")


# ── Main ─────────────────────────────────────────────────────────
def main():
    banner()

    if len(sys.argv) < 2:
        console.print("""
[bold]Usage:[/]
  python main.py [cyan]plan[/]              Generate 30-day content plan
  python main.py [cyan]script[/] <day>      Generate script for day N
  python main.py [cyan]video[/] <day>       Generate video for day N
  python main.py [cyan]upload[/] <day>      Upload video for day N
  python main.py [cyan]full[/] <day>        Full pipeline for day N
  python main.py [cyan]batch[/] <start> <end>  Batch process days
  python main.py [cyan]analytics[/]         Channel analytics
  python main.py [cyan]trending[/]          Trending content finder
  python main.py [cyan]templates[/]         List video templates
  python main.py [cyan]scheduler[/]         Start auto-scheduler
  python main.py [cyan]status[/]            Pipeline status
        """)
        cmd_status()
        return

    command = sys.argv[1].lower()

    if command == "plan":
        cmd_plan()
    elif command == "script":
        day = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        cmd_script(day)
    elif command == "video":
        day = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        cmd_video(day)
    elif command == "upload":
        day = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        date = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_upload(day, date)
    elif command == "full":
        day = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        cmd_full(day)
    elif command == "batch":
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        end = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        cmd_batch(start, end)
    elif command == "analytics":
        cmd_analytics()
    elif command == "trending":
        cmd_trending()
    elif command == "templates":
        cmd_templates()
    elif command == "scheduler":
        cmd_scheduler()
    elif command == "status":
        cmd_status()
    else:
        console.print(f"[red]Unknown command: {command}[/]")


if __name__ == "__main__":
    main()
