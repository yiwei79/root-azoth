#!/usr/bin/env python3
"""
roadmap_scaffold.py — create roadmap/backlog/spec skeletons for new roadmap work.

Usage examples:
  python3 scripts/roadmap_scaffold.py --title "Add roadmap audit helper"
  python3 scripts/roadmap_scaffold.py --title "Queue intake follow-up" --namespace backlog
  python3 scripts/roadmap_scaffold.py --title "New slice" --initiative-ref INI-RST-004 --decision-ref D47 D48
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import roadmap_task_id


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"
DEFAULT_BACKLOG = ROOT / ".azoth" / "backlog.yaml"
DEFAULT_SPECS_ROOT = ROOT / ".azoth" / "roadmap-specs"


def _die(message: str) -> None:
    raise SystemExit(message)


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    return deepcopy(roadmap_task_id.load_yaml(path))


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


def _find_initiative(roadmap: dict[str, Any], initiative_ref: str | None) -> dict[str, Any] | None:
    if not initiative_ref:
        return None

    for initiative in roadmap.get("initiatives") or []:
        if isinstance(initiative, dict) and initiative.get("id") == initiative_ref:
            return initiative

    _die(f"initiative_ref {initiative_ref!r} not found in roadmap.yaml initiatives[]")


def _normalize_decision_refs(values: list[str] | None) -> list[str]:
    refs: list[str] = []
    for raw in values or []:
        for token in raw.split(","):
            token = token.strip()
            if token and token not in refs:
                refs.append(token)
    return refs


def _normalize_blocked_by(values: list[str] | None) -> list[str]:
    blocked: list[str] = []
    for raw in values or []:
        for token in raw.split(","):
            token = token.strip()
            if token and token not in blocked:
                blocked.append(token)
    return blocked


def _default_source(prefix: str, created_date: str) -> str:
    return f"{prefix}-{created_date}"


def _expected_spec_ref(*, milestone: str, item_id: str) -> str:
    return f".azoth/roadmap-specs/{milestone}/{item_id}.yaml"


def _completed_task_ids(roadmap: dict[str, Any], backlog: dict[str, Any]) -> set[str]:
    completed: set[str] = set()

    for version in roadmap.get("versions") or []:
        if not isinstance(version, dict):
            continue
        for entry in version.get("completed_tasks") or []:
            if isinstance(entry, dict):
                task_id = str(entry.get("id") or "").strip()
                if task_id:
                    completed.add(task_id)

    for item in backlog.get("items") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") != "complete":
            continue
        task_id = str(item.get("roadmap_ref") or item.get("id") or "").strip()
        if task_id:
            completed.add(task_id)

    return completed


def _ensure_initiative_dimensions(initiative: dict[str, Any]) -> None:
    dimensions = initiative.get("dimensions")
    if not isinstance(dimensions, dict):
        dimensions = {}
        initiative["dimensions"] = dimensions

    theme = str(initiative.get("theme") or "").strip()
    if "themes" not in dimensions and theme:
        dimensions["themes"] = [theme]

    category = str(initiative.get("category") or "").strip()
    if "categories" not in dimensions and category:
        dimensions["categories"] = [category]

    dimensions.setdefault("tracks", [])


def _initiative_slices(initiative: dict[str, Any]) -> list[dict[str, Any]]:
    raw = initiative.get("slices")
    if isinstance(raw, list):
        return [deepcopy(item) for item in raw if isinstance(item, dict)]

    task_ref = str(initiative.get("task_ref") or "").strip()
    spec_ref = str(initiative.get("spec_ref") or "").strip()
    phase = initiative.get("phase")
    if not task_ref and not spec_ref and phase is None:
        return []

    status = "active" if phase else "historical"
    return [
        {
            "task_ref": task_ref or None,
            "spec_ref": spec_ref or None,
            "phase": phase,
            "status": status,
            "role": "primary",
        }
    ]


def _sync_slice_statuses(
    slices: list[dict[str, Any]],
    *,
    completed_ids: set[str],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in slices:
        task_ref = str(item.get("task_ref") or "").strip()
        normalized_item = deepcopy(item)
        if task_ref and task_ref in completed_ids:
            normalized_item["status"] = "complete"
            if str(normalized_item.get("role") or "") == "primary":
                normalized_item["role"] = "historical"
        normalized.append(normalized_item)
    return normalized


def _primary_slice_index(
    initiative: dict[str, Any],
    slices: list[dict[str, Any]],
) -> int | None:
    alias_task_ref = str(initiative.get("task_ref") or "").strip()
    if alias_task_ref:
        for index, item in enumerate(slices):
            if str(item.get("task_ref") or "").strip() == alias_task_ref:
                return index

    for index, item in enumerate(slices):
        if str(item.get("role") or "") == "primary":
            return index
    return 0 if slices else None


def _configure_initiative_for_new_slice(
    initiative: dict[str, Any],
    *,
    item_id: str,
    active_version: str,
    milestone: str,
    completed_ids: set[str],
) -> None:
    _ensure_initiative_dimensions(initiative)
    slices = _sync_slice_statuses(_initiative_slices(initiative), completed_ids=completed_ids)
    primary_index = _primary_slice_index(initiative, slices)
    primary_slice = slices[primary_index] if primary_index is not None else None
    primary_task_ref = str(primary_slice.get("task_ref") or "").strip() if primary_slice else ""
    primary_live = bool(primary_task_ref) and primary_task_ref not in completed_ids

    expected_spec_ref = _expected_spec_ref(milestone=milestone, item_id=item_id)
    new_slice = {
        "task_ref": item_id,
        "spec_ref": expected_spec_ref,
        "phase": active_version,
        "status": "planned" if primary_live else "active",
        "role": "follow-on" if primary_live else "primary",
    }

    if primary_live:
        slices.append(new_slice)
    else:
        if primary_index is not None:
            slices[primary_index]["status"] = "complete"
            slices[primary_index]["role"] = "historical"
        slices.append(new_slice)
        initiative["phase"] = active_version
        initiative["task_ref"] = item_id
        initiative["spec_ref"] = expected_spec_ref

    initiative["slices"] = slices


def _build_backlog_item(
    *,
    item_id: str,
    title: str,
    source: str,
    target_layer: str,
    delivery_pipeline: str,
    target_version: str,
    priority: int,
    created_date: str,
    description: str,
    decision_ref: list[str],
    blocked_by: list[str],
    initiative_ref: str | None,
    roadmap_backed: bool,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "source": source,
        "target_layer": target_layer,
        "delivery_pipeline": delivery_pipeline,
        "status": "pending",
        "target_version": target_version,
        "priority": priority,
        "created_date": created_date,
        "description": description,
    }
    if roadmap_backed:
        item["roadmap_ref"] = item_id
    if initiative_ref:
        item["initiative_ref"] = initiative_ref
    if decision_ref:
        item["decision_ref"] = decision_ref
    if blocked_by:
        item["blocked_by"] = blocked_by
    return item


def _build_roadmap_task(
    *,
    item_id: str,
    title: str,
    initiative_ref: str | None,
    decision_ref: list[str],
) -> dict[str, Any]:
    task: dict[str, Any] = {"id": item_id, "title": title}
    if decision_ref:
        task["decision_ref"] = decision_ref
    if initiative_ref:
        task["initiative_ref"] = initiative_ref
    return task


def _build_spec_stub(
    *,
    item_id: str,
    roadmap_version: str,
    title: str,
    decision_ref: list[str],
    target_layer: str,
    delivery_pipeline: str,
    blocked_by: list[str],
) -> dict[str, Any]:
    suggested_command = (
        "/deliver-full" if delivery_pipeline == "governed" or target_layer == "M1" else "/auto"
    )
    return {
        "id": item_id,
        "roadmap_version": roadmap_version,
        "title": title,
        "decision_ref": decision_ref,
        "intent": f'TODO: describe the intended delivery for "{title}".',
        "problem": f'TODO: explain the current roadmap/backlog pain that "{title}" resolves.',
        "scope": [
            "TODO: list the primary scaffolded artifact or code path",
        ],
        "non_goals": [
            "TODO: list explicit exclusions for this slice",
        ],
        "acceptance": [
            "TODO: define acceptance criteria for this scaffolded slice",
        ],
        "dependencies": blocked_by,
        "delivery": {
            "target_layer": target_layer,
            "delivery_pipeline": delivery_pipeline,
            "suggested_command": suggested_command,
        },
        "elasticity": "Phase 1 = replace placeholder sections with concrete scope. Phase 2 = refine acceptance and follow-on slices once the task is approved.",
    }


def _find_task_in_version(version: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    tasks = version.get("tasks")
    if not isinstance(tasks, list):
        return None
    for item in tasks:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == task_id:
            return item
    return None


def _backlog_row_exists(backlog: dict[str, Any], task_id: str) -> bool:
    items = backlog.get("items")
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip() == task_id:
            return True
        if str(item.get("roadmap_ref") or "").strip() == task_id:
            return True
    return False


def _hydrate_existing_task(
    *,
    args: argparse.Namespace,
    roadmap: dict[str, Any],
    backlog: dict[str, Any],
    active_version: str,
    active_entry: dict[str, Any],
    milestone: str,
    created_date: str,
) -> tuple[str, list[Path]]:
    task_id = str(args.hydrate_task or "").strip()
    if not task_id:
        _die("--hydrate-task requires a non-empty task id")

    task = _find_task_in_version(active_entry, task_id)
    if task is None:
        _die(f"--hydrate-task refused: {task_id!r} is not present in {active_version} tasks")

    if _backlog_row_exists(backlog, task_id):
        _die(f"--hydrate-task refused: backlog row already exists for {task_id}")

    title = str(task.get("title") or "").strip()
    if not title:
        _die(f"--hydrate-task refused: roadmap task {task_id!r} is missing a title")

    task_initiative_ref = str(task.get("initiative_ref") or "").strip() or None
    if args.initiative_ref and task_initiative_ref and args.initiative_ref != task_initiative_ref:
        _die(
            f"--hydrate-task refused: initiative_ref mismatch for {task_id} "
            f"({args.initiative_ref!r} != {task_initiative_ref!r})"
        )

    initiative_ref = args.initiative_ref or task_initiative_ref
    decision_ref = _normalize_decision_refs(args.decision_ref) or _normalize_decision_refs(
        task.get("decision_ref")
    )
    blocked_by = _normalize_blocked_by(args.blocked_by) or _normalize_blocked_by(
        task.get("blocked_by")
    )
    target_layer = args.target_layer or str(task.get("target_layer") or "infrastructure")
    delivery_pipeline = args.delivery_pipeline or str(
        task.get("delivery_pipeline") or "standard"
    )
    target_version = args.target_version or active_version
    priority = args.priority if args.priority is not None else 3
    source = args.source or _default_source(f"roadmap-hydrate-{task_id.lower()}", created_date)
    description = (
        args.description
        or f'TODO: flesh out backlog description for hydrated roadmap task "{title}".'
    )

    backlog["items"].append(
        _build_backlog_item(
            item_id=task_id,
            title=title,
            source=source,
            target_layer=target_layer,
            delivery_pipeline=delivery_pipeline,
            target_version=target_version,
            priority=priority,
            created_date=created_date,
            description=description,
            decision_ref=decision_ref,
            blocked_by=blocked_by,
            initiative_ref=initiative_ref,
            roadmap_backed=True,
        )
    )

    spec_path = args.specs_root / milestone / f"{task_id}.yaml"
    written = [args.backlog_yaml]
    if not spec_path.exists():
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        _dump_yaml(
            spec_path,
            _build_spec_stub(
                item_id=task_id,
                roadmap_version=milestone,
                title=title,
                decision_ref=decision_ref,
                target_layer=target_layer,
                delivery_pipeline=delivery_pipeline,
                blocked_by=blocked_by,
            ),
        )
        written.append(spec_path)

    _dump_yaml(args.backlog_yaml, backlog)
    return task_id, written


def scaffold(args: argparse.Namespace) -> tuple[str, list[Path]]:
    roadmap = _load_yaml(args.roadmap_yaml)
    backlog = _load_yaml(args.backlog_yaml)
    backlog.setdefault("schema_version", 1)
    backlog.setdefault("items", [])

    active_version, active_entry = _ensure_active_version(roadmap, args.active_version)
    milestone = args.milestone or roadmap_task_id.milestone_for_version(active_version)
    created_date = args.created_date or _today_utc()
    target_version = args.target_version or active_version
    decision_ref = _normalize_decision_refs(args.decision_ref)
    blocked_by = _normalize_blocked_by(args.blocked_by)
    target_layer = args.target_layer or "infrastructure"
    delivery_pipeline = args.delivery_pipeline or "standard"
    priority = args.priority if args.priority is not None else 3
    initiative = _find_initiative(roadmap, args.initiative_ref)
    completed_ids = _completed_task_ids(roadmap, backlog)

    if args.hydrate_task:
        if args.namespace != "roadmap":
            _die("--hydrate-task only supports the roadmap namespace")
        return _hydrate_existing_task(
            args=args,
            roadmap=roadmap,
            backlog=backlog,
            active_version=active_version,
            active_entry=active_entry,
            milestone=milestone,
            created_date=created_date,
        )

    if args.namespace == "backlog":
        if not args.title:
            _die("--title is required unless --hydrate-task is used")
        item_id = roadmap_task_id.next_backlog_id(roadmap, backlog, args.specs_root)
        source = args.source or _default_source("backlog-scaffold", created_date)
        description = (
            args.description or f'TODO: flesh out backlog-only description for "{args.title}".'
        )
        backlog["items"].append(
            _build_backlog_item(
                item_id=item_id,
                title=args.title,
                source=source,
                target_layer=target_layer,
                delivery_pipeline=delivery_pipeline,
                target_version=target_version,
                priority=priority,
                created_date=created_date,
                description=description,
                decision_ref=decision_ref,
                blocked_by=blocked_by,
                initiative_ref=args.initiative_ref,
                roadmap_backed=False,
            )
        )
        _dump_yaml(args.backlog_yaml, backlog)
        return item_id, [args.backlog_yaml]

    if not args.title:
        _die("--title is required unless --hydrate-task is used")

    item_id = roadmap_task_id.next_task_id(
        roadmap,
        backlog,
        args.specs_root,
        milestone=milestone,
        active_version=active_version,
    )
    source = args.source or _default_source("roadmap-scaffold", created_date)
    description = args.description or f'TODO: flesh out backlog description for "{args.title}".'

    backlog["items"].append(
        _build_backlog_item(
            item_id=item_id,
            title=args.title,
            source=source,
            target_layer=target_layer,
            delivery_pipeline=delivery_pipeline,
            target_version=target_version,
            priority=priority,
            created_date=created_date,
            description=description,
            decision_ref=decision_ref,
            blocked_by=blocked_by,
            initiative_ref=args.initiative_ref,
            roadmap_backed=True,
        )
    )

    active_entry.setdefault("tasks", [])
    active_entry["tasks"].append(
        _build_roadmap_task(
            item_id=item_id,
            title=args.title,
            initiative_ref=args.initiative_ref,
            decision_ref=decision_ref,
        )
    )

    spec_path = args.specs_root / milestone / f"{item_id}.yaml"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_stub = _build_spec_stub(
        item_id=item_id,
        roadmap_version=milestone,
        title=args.title,
        decision_ref=decision_ref,
        target_layer=target_layer,
        delivery_pipeline=delivery_pipeline,
        blocked_by=blocked_by,
    )
    _dump_yaml(spec_path, spec_stub)

    if initiative is not None:
        _configure_initiative_for_new_slice(
            initiative,
            item_id=item_id,
            active_version=active_version,
            milestone=milestone,
            completed_ids=completed_ids,
        )

    _dump_yaml(args.backlog_yaml, backlog)
    _dump_yaml(args.roadmap_yaml, roadmap)
    return item_id, [args.backlog_yaml, args.roadmap_yaml, spec_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a coherent roadmap/backlog/spec scaffold for a new task.",
    )
    parser.add_argument("--title", help="Task title to scaffold.")
    parser.add_argument(
        "--hydrate-task",
        help="Hydrate backlog/spec state for an existing active-version roadmap task.",
    )
    parser.add_argument(
        "--namespace",
        choices=("roadmap", "backlog"),
        default="roadmap",
        help="Scaffold a roadmap-backed task or a backlog-only BL item.",
    )
    parser.add_argument("--roadmap-yaml", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--backlog-yaml", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--specs-root", type=Path, default=DEFAULT_SPECS_ROOT)
    parser.add_argument("--active-version", type=str, default=None)
    parser.add_argument("--milestone", type=str, default=None)
    parser.add_argument("--target-version", type=str, default=None)
    parser.add_argument("--initiative-ref", type=str, default=None)
    parser.add_argument("--decision-ref", nargs="*", default=[])
    parser.add_argument("--blocked-by", nargs="*", default=[])
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--description", type=str, default=None)
    parser.add_argument("--target-layer", type=str, default=None)
    parser.add_argument("--delivery-pipeline", type=str, default=None)
    parser.add_argument("--priority", type=int, default=None)
    parser.add_argument("--created-date", type=str, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.title and not args.hydrate_task:
        parser.error("either --title or --hydrate-task is required")
    item_id, written = scaffold(args)
    print(item_id)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
