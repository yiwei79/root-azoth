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

from personal_harness_practice_rehearsal import run_practice_rehearsal  # noqa: E402
from test_personal_harness_context import _write_memory_fixture  # noqa: E402


CASES = ROOT / "tests" / "fixtures" / "personal_harness_practice_cases.yaml"


def test_practice_rehearsal_covers_daily_domains_and_modes(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    report = run_practice_rehearsal(
        repo_root=tmp_path,
        cases_path=CASES,
        as_of="2026-06-07T00:00:00Z",
    )

    assert report["ok"] is True
    assert report["case_count"] == 4
    assert report["no_write_contract"]["repo_mutated"] is False
    assert {case["domain"] for case in report["cases"]} == {
        "agent-context",
        "music",
        "thesis",
    }
    assert {case["profile"] for case in report["cases"]} == {
        "assisted",
        "governed_autonomy",
        "guide",
        "managed",
    }
    for case in report["cases"]:
        assert case["status"] == "pass"
        assert case["warnings"] == []


def test_practice_fixture_keeps_managed_and_governed_authority_explicit() -> None:
    doc = yaml.safe_load(CASES.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in doc["cases"]}

    managed = cases["music-managed-planning-hydration"]["expected"]
    governed = cases["agent-context-governed-autonomy"]["expected"]

    assert managed["authority_required"] is True
    assert managed["authority_plane"] == "project_local"
    assert governed["authority_required"] is True
    assert governed["authority_plane"] == "root_azoth"


def test_practice_rehearsal_cli_outputs_json(tmp_path: Path) -> None:
    _write_memory_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_harness_practice_rehearsal.py"),
            "--repo-root",
            str(tmp_path),
            "--cases",
            str(CASES),
            "--as-of",
            "2026-06-07T00:00:00Z",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["packet_type"] == "personal_harness_practice_rehearsal"
    assert report["ok"] is True
