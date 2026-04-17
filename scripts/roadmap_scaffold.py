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


def _ensure_active_version(roadmap: dict[str, Any], active_version: str | None) -> tuple[str, dict[str, Any]]:
    resolved = active_version or str(roadmap.get("active_version") or "").strip()
    if not resolved:
        _die("could not resolve active version from roadmap.yaml; pass --active-version")

    for version in roadmap.get("versions") or []:
        if isinstance(version, dict) and version.get("id") == resolved:
            return resolved, version

    _die(f"active version {resolved!r} was not found in roadmap.yaml versions[]")


def _find_initiative(
    roadmap: dict[str, Any], initiative_ref: str | None
) -> dict[str, Any] | None:
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
    suggested_command = "/deliver-full" if delivery_pipeline == "governed" or target_layer == "M1" else "/auto"
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
    initiative = _find_initiative(roadmap, args.initiative_ref)

    if args.namespace == "backlog":
        item_id = roadmap_task_id.next_backlog_id(roadmap, backlog, args.specs_root)
        source = args.source or _default_source("backlog-scaffold", created_date)
        description = args.description or f'TODO: flesh out backlog-only description for "{args.title}".'
        backlog["items"].append(
            _build_backlog_item(
                item_id=item_id,
                title=args.title,
                source=source,
                target_layer=args.target_layer,
                delivery_pipeline=args.delivery_pipeline,
                target_version=target_version,
                priority=args.priority,
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
            target_layer=args.target_layer,
            delivery_pipeline=args.delivery_pipeline,
            target_version=target_version,
            priority=args.priority,
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
        target_layer=args.target_layer,
        delivery_pipeline=args.delivery_pipeline,
        blocked_by=blocked_by,
    )
    _dump_yaml(spec_path, spec_stub)

    if initiative is not None:
        existing_task_ref = initiative.get("task_ref")
        if existing_task_ref and existing_task_ref != item_id:
            _die(
                f"initiative {args.initiative_ref!r} already points at task_ref {existing_task_ref!r}; "
                "manual update required"
            )
        existing_phase = initiative.get("phase")
        if existing_phase not in (None, active_version):
            _die(
                f"initiative {args.initiative_ref!r} already has phase {existing_phase!r}; "
                "manual rescheduling required"
            )
        existing_spec_ref = initiative.get("spec_ref")
        expected_spec_ref = f".azoth/roadmap-specs/{milestone}/{item_id}.yaml"
        if existing_spec_ref and existing_spec_ref != expected_spec_ref:
            _die(
                f"initiative {args.initiative_ref!r} already points at spec_ref {existing_spec_ref!r}; "
                "manual update required"
            )
        initiative["phase"] = active_version
        initiative["task_ref"] = item_id
        initiative["spec_ref"] = expected_spec_ref

    _dump_yaml(args.backlog_yaml, backlog)
    _dump_yaml(args.roadmap_yaml, roadmap)
    return item_id, [args.backlog_yaml, args.roadmap_yaml, spec_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a coherent roadmap/backlog/spec scaffold for a new task.",
    )
    parser.add_argument("--title", required=True, help="Task title to scaffold.")
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
    parser.add_argument("--target-layer", type=str, default="infrastructure")
    parser.add_argument("--delivery-pipeline", type=str, default="standard")
    parser.add_argument("--priority", type=int, default=3)
    parser.add_argument("--created-date", type=str, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    item_id, written = scaffold(args)
    print(item_id)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
