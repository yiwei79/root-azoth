#!/usr/bin/env python3
"""Exact-id reinforcement_count updates for existing M3 episodes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from episode_store import load_episode_records, rewrite_episode_records


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
    try:
        return load_episode_records(path)
    except RuntimeError as exc:
        raise ReinforcementError(str(exc)) from exc


def _episode_context(episode: dict[str, Any]) -> dict[str, Any]:
    context = episode.get("context")
    if isinstance(context, dict):
        return context
    if context is not None:
        raise ReinforcementError("episode context is malformed: expected a JSON object")
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
    matches = [
        episode for episode in episodes if str(episode.get("id") or "") == episode_id
    ]
    if len(matches) > 1:
        raise ReinforcementError(
            f"episode id is ambiguous: {episode_id} matches multiple stored episodes"
        )

    for episode in episodes:
        if str(episode.get("id") or "") != episode_id:
            continue

        context = _episode_context(episode)
        sessions = context.get("reinforced_by_sessions")
        if sessions is None:
            sessions = []
            context["reinforced_by_sessions"] = sessions
        elif not isinstance(sessions, list):
            raise ReinforcementError(
                "episode reinforcement audit metadata is malformed: "
                "'reinforced_by_sessions' must be a list"
            )

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

        try:
            rewrite_episode_records(episodes_path, episodes)
        except RuntimeError as exc:
            raise ReinforcementError(str(exc)) from exc

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
