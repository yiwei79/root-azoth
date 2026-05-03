#!/usr/bin/env python3
"""Read-only surfacing helpers for tracked Azoth planning banks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.markup import escape
from rich.panel import Panel

from yaml_helpers import safe_load_yaml_path


DESIGN_BANK_DIR = Path(".azoth/design-banks")
INITIATIVE_BANK_DIR = Path(".azoth/initiative-banks")


def _repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = safe_load_yaml_path(path) or {}
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _iter_bank_files(repo_root: Path, bank_dir: Path) -> list[Path]:
    root = repo_root / bank_dir
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*.yaml") if path.is_file())


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _summarize_design_bank(path: Path, doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    return {
        "kind": "design",
        "id": str(doc.get("id") or path.stem),
        "title": str(doc.get("title") or ""),
        "status": str(doc.get("status") or "unknown"),
        "path": _repo_rel(path, repo_root),
        "readiness_status": str(readiness.get("readiness_status") or "missing"),
        "human_decision": str(readiness.get("human_decision") or "missing"),
        "route_hint": str(
            readiness.get("target_route")
            or readiness.get("recommended_next_artifact")
            or "refine_design_bank"
        ),
        "proposal_refs": _string_list(doc.get("source_proposal_refs")),
    }


def _candidate_by_id(candidates: Any, candidate_id: str | None) -> dict[str, Any]:
    if not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "") == candidate_id:
            return candidate
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return {}


_OPEN_CANDIDATE_STATUSES = {"candidate", "parked", "ready_to_hydrate"}
_CLOSED_CANDIDATE_STATUSES = {"hydrated", "complete", "completed"}
_BACKLOG_DONE_STATUSES = {"complete", "completed", "deferred"}
_APPROVAL_BOUNDARY = (
    "Requires explicit approval before hydration, deployment, or personal-root mutation."
)
_POST_CANDIDATE_APPROVAL_BOUNDARY = (
    "No hydration, delivery, release, or deployment without fresh approval."
)
_POST_CANDIDATE_READINESS = "needs_context_recovery"


def _hydrated_task_ref(candidate: dict[str, Any]) -> str:
    hydration_plan = candidate.get("hydration_plan")
    if isinstance(hydration_plan, dict):
        task_ref = str(hydration_plan.get("hydrated_task_ref") or "").strip()
        if task_ref:
            return task_ref
    return str(candidate.get("proposed_task_id") or "").strip()


def _backlog_status_for_task(repo_root: Path, task_ref: str) -> str:
    if not task_ref:
        return ""
    backlog = _load_yaml_mapping(repo_root / ".azoth" / "backlog.yaml")
    items = backlog.get("items")
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == task_ref:
            return str(item.get("status") or "").strip()
    return ""


def _hydrated_task_is_still_open(repo_root: Path, candidate: dict[str, Any]) -> bool:
    task_status = _backlog_status_for_task(repo_root, _hydrated_task_ref(candidate))
    return bool(task_status) and task_status.casefold() not in _BACKLOG_DONE_STATUSES


def _strategic_context_refs(doc: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for value in _string_list(doc.get("source_proposal_refs")) + _string_list(
        doc.get("research_refs")
    ):
        if value not in refs:
            refs.append(value)
    contacts = doc.get("contacts")
    if isinstance(contacts, list):
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            path = str(contact.get("path") or "").strip()
            if path and path not in refs:
                refs.append(path)
    return refs


def _next_open_candidate(candidates: Any) -> dict[str, Any]:
    """Return the next not-yet-hydrated candidate slice, preserving bank order."""
    if not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        status = str(candidate.get("status") or "").casefold()
        if status in _OPEN_CANDIDATE_STATUSES:
            return candidate
    return {}


def _candidate_route_hint(
    *,
    readiness: dict[str, Any],
    readiness_candidate: dict[str, Any],
    display_candidate: dict[str, Any],
    initiative_title: str = "the initiative",
    no_open_candidates_after_closed_slice: bool = False,
    strategic_context_refs: list[str] | None = None,
) -> str:
    hydration_recommendation = str(readiness.get("hydration_recommendation") or "").strip()
    readiness_status = str(readiness_candidate.get("status") or "").casefold()
    display_id = str(display_candidate.get("candidate_id") or "").strip()
    readiness_id = str(readiness_candidate.get("candidate_id") or "").strip()
    if no_open_candidates_after_closed_slice:
        refs = [ref for ref in strategic_context_refs or [] if ref]
        ref_text = "; ".join(refs[:3])
        context_clause = f" Recover context from {ref_text}." if ref_text else ""
        if hydration_recommendation:
            route = f"{hydration_recommendation}{context_clause}"
            if _POST_CANDIDATE_APPROVAL_BOUNDARY not in route:
                route = f"{route} {_POST_CANDIDATE_APPROVAL_BOUNDARY}"
            if _APPROVAL_BOUNDARY not in route:
                route = f"{route} {_APPROVAL_BOUNDARY}"
            return route
        task_ref = str(display_candidate.get("proposed_task_id") or "missing").strip()
        return (
            f"all tracked candidate slices are closed after {display_id} -> {task_ref}; "
            f"open a fresh scoped continuation for {initiative_title} before more "
            f"hydration, delivery, release, or deployment."
            f"{context_clause} {_APPROVAL_BOUNDARY}"
        )
    if (
        display_candidate
        and display_id
        and display_id != readiness_id
        and readiness_status in _CLOSED_CANDIDATE_STATUSES
    ):
        task_ref = str(display_candidate.get("proposed_task_id") or "missing").strip()
        title = str(display_candidate.get("title") or "").strip()
        suffix = f": {title}" if title else ""
        return f"next open candidate {display_id} -> {task_ref}{suffix}; {_APPROVAL_BOUNDARY}"
    if hydration_recommendation:
        if _APPROVAL_BOUNDARY in hydration_recommendation:
            return hydration_recommendation
        return f"{hydration_recommendation} {_APPROVAL_BOUNDARY}"
    return f"refine initiative bank; {_APPROVAL_BOUNDARY}"


def _summarize_initiative_bank(path: Path, doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    candidates = doc.get("candidate_slices")
    readiness_candidate = _candidate_by_id(candidates, readiness.get("candidate_first_slice"))
    candidate = readiness_candidate
    if str(
        readiness_candidate.get("status") or ""
    ).casefold() in _CLOSED_CANDIDATE_STATUSES and not _hydrated_task_is_still_open(
        repo_root, readiness_candidate
    ):
        candidate = _next_open_candidate(candidates) or readiness_candidate
    open_candidates = [
        item
        for item in (candidates if isinstance(candidates, list) else [])
        if isinstance(item, dict)
        and str(item.get("status") or "").casefold() in _OPEN_CANDIDATE_STATUSES
    ]
    readiness_candidate_status = str(readiness_candidate.get("status") or "missing")
    status = str(candidate.get("status") or "missing")
    no_open_candidates_after_closed_slice = (
        bool(readiness_candidate)
        and readiness_candidate_status.casefold() in _CLOSED_CANDIDATE_STATUSES
        and not _hydrated_task_is_still_open(repo_root, readiness_candidate)
        and not open_candidates
    )
    readiness_status = str(readiness.get("readiness_status") or "missing")
    surface_readiness_status = (
        _POST_CANDIDATE_READINESS if no_open_candidates_after_closed_slice else readiness_status
    )
    strategic_context_refs = _strategic_context_refs(doc)
    ready_to_hydrate = (
        readiness_status == "ready_to_hydrate"
        and readiness.get("human_decision") == "approved"
        and readiness_candidate_status.casefold() not in _CLOSED_CANDIDATE_STATUSES
        and not no_open_candidates_after_closed_slice
    )
    return {
        "kind": "initiative",
        "id": str(doc.get("initiative_id") or path.stem),
        "title": str(doc.get("title") or ""),
        "status": str(doc.get("status") or "unknown"),
        "path": _repo_rel(path, repo_root),
        "readiness_status": readiness_status,
        "surface_readiness_status": surface_readiness_status,
        "human_decision": str(readiness.get("human_decision") or "missing"),
        "readiness_candidate_id": str(readiness_candidate.get("candidate_id") or "missing"),
        "readiness_candidate_status": readiness_candidate_status,
        "candidate_id": str(candidate.get("candidate_id") or "missing"),
        "candidate_task_ref": str(candidate.get("proposed_task_id") or "missing"),
        "candidate_status": status,
        "ready_to_hydrate": ready_to_hydrate,
        "open_candidate_count": len(open_candidates),
        "strategic_context_refs": strategic_context_refs,
        "route_hint": _candidate_route_hint(
            readiness=readiness,
            readiness_candidate=readiness_candidate,
            display_candidate=candidate,
            initiative_title=str(doc.get("title") or "the initiative"),
            no_open_candidates_after_closed_slice=no_open_candidates_after_closed_slice,
            strategic_context_refs=strategic_context_refs,
        ),
        "proposal_refs": _string_list(doc.get("source_proposal_refs")),
    }


def load_planning_bank_summaries(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Load tracked planning-bank summaries without validating or mutating them."""
    design_banks: list[dict[str, Any]] = []
    for path in _iter_bank_files(repo_root, DESIGN_BANK_DIR):
        doc = _load_yaml_mapping(path)
        if doc.get("bank_type") == "design":
            design_banks.append(_summarize_design_bank(path, doc, repo_root))

    initiative_banks: list[dict[str, Any]] = []
    for path in _iter_bank_files(repo_root, INITIATIVE_BANK_DIR):
        doc = _load_yaml_mapping(path)
        if doc.get("bank_type") == "initiative":
            initiative_banks.append(_summarize_initiative_bank(path, doc, repo_root))

    return {"design_banks": design_banks, "initiative_banks": initiative_banks}


