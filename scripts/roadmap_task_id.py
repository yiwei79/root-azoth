#!/usr/bin/env python3
"""
roadmap_task_id.py — resolve the next roadmap/backlog task id from roadmap policy.

Usage:
  python scripts/roadmap_task_id.py
  python scripts/roadmap_task_id.py --namespace backlog
  python scripts/roadmap_task_id.py --milestone v0.3.0
  python scripts/roadmap_task_id.py --active-version v0.2.0-p2
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROADMAP = ROOT / ".azoth" / "roadmap.yaml"
DEFAULT_BACKLOG = ROOT / ".azoth" / "backlog.yaml"
DEFAULT_SPECS_ROOT = ROOT / ".azoth" / "roadmap-specs"
BACKLOG_PREFIX = "BL"
BACKLOG_WIDTH = 3

_ID_RE = re.compile(r"^([A-Z][A-Z0-9]*)-(\d+)$")
_SLICE_RE = re.compile(r"^(v\d+\.\d+\.\d+)-p\d+$")


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - defensive
        _die(f"failed to load YAML from {path}: {exc}")


def milestone_for_version(version_id: str) -> str:
    match = _SLICE_RE.match(version_id.strip())
    if match:
        return match.group(1)
    return version_id.strip()


def resolve_namespace_policy(roadmap: dict[str, Any], milestone: str) -> tuple[str, int]:
    policy = roadmap.get("task_id_policy") or {}
    legacy = policy.get("legacy_milestones") or []
    frozen_legacy: tuple[str, int] | None = None
    for item in legacy:
        if not isinstance(item, dict):
            continue
        if item.get("milestone") == milestone:
            prefix = str(item.get("prefix") or "").strip()
            width = int(item.get("width", 3))
            if not prefix:
                _die(f"legacy task-id policy for {milestone} is missing prefix")
            if bool(item.get("frozen")):
                frozen_legacy = (prefix, width)
                break
            return prefix, width

    future = policy.get("future_default") or {}
    if future:
        prefix = str(future.get("prefix") or "T").strip()
        width = int(future.get("width", 3))
        if not prefix:
            _die("future_default task-id policy is missing prefix")
        return prefix, width

    if frozen_legacy is not None:
        return frozen_legacy

    if milestone == "v0.2.0" and not future and not legacy:
        return "P1", 3
    return "T", 3


def _maybe_collect_id(raw: Any, used: set[tuple[str, int]]) -> None:
    if not isinstance(raw, str):
        return
    match = _ID_RE.match(raw.strip())
    if match:
        used.add((match.group(1), int(match.group(2))))


def _collect_block_refs(block: dict[str, Any], used: set[tuple[str, int]]) -> None:
    _maybe_collect_id(block.get("id"), used)
    _maybe_collect_id(block.get("task_ref"), used)
    _maybe_collect_id(block.get("roadmap_ref"), used)
    for ref in block.get("blocked_by") or []:
        _maybe_collect_id(ref, used)


def collect_used_ids(
    roadmap: dict[str, Any], backlog: dict[str, Any], specs_dir: Path
) -> set[tuple[str, int]]:
    used: set[tuple[str, int]] = set()

    for item in roadmap.get("tasks") or []:
        if isinstance(item, dict):
            _collect_block_refs(item, used)

    for version in roadmap.get("versions") or []:
        if not isinstance(version, dict):
            continue
        for field in ("tasks", "completed_tasks", "deferred_tasks"):
            for item in version.get(field) or []:
                if isinstance(item, dict):
                    _collect_block_refs(item, used)
        for ref in version.get("pending_task_refs") or []:
            _maybe_collect_id(ref, used)

    for initiative in roadmap.get("initiatives") or []:
        if isinstance(initiative, dict):
            _collect_block_refs(initiative, used)

    for item in backlog.get("items") or []:
        if isinstance(item, dict):
            _collect_block_refs(item, used)

    if specs_dir.is_dir():
        for path in specs_dir.iterdir():
            if path.is_file():
                _maybe_collect_id(path.stem, used)

    return used


def next_backlog_id(
    roadmap: dict[str, Any],
    backlog: dict[str, Any],
    specs_root: Path,
    *,
    prefix: str = BACKLOG_PREFIX,
    width: int = BACKLOG_WIDTH,
) -> str:
    used = collect_used_ids(roadmap, backlog, specs_root)
    max_num = max((num for used_prefix, num in used if used_prefix == prefix), default=0)
    return f"{prefix}-{max_num + 1:0{width}d}"


def next_task_id(
    roadmap: dict[str, Any],
    backlog: dict[str, Any],
    specs_root: Path,
    *,
    milestone: str | None = None,
    active_version: str | None = None,
) -> str:
    selected_version = active_version or str(roadmap.get("active_version") or "").strip()
    if milestone is None:
        if not selected_version:
            _die(
                "could not resolve milestone: provide --milestone or ensure roadmap active_version exists"
            )
        milestone = milestone_for_version(selected_version)

    prefix, width = resolve_namespace_policy(roadmap, milestone)
    specs_dir = specs_root / milestone
    used = collect_used_ids(roadmap, backlog, specs_dir)
    max_num = max((num for used_prefix, num in used if used_prefix == prefix), default=0)
    return f"{prefix}-{max_num + 1:0{width}d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the next roadmap/backlog task id.")
    parser.add_argument("--roadmap-yaml", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--backlog-yaml", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--specs-root", type=Path, default=DEFAULT_SPECS_ROOT)
    parser.add_argument("--active-version", type=str, default=None)
    parser.add_argument("--milestone", type=str, default=None)
    parser.add_argument(
        "--namespace",
        choices=("roadmap", "backlog"),
        default="roadmap",
        help="Select the id family to mint. 'roadmap' uses task_id_policy; 'backlog' emits BL ids.",
    )
    args = parser.parse_args()

    roadmap = load_yaml(args.roadmap_yaml)
    backlog = load_yaml(args.backlog_yaml)
    if args.namespace == "backlog":
        print(next_backlog_id(roadmap, backlog, args.specs_root))
        return

    print(
        next_task_id(
            roadmap,
            backlog,
            args.specs_root,
            milestone=args.milestone,
            active_version=args.active_version,
        )
    )


if __name__ == "__main__":
    main()
