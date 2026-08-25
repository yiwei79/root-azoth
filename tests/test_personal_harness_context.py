from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from personal_harness_context import build_personal_harness_context  # noqa: E402


def _write_memory_fixture(repo: Path) -> None:
    memory_dir = repo / ".azoth" / "memory"
    memory_dir.mkdir(parents=True)
    episode = {
        "id": "ep-463",
        "timestamp": "2026-05-01T00:00:00Z",
        "type": "pattern",
        "goal": "Fix run ledger write claim handling",
        "summary": "Run-ledger clobber taught fail-closed write claims.",
        "lessons": ["Keep write claims explicit before autonomous work."],
        "tags": ["run-ledger", "write-claim", "context"],
        "reinforcement_count": 1,
        "context": {},
    }
    (memory_dir / "episodes.jsonl").write_text(json.dumps(episode) + "\n", encoding="utf-8")
    (memory_dir / "patterns.yaml").write_text(
        yaml.safe_dump(
            {
                "patterns": [
                    {
                        "id": "memory-authoring-quality",
                        "summary": "Memory authoring should preserve advisory authority.",
                        "trigger": "context packet",
                        "tags": ["context"],
                        "approved_date": "2026-05-02",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_build_personal_harness_context_combines_route_and_memory(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    packet = build_personal_harness_context(
        goal="Verify context before autonomous work",
        requested_actions=("focused_verification",),
        query_tags=("context", "write-claim"),
        repo_root=tmp_path,
        as_of="2026-05-03T00:00:00Z",
    )

    assert packet["schema_version"] == 1
    assert packet["packet_type"] == "personal_harness_context"
    assert packet["context_view"]["harness_profile"] == "assisted"
    assert packet["context_view"]["route_capsule"]["route_state"] == "assist"
    assert packet["context_view"]["memory_context"][0] == {
        "id": "ep-463",
        "kind": "m3_episode",
        "summary": "Run-ledger clobber taught fail-closed write claims.",
        "score": packet["context_view"]["memory_context"][0]["score"],
        "source_ref": str(tmp_path / ".azoth" / "memory" / "episodes.jsonl") + "#ep-463",
    }
    assert packet["memory_recall"]["packet_type"] == "context_recall_quality_query"
    assert packet["warnings"] == []


def test_missing_optional_personal_root_adds_warning_without_blocking(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    packet = build_personal_harness_context(
        goal="What mode should I use?",
        repo_root=tmp_path,
        personal_root=tmp_path / "missing-personal-root",
        as_of="2026-05-03T00:00:00Z",
    )

    assert packet["context_view"]["harness_profile"] == "guide"
    assert packet["context_view"]["personal_context"] == []
    assert any("personal knowledge recall skipped" in warning for warning in packet["warnings"])


def test_build_personal_harness_context_includes_project_readback(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    packet = build_personal_harness_context(
        goal="Verify context before project work",
        requested_actions=("focused_verification",),
        query_tags=("context",),
        repo_root=tmp_path,
        project_readback={
            "project": "example-service",
            "selected_mode": "assisted",
            "freshness": "current",
            "receipt_ref": ".azoth/project-mode-receipt.yaml",
        },
        as_of="2026-05-03T00:00:00Z",
    )

    assert packet["context_view"]["project_context"] == {
        "project": "example-service",
        "selected_mode": "assisted",
        "freshness": "current",
        "receipt_ref": ".azoth/project-mode-receipt.yaml",
    }


def test_cli_outputs_json_packet(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_harness_context.py"),
            "--goal",
            "Verify context before work",
            "--action",
            "focused_verification",
            "--tag",
            "context",
            "--repo-root",
            str(tmp_path),
            "--as-of",
            "2026-05-03T00:00:00Z",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["packet_type"] == "personal_harness_context"
    assert packet["context_view"]["harness_profile"] == "assisted"
