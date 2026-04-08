"""Tests for scripts/swarm_research_digest.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "swarm_research_digest.py"
DIGEST_V020 = REPO / ".azoth" / "roadmap-specs" / "v0.2.0" / "SWARM_RESEARCH_DIGEST.yaml"


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
