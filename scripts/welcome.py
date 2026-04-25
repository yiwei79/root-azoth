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
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from planning_bank_surfacing import format_planning_bank_plain
from planning_bank_surfacing import format_planning_bank_rich
from planning_bank_surfacing import load_planning_bank_summaries
from run_ledger import load_active_run as load_active_ledger_run
from run_ledger import load_resumable_sessions
from session_gate import active_session_gate, normalized_session_mode
from session_continuity import governance_mode as normalized_governance_mode
from session_continuity import selected_pipeline_command
from yaml_helpers import safe_load_yaml_path

ROOT = Path(__file__).resolve().parent.parent
console = Console()


# ── Data loaders ─────────────────────────────────────────────────────────────


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file, returning empty dict if missing or unparseable."""
    if not path.exists():
        return {}
    try:
        return safe_load_yaml_path(path) or {}
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

_DONE_STATUSES: set[str] = {"complete", "completed", "deferred"}
_TOP_BACKLOG_EXCLUDED_STATUSES: set[str] = _DONE_STATUSES | {"active"}


def filter_unblocked_items(
    items: list[dict[str, Any]], complete_ids: set[str]
) -> list[dict[str, Any]]:
    """Return non-complete backlog items whose blocked_by deps are all complete.

    Result is sorted by priority ascending (lower number = higher priority).
    """
    result = []
    for item in items:
        if item.get("status") in _TOP_BACKLOG_EXCLUDED_STATUSES:
            continue
        blocked_by = item.get("blocked_by") or []
        if all(bid in complete_ids for bid in blocked_by):
            result.append(item)
    return sorted(result, key=lambda x: x.get("priority", 99))


def is_governed_scope(scope: dict[str, Any]) -> bool:
    """True when scope-gate indicates M1 or governed delivery (matches PreToolUse hook)."""
    return normalized_governance_mode(scope) == "governed"


def pipeline_label(
    record: dict[str, Any],
    pipeline_gate: dict[str, Any] | None = None,
) -> str:
    """Return the normalized pipeline/governance label for operator-facing renders."""
    candidate = selected_pipeline_command(record, pipeline_gate)
    if candidate:
        return candidate
    for field_name in ("governance_mode", "delivery_pipeline", "pipeline"):
        value = str(record.get(field_name) or "").strip()
        if value:
            return value
    return "?"


def write_claim_status_line(scope: dict[str, Any] | None, claim: dict[str, Any] | None) -> str:
    """Return a single-line write-claim status string for the System Health panel.

    Returns a string containing 'HELD' when the claim is active and matches the scope session.
    Returns a string containing 'none' when no claim is present.
    """
    if claim is None:
        return "Write claim: none"
    holder = claim.get("session_id", "")
    scope_session = str((scope or {}).get("session_id") or "")
    if scope_session and holder == scope_session:
        expires = claim.get("expires_at", "?")
        return f"Write claim: HELD by '{holder}'  expires {expires}"
    expires = claim.get("expires_at", "?")
    return f"Write claim: held by '{holder}' (foreign)  expires {expires}"


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


def format_gate_ttl(
    gate: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Format remaining TTL for a scope-gate or pipeline-gate.

    Returns one of:
    - "EXPIRED" when expires_at is in the past
    - "12h 34m remaining" style human-readable delta
    - "" (empty string) when expires_at is absent or unparseable

    The *now* parameter supports clock injection for deterministic tests.
    """
    raw = gate.get("expires_at")
    if not raw:
        return ""
    exp = _parse_expires_at_utc(str(raw))
    if exp is None:
        return ""
    if now is None:
        now = utc_now()
    delta = exp - now
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "EXPIRED"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m remaining"
    if minutes > 0:
        return f"{minutes}m remaining"
    return "<1m remaining"


def resolve_strip_phase(azoth: dict[str, Any], roadmap: dict[str, Any]) -> int:
    """Index for the 1–8 Kernel→Next strip. Milestone mode uses lifecycle_phase, not local phase."""
    if azoth.get("milestone"):
        raw_lp = azoth.get("lifecycle_phase")
        if raw_lp is not None:
            try:
                return int(raw_lp)
            except (ValueError, TypeError):
                pass
        rlc = roadmap.get("lifecycle_phase")
        if rlc is not None:
            try:
                return int(rlc)
            except (ValueError, TypeError):
                pass
        return 0
    raw = azoth.get("phase")
    try:
        return int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0


