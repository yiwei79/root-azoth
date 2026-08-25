#!/usr/bin/env python3
"""
Azoth Sync — Deterministic pattern extraction from source frameworks.

5-phase extraction pipeline:
  1. SCAN    — Read source framework, build inventory with hashes
  2. DIFF    — Compare against Azoth's current state
  3. PROPOSE — Apply Promotion Rubric to each delta
  4. ALIGN   — Present proposals to human for approval
  5. SANITIZE — Strip org-specific references from approved items

Usage:
  python scripts/azoth-sync.py --source /path/to/framework
  python scripts/azoth-sync.py --source /path/to/framework --dry-run
  python scripts/azoth-sync.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yaml_helpers import safe_load_yaml_path

# ── Constants ───────────────────────────────────────────────────

AZOTH_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = AZOTH_ROOT / "sync-config.yaml"
SYNC_LOG = AZOTH_ROOT / ".azoth" / "sync-log.jsonl"

SYNCABLE_EXTENSIONS = {".md", ".yaml", ".yml", ".json", ".py", ".txt"}
SYNCABLE_DIRS = {"skills", "agents", "instructions", "commands", "pipelines"}
# Directories within the source that contain agent/skill content (may be nested)
SYNCABLE_PARENT_DIRS = {
    ".agents",
    ".claude",
    "skills",
    "agents",
    "instructions",
    "commands",
    "pipelines",
}


# ── Phase 1: SCAN ──────────────────────────────────────────────


def _is_excluded(rel_path: Path, strip_paths: list[str]) -> bool:
    """Check if a path should be excluded based on strip_paths config."""
    rel_str = str(rel_path)
    return any(rel_str.startswith(excluded) for excluded in strip_paths)


def scan_source(
    source_path: Path,
    strip_paths: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build inventory of syncable files in the source framework."""
    inventory: dict[str, dict[str, Any]] = {}
    strip_paths = strip_paths or []

    if not source_path.is_dir():
        print(f"[scan] ERROR: Source path does not exist: {source_path}", file=sys.stderr)
        sys.exit(1)

    for filepath in sorted(source_path.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix not in SYNCABLE_EXTENSIONS:
            continue

        rel_path = filepath.relative_to(source_path)

        # Exclude paths from strip_paths early (before proposing)
        if _is_excluded(rel_path, strip_paths):
            continue

        # Only sync from known agent/skill directories
        top_dir = rel_path.parts[0] if rel_path.parts else ""
        if top_dir not in SYNCABLE_PARENT_DIRS:
            continue

        content = filepath.read_text(encoding="utf-8", errors="replace")
        file_hash = hashlib.sha256(content.encode()).hexdigest()

        inventory[str(rel_path)] = {
            "path": str(rel_path),
            "hash": file_hash,
            "size": len(content),
            "lines": content.count("\n") + 1,
        }

    print(f"[scan] Found {len(inventory)} syncable files in {source_path}")
    return inventory


# ── Phase 2: DIFF ──────────────────────────────────────────────


def diff_inventories(
    source: dict[str, dict[str, Any]],
    target_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Compare source inventory against Azoth's current state."""
    results: dict[str, list[dict[str, Any]]] = {
        "new": [],
        "modified": [],
        "unchanged": [],
    }

    for rel_path, source_info in source.items():
        target_file = target_root / rel_path

        if not target_file.exists():
            results["new"].append(source_info)
            continue

        target_content = target_file.read_text(encoding="utf-8", errors="replace")
        target_hash = hashlib.sha256(target_content.encode()).hexdigest()

        if target_hash != source_info["hash"]:
            results["modified"].append(
                {
                    **source_info,
                    "target_hash": target_hash,
                }
            )
        else:
            results["unchanged"].append(source_info)

    print(
        f"[diff] New: {len(results['new'])}, "
        f"Modified: {len(results['modified'])}, "
        f"Unchanged: {len(results['unchanged'])}"
    )
    return results


# ── Phase 3: PROPOSE ──────────────────────────────────────────


def propose_actions(
    diff: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Apply Promotion Rubric to each delta. Returns proposals."""
    proposals: list[dict[str, Any]] = []

    for item in diff["new"]:
        proposals.append(
            {
                "action": "add",
                "path": item["path"],
                "size": item["size"],
                "lines": item["lines"],
                "rubric": "B (reuse test) — new pattern from source",
                "status": "pending",
            }
        )

    for item in diff["modified"]:
        proposals.append(
            {
                "action": "update",
                "path": item["path"],
                "size": item["size"],
                "lines": item["lines"],
                "rubric": "D (maturity test) — source has evolved",
                "status": "pending",
            }
        )

    print(f"[propose] Generated {len(proposals)} proposals")
    return proposals


# ── Phase 4: ALIGN ────────────────────────────────────────────


def align_with_human(
    proposals: list[dict[str, Any]],
    *,
    auto_approve: bool = False,
) -> list[dict[str, Any]]:
    """Present proposals to human for approval."""
    if not proposals:
        print("[align] No proposals to review.")
        return []

    print("\n" + "=" * 60)
    print("  SYNC PROPOSALS — Review Required")
    print("=" * 60)

    for i, prop in enumerate(proposals, 1):
        status_icon = "+" if prop["action"] == "add" else "~"
        print(f"\n  [{i}] {status_icon} {prop['path']}")
        print(f"      Action: {prop['action']} ({prop['lines']} lines)")
        print(f"      Rubric: {prop['rubric']}")

    print("\n" + "-" * 60)

    if auto_approve:
        print("[align] Auto-approving all proposals (--yes flag)")
        for prop in proposals:
            prop["status"] = "approved"
        return proposals

    print("\nOptions:")
    print("  a    — approve all")
    print("  r    — reject all")
    print("  1,3  — approve specific (comma-separated numbers)")
    print("  q    — quit without changes")

    choice = input("\nYour choice: ").strip().lower()

    if choice == "a":
        for prop in proposals:
            prop["status"] = "approved"
    elif choice == "r":
        for prop in proposals:
            prop["status"] = "rejected"
    elif choice == "q":
        print("[align] Aborted by user.")
        sys.exit(0)
    else:
        approved_indices = set()
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit():
                approved_indices.add(int(part))
        for i, prop in enumerate(proposals, 1):
            prop["status"] = "approved" if i in approved_indices else "rejected"

    approved = [p for p in proposals if p["status"] == "approved"]
    rejected = [p for p in proposals if p["status"] == "rejected"]
    print(f"[align] Approved: {len(approved)}, Rejected: {len(rejected)}")
    return proposals


# ── Phase 5: SANITIZE ─────────────────────────────────────────


def load_sanitize_config(config_path: Path) -> dict[str, Any]:
    """Load sanitization rules from sync-config.yaml."""
    if not config_path.exists():
        print(f"[sanitize] WARNING: Config not found at {config_path}, using defaults")
        return {"strip_patterns": [], "strip_paths": []}

    config = safe_load_yaml_path(config_path) or {}

    return config.get("sanitize", {"strip_patterns": [], "strip_paths": []})


def sanitize_content(content: str, config: dict[str, Any]) -> str:
    """Strip org-specific references from content."""
    for pattern in config.get("strip_patterns", []):
        content = content.replace(pattern, "{{REDACTED}}")
    return content


def execute_sync(
    proposals: list[dict[str, Any]],
    source_path: Path,
    target_root: Path,
    config: dict[str, Any],
    *,
    dry_run: bool = False,
) -> int:
    """Copy approved files from source to target, sanitizing content."""
    approved = [p for p in proposals if p["status"] == "approved"]
    synced = 0

    for prop in approved:
        source_file = source_path / prop["path"]
        target_file = target_root / prop["path"]

        if not source_file.exists():
            print(f"[sanitize] SKIP: Source file missing: {source_file}")
            continue

        # Check if path should be excluded
        skip = False
        for excluded in config.get("strip_paths", []):
            if prop["path"].startswith(excluded):
                print(f"[sanitize] SKIP (excluded path): {prop['path']}")
                skip = True
                break
        if skip:
            continue

        content = source_file.read_text(encoding="utf-8", errors="replace")
        content = sanitize_content(content, config)

        if dry_run:
            print(f"[dry-run] Would write: {target_file} ({len(content)} bytes)")
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            print(f"[sanitize] Wrote: {target_file}")

        synced += 1

    return synced


# ── Logging ───────────────────────────────────────────────────


def log_sync(
    source_path: Path,
    proposals: list[dict[str, Any]],
    synced: int,
    *,
    dry_run: bool = False,
) -> None:
    """Append sync event to sync log."""
    SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(source_path),
        "proposals": len(proposals),
        "approved": len([p for p in proposals if p["status"] == "approved"]),
        "rejected": len([p for p in proposals if p["status"] == "rejected"]),
        "synced": synced,
        "dry_run": dry_run,
    }

    with open(SYNC_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── CLI ───────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Azoth Sync — Extract patterns from source frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/azoth-sync.py --source ~/framework
  python scripts/azoth-sync.py --source ~/framework --dry-run
  python scripts/azoth-sync.py --source ~/framework --yes
        """,
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to source framework directory",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to sync config (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve all proposals (skip human alignment)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    source_path = args.source.resolve()
    config = load_sanitize_config(args.config)

    print(f"\n{'=' * 60}")
    print(f"  Azoth Sync — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Source: {source_path}")
    print(f"  Target: {AZOTH_ROOT}")
    print(f"  Mode:   {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'=' * 60}\n")

    # Phase 1: SCAN
    inventory = scan_source(source_path, strip_paths=config.get("strip_paths", []))
    if not inventory:
        print("[sync] No syncable files found. Done.")
        return

    # Phase 2: DIFF
    diff = diff_inventories(inventory, AZOTH_ROOT)
    if not diff["new"] and not diff["modified"]:
        print("[sync] Everything up to date. No changes needed.")
        return

    # Phase 3: PROPOSE
    proposals = propose_actions(diff)

    # Phase 4: ALIGN
    proposals = align_with_human(proposals, auto_approve=args.yes)

    # Phase 5: SANITIZE + EXECUTE
    synced = execute_sync(
        proposals,
        source_path,
        AZOTH_ROOT,
        config,
        dry_run=args.dry_run,
    )

    # Log
    log_sync(source_path, proposals, synced, dry_run=args.dry_run)

    print(f"\n[sync] Complete. {synced} files {'would be ' if args.dry_run else ''}synced.")


if __name__ == "__main__":
    main()
