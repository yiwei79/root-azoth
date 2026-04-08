#!/usr/bin/env python3
"""
welcome.py — Azoth session welcome dashboard.

Renders a Rich-based 5-panel cockpit for session orientation.
System Health includes pipeline gate status when scope-gate is governed (M1 / delivery_pipeline).

``--plain`` prints the same facts as structured UTF-8 text (no Rich markup). Use for
SessionStart hooks and any capture where ANSI/markup is lost — keeps the full dashboard
in model context instead of a thin summary.

Usage: python scripts/welcome.py [--plain]
"""

from __future__ import annotations

import argparse
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
        if item.get("status") in {"complete", "deferred"}:
            continue
        blocked_by = item.get("blocked_by") or []
        if all(bid in complete_ids for bid in blocked_by):
            result.append(item)
    return sorted(result, key=lambda x: x.get("priority", 99))


def is_governed_scope(scope: dict[str, Any]) -> bool:
    """True when scope-gate indicates M1 or governed delivery (matches PreToolUse hook)."""
    return scope.get("delivery_pipeline") == "governed" or scope.get("target_layer") == "M1"


def _parse_expires_at_utc(raw: str) -> datetime | None:
    """Parse ISO 8601 expires_at; normalize Z suffix for Python <3.11."""
    if not raw:
        return None
    try:
        s = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def is_pipeline_gate_valid(scope: dict[str, Any], pg: dict[str, Any]) -> bool:
    """True when pipeline-gate.json satisfies mechanical enforcement for this scope."""
    if not pg.get("approved"):
        return False
    sid = scope.get("session_id", "")
    if not sid or pg.get("session_id") != sid:
        return False
    exp = _parse_expires_at_utc(str(pg.get("expires_at", "")))
    if exp is None:
        return False
    return datetime.now(timezone.utc) < exp


def is_scope_active(scope: dict[str, Any], complete_ids: set[str] | None = None) -> bool:
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
    exp_dt = _parse_expires_at_utc(str(expires_raw))
    if exp_dt is None:
        return False
    if exp_dt <= datetime.now(timezone.utc):
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
        repo = url.rstrip("/").split("/")[-1].replace(".git", "") if url else ROOT.name
    except OSError:
        repo = ROOT.name

    return repo, branch


# ── Dashboard data + renderers ────────────────────────────────────────────────


def gather_dashboard_state() -> dict[str, Any]:
    """Load all dashboard inputs; shared by Rich and plain renderers."""
    azoth = load_yaml(ROOT / "azoth.yaml")
    backlog_data = load_yaml(ROOT / ".azoth" / "backlog.yaml")
    scope = load_json(ROOT / ".azoth" / "scope-gate.json")
    pipeline_gate = load_json(ROOT / ".azoth" / "pipeline-gate.json")
    episodes = load_jsonl(ROOT / ".azoth" / "memory" / "episodes.jsonl")

    repo, branch = git_info()
    today = datetime.now().strftime("%Y-%m-%d")
    version = azoth.get("version", "?")
    phase = azoth.get("phase", "?")

    items = backlog_data.get("items", [])
    complete_ids = {item["id"] for item in items if item.get("status") == "complete"}
    top3 = filter_unblocked_items(items, complete_ids)[:3]

    return {
        "azoth": azoth,
        "backlog_data": backlog_data,
        "scope": scope,
        "pipeline_gate": pipeline_gate,
        "episodes": episodes,
        "repo": repo,
        "branch": branch,
        "today": today,
        "version": version,
        "phase": phase,
        "items": items,
        "complete_ids": complete_ids,
        "top3": top3,
    }


def _wrap_plain(text: str, width: int, indent: str) -> list[str]:
    """Simple word-wrap for episode summary."""
    if not text:
        return [f"{indent}(no summary)"]
    words = text.split()
    lines_out: list[str] = []
    cur = indent
    for w in words:
        if len(cur) + len(w) + 1 > width and len(cur) > len(indent):
            lines_out.append(cur)
            cur = indent + w
        else:
            cur = cur + (" " if cur != indent else "") + w
    if cur.strip():
        lines_out.append(cur)
    return lines_out[:20]


