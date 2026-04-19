"""P1-017 runtime tests for exact-id reinforcement updates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import reinforcement_count  # noqa: E402


def _episodes_path(tmp_path: Path) -> Path:
    path = tmp_path / ".azoth" / "memory" / "episodes.jsonl"
    path.parent.mkdir(parents=True)
    return path


def _write_episode(path: Path, episode: dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(episode) + "\n")


def _read_episodes(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_increment_reinforcement_count_targets_exact_episode_id(tmp_path: Path) -> None:
    episodes_path = _episodes_path(tmp_path)
    _write_episode(
        episodes_path,
        {
            "id": "ep-010",
            "reinforcement_count": 0,
            "context": {},
        },
    )
    _write_episode(
        episodes_path,
        {
            "id": "ep-011",
            "reinforcement_count": 3,
            "context": {},
        },
    )

    result = reinforcement_count.increment_reinforcement_count(
        tmp_path,
        "ep-010",
        "2026-04-14-bl-041",
        source="promote",
    )

    episodes = _read_episodes(episodes_path)
    assert result.changed is True
    assert episodes[0]["reinforcement_count"] == 1
    assert episodes[1]["reinforcement_count"] == 3
    assert episodes[0]["context"]["reinforced_by_sessions"] == ["2026-04-14-bl-041"]
    assert episodes[0]["context"]["last_reinforced_source"] == "promote"


def test_increment_reinforcement_count_is_idempotent_per_session(tmp_path: Path) -> None:
    episodes_path = _episodes_path(tmp_path)
    _write_episode(
        episodes_path,
        {
            "id": "ep-010",
            "reinforcement_count": 1,
            "context": {"reinforced_by_sessions": ["older-session"]},
        },
    )

    first = reinforcement_count.increment_reinforcement_count(
        tmp_path,
        "ep-010",
        "2026-04-14-bl-041",
        source="closeout",
    )
    second = reinforcement_count.increment_reinforcement_count(
        tmp_path,
        "ep-010",
        "2026-04-14-bl-041",
        source="closeout",
    )

    episodes = _read_episodes(episodes_path)
    assert first.changed is True
    assert second.changed is False
    assert episodes[0]["reinforcement_count"] == 2
    assert episodes[0]["context"]["reinforced_by_sessions"] == [
        "older-session",
        "2026-04-14-bl-041",
    ]


def test_increment_reinforcement_count_requires_exact_existing_id(tmp_path: Path) -> None:
    episodes_path = _episodes_path(tmp_path)
    _write_episode(episodes_path, {"id": "ep-010", "reinforcement_count": 0, "context": {}})

    with pytest.raises(reinforcement_count.ReinforcementError, match="episode id not found"):
        reinforcement_count.increment_reinforcement_count(
            tmp_path,
            "ep-999",
            "2026-04-14-bl-041",
            source="promote",
        )
