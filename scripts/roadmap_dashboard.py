#!/usr/bin/env python3
"""
roadmap_dashboard.py — Rich roadmap cockpit (D48 versioned roadmap).

Reads `.azoth/roadmap.yaml` and prints one panel per roadmap version with
status, phase scope, goals, notes, and task lists (completed vs pending).

Usage:
  python scripts/roadmap_dashboard.py
  python scripts/roadmap_dashboard.py --roadmap /path/to/roadmap.yaml
  python scripts/roadmap_dashboard.py --theme E
  python scripts/roadmap_dashboard.py --track autonomous-quality
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from planning_bank_surfacing import load_planning_bank_summaries
from planning_bank_surfacing import render_planning_bank_panel
from yaml_helpers import safe_load_yaml, safe_load_yaml_path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"
DEFAULT_BACKLOG = ROOT / ".azoth" / "backlog.yaml"

FOOTER = (
    "[dim]Canonical roadmap data: `versions[]` (D48). The legacy top-level `tasks:` "
    "block is retained for older tooling; prefer versioned blocks for planning.[/]"
)

MAX_SCHEMA_WARNINGS = 25
ROADMAP_REF_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.]*-[A-Za-z0-9][A-Za-z0-9.-]*")
FILTERED_REF_PLACEHOLDER = "other-slice work"


class RoadmapLoadDiag(NamedTuple):
    """Result of loading roadmap YAML: data (possibly empty) and why it is empty."""

    data: dict[str, Any]
    empty_reason: str | None  # None iff data is non-empty; else diagnostic tag/message


def _normalize_str_list(raw: Any) -> list[str]:
    """Normalize a scalar-or-list field into a list of non-empty strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        items = [raw]
    values: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _unique_folded(values: list[str]) -> list[str]:
    """Deduplicate while preserving first-seen casing/order."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _initiative_dimension_values(initiative: dict[str, Any], key: str) -> list[str]:
    """Return normalized initiative dimension values, falling back to legacy top-level fields."""
    values: list[str] = []
    if key == "themes":
        values.extend(_normalize_str_list(initiative.get("theme")))
    dims = initiative.get("dimensions")
    if isinstance(dims, dict):
        values.extend(_normalize_str_list(dims.get(key)))
    return _unique_folded(values)


def initiative_matches_filters(
    initiative: dict[str, Any],
    *,
    theme: str | None = None,
    track: str | None = None,
) -> bool:
    """True when an initiative matches the requested cross-section filters."""
    if not isinstance(initiative, dict):
        return False
    if theme:
        themes = {value.casefold() for value in _initiative_dimension_values(initiative, "themes")}
        if theme.casefold() not in themes:
            return False
    if track:
        tracks = {value.casefold() for value in _initiative_dimension_values(initiative, "tracks")}
        if track.casefold() not in tracks:
            return False
    return True


def _task_refs_for_initiative(initiative: dict[str, Any]) -> set[str]:
    """Collect every task id linked to an initiative across primary and slice refs."""
    refs: set[str] = set()
    for raw in _normalize_str_list(initiative.get("task_ref")):
        refs.add(raw)
    slices = initiative.get("slices")
    if isinstance(slices, list):
        for item in slices:
            if not isinstance(item, dict):
                continue
            for raw in _normalize_str_list(item.get("task_ref")):
                refs.add(raw)
    return refs


def _task_refs_from_entries(raw: Any) -> set[str]:
    """Collect task ids from a version or legacy task list."""
    refs: set[str] = set()
    if not isinstance(raw, list):
        return refs
    for item in raw:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("id", "")).strip()
        if task_id:
            refs.add(task_id)
    return refs


def _roadmap_known_refs(data: dict[str, Any]) -> set[str]:
    """Collect initiative/task ids that may appear in roadmap narrative prose."""
    refs = _task_refs_from_entries(data.get("tasks"))

    raw_initiatives = data.get("initiatives")
    if isinstance(raw_initiatives, list):
        for item in raw_initiatives:
            if not isinstance(item, dict):
                continue
            initiative_id = str(item.get("id", "")).strip()
            if initiative_id:
                refs.add(initiative_id)
            refs.update(_task_refs_for_initiative(item))

    raw_versions = data.get("versions")
    if isinstance(raw_versions, list):
        for version in raw_versions:
            if not isinstance(version, dict):
                continue
            for block in ("completed_tasks", "tasks", "deferred_tasks"):
                refs.update(_task_refs_from_entries(version.get(block)))
            pending_refs = version.get("pending_task_refs")
            if isinstance(pending_refs, list):
                refs.update(str(ref).strip() for ref in pending_refs if str(ref).strip())

    return refs


def _excluded_roadmap_refs(
    *,
    matched_refs: set[str],
    known_refs: set[str],
) -> set[str]:
    """Return known roadmap refs that are outside the active filtered cross-section."""
    matched_folded = {ref.casefold() for ref in matched_refs if ref}
    return {ref.casefold() for ref in known_refs if ref and ref.casefold() not in matched_folded}


def _sanitize_filtered_ref_text(value: Any, *, excluded_refs: set[str]) -> str:
    """Replace off-slice roadmap refs inside filtered task text with neutral prose."""
    text = str(value).strip()
    if not text or not excluded_refs:
        return text

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.casefold() in excluded_refs:
            return FILTERED_REF_PLACEHOLDER
        return token

    sanitized = ROADMAP_REF_TOKEN_RE.sub(_replace, text)
    placeholder = re.escape(FILTERED_REF_PLACEHOLDER)
    sanitized = re.sub(
        rf"{placeholder}(?:\s*(?:,|/|and|or)\s*{placeholder})+",
        FILTERED_REF_PLACEHOLDER,
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"\s{2,}", " ", sanitized)
    sanitized = re.sub(r"\s+([,.;:])", r"\1", sanitized)
    return sanitized.strip()


def _sanitize_filtered_task_entry(
    task: dict[str, Any], *, excluded_refs: set[str]
) -> dict[str, Any]:
    """Sanitize task fields that can mention roadmap refs outside the filtered slice."""
    if not excluded_refs:
        return task
    task_copy = dict(task)
    for field in ("title", "note", "deferred_from"):
        value = task_copy.get(field)
        if value:
            task_copy[field] = _sanitize_filtered_ref_text(value, excluded_refs=excluded_refs)
    return task_copy


def _sanitize_filtered_version(
    version: dict[str, Any], *, excluded_refs: set[str]
) -> dict[str, Any]:
    """Make filtered version panels strict slice summaries."""
    version_copy = dict(version)
    version_copy.pop("goal", None)
    version_copy.pop("note", None)
    for block in ("completed_tasks", "tasks", "deferred_tasks"):
        entries = version_copy.get(block)
        if isinstance(entries, list):
            version_copy[block] = [
                _sanitize_filtered_task_entry(item, excluded_refs=excluded_refs)
                if isinstance(item, dict)
                else item
                for item in entries
            ]
    return version_copy


def filter_roadmap_cross_section(
    data: dict[str, Any],
    *,
    theme: str | None = None,
    track: str | None = None,
) -> dict[str, Any]:
    """Return a roadmap view filtered by initiative dimensions and linked task refs."""
    if not theme and not track:
        return data

    filtered = dict(data)
    raw_initiatives = data.get("initiatives")
    initiatives = raw_initiatives if isinstance(raw_initiatives, list) else []
    matched_initiatives = [
        item
        for item in initiatives
        if isinstance(item, dict) and initiative_matches_filters(item, theme=theme, track=track)
    ]
    filtered["initiatives"] = matched_initiatives

    matched_task_refs: set[str] = set()
    for initiative in matched_initiatives:
        matched_task_refs.update(_task_refs_for_initiative(initiative))
    matched_initiative_refs = {
        str(item.get("id", "")).strip()
        for item in matched_initiatives
        if str(item.get("id", "")).strip()
    }
    known_refs = _roadmap_known_refs(data)
    excluded_refs = _excluded_roadmap_refs(
        matched_refs=matched_task_refs | matched_initiative_refs,
        known_refs=known_refs,
    )

    versions_raw = data.get("versions")
    if not isinstance(versions_raw, list):
        return filtered

    filtered_versions: list[Any] = []
    for version in versions_raw:
        if not isinstance(version, dict):
            continue
        version_id = str(version.get("id", ""))
        phase_matches = any(
            isinstance(item, dict)
            and item.get("phase") == version_id
            and item.get("status") not in ("complete", "completed")
            for item in matched_initiatives
        )

        version_copy = dict(version)
        matched_any = phase_matches

        for block in ("completed_tasks", "tasks", "deferred_tasks"):
            entries = version.get(block)
            if isinstance(entries, list):
                filtered_entries = [
                    item
                    for item in entries
                    if isinstance(item, dict) and str(item.get("id", "")) in matched_task_refs
                ]
                version_copy[block] = filtered_entries
                matched_any = matched_any or bool(filtered_entries)

        pending_refs = version.get("pending_task_refs")
        if isinstance(pending_refs, list):
            filtered_refs = [ref for ref in pending_refs if str(ref) in matched_task_refs]
            version_copy["pending_task_refs"] = filtered_refs
            matched_any = matched_any or bool(filtered_refs)

        if matched_any:
            version_copy = _sanitize_filtered_version(version_copy, excluded_refs=excluded_refs)
            filtered_versions.append(version_copy)

    filtered["versions"] = filtered_versions
    return filtered


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
        data = safe_load_yaml(text)
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


def load_backlog(path: Path | None = None) -> dict[str, Any]:
    """Load backlog YAML; return empty dict if missing or invalid."""
    p = path or DEFAULT_BACKLOG
    if not p.exists():
        return {}
    try:
        data = safe_load_yaml_path(p) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _backlog_path_for_roadmap(roadmap_path: Path) -> Path:
    sibling = roadmap_path.with_name("backlog.yaml")
    if sibling.exists():
        return sibling
    return DEFAULT_BACKLOG


def _repo_root_for_roadmap(roadmap_path: Path) -> Path:
    if roadmap_path.name == "roadmap.yaml" and roadmap_path.parent.name == ".azoth":
        return roadmap_path.parent.parent
    return roadmap_path.parent


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


def _completed_backlog_task_ids(backlog: dict[str, Any]) -> set[str]:
    completed: set[str] = set()
    items = backlog.get("items")
    if not isinstance(items, list):
        return completed
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").casefold() not in {"complete", "completed"}:
            continue
        task_id = str(item.get("roadmap_ref") or item.get("id") or "").strip()
        if task_id:
            completed.add(task_id)
    return completed


def _initiative_alias_slice(initiative: dict[str, Any]) -> dict[str, Any] | None:
    alias = str(initiative.get("task_ref") or "").strip()
    if not alias:
        return None
    slices = initiative.get("slices")
    if not isinstance(slices, list):
        return None
    for item in slices:
        if isinstance(item, dict) and str(item.get("task_ref") or "").strip() == alias:
            return item
    return None


def _slice_is_actionable(slice_item: dict[str, Any]) -> bool:
    status = str(slice_item.get("status") or "").strip().casefold()
    role = str(slice_item.get("role") or "").strip().casefold()
    return status not in {"complete", "completed"} and role != "historical"


def _initiative_has_actionable_open_slice(initiative: dict[str, Any]) -> bool:
    slices = initiative.get("slices")
    if isinstance(slices, list) and slices:
        return any(isinstance(item, dict) and _slice_is_actionable(item) for item in slices)
    return str(initiative.get("status") or "").strip().casefold() not in {"complete", "completed"}


def _scheduled_initiative_points_at_stale_slice(initiative: dict[str, Any]) -> bool:
    if initiative.get("phase") is None:
        return False
    alias_slice = _initiative_alias_slice(initiative)
    if alias_slice is not None:
        return not _slice_is_actionable(alias_slice)
    return not _initiative_has_actionable_open_slice(initiative)


def build_drift_warnings(
    roadmap: dict[str, Any],
    *,
    backlog: dict[str, Any] | None = None,
) -> list[str]:
    warnings: list[str] = []
    completed_backlog_ids = _completed_backlog_task_ids(backlog or {})

    for version in roadmap.get("versions") or []:
        if not isinstance(version, dict):
            continue
        version_id = str(version.get("id") or "?")
        tasks, _ = _normalize_task_entries(version.get("tasks"), block_label="tasks")
        open_task_ids = [str(task.get("id") or "").strip() for task in tasks if task.get("id")]
        stale_ids = [task_id for task_id in open_task_ids if task_id in completed_backlog_ids]
        if stale_ids:
            warnings.append(
                f"{version_id}: backlog-complete task(s) still listed in tasks — "
                f"{', '.join(stale_ids)}"
            )
        if str(version.get("status") or "").strip().casefold() == "complete" and open_task_ids:
            warnings.append(
                f"{version_id}: version is complete but still has open task(s) — "
                f"{', '.join(open_task_ids)}"
            )

    for initiative in roadmap.get("initiatives") or []:
        if not isinstance(initiative, dict):
            continue
        if not _scheduled_initiative_points_at_stale_slice(initiative):
            continue
        initiative_id = str(initiative.get("id") or "?")
        phase = str(initiative.get("phase") or "?")
        alias = str(initiative.get("task_ref") or "").strip()
        if alias:
            warnings.append(
                f"{initiative_id}: scheduled phase {phase} still points at completed or "
                f"historical slice {alias}"
            )
        else:
            warnings.append(f"{initiative_id}: scheduled phase {phase} has no live primary slice")

    return warnings


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


def _phase_initiatives_for_version(
    roadmap: dict[str, Any], version_id: str
) -> list[dict[str, Any]]:
    """Return non-complete initiatives explicitly assigned to a roadmap version."""
    raw = roadmap.get("initiatives")
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if item.get("phase") != version_id:
            continue
        if item.get("status") in ("complete", "completed"):
            continue
        items.append(item)
    return items


def build_version_body(version: Any, roadmap: dict[str, Any] | None = None) -> str:
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
    deferred, dw = _normalize_task_entries(version.get("deferred_tasks"), block_label="deferred_tasks")
    pending, pw = _normalize_task_entries(version.get("tasks"), block_label="tasks")
    phase_initiatives = []
    if isinstance(roadmap, dict):
        phase_initiatives = _phase_initiatives_for_version(roadmap, str(version.get("id", "?")))

    if completed or deferred or pending or cw or dw or pw or phase_initiatives:
        lines.append("")

    lines.extend(_format_task_block("Delivered", completed, done=True, schema_warnings=cw))
    if (completed or cw) and (deferred or dw or pending or pw or phase_initiatives):
        lines.append("")
    lines.extend(_format_task_block("Carried Forward", deferred, done=False, schema_warnings=dw))
    if (deferred or dw) and (pending or pw or phase_initiatives):
        lines.append("")
    lines.extend(_format_task_block("Upcoming", pending, done=False, schema_warnings=pw))
    if phase_initiatives:
        if pending or pw:
            lines.append("")
        lines.append("[bold]Initiatives[/bold]")
        for item in phase_initiatives:
            iid = escape(str(item.get("id", "?")))
            title = escape(str(item.get("title", "")))
            lines.append(f"  :large_blue_circle: [cyan]{iid}[/]  {title}")

    return "\n".join(lines)


def render_header(
    data: Any,
    *,
    theme_filter: str | None = None,
    track_filter: str | None = None,
) -> Panel:
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
    if theme_filter or track_filter:
        header.append("  ·  cross-section ", style="dim")
        filters: list[str] = []
        if theme_filter:
            filters.append(f"theme={theme_filter}")
        if track_filter:
            filters.append(f"track={track_filter}")
        header.append(" / ".join(filters), style="bold magenta")
    return Panel(header, box=box.HEAVY)


def render_version_panel(version: Any, roadmap: dict[str, Any] | None = None) -> Panel:
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
    body = build_version_body(version, roadmap=roadmap)
    ss = _status_style(st)
    title_bar = f"[bold]{escape(str(vid))}[/]  [{ss}]{escape(str(st))}[/{ss}]"
    return Panel(
        body,
        title=title_bar,
        border_style=_status_style(st),
        box=box.ROUNDED,
    )


_PRIORITY_BADGE: dict[str, str] = {
    "high": "[bold red]●[/]",
    "medium": "[yellow]●[/]",
    "low": "[dim]●[/]",
}
_CATEGORY_ORDER = ["memory", "governance", "ux", "infra", "platform"]


def gather_initiatives(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group unscheduled roadmap initiatives by category.

    Skips non-dict entries, scheduled initiatives (phase != null), and completed ones.
    Returns {} when absent.
    """
    raw = data.get("initiatives")
    if not raw or not isinstance(raw, list):
        return {}
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        if item.get("phase") is not None:
            continue
        if item.get("status") in ("complete", "completed"):
            continue
        if not _initiative_has_actionable_open_slice(item):
            continue
        cat = str(item.get("category", "uncategorized"))
        by_category.setdefault(cat, []).append(item)
    return by_category