def has_planning_bank_summaries(summaries: dict[str, list[dict[str, Any]]]) -> bool:
    return bool(summaries.get("design_banks") or summaries.get("initiative_banks"))


def _plain_bank_line(bank: dict[str, Any]) -> list[str]:
    kind = str(bank.get("kind") or "bank")
    bank_id = str(bank.get("id") or "?")
    title = str(bank.get("title") or "")
    status = str(bank.get("status") or "?")
    readiness = str(bank.get("surface_readiness_status") or bank.get("readiness_status") or "?")
    human_decision = str(bank.get("human_decision") or "?")
    route = str(bank.get("route_hint") or "refine planning bank")
    lines = [f"  {bank_id}  [{kind}; {status}; readiness: {readiness}; human: {human_decision}]"]
    if title:
        lines.append(f"    {title}")
    if kind == "initiative":
        lines.append(
            "    "
            f"candidate {bank.get('candidate_id', '?')} -> {bank.get('candidate_task_ref', '?')} "
            f"({bank.get('candidate_status', '?')})"
        )
    lines.append(f"    route: {route}")
    lines.append("")
    return lines


def format_planning_bank_plain(
    summaries: dict[str, list[dict[str, Any]]], *, limit: int = 4
) -> list[str]:
    """Return plain-text dashboard lines for tracked planning banks."""
    banks = (summaries.get("design_banks") or []) + (summaries.get("initiative_banks") or [])
    if not banks:
        return []
    lines = [
        "  Tracked planning banks (read-only planning/readiness state):",
        "    Proposal drafts are source history only; use explicit hydration before backlog/spec work.",
        "",
    ]
    for bank in banks[:limit]:
        lines.extend(_plain_bank_line(bank))
    return lines


