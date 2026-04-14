#!/usr/bin/env python3
"""Exact-id reinforcement_count updates for existing M3 episodes."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EPISODES_PATH = Path(".azoth") / "memory" / "episodes.jsonl"


class ReinforcementError(RuntimeError):
    """Raised when an exact-id reinforcement update cannot be applied."""


@dataclass(frozen=True)
class ReinforcementResult:
    episode_id: str
    session_id: str
    changed: bool
    reinforcement_count: int


def load_episodes(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ReinforcementError(f"episodes file not found: {path}")

    episodes: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReinforcementError(
                    f"invalid JSON in {path} line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise ReinforcementError(f"expected JSON object in {path} line {line_number}")
            episodes.append(record)
    return episodes


def _episode_context(episode: dict[str, Any]) -> dict[str, Any]:
    context = episode.get("context")
    if isinstance(context, dict):
        return context
    context = {}
    episode["context"] = context
    return context


def increment_reinforcement_count(
    repo_root: Path,
    episode_id: str,
    session_id: str,
    *,
    source: str,
) -> ReinforcementResult:
    """Increment reinforcement_count once per session for an exact episode id."""

    episodes_path = repo_root / EPISODES_PATH
    episodes = load_episodes(episodes_path)

    for episode in episodes:
        if str(episode.get("id") or "") != episode_id:
            continue

        context = _episode_context(episode)
        sessions = context.get("reinforced_by_sessions")
        if not isinstance(sessions, list):
            sessions = []
            context["reinforced_by_sessions"] = sessions

        if session_id in sessions:
            return ReinforcementResult(
                episode_id=episode_id,
                session_id=session_id,
                changed=False,
                reinforcement_count=int(episode.get("reinforcement_count") or 0),
            )

        current = int(episode.get("reinforcement_count") or 0)
        episode["reinforcement_count"] = current + 1
        sessions.append(session_id)
        context["last_reinforced_source"] = source
        context["last_reinforced_session"] = session_id

        with open(episodes_path, "w", encoding="utf-8") as handle:
            for record in episodes:
                handle.write(json.dumps(record) + "\n")

        return ReinforcementResult(
            episode_id=episode_id,
            session_id=session_id,
            changed=True,
            reinforcement_count=current + 1,
        )

    raise ReinforcementError(f"episode id not found: {episode_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Increment reinforcement_count for an exact prior episode id."
    )
    parser.add_argument("episode_id", help="Existing episode id, for example ep-173")
    parser.add_argument(
        "--session-id",
        required=True,
        help="Active session id used to enforce once-per-session idempotency.",
    )
    parser.add_argument(
        "--source",
        default="manual",
        help="Human-confirmed source for the reinforcement update (for audit context).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="Repo root containing .azoth/memory/episodes.jsonl.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = increment_reinforcement_count(
        Path(args.repo_root),
        args.episode_id,
        args.session_id,
        source=args.source,
    )
    if result.changed:
        print(
            f"reinforcement updated: {result.episode_id} -> {result.reinforcement_count} "
            f"(session {result.session_id})"
        )
    else:
        print(
            f"reinforcement unchanged: {result.episode_id} already updated in "
            f"session {result.session_id}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