def render_drift_warnings_panel(warnings: list[str]) -> Panel | None:
    if not warnings:
        return None
    lines = [
        "[yellow]Roadmap drift detected.[/] `/roadmap` still renders authored roadmap state,",
        "[yellow]so repair the source data instead of relying on silent suppression.[/]",
        "",
    ]
    for warning in warnings:
        lines.append(f"- {escape(warning)}")
    return Panel(
        "\n".join(lines),
        title="[bold]Planning Drift Warnings[/]",
        border_style="yellow",
        box=box.ROUNDED,
    )


def render_initiatives_panel(
    by_category: dict[str, list[dict[str, Any]]],
) -> Panel | None:
    """Render a Rich Panel of phase-agnostic initiatives grouped by category. None when empty."""
    if not by_category:
        return None
    lines: list[str] = []
    cats = sorted(
        by_category.keys(),
        key=lambda c: (_CATEGORY_ORDER.index(c) if c in _CATEGORY_ORDER else 99, c),
    )
    for cat in cats:
        lines.append(f"[bold dim]{escape(cat.upper())}[/]")
        for item in by_category[cat]:
            iid = escape(str(item.get("id", "?")))
            title = escape(str(item.get("title", "")))
            badge = _PRIORITY_BADGE.get(str(item.get("priority", "")), "[dim]●[/]")
            lines.append(f"  {badge} [cyan]{iid}[/]  {title}")
        lines.append("")
    body = "\n".join(lines).rstrip()
    return Panel(
        body,
        title="[bold]Initiatives[/] [dim](phase: null — unscheduled)[/]",
        border_style="dim",
        box=box.ROUNDED,
    )


