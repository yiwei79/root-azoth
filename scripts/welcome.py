#!/usr/bin/env python3
"""
welcome.py — Azoth session welcome dashboard.

Renders a Rich-based 5-panel cockpit for session orientation.
Usage: python scripts/welcome.py
"""

from __future__ import annotations

import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
console = Console()


# ── Data loaders ─────────────────────────────────────────────────────────────


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file, returning empty dict if missing or unparseable."""
    if not path.exists():
        return {}
    try:
        with path.open() as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON file, returning empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file, silently skipping malformed lines."""
    if not path.exists():
        return []
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


# ── Pure business-logic helpers (testable) ───────────────────────────────────


def filter_unblocked_items(
    items: list[dict[str, Any]], complete_ids: set[str]
) -> list[dict[str, Any]]:
    """Return non-complete backlog items whose blocked_by deps are all complete.

    Result is sorted by priority ascending (lower number = higher priority).
    """
    result = []
    for item in items:
        if item.get("status") == "complete":
            continue
        blocked_by = item.get("blocked_by") or []
        if all(bid in complete_ids for bid in blocked_by):
            result.append(item)
    return sorted(result, key=lambda x: x.get("priority", 99))


def is_scope_active(
    scope: dict[str, Any], complete_ids: set[str] | None = None
) -> bool:
    """Return True if the scope gate is approved, unexpired, and not already complete.

    If complete_ids is provided, the gate is treated as inactive when the goal's
    referenced backlog item (e.g. "BL-007: ...") appears in the completed set.
    This prevents a stale gate from surfacing a "resume" option for finished work.
    """
    if not scope.get("approved"):
        return False
    expires_raw = scope.get("expires_at") or ""
    if not expires_raw:
        return False
    try:
        exp_dt = datetime.fromisoformat(str(expires_raw))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if exp_dt <= datetime.now(timezone.utc):
            return False
    except (ValueError, TypeError):
        return False
    if complete_ids:
        goal = scope.get("goal") or ""
        goal_id = goal.split(":")[0].strip()
        if goal_id in complete_ids:
            return False
    return True


def git_info() -> tuple[str, str]:
    """Return (repo_name, branch) by querying git, falling back gracefully."""
    try:
        branch = (
            subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=ROOT,
                check=False,
            ).stdout.strip()
            or "unknown"
        )
    except OSError:
        branch = "unknown"

    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        ).stdout.strip()
        repo = (
            url.rstrip("/").split("/")[-1].replace(".git", "") if url else ROOT.name
        )
    except OSError:
        repo = ROOT.name

    return repo, branch


# ── Dashboard renderer ────────────────────────────────────────────────────────