def format_planning_bank_rich(summaries: dict[str, list[dict[str, Any]]], *, limit: int = 4) -> str:
    """Return Rich-markup text for tracked planning-bank summaries."""
    banks = (summaries.get("design_banks") or []) + (summaries.get("initiative_banks") or [])
    if not banks:
        return ""
    lines = [
        "[dim]Tracked planning/readiness state. Proposal drafts are source history,",
        "not executable dashboard truth; hydrate explicitly before backlog/spec work.[/dim]",
        "",
    ]
    for bank in banks[:limit]:
        kind = escape(str(bank.get("kind") or "bank"))
        bank_id = escape(str(bank.get("id") or "?"))
        title = escape(str(bank.get("title") or ""))
        status = escape(str(bank.get("status") or "?"))
        readiness = escape(
            str(bank.get("surface_readiness_status") or bank.get("readiness_status") or "?")
        )
        human_decision = escape(str(bank.get("human_decision") or "?"))
        route = escape(str(bank.get("route_hint") or "refine planning bank"))
        lines.append(
            f"[bold cyan]{bank_id}[/bold cyan]  "
            f"[dim]{kind}; {status}; {readiness}; human: {human_decision}[/dim]"
        )
        if title:
            lines.append(f"  {title}")
        if bank.get("kind") == "initiative":
            candidate_id = escape(str(bank.get("candidate_id") or "?"))
            task_ref = escape(str(bank.get("candidate_task_ref") or "?"))
            candidate_status = escape(str(bank.get("candidate_status") or "?"))
            lines.append(
                f"  [dim]candidate {candidate_id} -> {task_ref} ({candidate_status})[/dim]"
            )
        lines.append(f"  [dim]route:[/] {route}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_planning_bank_panel(
    summaries: dict[str, list[dict[str, Any]]],
) -> Panel | None:
    if not has_planning_bank_summaries(summaries):
        return None
    return Panel(
        format_planning_bank_rich(summaries),
        title="[bold]Planning Banks[/] [dim](tracked, read-only)[/]",
        border_style="cyan",
    )
