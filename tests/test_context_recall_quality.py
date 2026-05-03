from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
RECALL_SCRIPT = SCRIPTS_DIR / "context_recall_quality.py"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "context_recall_quality.yaml"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import context_recall_quality as recall_quality  # noqa: E402

TOP_LEVEL_KEYS = {
    "schema_version",
    "packet_type",
    "query",
    "query_tags",
    "as_of",
    "top_k",
    "corpus",
    "results",
    "warnings",
    "no_match",
    "advisory_authority",
}
RESULT_KEYS = {
    "rank",
    "source_type",
    "id",
    "source_ref",
    "summary",
    "timestamp",
    "tags",
    "score_total",
    "score_components",
    "match_reasons",
    "freshness_status",
    "conflict_status",
    "advisory_authority",
}
SCORE_COMPONENT_KEYS = {
    "tag_overlap",
    "token_overlap",
    "recency_bonus",
    "reinforcement_bonus",
    "pattern_trigger_bonus",
    "total",
}

def _episode(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": "ep-001",
        "timestamp": "2026-05-01T00:00:00Z",
        "session_id": "session-001",
        "type": "success",
        "goal": "Context recall quality harness",
        "summary": "Context recall uses M3 and M2 evidence.",
        "lessons": ["Recall should be deterministic."],
        "tags": ["context-recall", "memory"],
        "reinforcement_count": 0,
        "context": {},
    }
    record.update(overrides)
    return record

def _write_episodes(path: Path, records: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path

def _write_patterns(path: Path, patterns: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"patterns": patterns}, sort_keys=True), encoding="utf-8")
    return path

def _pattern(pattern_id: str, **overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": pattern_id,
        "approved": True,
        "approved_date": "2026-04-20",
        "reinforced_by": ["ep-001", "ep-002"],
        "trigger": "any memory retrieval or context recall quality work",
        "summary": "Read back approved memory before selecting actions.",
        "how_to_apply": "Use advisory memory without mutating M2.",
    }
    record.update(overrides)
    return record

def test_query_contract_ranks_m3_and_m2_with_advisory_result_fields(tmp_path: Path) -> None:
    episodes_path = _write_episodes(
        tmp_path / "episodes.jsonl",
        [
            _episode(id="ep-older", timestamp="2026-04-01T00:00:00Z", tags=["memory"]),
            _episode(
                id="ep-context",
                timestamp="2026-05-01T12:00:00Z",
                tags=["context-recall", "D45"],
                summary="Delivered deterministic context recall packet fields.",
                reinforcement_count=2,
            ),
        ],
    )
    patterns_path = _write_patterns(
        tmp_path / "patterns.yaml",
        [_pattern("memory-readback", trigger="any memory read-back work")],
    )

    packet = recall_quality.build_recall_packet(
        query="context recall D45",
        query_tags=["context-recall", "D45"],
        top_k=2,
        as_of="2026-05-03T00:00:00Z",
        episodes_path=episodes_path,
        patterns_path=patterns_path,
    )

    assert set(packet) == TOP_LEVEL_KEYS
    assert packet["packet_type"] == "context_recall_quality_query"
    assert packet["query"] == "context recall D45"
    assert packet["query_tags"] == ["context-recall", "D45"]
    assert packet["top_k"] == 2
    assert packet["no_match"] is False
    assert packet["advisory_authority"] == recall_quality.ADVISORY_AUTHORITY
    assert packet["corpus"]["m3_episode_count"] == 2
    assert packet["corpus"]["m2_pattern_count"] == 1
    first = packet["results"][0]
    assert set(first) == RESULT_KEYS
    assert first["rank"] == 1
    assert first["source_type"] == "m3_episode"
    assert first["id"] == "ep-context"
    assert set(first["score_components"]) == SCORE_COMPONENT_KEYS
    assert first["score_components"]["tag_overlap"] == pytest.approx(4.0)
    assert first["score_total"] == first["score_components"]["total"]
    assert "tag_overlap" in first["match_reasons"]