def render_dashboard_plain(state: dict[str, Any]) -> None:
    """Structured plain text: same information density as Rich, no markup."""
    azoth = state["azoth"]
    scope = state["scope"]
    pipeline_gate = state["pipeline_gate"]
    episodes = state["episodes"]
    repo = state["repo"]
    branch = state["branch"]
    today = state["today"]
    version = state["version"]
    phase = state["phase"]
    complete_ids = state["complete_ids"]
    top3 = state["top3"]

    phase_num = phase
    try:
        current_phase = int(phase)
    except (ValueError, TypeError):
        current_phase = 0

    lines: list[str] = []
    lines.append("# AZOTH_SESSION_ORIENTATION_BEGIN")
    lines.append(
        "# Claude Code: SessionStart injects this block; .azoth/session-orientation.txt "
        "mirrors it. Prefer relying on injection (token-efficient). Read+paste the file "
        "only when the user asks for verbatim/full orientation in chat (see CLAUDE.md rule 9)."
    )
    lines.append("")
    sep = "═" * 72
    lines.append(sep)
    lines.append(
        f"  AZOTH  ·  v{version}  ·  Phase {phase_num}  ·  {repo}  ·  {branch}  ·  {today}"
    )
    lines.append("  (plain layout — full orientation; Rich panels: run without --plain)")
    lines.append(sep)
    lines.append("")

    _phases = [
        (1, "Kernel"),
        (2, "Skills"),
        (3, "Agents"),
        (4, "Distribution"),
        (5, "Trust"),
        (6, "Meta"),
        (7, "Publish"),
    ]
    pl: list[str] = []
    for num, name in _phases:
        if num < current_phase:
            pl.append(f"[{num}]✓ {name}")
        elif num == current_phase:
            pl.append(f"[{num}]→ {name}  (current)")
        else:
            pl.append(f"[{num}]○ {name}")
    lines.append("Phases:  " + "   ".join(pl))
    lines.append("")

    layers = azoth.get("layers", {})
    _layer_map = [
        ("molecule", "L0", "Kernel"),
        ("mineral", "L1", "Skills"),
        ("wave", "L2", "Agents"),
        ("current", "L3", "Pipelines"),
    ]
    lines.append("── System Health ──")
    for key, label, name in _layer_map:
        layer = layers.get(key, {})
        status = layer.get("status", "unknown")
        detail_keys = [k for k in layer if k != "status"]
        details = "  ".join(f"{k}={layer[k]}" for k in detail_keys)
        icon = "✓" if status == "complete" else ("…" if status == "active" else "?")
        lines.append(f"  {icon} {label} {name}  ({status})  {details}")

    patterns_path = ROOT / ".azoth" / "memory" / "patterns.yaml"
    patterns_data = load_yaml(patterns_path) if patterns_path.exists() else {}
    pattern_count = len(patterns_data.get("patterns", []))
    lines.append("")
    lines.append("  Memory")
    lines.append(f"    M3 episodes : {len(episodes)}")
    lines.append(f"    M2 patterns : {pattern_count}")
    lines.append("    M1 kernel   : active")
    lines.append("")

    if is_scope_active(scope, complete_ids):
        session_id = scope.get("session_id", "")
        lines.append(f"  Scope: ACTIVE  ({session_id})")
        goal = scope.get("goal", "")
        if goal:
            lines.append(f"    Goal: {goal}")
        if is_governed_scope(scope):
            if is_pipeline_gate_valid(scope, pipeline_gate):
                pipe = pipeline_gate.get("pipeline", "?")
                lines.append(f"    Pipeline gate: OK  ({pipe})")
            else:
                lines.append(
                    "    Pipeline gate: OPEN  (Stage 0 of /deliver-full, /auto, or /deliver)"
                )
    else:
        lines.append("  Scope: NONE  (run /next to open a scope card)")

    lines.append("")
    lines.append("── Top Backlog (next unblocked) ──")
    if top3:
        for item in top3:
            iid = item.get("id", "?")
            title = item.get("title", "?")
            layer = item.get("target_layer", "?")
            pipeline = item.get("delivery_pipeline", "?")
            status = item.get("status", "?")
            lines.append(f"  {iid}  [{status}]")
            lines.append(f"    {title}")
            lines.append(f"    {layer} · {pipeline}")
            lines.append("")
    else:
        lines.append("  (all backlog items complete)")
        lines.append("")

    lines.append("── Last Session (M3) ──")
    if episodes:
        ep = episodes[-1]
        ep_id = ep.get("id", "?")
        ts = (ep.get("timestamp") or "")[:10]
        goal = ep.get("goal", "?")
        summary = ep.get("summary", "")
        tags = ", ".join(ep.get("tags", [])[:8])
        lines.append(f"  {ep_id}  {ts}")
        lines.append(f"  Goal: {goal}")
        for chunk in _wrap_plain(summary, width=68, indent="    "):
            lines.append(chunk)
        if tags:
            lines.append(f"  Tags: {tags}")
    else:
        lines.append("  No episodes recorded yet.")
    lines.append("")

    lines.append("── START (what to type) ──")
    if is_scope_active(scope, complete_ids):
        goal_truncated = (scope.get("goal") or "")[:72]
        lines.append(f"  resume   → continue approved scope: {goal_truncated}")
    lines.append("  next     → /next — scope card for next priority task")
    lines.append("  intake   → /intake — process .azoth/inbox/")
    lines.append("  promote  → /promote — M2→M1 promotion review")
    lines.append("  eval     → /eval — quality gate")
    lines.append("  <goal>   → /auto — auto-pipeline for a custom goal")
    lines.append("")
    lines.append(sep)
    lines.append("  AZOTH session orientation (end)")
    lines.append("# AZOTH_SESSION_ORIENTATION_END")
    lines.append(sep)

    out = "\n".join(lines) + "\n"
    console.print(out)


