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


def _summarize_initiative_bank(
    path: Path, doc: dict[str, Any], repo_root: Path
) -> dict[str, Any]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    candidates = doc.get("candidate_slices")
    candidate = _candidate_by_id(candidates, readiness.get("candidate_first_slice"))
    open_candidates = [
        item
        for item in (candidates if isinstance(candidates, list) else [])
        if isinstance(item, dict)
        and str(item.get("status") or "").casefold() in {"candidate", "parked", "rejected"}
    ]
    status = str(candidate.get("status") or "missing")
    ready_to_hydrate = (
        readiness.get("readiness_status") == "ready_to_hydrate"
        and readiness.get("human_decision") == "approved"
        and status not in {"hydrated", "complete"}
    )
    return {
        "kind": "initiative",
        "id": str(doc.get("initiative_id") or path.stem),
        "title": str(doc.get("title") or ""),
        "status": str(doc.get("status") or "unknown"),
        "path": _repo_rel(path, repo_root),
        "readiness_status": str(readiness.get("readiness_status") or "missing"),
        "human_decision": str(readiness.get("human_decision") or "missing"),
        "candidate_id": str(candidate.get("candidate_id") or "missing"),
        "candidate_task_ref": str(candidate.get("proposed_task_id") or "missing"),
        "candidate_status": status,
        "ready_to_hydrate": ready_to_hydrate,
        "open_candidate_count": len(open_candidates),
        "route_hint": str(
            readiness.get("hydration_recommendation")
            or "refine initiative bank; hydrate only after explicit approval"
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
    readiness = str(bank.get("readiness_status") or "?")
    human_decision = str(bank.get("human_decision") or "?")
    route = str(bank.get("route_hint") or "refine planning bank")
    lines = [
        f"  {bank_id}  [{kind}; {status}; readiness: {readiness}; human: {human_decision}]"
    ]
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


def format_planning_bank_rich(
    summaries: dict[str, list[dict[str, Any]]], *, limit: int = 4
) -> str:
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
        readiness = escape(str(bank.get("readiness_status") or "?"))
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
            lines.append(f"  [dim]candidate {candidate_id} -> {task_ref} ({candidate_status})[/dim]")
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
