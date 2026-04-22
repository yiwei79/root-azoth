#!/usr/bin/env python3
"""
initiative_scaffold.py — create initiative stubs plus roadmap task placeholders.

Usage examples:
  python3 scripts/initiative_scaffold.py --id INI-KRP-001 --title "Karpathy Principles" --tasks 5
  python3 scripts/initiative_scaffold.py --id INI-RST-007 --tasks 3 --backlog-items
  python3 scripts/initiative_scaffold.py --id INI-PPL-003 --tasks 2 --task-title "Slice A" --task-title "Slice B"
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import roadmap_task_id


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"
DEFAULT_BACKLOG = ROOT / ".azoth" / "backlog.yaml"
INI_ID_RE = re.compile(r"^INI-([A-Z0-9]+)-\d+$")


def _die(message: str) -> None:
    raise SystemExit(message)


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load_yaml(path: Path) -> dict[str, Any]:
    return roadmap_task_id.load_yaml(path)


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _ensure_active_version(
    roadmap: dict[str, Any], active_version: str | None
) -> tuple[str, dict[str, Any]]:
    resolved = active_version or str(roadmap.get("active_version") or "").strip()
    if not resolved:
        _die("could not resolve active version from roadmap.yaml; pass --active-version")

    for version in roadmap.get("versions") or []:
        if isinstance(version, dict) and version.get("id") == resolved:
            return resolved, version

    _die(f"active version {resolved!r} was not found in roadmap.yaml versions[]")


def _initiative_token(initiative_id: str) -> str:
    match = INI_ID_RE.match(initiative_id.strip())
    if not match:
        _die(
            "initiative ids must match INI-<TOKEN>-<NNN> so task stubs can be derived "
            f"(got {initiative_id!r})"
        )
    return match.group(1)


def _excel_column(index: int) -> str:
    if index < 0:
        _die("task label index must be non-negative")
    label = ""
    value = index
    while True:
        value, remainder = divmod(value, 26)
        label = chr(ord("A") + remainder) + label
        if value == 0:
            return label
        value -= 1


def _collect_raw_ids(block: Any, used: set[str]) -> None:
    if isinstance(block, dict):
        for key in ("id", "task_ref", "roadmap_ref", "initiative_ref"):
            raw = block.get(key)
            if isinstance(raw, str) and raw.strip():
                used.add(raw.strip())
        blocked_by = block.get("blocked_by")
        if isinstance(blocked_by, list):
            for entry in blocked_by:
                if isinstance(entry, str) and entry.strip():
                    used.add(entry.strip())


def _collect_id_list(entries: Any, used: set[str]) -> None:
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, str) and entry.strip():
                used.add(entry.strip())


def _used_ids(roadmap: dict[str, Any], backlog: dict[str, Any]) -> set[str]:
    used: set[str] = set()
    for task in roadmap.get("tasks") or []:
        if isinstance(task, dict):
            _collect_raw_ids(task, used)

    for section in (
        roadmap.get("versions") or [],
        roadmap.get("initiatives") or [],
        backlog.get("items") or [],
    ):
        if isinstance(section, list):
            for block in section:
                if isinstance(block, dict):
                    _collect_raw_ids(block, used)
                    _collect_id_list(block.get("pending_task_refs"), used)
                    for nested_key in ("tasks", "completed_tasks", "deferred_tasks", "slices"):
                        nested = block.get(nested_key)
                        if isinstance(nested, list):
                            for item in nested:
                                _collect_raw_ids(item, used)
    return used


def _normalize_tokens(values: list[str] | None) -> list[str]:
    tokens: list[str] = []
    for raw in values or []:
        for token in raw.split(","):
            token = token.strip()
            if token and token not in tokens:
                tokens.append(token)
    return tokens


def _task_titles(title: str, count: int, provided: list[str]) -> list[str]:
    if len(provided) > count:
        _die(f"received {len(provided)} --task-title values for only {count} task slots")

    titles = [entry.strip() for entry in provided if entry.strip()]
    while len(titles) < count:
        label = _excel_column(len(titles))
        titles.append(f"{title} [stub {label}]")
    return titles


def _initiative_dimensions(theme: str, category: str, tracks: list[str]) -> dict[str, list[str]]:
    return {
        "themes": [theme],
        "categories": [category],
        "tracks": tracks,
    }


def _build_initiative(
    *,
    initiative_id: str,
    title: str,
    category: str,
    theme: str,
    tracks: list[str],
    phase: str | None,
    priority: str,
    summary: str,
    decision_ref: list[str],
    research_ref: str | None,
    task_ids: list[str],
) -> dict[str, Any]:
    initiative: dict[str, Any] = {
        "id": initiative_id,
        "title": title,
        "category": category,
        "theme": theme,
        "dimensions": _initiative_dimensions(theme, category, tracks),
        "phase": phase,
        "priority": priority,
        "summary": summary,
        "slices": [],
    }
    if research_ref:
        initiative["research_ref"] = research_ref
    if decision_ref:
        initiative["decision_ref"] = decision_ref

    for index, task_id in enumerate(task_ids):
        initiative["slices"].append(
            {
                "task_ref": task_id,
                "phase": phase,
                "role": "primary" if index == 0 else "follow-on",
                "status": "planned",
            }
        )
    return initiative


def _build_task_stub(
    *,
    task_id: str,
    title: str,
    initiative_id: str,
    target_layer: str,
    delivery_pipeline: str,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "target_layer": target_layer,
        "delivery_pipeline": delivery_pipeline,
        "initiative_ref": initiative_id,
        "status": "planned",
    }


def _build_backlog_item(
    *,
    task_id: str,
    title: str,
    initiative_id: str,
    source: str,
    target_layer: str,
    delivery_pipeline: str,
    target_version: str,
    priority: int,
    created_date: str,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "source": source,
        "roadmap_ref": task_id,
        "initiative_ref": initiative_id,
        "target_layer": target_layer,
        "delivery_pipeline": delivery_pipeline,
        "status": "pending",
        "target_version": target_version,
        "priority": priority,
        "created_date": created_date,
        "description": f'TODO: flesh out backlog description for "{title}".',
    }


def scaffold(args: argparse.Namespace) -> tuple[str, list[Path]]:
    roadmap = _load_yaml(args.roadmap_yaml)
    backlog = _load_yaml(args.backlog_yaml)
    backlog.setdefault("schema_version", 1)
    backlog.setdefault("items", [])
    roadmap.setdefault("initiatives", [])

    active_version, active_entry = _ensure_active_version(roadmap, args.active_version)
    if any(
        isinstance(item, dict) and str(item.get("id") or "").strip() == args.id
        for item in roadmap.get("initiatives") or []
    ):
        _die(f"initiative id {args.id!r} already exists in roadmap.yaml")

    used = _used_ids(roadmap, backlog)
    if args.id in used:
        _die(f"initiative id {args.id!r} collides with an existing roadmap/backlog identifier")

    created_date = args.created_date or _today_utc()
    source = args.source or f"initiative-scaffold-{created_date}"
    tracks = _normalize_tokens(args.track)
    decision_ref = _normalize_tokens(args.decision_ref)
    phase = None if args.phase in {None, "null"} else args.phase
    if phase is not None and phase != active_version:
        _die(
            f"--phase {phase!r} must match the resolved target version {active_version!r}; "
            "pass --active-version to target a scheduled version or use --phase null"
        )
    target_version = args.target_version or active_version
    token = args.task_prefix or f"T-{_initiative_token(args.id)}"

    task_ids = [f"{token}-{_excel_column(index)}" for index in range(args.tasks)]
    for task_id in task_ids:
        if task_id in used:
            _die(f"task id {task_id!r} already exists; pass --task-prefix to choose another family")

    titles = _task_titles(args.title, args.tasks, args.task_title)
    initiative = _build_initiative(
        initiative_id=args.id,
        title=args.title,
        category=args.category,
        theme=args.theme,
        tracks=tracks,
        phase=phase,
        priority=args.priority,
        summary=args.summary,
        decision_ref=decision_ref,
        research_ref=args.research_ref,
        task_ids=task_ids,
    )

    active_entry.setdefault("tasks", [])
    for task_id, title in zip(task_ids, titles):
        active_entry["tasks"].append(
            _build_task_stub(
                task_id=task_id,
                title=title,
                initiative_id=args.id,
                target_layer=args.target_layer,
                delivery_pipeline=args.delivery_pipeline,
            )
        )
        if args.backlog_items:
            backlog["items"].append(
                _build_backlog_item(
                    task_id=task_id,
                    title=title,
                    initiative_id=args.id,
                    source=source,
                    target_layer=args.target_layer,
                    delivery_pipeline=args.delivery_pipeline,
                    target_version=target_version,
                    priority=args.backlog_priority,
                    created_date=created_date,
                )
            )

    roadmap["initiatives"].append(initiative)
    _dump_yaml(args.roadmap_yaml, roadmap)
    written = [args.roadmap_yaml]
    if args.backlog_items:
        _dump_yaml(args.backlog_yaml, backlog)
        written.append(args.backlog_yaml)

    return args.id, written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a new initiative block plus planned task stubs in roadmap.yaml.",
    )
    parser.add_argument("--id", required=True, help="Initiative id, e.g. INI-KRP-001.")
    parser.add_argument("--title", type=str, default=None, help="Initiative title.")
    parser.add_argument("--tasks", type=int, required=True, help="Number of task stubs to create.")
    parser.add_argument("--roadmap-yaml", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--backlog-yaml", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--active-version", type=str, default=None)
    parser.add_argument(
        "--phase",
        type=str,
        default="null",
        help=(
            "Initiative phase value. Pass 'null' for phase-free initiatives, or a version id "
            "that matches the resolved --active-version target."
        ),
    )
    parser.add_argument("--category", type=str, default="run-state")
    parser.add_argument("--theme", type=str, default="A")
    parser.add_argument("--track", action="append", default=[])
    parser.add_argument("--priority", type=str, default="medium")
    parser.add_argument("--summary", type=str, default=None)
    parser.add_argument("--decision-ref", nargs="*", default=[])
    parser.add_argument("--research-ref", type=str, default=None)
    parser.add_argument("--task-prefix", type=str, default=None)
    parser.add_argument("--task-title", action="append", default=[])
    parser.add_argument("--target-layer", type=str, default="infrastructure")
    parser.add_argument("--delivery-pipeline", type=str, default="standard")
    parser.add_argument(
        "--backlog-items",
        action="store_true",
        help="Also create pending roadmap-backed backlog rows for each generated T-* stub.",
    )
    parser.add_argument("--backlog-priority", type=int, default=3)
    parser.add_argument("--target-version", type=str, default=None)
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--created-date", type=str, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.tasks <= 0:
        _die("--tasks must be greater than 0")
    if not args.title:
        args.title = f"TODO: title for {args.id}"
    if not args.summary:
        args.summary = f'TODO: describe the motivation and intended outcomes for "{args.title}".'
    initiative_id, written = scaffold(args)
    print(initiative_id)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
