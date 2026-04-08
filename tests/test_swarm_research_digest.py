"""Tests for scripts/swarm_research_digest.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "swarm_research_digest.py"
DIGEST_V020 = REPO / ".azoth" / "roadmap-specs" / "v0.2.0" / "SWARM_RESEARCH_DIGEST.yaml"

_srd_spec = importlib.util.spec_from_file_location("swarm_research_digest", SCRIPT)
_srd = importlib.util.module_from_spec(_srd_spec)
assert _srd_spec.loader is not None
_srd_spec.loader.exec_module(_srd)
validate_digest = _srd.validate_digest


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_existing_v020_digest() -> None:
    assert DIGEST_V020.is_file()
    r = _run("validate", str(DIGEST_V020))
    assert r.returncode == 0, r.stderr
    assert "OK:" in r.stdout


def test_init_refuse_existing(tmp_path: Path) -> None:
    p = tmp_path / "d.yaml"
    p.write_text("x: 1\n", encoding="utf-8")
    r = _run("init", str(p))
    assert r.returncode == 1


def test_init_append_validate_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "SWARM_RESEARCH_DIGEST.yaml"
    r = _run("init", str(p), "--roadmap-version", "v9.9.9")
    assert r.returncode == 0, r.stderr
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["roadmap_version"] == "v9.9.9"
    assert data["research_packs"] == []

    pack = dedent(
        """
        id: RP-TEST
        topic: "test topic"
        sources:
          - { title: "T", url: "https://example.com" }
        implications_for_azoth:
          - "one"
        risks:
          - "r"
        """
    )
    r2 = subprocess.run(
        [sys.executable, str(SCRIPT), "append-pack", str(p)],
        cwd=REPO,
        input=pack,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    data2 = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert len(data2["research_packs"]) == 1
    assert data2["research_packs"][0]["id"] == "RP-TEST"

    r3 = _run("validate", str(p), "--quiet")
    assert r3.returncode == 0, r3.stderr

    r4 = subprocess.run(
        [sys.executable, str(SCRIPT), "append-pack", str(p)],
        cwd=REPO,
        input=pack,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r4.returncode == 1
    assert "already exists" in r4.stderr or "already exists" in r4.stdout


def test_validate_rejects_missing_key(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        yaml.safe_dump({"schema_version": 1, "roadmap_version": "v1"}),
        encoding="utf-8",
    )
    r = _run("validate", str(p))
    assert r.returncode == 1


def _minimal_digest(**extra: object) -> dict:
    base = {
        "schema_version": 1,
        "roadmap_version": "v0.0.0",
        "consensus_themes": [{"id": "t1", "summary": "s"}],
        "research_packs": [
            {
                "id": "RP-X",
                "topic": "t",
                "sources": [{"title": "a", "url": "https://a"}],
                "implications_for_azoth": ["i"],
                "risks": ["r"],
            }
        ],
        "explore_swarm_summary": {"wave": "B", "findings": ["f"]},
        "mapped_roadmap_tasks": ["P8-001"],
    }
    base.update(extra)
    return base


def test_validate_rejects_non_dict_mapping_notes() -> None:
    d = _minimal_digest(mapping_notes="not-a-mapping")
    errs = validate_digest(d)
    assert any("mapping_notes must be a mapping" in e for e in errs)


def test_validate_rejects_bad_contributing_packs() -> None:
    d = _minimal_digest(
        consensus_themes=[{"id": "t1", "summary": "s", "contributing_packs": [1]}],
    )
    errs = validate_digest(d)
    assert any("contributing_packs[0]" in e and "str" in e for e in errs)


def test_validate_rejects_contributing_packs_not_list() -> None:
    d = _minimal_digest(
        consensus_themes=[
            {"id": "t1", "summary": "s", "contributing_packs": "RP-A"},
        ],
    )
    errs = validate_digest(d)
    assert any("contributing_packs must be a list" in e for e in errs)


def test_validate_rejects_mapping_notes_empty_key() -> None:
    d = _minimal_digest(mapping_notes={"": "has value but key empty"})
    errs = validate_digest(d)
    assert any("mapping_notes keys must be non-empty str" in e for e in errs)


def test_validate_rejects_mapping_notes_empty_value() -> None:
    d = _minimal_digest(mapping_notes={"P8-001": "   "})
    errs = validate_digest(d)
    assert any("mapping_notes[" in e and "non-empty str" in e for e in errs)


def test_validate_rejects_mapping_notes_non_string_value() -> None:
    d = _minimal_digest(mapping_notes={"P8-001": 99})
    errs = validate_digest(d)
    assert any("mapping_notes[" in e and "non-empty str" in e for e in errs)


def test_append_pack_missing_file_exits_io(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    r = _run("append-pack", str(missing), "--pack", str(tmp_path / "pack.yaml"))
    assert r.returncode == 2
    assert "no file" in r.stderr.lower() or "read" in r.stderr.lower()


def test_append_pack_bad_pack_path_exits_io(tmp_path: Path) -> None:
    p = tmp_path / "d.yaml"
    r_init = _run("init", str(p), "--roadmap-version", "v1")
    assert r_init.returncode == 0
    r2 = _run("append-pack", str(p), "--pack", str(tmp_path / "missing_pack.yaml"))
    assert r2.returncode == 2
    assert "read pack failed" in r2.stderr or "pack" in r2.stderr.lower()
