from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import episode_store  # noqa: E402


def _episode(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": "ep-001",
        "timestamp": "2026-04-21T00:00:00Z",
        "session_id": "sess-001",
        "type": "success",
        "goal": "Test episode",
        "summary": "Recorded safely.",
        "lessons": [],
        "tags": ["memory"],
        "reinforcement_count": 0,
        "context": {},
    }
    record.update(overrides)
    return record


def test_append_episode_record_requires_verbatim_pair(tmp_path: Path) -> None:
    path = tmp_path / "episodes.jsonl"
    record = _episode(context={episode_store.VERBATIM_SOURCE_FIELD: "scope-gate.json"})

    with pytest.raises(episode_store.EpisodeStoreError, match="must set both"):
        episode_store.append_episode_record(path, record)


def test_append_episode_record_rejects_lossy_context_keys(tmp_path: Path) -> None:
    path = tmp_path / "episodes.jsonl"
    record = _episode(
        context={
            "compressed_payload": {"goal": "lossy"},
            episode_store.VERBATIM_SOURCE_FIELD: "scope-gate.json",
            episode_store.VERBATIM_PAYLOAD_FIELD: {"goal": "raw"},
        }
    )

    with pytest.raises(episode_store.EpisodeStoreError, match="lossy context keys"):
        episode_store.append_episode_record(path, record)


def test_append_episode_record_round_trips_verbatim_payload(tmp_path: Path) -> None:
    path = tmp_path / "episodes.jsonl"
    record = episode_store.with_verbatim_context(
        _episode(),
        source="scope-gate.json",
        payload={"goal": "P1-020", "backlog_id": "P1-020"},
    )

    episode_store.append_episode_record(path, record, require_verbatim=True)
    loaded = episode_store.load_episode_records(path)

    assert loaded == [record]


def test_merge_episode_records_dedupes_exact_rows_and_keeps_verbatim_payload() -> None:
    target = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", session_id="capture"),
            source="scope-gate.json",
            payload={"goal": "first"},
        ),
        _episode(id="ep-112", session_id="closeout", summary="second"),
    ]
    producer = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", session_id="capture"),
            source="scope-gate.json",
            payload={"goal": "first"},
        ),
        episode_store.with_verbatim_context(
            _episode(id="ep-130", session_id="new", summary="third"),
            source="scope-gate.json",
            payload={"goal": "third"},
        ),
    ]

    merged = episode_store.merge_episode_records(target, producer)

    assert merged == [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", session_id="capture"),
            source="scope-gate.json",
            payload={"goal": "first"},
        ),
        _episode(id="ep-112", session_id="closeout", summary="second"),
        episode_store.with_verbatim_context(
            _episode(id="ep-130", session_id="new", summary="third"),
            source="scope-gate.json",
            payload={"goal": "third"},
        ),
    ]


def test_merge_episode_records_reconciles_same_id_rewrite_when_verbatim_payload_matches() -> None:
    target = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", reinforcement_count=0),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]
    producer = [
        episode_store.with_verbatim_context(
            _episode(
                id="ep-112",
                reinforcement_count=1,
                context={
                    "reinforced_by_sessions": ["sess-002"],
                    "last_reinforced_session": "sess-002",
                    "last_reinforced_source": "closeout",
                },
            ),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]

    merged = episode_store.merge_episode_records(target, producer)

    assert merged == producer


def test_merge_episode_records_rejects_non_reinforcement_same_id_rewrite() -> None:
    target = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", summary="original"),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]
    producer = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", summary="rewritten"),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]

    with pytest.raises(episode_store.EpisodeStoreError, match="non-audited rewrite"):
        episode_store.merge_episode_records(target, producer)


def test_merge_episode_records_rejects_legacy_same_id_rewrite() -> None:
    target = [_episode(id="ep-112", summary="original")]
    producer = [_episode(id="ep-112", summary="rewritten")]

    with pytest.raises(episode_store.EpisodeStoreError, match="ambiguous same-id rewrite"):
        episode_store.merge_episode_records(target, producer)


def test_merge_episode_records_rejects_duplicate_verbatim_backed_target_identity() -> None:
    target = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", session_id="capture-a"),
            source="scope-gate.json",
            payload={"goal": "first"},
        ),
        episode_store.with_verbatim_context(
            _episode(id="ep-112", session_id="capture-b"),
            source="scope-gate.json",
            payload={"goal": "first"},
        ),
    ]

    with pytest.raises(episode_store.EpisodeStoreError, match="duplicate verbatim-backed"):
        episode_store.merge_episode_records(target, [])


def test_merge_episode_records_rejects_duplicate_new_producer_episode_id() -> None:
    producer = [
        _episode(id="ep-112", session_id="producer-a", summary="first"),
        _episode(id="ep-112", session_id="producer-b", summary="second"),
    ]

    with pytest.raises(episode_store.EpisodeStoreError, match="ambiguous same-id rewrite"):
        episode_store.merge_episode_records([], producer)


def test_merge_episode_records_rejects_exact_duplicate_target_row() -> None:
    row = episode_store.with_verbatim_context(
        _episode(id="ep-112"),
        source="scope-gate.json",
        payload={"goal": "first"},
    )

    with pytest.raises(episode_store.EpisodeStoreError, match="duplicate exact episode row"):
        episode_store.merge_episode_records([row, row], [])


def test_merge_episode_records_rejects_exact_duplicate_producer_row() -> None:
    row = episode_store.with_verbatim_context(
        _episode(id="ep-112"),
        source="scope-gate.json",
        payload={"goal": "first"},
    )

    with pytest.raises(episode_store.EpisodeStoreError, match="duplicate exact episode row"):
        episode_store.merge_episode_records([], [row, row])


def test_merge_episode_records_rejects_malformed_reinforcement_audit_metadata() -> None:
    target = [
        episode_store.with_verbatim_context(
            _episode(id="ep-112", reinforcement_count=0),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]
    producer = [
        episode_store.with_verbatim_context(
            _episode(
                id="ep-112",
                reinforcement_count=1,
                context={
                    "reinforced_by_sessions": ["sess-002"],
                    "last_reinforced_session": "wrong-session",
                    "last_reinforced_source": "closeout",
                },
            ),
            source="scope-gate.json",
            payload={"goal": "first"},
        )
    ]

    with pytest.raises(episode_store.EpisodeStoreError, match="non-audited rewrite"):
        episode_store.merge_episode_records(target, producer)


def test_rewrite_episode_records_rejects_lossy_context_keys(tmp_path: Path) -> None:
    path = tmp_path / "episodes.jsonl"
    records = [
        episode_store.with_verbatim_context(
            _episode(),
            source="scope-gate.json",
            payload={"goal": "P1-020"},
        ),
        _episode(
            id="ep-002",
            context={"compressed_payload": {"goal": "lossy"}},
        ),
    ]

    with pytest.raises(episode_store.EpisodeStoreError, match="lossy context keys"):
        episode_store.rewrite_episode_records(path, records)
