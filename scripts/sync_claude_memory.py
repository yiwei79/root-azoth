#!/usr/bin/env python3
"""Replay deferred Claude memory mirroring from repo-local Azoth state."""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

import do_closeout

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _latest_episode(repo_root: pathlib.Path) -> dict[str, Any]:
    episodes = do_closeout.load_episode_records(repo_root / ".azoth" / "memory" / "episodes.jsonl")
    return episodes[-1] if episodes else {}


def _next_action(repo_root: pathlib.Path, pending: dict[str, Any]) -> str:
    pending_next_action = str(pending.get("next_action") or "").strip()
    if pending_next_action:
        return pending_next_action
    session_state = do_closeout.load_yaml(repo_root / ".azoth" / "session-state.md")
    session_next_action = str(session_state.get("next_action") or "").strip()
    if session_next_action:
        return session_next_action
    return do_closeout.default_next_action()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay deferred Claude memory mirroring from repo-local Azoth state."
    )
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="Repository root containing .azoth/ state.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    pending_path = repo_root / do_closeout.CLAUDE_MEMORY_SYNC_PENDING
    pending = do_closeout.load_json(pending_path)
    latest_episode = _latest_episode(repo_root)
    next_action = _next_action(repo_root, pending)

    try:
        do_closeout.write_claude_memory_mirror(
            repo_root,
            latest_episode=latest_episode,
            next_action=next_action,
        )
    except PermissionError as exc:
        print(
            "Claude memory sync blocked — grant host write access to ~/.claude/.../memory/ "
            f"and rerun `python3 scripts/sync_claude_memory.py` ({exc})"
        )
        return 1
    except OSError as exc:
        print(f"Claude memory sync failed: {exc}")
        return 1

    synced_path = do_closeout.mark_claude_memory_sync_pending_synced(repo_root)
    if synced_path is not None:
        print(f"Claude memory sync completed and marked pending artifact synced: {synced_path}")
    else:
        print("Claude memory sync completed from latest repo state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