def render_dashboard() -> None:
    """Render the 5-panel Azoth session dashboard to the console."""
    azoth = load_yaml(ROOT / "azoth.yaml")
    backlog_data = load_yaml(ROOT / ".azoth" / "backlog.yaml")
    scope = load_json(ROOT / ".azoth" / "scope-gate.json")
    episodes = load_jsonl(ROOT / ".azoth" / "memory" / "episodes.jsonl")

    repo, branch = git_info()
    today = datetime.now().strftime("%Y-%m-%d")
    version = azoth.get("version", "?")
    phase = azoth.get("phase", "?")

    # ── Panel 1: Header (box.HEAVY) ──────────────────────────────────────────
    header_text = Text(justify="center")
    header_text.append("AZOTH", style="bold white")
    header_text.append("  ·  ", style="dim white")
    header_text.append(f"v{version}", style="bold cyan")
    header_text.append("  ·  ", style="dim white")
    header_text.append(f"Phase {phase}", style="bold yellow")
    header_text.append("  ·  ", style="dim white")
    header_text.append(repo, style="bold white")
    header_text.append("  ·  ", style="dim white")
    header_text.append(branch, style="bold green")
    header_text.append("  ·  ", style="dim white")
    header_text.append(today, style="dim white")
    header_panel = Panel(header_text, box=box.HEAVY)

    # ── Panel 2: Phases strip (box.MINIMAL) ──────────────────────────────────
    _phases = [
        (1, "Kernel"),
        (2, "Skills"),
        (3, "Agents"),
        (4, "Distribution"),
        (5, "Trust"),
        (6, "Meta"),
    ]
    try:
        current_phase = int(phase)
    except (ValueError, TypeError):
        current_phase = 0

    phase_parts = []
    for num, name in _phases:
        if num < current_phase:
            phase_parts.append(f"[green][{num}]:check_mark: {name}[/green]")
        elif num == current_phase:
            phase_parts.append(f"[bold yellow][{num}]:right_arrow: {name}[/bold yellow]")
        else:
            phase_parts.append(f"[dim][{num}]:white_circle: {name}[/dim]")
    phases_panel = Panel("  ".join(phase_parts), box=box.MINIMAL)

    # ── Panel 3L: System health (box.ROUNDED) ────────────────────────────────
    layers = azoth.get("layers", {})
    _layer_map = [
        ("molecule", "L0", "Kernel"),
        ("mineral", "L1", "Skills"),
        ("wave", "L2", "Agents"),
        ("current", "L3", "Pipelines"),
    ]
    health_lines: list[str] = []
    for key, label, name in _layer_map:
        layer = layers.get(key, {})
        status = layer.get("status", "unknown")
        icon = (
            ":white_check_mark:"
            if status == "complete"
            else (":construction:" if status == "active" else ":question_mark:")
        )
        detail_keys = [k for k in layer if k != "status"]
        details = "  ".join(f"[dim]{k}={layer[k]}[/dim]" for k in detail_keys)
        health_lines.append(f"{icon} [bold]{label}[/bold] {name}  {details}")

    patterns_path = ROOT / ".azoth" / "memory" / "patterns.yaml"
    patterns_data = load_yaml(patterns_path) if patterns_path.exists() else {}
    pattern_count = len(patterns_data.get("patterns", []))
    health_lines += [
        "",
        "[bold]Memory[/bold]",
        f"  M3 episodes : {len(episodes)}",
        f"  M2 patterns : {pattern_count}",
        "  M1 kernel   : active",
        "",
    ]

    # ── Backlog state (needed for both health panel and backlog panel) ────────
    items = backlog_data.get("items", [])
    complete_ids = {item["id"] for item in items if item.get("status") == "complete"}
    top3 = filter_unblocked_items(items, complete_ids)[:3]

    if is_scope_active(scope, complete_ids):
        session_id = scope.get("session_id", "")
        health_lines.append(
            f":green_circle: [green]Scope: ACTIVE[/green]  [dim]{session_id}[/dim]"
        )
    else:
        health_lines.append(
            ":red_circle: [red]Scope: NONE[/red]  [dim](run /next to open)[/dim]"
        )
    health_panel = Panel(
        "\n".join(health_lines), title="[bold]System Health[/bold]", box=box.ROUNDED
    )

    # ── Panel 3R: Top backlog (box.ROUNDED) ──────────────────────────────────

    backlog_lines: list[str] = []
    for item in top3:
        iid = item.get("id", "?")
        title = item.get("title", "?")
        layer = item.get("target_layer", "?")
        pipeline = item.get("delivery_pipeline", "?")
        status = item.get("status", "?")
        status_col = "yellow" if status == "active" else "dim"
        backlog_lines.append(
            f"[bold cyan]{iid}[/bold cyan]  [{status_col}]{status}[/{status_col}]\n"
            f"  {title}\n"
            f"  [dim]{layer} · {pipeline}[/dim]"
        )
    if not top3:
        backlog_lines.append(
            "[green]:party_popper: All backlog items complete![/green]"
        )
    backlog_panel = Panel(
        "\n\n".join(backlog_lines), title="[bold]Top Backlog[/bold]", box=box.ROUNDED
    )

    # ── Panel 4: Last session (box.ROUNDED) ──────────────────────────────────
    if episodes:
        ep = episodes[-1]
        ep_id = ep.get("id", "?")
        ts = (ep.get("timestamp") or "")[:10]
        goal = ep.get("goal", "?")
        summary = ep.get("summary", "")
        if len(summary) > 200:
            summary = summary[:197] + "..."
        tags = ", ".join(ep.get("tags", [])[:5])
        last_content = (
            f"[bold cyan]{ep_id}[/bold cyan]  [dim]{ts}[/dim]\n"
            f"[bold]{goal}[/bold]\n\n"
            f"{summary}\n\n"
            f"[dim]{tags}[/dim]"
        )
    else:
        last_content = "[dim]No episodes recorded yet.[/dim]"
    last_panel = Panel(
        last_content, title="[bold]Last Session[/bold]", box=box.ROUNDED
    )

    # ── Panel 5: START options (box.ROUNDED) ─────────────────────────────────
    options_lines: list[str] = []
    if is_scope_active(scope, complete_ids):
        goal_truncated = (scope.get("goal") or "")[:60]
        options_lines.append(
            f"[bold green]:right_arrow: resume[/bold green]"
            f"   Continue: [italic]{goal_truncated}[/italic]"
        )
        options_lines.append("")
    options_lines += [
        "[bold cyan]next[/bold cyan]     :right_arrow: /next — open scope card for next priority task",
        "[bold cyan]intake[/bold cyan]   :right_arrow: /intake — process queued insights from inbox",
        "[bold cyan]promote[/bold cyan]  :right_arrow: /promote — review M2:right_arrow:M1 promotion candidates",
        "[bold cyan]eval[/bold cyan]     :right_arrow: /eval — run quality gate on current work",
        "[bold cyan]<goal>[/bold cyan]   :right_arrow: /auto — launch auto-pipeline for custom goal",
    ]
    start_panel = Panel(
        "\n".join(options_lines), title="[bold]START[/bold]", box=box.ROUNDED
    )

    # ── Render all panels ─────────────────────────────────────────────────────
    console.print()
    console.print(header_panel)
    console.print(phases_panel)
    console.print(Columns([health_panel, backlog_panel], equal=True, expand=True))
    console.print(last_panel)
    console.print(start_panel)
    console.print()


if __name__ == "__main__":
    render_dashboard()