def header_phase_label(azoth: dict[str, Any], phase_display: Any) -> str:
    m = azoth.get("milestone")
    if m:
        return f"Phase {phase_display} · {m}"
    return f"Phase {phase_display}"


def is_pipeline_gate_valid(
    scope: dict[str, Any],
    pg: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    """True when pipeline-gate.json satisfies mechanical enforcement for this scope."""
    if not pg.get("approved"):
        return False
    sid = scope.get("session_id", "")
    if not sid or pg.get("session_id") != sid:
        return False
    exp = _parse_expires_at_utc(str(pg.get("expires_at", "")))
    if exp is None:
        return False
    if now is None:
        now = utc_now()
    return now < exp


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


def continuity_status(
    scope: dict[str, Any],
    session_state: dict[str, Any],
    sessions: list[dict[str, Any]],
    *,
    complete_ids: set[str] | None = None,
) -> tuple[str, str] | None:
    """Report whether registry, active scope, and session-state mirror agree."""
    scope_session_id = (
        str(scope.get("session_id") or "") if is_scope_active(scope, complete_ids) else ""
    )
    if not scope_session_id:
        return None
    mirror_session_id = (
        str(session_state.get("session_id") or "")
        if str(session_state.get("state") or "").strip() == "active"
        else ""
    )
    registry_session = next(
        (entry for entry in sessions if entry.get("session_id") == scope_session_id), None
    )

    if scope_session_id and registry_session and mirror_session_id == scope_session_id:
        return ("OK", scope_session_id)
    detail = f"scope={scope_session_id or '-'} / mirror={mirror_session_id or '-'}"
    return ("MISMATCH", detail)


def resume_menu_state(
    scope: dict[str, Any],
    session_state: dict[str, Any],
    open_sessions: list[dict[str, Any]],
    *,
    complete_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build the primary and alternate resume actions for dashboard rendering.

    The resumable session registry is authoritative. A parked session-state mirror is
    only used as the primary resume target when the same session still exists in the
    resumable registry, which prevents stale closed/finalized mirrors from surfacing
    as resumable work.
    """
    scope_session_id = (
        str(scope.get("session_id") or "") if is_scope_active(scope, complete_ids) else ""
    )
    resumable_entries = [
        entry
        for entry in open_sessions
        if isinstance(entry, dict) and str(entry.get("session_id") or "").strip()
    ]
    parked_session_id = (
        str(session_state.get("session_id") or "")
        if str(session_state.get("state") or "").strip() == "parked"
        else ""
    )

    primary_kind: str | None = None
    primary_goal = ""
    alternate_entries = resumable_entries

    if scope_session_id:
        primary_kind = "scope"
        primary_goal = str(scope.get("goal") or "")
        alternate_entries = [
            entry
            for entry in resumable_entries
            if str(entry.get("session_id") or "") != scope_session_id
        ]
    else:
        parked_entry = next(
            (
                entry
                for entry in resumable_entries
                if str(entry.get("session_id") or "") == parked_session_id
            ),
            None,
        )
        if parked_entry is not None:
            primary_kind = "parked"
            primary_goal = str(
                session_state.get("approved_scope")
                or session_state.get("active_task")
                or parked_entry.get("goal")
                or ""
            )
            alternate_entries = [
                entry
                for entry in resumable_entries
                if str(entry.get("session_id") or "") != parked_session_id
            ]

    return {
        "primary_kind": primary_kind,
        "primary_goal": primary_goal,
        "alternate_entries": alternate_entries,
    }


# ── Dashboard data + renderers ────────────────────────────────────────────────


_INITIATIVE_PRIO: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def _slice_is_actionable(slice_item: dict[str, Any]) -> bool:
    status = str(slice_item.get("status") or "").strip().casefold()
    role = str(slice_item.get("role") or "").strip().casefold()
    return status not in {"complete", "completed"} and role != "historical"


def _initiative_has_actionable_open_slice(initiative: dict[str, Any]) -> bool:
    slices = initiative.get("slices")
    if isinstance(slices, list) and slices:
        return any(isinstance(item, dict) and _slice_is_actionable(item) for item in slices)
    return str(initiative.get("status") or "").strip().casefold() not in {"complete", "completed"}


def load_active_run(root: Path) -> dict[str, Any] | None:
    """Return the last active entry from run-ledger.local.yaml, or None if absent."""
    return load_active_ledger_run(root)


def gather_unphased_initiatives(roadmap_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return actionable phase-null initiatives sorted by priority (high→medium→low)."""
    raw = roadmap_data.get("initiatives")
    if not raw or not isinstance(raw, list):
        return []
    result = [
        item
        for item in raw
        if isinstance(item, dict)
        and item.get("phase") is None
        and _initiative_has_actionable_open_slice(item)
    ]
    return sorted(result, key=lambda x: _INITIATIVE_PRIO.get(str(x.get("priority", "")), 9))


def gather_dashboard_state() -> dict[str, Any]:
    """Load all dashboard inputs; shared by Rich and plain renderers."""
    azoth = load_yaml(ROOT / "azoth.yaml")
    roadmap_data = load_yaml(ROOT / ".azoth" / "roadmap.yaml")
    backlog_data = load_yaml(ROOT / ".azoth" / "backlog.yaml")
    scope = load_json(ROOT / ".azoth" / "scope-gate.json")
    session_gate = active_session_gate(ROOT)
    pipeline_gate = load_json(ROOT / ".azoth" / "pipeline-gate.json")
    session_state = load_yaml(ROOT / ".azoth" / "session-state.md")
    episodes = load_jsonl(ROOT / ".azoth" / "memory" / "episodes.jsonl")
    open_sessions = load_resumable_sessions(ROOT)

    repo, branch = git_info()
    now = utc_now()
    today = now.strftime("%Y-%m-%d")
    version = azoth.get("version", "?")
    phase = azoth.get("phase", "?")
    strip_phase = resolve_strip_phase(azoth, roadmap_data)
    phase_header = header_phase_label(azoth, phase)

    items = backlog_data.get("items", [])
    complete_ids = {item["id"] for item in items if item.get("status") in {"complete", "completed"}}
    top3 = filter_unblocked_items(items, complete_ids)[:3]
    unphased_initiatives = gather_unphased_initiatives(roadmap_data)
    planning_banks = load_planning_bank_summaries(ROOT)

    return {
        "azoth": azoth,
        "roadmap": roadmap_data,
        "backlog_data": backlog_data,
        "scope": scope,
        "session_gate": session_gate,
        "pipeline_gate": pipeline_gate,
        "session_state": session_state,
        "episodes": episodes,
        "repo": repo,
        "branch": branch,
        "now": now,
        "today": today,
        "version": version,
        "phase": phase,
        "strip_phase": strip_phase,
        "phase_header": phase_header,
        "items": items,
        "complete_ids": complete_ids,
        "top3": top3,
        "unphased_initiatives": unphased_initiatives,
        "planning_banks": planning_banks,
        "open_sessions": open_sessions,
        "continuity": continuity_status(
            scope,
            session_state,
            open_sessions,
            complete_ids=complete_ids,
        ),
        "run_ledger": load_active_run(ROOT),
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
    session_gate = state["session_gate"]
    pipeline_gate = state["pipeline_gate"]
    session_state = state["session_state"]
    episodes = state["episodes"]
    repo = state["repo"]
    branch = state["branch"]
    today = state["today"]
    version = state["version"]
    phase = state["phase"]
    strip_phase = int(state.get("strip_phase") or 0)
    phase_header = str(state.get("phase_header") or f"Phase {phase}")
    complete_ids = state["complete_ids"]
    top3 = state["top3"]
    planning_banks = state.get("planning_banks", {})
    open_sessions = state.get("open_sessions", [])
    continuity = state.get("continuity")
    now = state.get("now")
    resume_state = resume_menu_state(
        scope,
        session_state,
        open_sessions,
        complete_ids=complete_ids,
    )

    current_phase = strip_phase

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
    lines.append(f"  AZOTH  ·  v{version}  ·  {phase_header}  ·  {repo}  ·  {branch}  ·  {today}")
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
        (8, "Next"),
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
        scope_ttl = format_gate_ttl(scope, now=now)
        ttl_suffix = f"  [{scope_ttl}]" if scope_ttl else ""
        lines.append(f"  Scope: ACTIVE  ({session_id}){ttl_suffix}")
        goal = scope.get("goal", "")
        if goal:
            lines.append(f"    Goal: {goal}")
        if is_governed_scope(scope):
            pipeline_gate_ttl = format_gate_ttl(pipeline_gate, now=now)
            if is_pipeline_gate_valid(scope, pipeline_gate, now=now):
                pipe = pipeline_label(scope, pipeline_gate)
                pg_suffix = f"  [{pipeline_gate_ttl}]" if pipeline_gate_ttl else ""
                lines.append(f"    Pipeline gate: OK  ({pipe}){pg_suffix}")
            elif pipeline_gate_ttl == "EXPIRED":
                lines.append("    Pipeline gate: EXPIRED  (rerun Stage 0 to reopen)")
            else:
                lines.append(
                    "    Pipeline gate: OPEN  (Stage 0 of /deliver-full, /auto, or /deliver)"
                )
    elif scope.get("expires_at") and format_gate_ttl(scope, now=now) == "EXPIRED":
        lines.append("  Scope: EXPIRED  (run /next to open a new scope card)")
    else:
        lines.append("  Scope: NONE  (run /next to open a scope card)")
        if session_gate:
            session_mode = normalized_session_mode(session_gate)
            lines.append(
                f"  Session: ACTIVE  ({session_mode}, {session_gate.get('session_id', '?')})"
            )
            lines.append(f"    Goal: {session_gate.get('goal', '')}")

    if continuity:
        status, detail = continuity
        lines.append(f"  Continuity: {status}  ({detail})")

    if open_sessions:
        lines.append("")
        lines.append("  Sessions")
        mirror_session_id = str(session_state.get("session_id") or "")
        scope_session_id = (
            str(scope.get("session_id") or "") if is_scope_active(scope, complete_ids) else ""
        )
        for entry in open_sessions[:3]:
            session_id = str(entry.get("session_id") or "?")
            status = str(entry.get("status") or "?")
            ide = str(entry.get("ide") or "?")
            backlog_id = str(entry.get("backlog_id") or "?")
            markers: list[str] = []
            if session_id == scope_session_id:
                markers.append("scope")
            if session_id == mirror_session_id:
                markers.append("mirror")
            marker_text = f" [{'|'.join(markers)}]" if markers else ""
            lines.append(f"    {session_id}{marker_text}  ({status}, {ide})")
            lines.append(f"      {backlog_id} -> {(entry.get('next_action') or '')[:120]}")

    active_run = state.get("run_ledger")
    if active_run:
        run_id = active_run.get("run_id", "?")
        mode = active_run.get("mode", "?")
        next_action = (active_run.get("next_action") or "")[:120]
        lines.append(f"  \u25cf Active run  {run_id}  ({mode})  \u2192 {next_action}")

    lines.append("")
    lines.append("── Top Backlog (next unblocked) ──")
    if top3:
        for item in top3:
            iid = item.get("id", "?")
            title = item.get("title", "?")
            layer = item.get("target_layer", "?")
            pipeline = pipeline_label(item)
            status = item.get("status", "?")
            lines.append(f"  {iid}  [{status}]")
            lines.append(f"    {title}")
            lines.append(f"    {layer} · {pipeline}")
            lines.append("")
    else:
        planning_lines = format_planning_bank_plain(planning_banks)
        if planning_lines:
            lines.extend(planning_lines)
            lines.append("  No claimable backlog item is required before refining a planning bank.")
            lines.append("")
            return_to_backlog = True
        else:
            return_to_backlog = False
        ini_fallback = state.get("unphased_initiatives", [])[:3]
        if ini_fallback:
            if not return_to_backlog:
                lines.append("  No unblocked pending backlog items — unscheduled initiatives:")
            else:
                lines.append("  Also visible from roadmap initiatives:")
            lines.append("")
            for ini in ini_fallback:
                iid = ini.get("id", "?")
                title = ini.get("title", "?")
                prio = ini.get("priority", "?")
                lines.append(f"  {iid}  [priority: {prio}]")
                lines.append(f"    {title}")
                lines.append("")
        elif not planning_lines:
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
    if resume_state["primary_kind"] == "scope":
        goal_truncated = resume_state["primary_goal"][:72]
        lines.append(f"  resume   → continue approved scope: {goal_truncated}")
    elif resume_state["primary_kind"] == "parked":
        parked_goal = resume_state["primary_goal"][:72]
        lines.append(f"  resume   → /resume — reopen parked session: {parked_goal}")
    for entry in resume_state["alternate_entries"][:3]:
        session_id = str(entry.get("session_id") or "")
        if session_id:
            lines.append(f"  resume {session_id}   → /resume — reopen parked session directly")
    lines.append("  next     → /next — scope card for next priority task")
    lines.append("  intake   → /intake — process .azoth/inbox/")
    lines.append("  promote  → /promote — M2→M1 promotion review")
    lines.append("  eval     → /eval — quality gate")
    lines.append("  roadmap  → /roadmap — versioned roadmap dashboard (D48)")
    lines.append("  plan     → /plan — structured autonomy / planning")
    lines.append("  remember → /remember — quick M3 capture (no full closeout)")
    if session_gate and normalized_session_mode(session_gate) == "exploratory" and not is_scope_active(
        scope, complete_ids
    ):
        lines.append("  closeout → /session-closeout — light closeout for exploratory session")
    else:
        lines.append("  closeout → /session-closeout — episodes W1–W4 + handoff capsule")
    lines.append(
        "  <goal>   → /start route — exploratory goals open a session; delivery goals escalate to /auto"
    )
    lines.append(
        "  codex    → primary: /skills or $azoth-resume / $azoth-next / $azoth-auto / $azoth-autonomous-auto; app slash list for enabled azoth-* skills; raw slash tokens remain compatibility fallback"
    )
    lines.append("")
    lines.append(sep)
    lines.append("  AZOTH session orientation (end)")
    lines.append("# AZOTH_SESSION_ORIENTATION_END")
    lines.append(sep)

    out = "\n".join(lines) + "\n"
    console.print(out, markup=False)


def render_dashboard() -> None:
    """Render the 5-panel Azoth session dashboard to the console."""
    state = gather_dashboard_state()
    azoth = state["azoth"]
    scope = state["scope"]
    session_gate = state["session_gate"]
    pipeline_gate = state["pipeline_gate"]
    session_state = state["session_state"]
    episodes = state["episodes"]
    repo = state["repo"]
    branch = state["branch"]
    today = state["today"]
    version = state["version"]
    phase = state["phase"]
    strip_phase = int(state.get("strip_phase") or 0)
    phase_header = str(state.get("phase_header") or f"Phase {phase}")
    complete_ids = state["complete_ids"]
    top3 = state["top3"]
    planning_banks = state.get("planning_banks", {})
    open_sessions = state.get("open_sessions", [])
    continuity = state.get("continuity")
    now = state.get("now")
    resume_state = resume_menu_state(
        scope,
        session_state,
        open_sessions,
        complete_ids=complete_ids,
    )

    header_text = Text(justify="center")
    header_text.append("AZOTH", style="bold white")
    header_text.append("  ·  ", style="dim white")
    header_text.append(f"v{version}", style="bold cyan")
    header_text.append("  ·  ", style="dim white")
    header_text.append(phase_header, style="bold yellow")
    header_text.append("  ·  ", style="dim white")
    header_text.append(repo, style="bold white")
    header_text.append("  ·  ", style="dim white")
    header_text.append(branch, style="bold green")
    header_text.append("  ·  ", style="dim white")
    header_text.append(today, style="dim white")
    header_panel = Panel(header_text, box=box.HEAVY)

    _phases = [
        (1, "Kernel"),
        (2, "Skills"),
        (3, "Agents"),
        (4, "Distribution"),
        (5, "Trust"),
        (6, "Meta"),
        (7, "Publish"),
        (8, "Next"),
    ]
    phase_parts = []
    for num, name in _phases:
        if num < strip_phase:
            phase_parts.append(f"[green][{num}]:check_mark: {name}[/green]")
        elif num == strip_phase:
            phase_parts.append(f"[bold yellow][{num}]:right_arrow: {name}[/bold yellow]")
        else:
            phase_parts.append(f"[dim][{num}]:white_circle: {name}[/dim]")
    phases_panel = Panel("  ".join(phase_parts), box=box.MINIMAL)

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

    if is_scope_active(scope, complete_ids):
        session_id = scope.get("session_id", "")
        scope_ttl = format_gate_ttl(scope, now=now)
        ttl_markup = f"  [dim]{scope_ttl}[/dim]" if scope_ttl else ""
        health_lines.append(
            f":green_circle: [green]Scope: ACTIVE[/green]  [dim]{session_id}[/dim]{ttl_markup}"
        )
        if is_governed_scope(scope):
            pipeline_gate_ttl = format_gate_ttl(pipeline_gate, now=now)
            if is_pipeline_gate_valid(scope, pipeline_gate, now=now):
                pipe = pipeline_label(scope, pipeline_gate)
                pg_markup = f"  [dim]{pipeline_gate_ttl}[/dim]" if pipeline_gate_ttl else ""
                health_lines.append(
                    f"  :green_circle: [green]Pipeline gate: OK[/green]  [dim]{pipe}[/dim]{pg_markup}"
                )
            elif pipeline_gate_ttl == "EXPIRED":
                health_lines.append(
                    "  :orange_circle: [yellow]Pipeline gate: EXPIRED[/yellow]  "
                    "[dim](rerun Stage 0 to reopen)[/dim]"
                )
            else:
                health_lines.append(
                    "  :red_circle: [red]Pipeline gate: OPEN[/red]  "
                    "[dim](Stage 0 of /deliver-full, /auto, or /deliver)[/dim]"
                )
    elif scope.get("expires_at") and format_gate_ttl(scope, now=now) == "EXPIRED":
        health_lines.append(
            ":orange_circle: [yellow]Scope: EXPIRED[/yellow]  [dim](run /next to open)[/dim]"
        )
    else:
        health_lines.append(":red_circle: [red]Scope: NONE[/red]  [dim](run /next to open)[/dim]")
        if session_gate:
            session_mode = normalized_session_mode(session_gate)
            health_lines.append(
                f":speech_balloon: [cyan]Session: ACTIVE[/cyan]  "
                f"[dim]{session_mode}, {session_gate.get('session_id', '?')}[/dim]"
            )

    if continuity:
        status, detail = continuity
        style = "green" if status == "OK" else "yellow"
        health_lines.append(f":link: [{style}]Continuity: {status}[/{style}]  [dim]{detail}[/dim]")

    if open_sessions:
        health_lines.append("")
        health_lines.append("[bold]Sessions[/bold]")
        mirror_session_id = str(session_state.get("session_id") or "")
        scope_session_id = (
            str(scope.get("session_id") or "") if is_scope_active(scope, complete_ids) else ""
        )
        for entry in open_sessions[:3]:
            session_id = str(entry.get("session_id") or "?")
            status = str(entry.get("status") or "?")
            ide = str(entry.get("ide") or "?")
            backlog_id = str(entry.get("backlog_id") or "?")
            markers: list[str] = []
            if session_id == scope_session_id:
                markers.append("scope")
            if session_id == mirror_session_id:
                markers.append("mirror")
            marker_text = f" [{'|'.join(markers)}]" if markers else ""
            health_lines.append(
                f"  [bold cyan]{session_id}[/bold cyan]{marker_text}"
                f"  [dim]({status}, {ide}, {backlog_id})[/dim]"
            )

    active_run = state.get("run_ledger")
    if active_run:
        run_id = active_run.get("run_id", "?")
        mode = active_run.get("mode", "?")
        next_action = (active_run.get("next_action") or "")[:120]
        health_lines.append(
            f":blue_circle: [bold]Active run[/bold]  [cyan]{run_id}[/cyan]"
            f"  [dim]({mode})[/dim]  \u2192 {next_action}"
        )

    health_panel = Panel(
        "\n".join(health_lines), title="[bold]System Health[/bold]", box=box.ROUNDED
    )

    backlog_lines: list[str] = []
    for item in top3:
        iid = item.get("id", "?")
        title = item.get("title", "?")
        layer = item.get("target_layer", "?")
        pipeline = pipeline_label(item)
        status = item.get("status", "?")
        status_col = "yellow" if status == "active" else "dim"
        backlog_lines.append(
            f"[bold cyan]{iid}[/bold cyan]  [{status_col}]{status}[/{status_col}]\n"
            f"  {title}\n"
            f"  [dim]{layer} · {pipeline}[/dim]"
        )
    if not top3:
        planning_body = format_planning_bank_rich(planning_banks)
        ini_fallback = state.get("unphased_initiatives", [])[:3]
        if planning_body:
            backlog_lines.append(planning_body)
        if ini_fallback:
            for ini in ini_fallback:
                iid = ini.get("id", "?")
                title = ini.get("title", "?")
                prio = ini.get("priority", "?")
                prio_col = {"high": "red", "medium": "yellow", "low": "dim"}.get(str(prio), "dim")
                backlog_lines.append(
                    f"[bold cyan]{iid}[/bold cyan]  [{prio_col}]{prio}[/{prio_col}]\n"
                    f"  {title}\n"
                    f"  [dim]initiative · unscheduled[/dim]"
                )
        elif not planning_body:
            backlog_lines.append("[green]:party_popper: All backlog items complete![/green]")
    backlog_panel = Panel(
        "\n\n".join(backlog_lines), title="[bold]Top Backlog[/bold]", box=box.ROUNDED
    )

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

    options_lines: list[str] = []
    if resume_state["primary_kind"] == "scope":
        goal_truncated = resume_state["primary_goal"][:60]
        options_lines.append(
            f"[bold green]:right_arrow: resume[/bold green]"
            f"   Continue: [italic]{goal_truncated}[/italic]"
        )
        options_lines.append("")
    elif resume_state["primary_kind"] == "parked":
        parked_goal = resume_state["primary_goal"][:60]
        options_lines.append(
            f"[bold green]:right_arrow: resume[/bold green]"
            f"   Reopen parked session: [italic]{parked_goal}[/italic]"
        )
        options_lines.append("")
    for entry in resume_state["alternate_entries"][:3]:
        session_id = str(entry.get("session_id") or "")
        if session_id:
            options_lines.append(
                f"[bold cyan]resume {session_id}[/bold cyan]"
                "   :right_arrow: /resume — reopen parked session directly"
            )
    options_lines += [
        "[bold cyan]next[/bold cyan]     :right_arrow: /next — open scope card for next priority task",
        "[bold cyan]intake[/bold cyan]   :right_arrow: /intake — process queued insights from inbox",
        "[bold cyan]promote[/bold cyan]  :right_arrow: /promote — review M2:right_arrow:M1 promotion candidates",
        "[bold cyan]eval[/bold cyan]     :right_arrow: /eval — run quality gate on current work",
        "[bold cyan]roadmap[/bold cyan]  :right_arrow: /roadmap — versioned roadmap dashboard (D48)",
        "[bold cyan]plan[/bold cyan]     :right_arrow: /plan — structured autonomy / planning",
        "[bold cyan]remember[/bold cyan] :right_arrow: /remember — quick M3 capture (not full closeout)",
        (
            "[bold cyan]closeout[/bold cyan] :right_arrow: /session-closeout — light closeout for exploratory session"
            if session_gate
            and normalized_session_mode(session_gate) == "exploratory"
            and not is_scope_active(scope, complete_ids)
            else "[bold cyan]closeout[/bold cyan] :right_arrow: /session-closeout — W1–W4 + session handoff"
        ),
        "[bold cyan]<goal>[/bold cyan]   :right_arrow: /start route — exploratory goals open a session; delivery goals escalate to /auto",
        "[bold magenta]codex[/bold magenta]    :right_arrow: primary: /skills or $azoth-resume / $azoth-next / $azoth-auto / $azoth-autonomous-auto; app slash list for enabled azoth-* skills; raw slash tokens remain compatibility fallback",
    ]
    start_panel = Panel("\n".join(options_lines), title="[bold]START[/bold]", box=box.ROUNDED)

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
