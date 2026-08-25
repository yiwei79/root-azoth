from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from personal_harness_practice_rehearsal import (  # noqa: E402
    _tree_fingerprint,
    run_practice_rehearsal,
)

CASES = ROOT / "examples" / "personal-harness" / "rehearsal-cases.yaml"


def test_practice_rehearsal_covers_daily_domains_and_modes(tmp_path: Path) -> None:
    report = run_practice_rehearsal(
        repo_root=tmp_path,
        cases_path=CASES,
    )

    assert report["ok"] is True
    assert report["case_count"] == 4
    assert report["no_write_contract"]["repo_mutated"] is False
    assert str(tmp_path) not in json.dumps(report)
    assert {case["domain"] for case in report["cases"]} == {
        "governed-automation",
        "product-discovery",
        "project-management",
        "software-delivery",
    }
    assert {case["profile"] for case in report["cases"]} == {
        "assisted",
        "governed_autonomy",
        "guide",
        "managed",
    }
    for case in report["cases"]:
        assert case["status"] == "pass"
        assert any("memory recall skipped" in warning for warning in case["warnings"])


def test_practice_fixture_keeps_managed_and_governed_authority_explicit() -> None:
    doc = yaml.safe_load(CASES.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in doc["cases"]}

    managed = cases["managed-state"]["expected"]
    governed = cases["governed-campaign"]["expected"]

    assert managed["authority_required"] is True
    assert managed["authority_plane"] == "project_local"
    assert governed["authority_required"] is True
    assert governed["authority_plane"] == "toolkit_governance"


def test_practice_rehearsal_cli_outputs_json(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_harness_practice_rehearsal.py"),
            "--repo-root",
            str(tmp_path),
            "--cases",
            str(CASES),
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
    assert str(tmp_path) not in result.stdout


def test_default_cases_resolve_under_repo_root(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    cases = repo / "examples" / "personal-harness" / "rehearsal-cases.yaml"
    cases.parent.mkdir(parents=True)
    shutil.copy2(CASES, cases)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    report = run_practice_rehearsal(repo_root=repo)

    assert report["ok"] is True
    assert report["case_count"] == 4


def test_relative_cases_path_cannot_escape_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.yaml"
    shutil.copy2(CASES, outside)

    with pytest.raises(ValueError, match="must stay under repo_root"):
        run_practice_rehearsal(
            repo_root=repo,
            cases_path=Path("../outside.yaml"),
        )


def test_fingerprint_excludes_ignored_content_and_never_follows_symlink(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cases = repo / "examples" / "personal-harness" / "rehearsal-cases.yaml"
    cases.parent.mkdir(parents=True)
    shutil.copy2(CASES, cases)
    (repo / ".gitignore").write_text("private/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    private = repo / "private"
    private.mkdir()
    secret = private / "secret.txt"
    secret.write_text("first private value\n", encoding="utf-8")
    nested = repo / "nested"
    nested.mkdir()
    (nested / "inside.txt").write_text("tracked nested value\n", encoding="utf-8")
    (private / "inside.txt").write_text("external nested value\n", encoding="utf-8")
    (repo / "tracked-link").symlink_to(secret)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "add", ".gitignore", "tracked.txt", "tracked-link", "nested", "examples"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Azoth Test",
            "-c",
            "user.email=azoth-test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=repo,
        check=True,
    )

    before = _tree_fingerprint(repo, cases_path=cases)
    secret.write_text("different ignored private value\n", encoding="utf-8")
    after_private_change = _tree_fingerprint(repo, cases_path=cases)
    assert after_private_change == before

    shutil.rmtree(nested)
    nested.symlink_to(private, target_is_directory=True)
    symlink_parent_before = _tree_fingerprint(repo, cases_path=cases)
    (private / "inside.txt").write_text("changed external nested value\n", encoding="utf-8")
    assert _tree_fingerprint(repo, cases_path=cases) == symlink_parent_before

    (repo / "tracked.txt").write_text("tracked mutation\n", encoding="utf-8")
    assert _tree_fingerprint(repo, cases_path=cases) != before


def test_fingerprint_tracks_untracked_nonignored_metadata(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cases = repo / "examples" / "personal-harness" / "rehearsal-cases.yaml"
    cases.parent.mkdir(parents=True)
    shutil.copy2(CASES, cases)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "examples"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Azoth Test",
            "-c",
            "user.email=azoth-test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=repo,
        check=True,
    )
    untracked = repo / "operator-note.txt"
    untracked.write_text("one\n", encoding="utf-8")

    before = _tree_fingerprint(repo, cases_path=cases)
    untracked.write_text("ordinary metadata change\n", encoding="utf-8")

    assert _tree_fingerprint(repo, cases_path=cases) != before
