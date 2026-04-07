#!/usr/bin/env python3
"""
roadmap_dashboard.py — Rich roadmap cockpit (D48 versioned roadmap).

Reads `.azoth/roadmap.yaml` and prints one panel per roadmap version with
status, phase scope, goals, notes, and task lists (completed vs pending).

Usage:
  python scripts/roadmap_dashboard.py
  python scripts/roadmap_dashboard.py --roadmap /path/to/roadmap.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"

FOOTER = (
    "[dim]Canonical roadmap data: `versions[]` (D48). The legacy top-level `tasks:` "
    "block is retained for older tooling; prefer versioned blocks for planning.[/]"
)


def load_roadmap(path: Path | None = None) -> dict[str, Any]:
    """Load roadmap YAML; return empty dict if missing or invalid."""
    p = path or DEFAULT_ROADMAP
    if not p.exists():
        return {}
    try:
        with p.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _status_style(status: str) -> str:
    return {
        "complete": "green",
        "active": "bold yellow",
        "planned": "cyan",
        "backlog": "magenta",
        "target": "bold white",
    }.get(status, "white")


def _task_done_icon(done: bool) -> str:
    return ":white_check_mark:" if done else ":white_circle:"


def _format_task_block(
    label: str,
    entries: list[dict[str, Any]],
    *,
    done: bool,
) -> list[str]:
    lines: list[str] = []
    if not entries:
        return lines
    lines.append(f"[bold]{label}[/bold]")
    for task in entries:
        tid = task.get("id", "?")
        title = task.get("title", "")
        mark = _task_done_icon(done)
        lines.append(f"  {mark} [cyan]{tid}[/]  {title}")
        for key in ("note", "deferred_from"):
            val = task.get(key)
            if val:
                lines.append(f"      [dim]{val}[/]")
    return lines


def build_version_body(version: dict[str, Any]) -> str:
    """Build markdown-rich body text for one roadmap version block."""
    st = version.get("status", "?")
    lines: list[str] = []

    lines.append(f"[{_status_style(st)}]● {str(st).upper()}[/]")
    ps = version.get("phase_scope")
    if ps is not None:
        lines.append(f"[dim]Phases:[/] {ps!s}")
    lines.append("")
    goal = version.get("goal", "")
    if goal:
        lines.append(goal)

    if "current_patch" in version:
        lines.append(f"[dim]current_patch:[/] {version['current_patch']}")
    if "final_patch" in version:
        lines.append(f"[dim]final_patch:[/] {version['final_patch']}")
    cd = version.get("completed_date")
    if cd:
        lines.append(f"[dim]completed_date:[/] {cd}")

    note = version.get("note", "")
    if note:
        lines.append("")
        lines.append(f"[dim italic]{note}[/]")

    completed = version.get("completed_tasks") or []
    pending = version.get("tasks") or []

    if completed or pending:
        lines.append("")

    lines.extend(_format_task_block("Delivered", completed, done=True))
    if completed and pending:
        lines.append("")
    lines.extend(_format_task_block("Upcoming", pending, done=False))

    return "\n".join(lines)


def render_header(data: dict[str, Any]) -> Panel:
    """Top banner: active_version + schema hint."""
    av = data.get("active_version", "?")
    header = Text()
    header.append("ROADMAP ", style="bold white")
    header.append("·  active_version ", style="dim")
    header.append(str(av), style="bold cyan")
    header.append("  ·  D48 + D53", style="dim")
    return Panel(header, box=box.HEAVY)


def render_version_panel(version: dict[str, Any]) -> Panel:
    """Single bordered panel for one `versions[]` entry."""
    vid = version.get("id", "?")
    st = version.get("status", "?")
    body = build_version_body(version)
    title_bar = f"[bold]{vid}[/]  [{_status_style(st)}]{st}[/{_status_style(st)}]"
    return Panel(
        body,
        title=title_bar,
        border_style=_status_style(st),
        box=box.ROUNDED,
    )


def render_dashboard(
    roadmap_path: Path | None = None,
    *,
    console: Console | None = None,
) -> None:
    """Print full roadmap dashboard to console."""
    path = roadmap_path or DEFAULT_ROADMAP
    data = load_roadmap(path)
    out = console or Console(width=100)

    out.print()
    if not data:
        out.print(
            Panel(
                f"[yellow]No roadmap data at {path}[/]",
                title="Roadmap",
                box=box.HEAVY,
            )
        )
        return

    out.print(render_header(data))
    out.print()

    versions = data.get("versions") or []
    for v in versions:
        out.print(render_version_panel(v))
        out.print()

    out.print(Panel(FOOTER, box=box.MINIMAL))
    out.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Azoth roadmap dashboard (Rich).")
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=None,
        help=f"Path to roadmap.yaml (default: {DEFAULT_ROADMAP})",
    )
    args = parser.parse_args()
    render_dashboard(roadmap_path=args.roadmap)


if __name__ == "__main__":
    main()
