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
from typing import Any, NamedTuple

import yaml
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"

FOOTER = (
    "[dim]Canonical roadmap data: `versions[]` (D48). The legacy top-level `tasks:` "
    "block is retained for older tooling; prefer versioned blocks for planning.[/]"
)

MAX_SCHEMA_WARNINGS = 25


class RoadmapLoadDiag(NamedTuple):
    """Result of loading roadmap YAML: data (possibly empty) and why it is empty."""

    data: dict[str, Any]
    empty_reason: str | None  # None iff data is non-empty; else diagnostic tag/message


def load_roadmap_diag(path: Path | None = None) -> RoadmapLoadDiag:
    """Load roadmap YAML with a reason when the result is an empty mapping."""
    p = path or DEFAULT_ROADMAP
    if not p.exists():
        return RoadmapLoadDiag({}, "missing")
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return RoadmapLoadDiag({}, f"read_error: {exc}")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return RoadmapLoadDiag({}, f"yaml_parse_error: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        return RoadmapLoadDiag({}, f"parse_error: {exc}")
    if data is None:
        return RoadmapLoadDiag({}, "null_root")
    if not isinstance(data, dict):
        return RoadmapLoadDiag({}, f"non_dict_root:{type(data).__name__}")
    if not data:
        return RoadmapLoadDiag({}, "empty_mapping")
    return RoadmapLoadDiag(data, None)


def load_roadmap(path: Path | None = None) -> dict[str, Any]:
    """Load roadmap YAML; return empty dict if missing or invalid.

    For differentiated empty-file UX in the dashboard, use ``load_roadmap_diag``.
    """
    return load_roadmap_diag(path).data


def _empty_roadmap_panel_body(path: Path, reason: str | None) -> str:
    """Human-facing copy when ``data`` is empty (missing, parse error, wrong shape)."""
    r = reason or "unknown"
    loc = escape(str(path))
    if r == "missing":
        return f"[yellow]Roadmap file not found:[/] {loc}"
    if r.startswith("read_error:"):
        return f"[yellow]Could not read roadmap file[/] {loc}\n[dim]{escape(r)}[/]"
    if r.startswith("yaml_parse_error:") or r.startswith("parse_error:"):
        return f"[yellow]Invalid YAML[/] {loc}\n[dim]{escape(r)}[/]"
    if r.startswith("non_dict_root:"):
        return f"[yellow]Roadmap root must be a mapping[/] {loc}\n[dim]{escape(r)}[/]"
    if r == "null_root":
        return f"[yellow]Roadmap YAML is null or empty[/] {loc}"
    if r == "empty_mapping":
        return f"[yellow]Roadmap is an empty mapping[/] {loc}"
    return f"[yellow]No roadmap data[/] {loc}\n[dim]{escape(r)}[/]"


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


def _normalize_task_entries(
    raw: Any, *, block_label: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return dict tasks and human-readable warnings for invalid items."""
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [f"{block_label}: expected list, got {type(raw).__name__}"]
    valid: list[dict[str, Any]] = []
    warnings: list[str] = []
    for i, item in enumerate(raw):
        if isinstance(item, dict):
            valid.append(item)
        else:
            warnings.append(f"{block_label}[{i}]: expected mapping, got {type(item).__name__}")
    return valid, warnings


def _format_task_block(
    label: str,
    entries: list[dict[str, Any]],
    *,
    done: bool,
    schema_warnings: list[str],
) -> list[str]:
    lines: list[str] = []
    if not entries and not schema_warnings:
        return lines
    lines.append(f"[bold]{label}[/bold]")
    shown = schema_warnings[:MAX_SCHEMA_WARNINGS]
    for w in shown:
        lines.append(f"  [yellow]schema:[/] [dim]{escape(w)}[/]")
    extra = len(schema_warnings) - len(shown)
    if extra > 0:
        lines.append(f"  [dim]... and {extra} more schema warning(s)[/]")
    for task in entries:
        if not isinstance(task, dict):
            lines.append(
                "  [yellow]schema:[/] [dim]"
                f"{escape(f'task entry: expected mapping, got {type(task).__name__}')}"
                "[/]"
            )
            continue
        tid = escape(str(task.get("id", "?")))
        title = escape(str(task.get("title", "")))
        mark = _task_done_icon(done)
        lines.append(f"  {mark} [cyan]{tid}[/]  {title}")
        for key in ("note", "deferred_from"):
            val = task.get(key)
            if val:
                lines.append(f"      [dim]{escape(str(val))}[/]")
    return lines


def build_version_body(version: Any) -> str:
    """Build markdown-rich body text for one roadmap version block."""
    if not isinstance(version, dict):
        return (
            "[yellow]Invalid version block:[/] "
            f"expected mapping, got [dim]{escape(type(version).__name__)}[/]"
        )
    st = version.get("status", "?")
    lines: list[str] = []

    lines.append(f"[{_status_style(st)}]● {escape(str(st).upper())}[/]")
    ps = version.get("phase_scope")
    if ps is not None:
        lines.append(f"[dim]Phases:[/] {escape(str(ps))}")
    lines.append("")
    goal = version.get("goal", "")
    if goal:
        lines.append(escape(str(goal)))

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
        lines.append(f"[dim italic]{escape(str(note))}[/]")

    completed, cw = _normalize_task_entries(
        version.get("completed_tasks"), block_label="completed_tasks"
    )
    pending, pw = _normalize_task_entries(version.get("tasks"), block_label="tasks")

    if completed or pending or cw or pw:
        lines.append("")

    lines.extend(_format_task_block("Delivered", completed, done=True, schema_warnings=cw))
    if (completed or cw) and (pending or pw):
        lines.append("")
    lines.extend(_format_task_block("Upcoming", pending, done=False, schema_warnings=pw))

    return "\n".join(lines)


def render_header(data: Any) -> Panel:
    """Top banner: active_version + schema hint."""
    if not isinstance(data, dict):
        return Panel(
            f"[yellow]Invalid roadmap root:[/] expected mapping, got {type(data).__name__}",
            title="Roadmap error",
            border_style="yellow",
            box=box.HEAVY,
        )
    av = data.get("active_version", "?")
    header = Text()
    header.append("ROADMAP ", style="bold white")
    header.append("·  active_version ", style="dim")
    header.append(str(av), style="bold cyan")
    header.append("  ·  D48 + D53", style="dim")
    return Panel(header, box=box.HEAVY)


def render_version_panel(version: Any) -> Panel:
    """Single bordered panel for one `versions[]` entry."""
    if not isinstance(version, dict):
        return Panel(
            f"[yellow]Invalid version:[/] expected mapping, got {escape(type(version).__name__)}",
            title="Version schema",
            border_style="yellow",
            box=box.ROUNDED,
        )
    vid = version.get("id", "?")
    st = version.get("status", "?")
    body = build_version_body(version)
    ss = _status_style(st)
    title_bar = f"[bold]{escape(str(vid))}[/]  [{ss}]{escape(str(st))}[/{ss}]"
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
    diag = load_roadmap_diag(path)
    data = diag.data
    out = console or Console(width=100)

    out.print()
    if not data:
        out.print(
            Panel(
                _empty_roadmap_panel_body(path, diag.empty_reason),
                title="Roadmap",
                box=box.HEAVY,
            )
        )
        return

    out.print(render_header(data))
    out.print()

    versions_raw = data.get("versions")
    if versions_raw is None:
        versions_iter: list[Any] = []
    elif not isinstance(versions_raw, list):
        out.print(
            Panel(
                f"[red]Invalid `versions`:[/] expected list, got {type(versions_raw).__name__}",
                title="Roadmap error",
                border_style="red",
                box=box.HEAVY,
            )
        )
        out.print(Panel(FOOTER, box=box.MINIMAL))
        out.print()
        return
    else:
        versions_iter = versions_raw

    for i, v in enumerate(versions_iter):
        if not isinstance(v, dict):
            out.print(
                Panel(
                    f"[yellow]Skipping versions[{i}]:[/] expected mapping, got {type(v).__name__!r}",
                    title="Version schema",
                    border_style="yellow",
                    box=box.ROUNDED,
                )
            )
            out.print()
            continue
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