def render_dashboard() -> None:
    """Render the 5-panel Azoth session dashboard to the console."""
    state = gather_dashboard_state()
    azoth = state["azoth"]
    scope = state["scope"]
    pipeline_gate = state["pipeline_gate"]
    episodes = state["episodes"]
    repo = state["repo"]
    branch = state["branch"]
    today = state["today"]
    version = state["version"]
    phase = state["phase"]
    complete_ids = state["complete_ids"]
    top3 = state["top3"]

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
        (7, "Publish"),
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

    # Backlog / top3 already computed in gather_dashboard_state()

    if is_scope_active(scope, complete_ids):
        session_id = scope.get("session_id", "")
        health_lines.append(f":green_circle: [green]Scope: ACTIVE[/green]  [dim]{session_id}[/dim]")
        if is_governed_scope(scope):
            if is_pipeline_gate_valid(scope, pipeline_gate):
                pipe = pipeline_gate.get("pipeline", "?")
                health_lines.append(
                    f"  :green_circle: [green]Pipeline gate: OK[/green]  [dim]{pipe}[/dim]"
                )
            else:
                health_lines.append(
                    "  :red_circle: [red]Pipeline gate: OPEN[/red]  "
                    "[dim](Stage 0 of /deliver-full, /auto, or /deliver)[/dim]"
                )
    else:
        health_lines.append(":red_circle: [red]Scope: NONE[/red]  [dim](run /next to open)[/dim]")
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
        backlog_lines.append("[green]:party_popper: All backlog items complete![/green]")
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
    last_panel = Panel(last_content, title="[bold]Last Session[/bold]", box=box.ROUNDED)

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
    start_panel = Panel("\n".join(options_lines), title="[bold]START[/bold]", box=box.ROUNDED)

    # ── Render all panels ─────────────────────────────────────────────────────
    console.print()
    console.print(header_panel)
    console.print(phases_panel)
    console.print(Columns([health_panel, backlog_panel], equal=True, expand=True))
    console.print(last_panel)
    console.print(start_panel)
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Azoth session welcome dashboard.")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Structured UTF-8 text (no Rich). Use for SessionStart hooks so full "
        "orientation survives in model context.",
    )
    args = parser.parse_args()
    if args.plain:
        render_dashboard_plain(gather_dashboard_state())
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
