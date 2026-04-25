from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "initiative_intake.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import initiative_intake  # noqa: E402
from initiative_intake import (  # noqa: E402
    APPROVAL_SCOPE,
    EXECUTABLE_OUTPUTS,
    InitiativeIntakeValidationError,
    approval_scope_authorizes,
    render_initiative_seed,
    validate_intake_contract,
    validate_raw_intake,
    write_seed,
)


def _valid_intake() -> dict[str, Any]:
    return {
        "initiative_id": "INI-RAW-001",
        "operator_goal": "Create a safe raw initiative intake path.",
        "why_now": "Autonomous-auto needs seed-only discovery before hydration.",
        "known_constraints": [
            "Do not create delivery artifacts.",
            "Keep this slice to planning discovery.",
        ],
        "protected_boundaries": [
            "No kernel changes.",
            "No governance changes.",
            "No network or credential expansion.",
        ],
        "success_signals": [
            "A raw initiative validates as planning discovery.",
            "Hydration and shipping stay blocked.",
        ],
        "initial_uncertainty": [
            "Which later slice should become hydration-ready?",
        ],
        "approval_scope": APPROVAL_SCOPE,
        "approval_basis": "Operator approved T-023 seed-only intake.",
        "allowed_outputs": [
            "initiative_bank_seed",
            "validation_report",
        ],
        "forbidden_outputs": sorted(EXECUTABLE_OUTPUTS),
    }


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_valid_raw_intake_classifies_as_planning_discovery_seed() -> None:
    report = validate_raw_intake(_valid_intake())

    assert report["classification"] == "planning_discovery_seed"
    assert report["delivery_authorized"] is False
    assert report["approval_scope"] == APPROVAL_SCOPE
    assert "hydrate_task" in report["blocked_actions"]
    assert "ship_task" in report["blocked_actions"]


def test_validate_intake_contract_returns_report_schema() -> None:
    report = validate_intake_contract(_valid_intake())

    assert report["report_type"] == "initiative_intake_validation"
    assert report["valid"] is True
    assert report["classification"] == "planning_discovery_seed"
    assert report["write_allowed"] is True
    assert report["delivery_authorized"] is False
    assert report["next_safe_actions"] == ["research_initiative", "refine_proposal"]
    assert "hydrate_task" in report["blocked_actions"]
    assert "ship_task" in report["blocked_actions"]


@pytest.mark.parametrize(
    "field",
    [
        "initiative_id",
        "operator_goal",
        "why_now",
        "known_constraints",
        "protected_boundaries",
        "success_signals",
        "initial_uncertainty",
        "approval_scope",
        "approval_basis",
        "allowed_outputs",
        "forbidden_outputs",
    ],
)
def test_missing_required_fields_fail_closed(field: str) -> None:
    intake = _valid_intake()
    intake.pop(field)

    with pytest.raises(InitiativeIntakeValidationError, match=field):
        validate_raw_intake(intake)


def test_executable_allowed_output_is_rejected() -> None:
    intake = _valid_intake()
    intake["allowed_outputs"] = ["initiative_bank_seed", "scope_gate", "hydrate_task"]

    with pytest.raises(InitiativeIntakeValidationError, match="allowed_outputs"):
        validate_raw_intake(intake)


def test_missing_forbidden_executable_output_is_rejected() -> None:
    intake = _valid_intake()
    intake["forbidden_outputs"] = [
        output for output in EXECUTABLE_OUTPUTS if output != "ship_task"
    ]

    with pytest.raises(InitiativeIntakeValidationError, match="forbidden_outputs"):
        validate_raw_intake(intake)


def test_planning_seed_scope_never_authorizes_hydrate_or_ship() -> None:
    assert approval_scope_authorizes(APPROVAL_SCOPE, "initiative_bank_seed") is True
    assert approval_scope_authorizes(APPROVAL_SCOPE, "hydrate_task") is False
    assert approval_scope_authorizes(APPROVAL_SCOPE, "ship_task") is False


def test_seed_render_and_write_only_creates_initiative_bank_seed(tmp_path: Path) -> None:
    repo = tmp_path
    output = repo / ".azoth" / "initiative-banks" / "INI-RAW-001.yaml"

    rendered = render_initiative_seed(_valid_intake(), output_path=output, repo_root=repo)
    written = write_seed(_valid_intake(), output, repo_root=repo)

    assert written == rendered
    assert output.exists()
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded == rendered
    assert loaded["classification"] == "planning_discovery_seed"
    assert loaded["status"] == "planning_discovery_seed"
    assert loaded["readiness"]["approval_scope"] == APPROVAL_SCOPE
    assert loaded["readiness"]["delivery_authorized"] is False
    assert loaded["readiness"]["blocked_actions"] == sorted(EXECUTABLE_OUTPUTS)
    assert loaded["candidate_slices"] == []
    assert loaded["hydration_history"] == []

    forbidden_artifacts = [
        repo / ".azoth" / "scope-gate.json",
        repo / ".azoth" / "pipeline-gate.json",
        repo / ".azoth" / "run-ledger.local.yaml",
        repo / ".azoth" / "backlog.yaml",
        repo / ".azoth" / "roadmap.yaml",
        repo / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-999.yaml",
    ]
    assert all(not path.exists() for path in forbidden_artifacts)


def test_write_seed_rejects_output_outside_initiative_banks(tmp_path: Path) -> None:
    repo = tmp_path
    output = repo / ".azoth" / "proposals" / "INI-RAW-001.yaml"

    with pytest.raises(InitiativeIntakeValidationError, match="initiative-banks"):
        write_seed(_valid_intake(), output, repo_root=repo)

    assert not output.exists()


def test_no_write_fail_closed_snapshot_for_invalid_intake(tmp_path: Path) -> None:
    repo = tmp_path
    output = repo / ".azoth" / "initiative-banks" / "INI-RAW-001.yaml"
    intake = _valid_intake()
    intake.pop("approval_basis")

    with pytest.raises(InitiativeIntakeValidationError, match="approval_basis"):
        write_seed(intake, output, repo_root=repo)

    assert not output.exists()
    assert not (repo / ".azoth" / "scope-gate.json").exists()
    assert not (repo / ".azoth" / "run-ledger.local.yaml").exists()
    assert not (repo / ".azoth" / "roadmap.yaml").exists()
    assert not (repo / ".azoth" / "backlog.yaml").exists()
    assert not (repo / ".azoth" / "roadmap-specs").exists()


def test_cli_validate_and_render_seed_json(tmp_path: Path) -> None:
    intake_path = tmp_path / "intake.yaml"
    _write_yaml(intake_path, _valid_intake())

    validate_result = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", "--input", str(intake_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    render_result = subprocess.run(
        [sys.executable, str(SCRIPT), "render-seed", "--input", str(intake_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_result.returncode == 0, validate_result.stderr
    assert render_result.returncode == 0, render_result.stderr
    validate_payload = json.loads(validate_result.stdout)
    render_payload = json.loads(render_result.stdout)
    assert validate_payload["classification"] == "planning_discovery_seed"
    assert render_payload["classification"] == "planning_discovery_seed"
    assert render_payload["readiness"]["delivery_authorized"] is False


def test_cli_write_seed_fails_closed_without_output(tmp_path: Path) -> None:
    intake_path = tmp_path / "intake.yaml"
    _write_yaml(intake_path, _valid_intake())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write-seed", "--input", str(intake_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "output" in payload["error"]