def render_dashboard(
    roadmap_path: Path | None = None,
    *,
    console: Console | None = None,
    theme: str | None = None,
    track: str | None = None,
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

    filtered_data = filter_roadmap_cross_section(data, theme=theme, track=track)

    if (theme or track) and not filtered_data.get("initiatives") and not filtered_data.get("versions"):
        filters: list[str] = []
        if theme:
            filters.append(f"theme={theme}")
        if track:
            filters.append(f"track={track}")
        out.print(
            Panel(
                f"[yellow]No roadmap items matched:[/] {escape(', '.join(filters))}",
                title="Roadmap cross-section",
                box=box.HEAVY,
            )
        )
        return

    out.print(render_header(filtered_data, theme_filter=theme, track_filter=track))
    out.print()

    backlog_data = load_backlog(_backlog_path_for_roadmap(path))
    drift_panel = render_drift_warnings_panel(
        build_drift_warnings(filtered_data, backlog=backlog_data)
    )
    if drift_panel is not None:
        out.print(drift_panel)
        out.print()

    planning_bank_panel = render_planning_bank_panel(
        load_planning_bank_summaries(_repo_root_for_roadmap(path))
    )
    if planning_bank_panel is not None:
        out.print(planning_bank_panel)
        out.print()

    ini_panel = render_initiatives_panel(gather_initiatives(filtered_data))
    if ini_panel is not None:
        out.print(ini_panel)
        out.print()

    versions_raw = filtered_data.get("versions")
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
        out.print(render_version_panel(v, roadmap=filtered_data))
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
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Filter to roadmap initiatives/tasks matching a theme code (for example: E).",
    )
    parser.add_argument(
        "--track",
        type=str,
        default=None,
        help="Filter to roadmap initiatives/tasks matching a dimension track.",
    )
    args = parser.parse_args()
    render_dashboard(roadmap_path=args.roadmap, theme=args.theme, track=args.track)


if __name__ == "__main__":
    main()
