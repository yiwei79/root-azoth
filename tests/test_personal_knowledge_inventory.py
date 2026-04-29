from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


REQUIRED_KEYS = {
    "candidate_id",
    "source_plane",
    "source_path",
    "recommended_card_type",
    "provenance",
    "risk",
    "risk_reason",
    "later_use_notes",
}


def _write_source_file(
    root: Path,
    rel_path: str,
    text: str = "content is intentionally opaque",
) -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _source_file_list(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _run_inventory(source_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "personal_knowledge_inventory.py"),
            "--source-root",
            str(source_root),
            "--source-plane",
            "root-azoth",
            *args,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _records_by_path(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["source_path"]: record for record in records}


def test_inventory_lists_approved_sources_deterministically_without_writes(tmp_path: Path) -> None:
    source_root = tmp_path / "root-azoth"
    _write_source_file(source_root, ".azoth/memory/patterns.yaml")
    _write_source_file(
        source_root,
        ".azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md",
    )
    _write_source_file(
        source_root,
        ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md",
    )
    _write_source_file(
        source_root,
        ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md",
    )
    before_files = _source_file_list(source_root)

    first = _run_inventory(source_root, "--json")
    second = _run_inventory(source_root, "--json")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    assert _source_file_list(source_root) == before_files

    records = json.loads(first.stdout)
    assert isinstance(records, list)
    assert [record["source_path"] for record in records] == sorted(
        record["source_path"] for record in records
    )
    assert all(set(record) == REQUIRED_KEYS for record in records)

    by_path = _records_by_path(records)
    assert by_path[".azoth/memory/patterns.yaml"] == {
        "candidate_id": "root-azoth-azoth-memory-patterns-yaml",
        "source_plane": "root-azoth",
        "source_path": ".azoth/memory/patterns.yaml",
        "recommended_card_type": "toolkit_lesson",
        "provenance": "root-azoth:.azoth/memory/patterns.yaml",
        "risk": "approved_source_candidate",
        "risk_reason": "Approved M2 pattern source; review and excerpt before card drafting.",
        "later_use_notes": "May inform a future reviewed personal knowledge candidate batch.",
    }
    assert by_path[
        ".azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md"
    ]["recommended_card_type"] == "decision_context"
    assert by_path[
        ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md"
    ]["recommended_card_type"] == "source_note"
    assert by_path[
        ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md"
    ]["recommended_card_type"] == "source_note"


def test_inventory_marks_raw_memory_and_inbox_sources_as_non_importable(tmp_path: Path) -> None:
    source_root = tmp_path / "root-azoth"
    _write_source_file(source_root, ".azoth/memory/episodes.jsonl")
    _write_source_file(source_root, ".azoth/inbox/.gitkeep")
    _write_source_file(source_root, ".azoth/inbox/session-reflection.jsonl")
    _write_source_file(source_root, ".azoth/inbox/processed/.gitkeep")
    _write_source_file(source_root, ".azoth/inbox/processed/review.jsonl")

    result = _run_inventory(source_root, "--json")

    assert result.returncode == 0, result.stderr
    by_path = _records_by_path(json.loads(result.stdout))
    assert ".azoth/inbox/.gitkeep" not in by_path
    assert ".azoth/inbox/processed/.gitkeep" not in by_path
    assert by_path[".azoth/memory/episodes.jsonl"]["risk"] == "raw_memory_bulk_import_forbidden"
    assert "bulk import" in by_path[".azoth/memory/episodes.jsonl"]["risk_reason"]
    assert (
        by_path[".azoth/inbox/session-reflection.jsonl"]["risk"]
        == "inbox_requires_intake_or_manual_excerpt"
    )
    assert (
        by_path[".azoth/inbox/processed/review.jsonl"]["risk"]
        == "inbox_requires_intake_or_manual_excerpt"
    )


def test_inventory_fails_closed_for_missing_json_or_bad_source_plane(tmp_path: Path) -> None:
    source_root = tmp_path / "root-azoth"
    _write_source_file(source_root, ".azoth/memory/patterns.yaml")

    no_json = _run_inventory(source_root)
    bad_plane = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "personal_knowledge_inventory.py"),
            "--source-root",
            str(source_root),
            "--source-plane",
            "personal-root",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert no_json.returncode != 0
    assert "requires --json" in no_json.stderr
    assert bad_plane.returncode != 0
    assert "supports only root-azoth" in bad_plane.stderr


def test_inventory_uses_path_metadata_without_reading_source_contents(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_root = tmp_path / "root-azoth"
    _write_source_file(source_root, ".azoth/memory/patterns.yaml", "do not read me")
    inventory = importlib.import_module("personal_knowledge_inventory")

    def forbid_read_text(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("inventory must not read source file contents")

    def forbid_open(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("inventory must not open source file contents")

    monkeypatch.setattr(Path, "read_text", forbid_read_text)
    monkeypatch.setattr(Path, "open", forbid_open)

    records = inventory.build_inventory(source_root, source_plane="root-azoth")

    assert [record["source_path"] for record in records] == [".azoth/memory/patterns.yaml"]