def test_fixture_eval_passes_all_research_fixtures() -> None:
    packet = recall_quality.evaluate_fixture_file(FIXTURE_PATH)
    assert packet["packet_type"] == "context_recall_quality_fixture_eval"
    assert packet["fixture_set_id"] == "context-recall-quality-v1"
    assert packet["pass_fail"] is True
    assert packet["failed_fixture_ids"] == []
    assert len(packet["fixture_results"]) == 8
    assert packet["top3_pass_count"] == 8
    by_id = {result["fixture_id"]: result for result in packet["fixture_results"]}
    assert by_id["exact_context_recall_delivery"]["actual_top_ids"][0] == "ep-052"
    assert by_id["m2_read_back_pattern"]["actual_top_ids"][0] == (
        "memory-requires-read-back-mechanism"
    )
    assert by_id["same_day_recency_tiebreak_closeout"]["actual_top_ids"][:3] == [
        "ep-532",
        "ep-531",
        "ep-530",
    ]
    assert by_id["no_match_empty_result"]["no_match"] is True

def test_query_does_not_mutate_episode_or_pattern_files(tmp_path: Path) -> None:
    episodes_path = _write_episodes(tmp_path / "episodes.jsonl", [_episode()])
    patterns_path = _write_patterns(tmp_path / "patterns.yaml", [_pattern("memory-readback")])
    before_episodes = episodes_path.read_bytes()
    before_patterns = patterns_path.read_bytes()
    recall_quality.build_recall_packet(
        query="context recall",
        query_tags=["context-recall"],
        top_k=3,
        as_of="2026-05-03",
        episodes_path=episodes_path,
        patterns_path=patterns_path,
    )
    assert episodes_path.read_bytes() == before_episodes
    assert patterns_path.read_bytes() == before_patterns

def test_no_match_returns_empty_results_without_forced_output(tmp_path: Path) -> None:
    episodes_path = _write_episodes(tmp_path / "episodes.jsonl", [_episode()])
    patterns_path = _write_patterns(tmp_path / "patterns.yaml", [_pattern("memory-readback")])
    packet = recall_quality.build_recall_packet(
        query="mars colony espresso index",
        query_tags=["mars-colony", "espresso-index"],
        top_k=3,
        as_of="2026-05-03",
        episodes_path=episodes_path,
        patterns_path=patterns_path,
    )
    assert packet["results"] == []
    assert packet["no_match"] is True

def test_missing_patterns_file_is_graceful_with_warning(tmp_path: Path) -> None:
    episodes_path = _write_episodes(tmp_path / "episodes.jsonl", [_episode()])
    missing_patterns_path = tmp_path / "missing-patterns.yaml"
    packet = recall_quality.build_recall_packet(
        query="context recall",
        query_tags=["context-recall"],
        top_k=3,
        as_of="2026-05-03",
        episodes_path=episodes_path,
        patterns_path=missing_patterns_path,
    )
    assert packet["corpus"]["m2_pattern_count"] == 0
    assert packet["warnings"] == [f"patterns file not found: {missing_patterns_path}"]
    assert [result["id"] for result in packet["results"]] == ["ep-001"]

def test_malformed_m3_fails_closed_through_cli_nonzero(tmp_path: Path) -> None:
    episodes_path = tmp_path / "episodes.jsonl"
    episodes_path.write_text("{not-json}\n", encoding="utf-8")
    patterns_path = _write_patterns(tmp_path / "patterns.yaml", [])
    result = subprocess.run(
        [
            sys.executable,
            str(RECALL_SCRIPT),
            "--query",
            "context recall",
            "--tags",
            "context-recall",
            "--episodes-path",
            str(episodes_path),
            "--patterns-path",
            str(patterns_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "EpisodeStoreError" in result.stderr
    assert result.stdout == ""

def test_cli_requires_json_flag(tmp_path: Path) -> None:
    episodes_path = _write_episodes(tmp_path / "episodes.jsonl", [_episode()])
    result = subprocess.run(
        [
            sys.executable,
            str(RECALL_SCRIPT),
            "--query",
            "context recall",
            "--episodes-path",
            str(episodes_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--json is required" in result.stderr

def test_script_uses_only_zero_dependency_recall_imports() -> None:
    tree = ast.parse(RECALL_SCRIPT.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    forbidden = {
        "chromadb",
        "faiss",
        "numpy",
        "openai",
        "pandas",
        "requests",
        "sentence_transformers",
        "sklearn",
        "yaml",
    }
    assert imported_roots.isdisjoint(forbidden)
    assert {"episode_store", "yaml_helpers"}.issubset(imported_roots)
    assert "load_episode_records(" in RECALL_SCRIPT.read_text(encoding="utf-8")
