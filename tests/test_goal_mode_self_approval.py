from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import goal_mode_self_approval as goal_mode  # noqa: E402


NOW = datetime(2026, 5, 19, 14, 34, 28, tzinfo=timezone.utc)


def _request(**overrides: object) -> goal_mode.GoalModeSelfApprovalRequest:
    payload: dict[str, object] = {
        "active_goal": "Design deployment readiness and cockpit upgrade.",
        "session_id": "2026-05-19-deployment-readiness-seed",
        "goal": "Create planning-seed artifacts for deployment readiness.",
        "allowed_writes": [
            ".azoth/proposals/azoth-deployment-readiness-cockpit-upgrade.yaml",
            ".azoth/initiative-banks/INI-DEP-001.yaml",
        ],
    }
    payload.update(overrides)
    return goal_mode.GoalModeSelfApprovalRequest.from_mapping(payload)


def test_valid_request_builds_self_approved_scope_and_pipeline() -> None:
    request = _request()

    scope, pipeline = goal_mode.build_gate_payloads(request, now=NOW)

    assert scope["approved"] is True
    assert scope["approved_by"] == "goal-mode-self-approval"
    assert scope["session_id"] == "2026-05-19-deployment-readiness-seed"
    assert scope["goal_mode_self_approval"]["schema_version"] == 1
    assert scope["goal_mode_self_approval"]["allowed_writes"] == list(request.allowed_writes)
    assert pipeline["pipeline_command"] == "auto"
    assert pipeline["session_id"] == request.session_id


def test_repo_repair_request_allows_bounded_scripts_and_tests_scope() -> None:
    request = _request(
        scope_class="repo_repair",
        target_layer="repo-local-repair",
        allowed_writes=[
            "scripts/azoth_release_profile.py",
            "tests/test_azoth_release_profile.py",
        ],
    )

    scope, pipeline = goal_mode.build_gate_payloads(request, now=NOW)

    assert scope["goal_mode_self_approval"]["scope_class"] == "repo_repair"
    assert scope["goal_mode_self_approval"]["allowed_writes"] == [
        "scripts/azoth_release_profile.py",
        "tests/test_azoth_release_profile.py",
    ]
    assert "bounded repo-local implementation" in scope["approval_basis"]
    assert pipeline["pipeline_command"] == "auto"


def test_rejects_unknown_scope_class() -> None:
    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="scope_class"):
        _request(scope_class="release_publish")


@pytest.mark.parametrize(
    "path",
    [
        "scripts/goal_mode_self_approval.py",
        "scripts/check_gates.py",
        "scripts/scope_gate_check.py",
        "scripts/run_ledger.py",
        "scripts/do_closeout.py",
    ],
)
def test_repo_repair_rejects_gate_control_plane_scripts(path: str) -> None:
    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="requires human approval"):
        _request(scope_class="repo_repair", allowed_writes=[path])


def test_writes_scope_and_pipeline_when_existing_gate_is_closed(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "scope-gate.json").write_text(
        json.dumps({"approved": False, "session_id": "closed"}), encoding="utf-8"
    )

    goal_mode.write_self_approved_gates(tmp_path, _request(), now=NOW)

    scope = json.loads((azoth / "scope-gate.json").read_text(encoding="utf-8"))
    pipeline = json.loads((azoth / "pipeline-gate.json").read_text(encoding="utf-8"))
    assert scope["approved_by"] == "goal-mode-self-approval"
    assert pipeline["approved"] is True


def test_allows_replacing_human_bootstrap_scope_only(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "human",
                "expires_at": "2026-05-19T16:34:28Z",
                "session_id": "2026-05-19-goal-mode-self-approval-v1",
                "goal_mode_bootstrap": True,
            }
        ),
        encoding="utf-8",
    )

    goal_mode.write_self_approved_gates(tmp_path, _request(), now=NOW)

    scope = json.loads((azoth / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["session_id"] == "2026-05-19-deployment-readiness-seed"
    assert scope["approved_by"] == "goal-mode-self-approval"


def test_rejects_replacing_unrelated_active_scope(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "human",
                "expires_at": "2026-05-19T16:34:28Z",
                "session_id": "other-session",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="another session"):
        goal_mode.write_self_approved_gates(tmp_path, _request(), now=NOW)


def test_allows_same_goal_continuation_to_replace_goal_mode_scope(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "goal-mode-self-approval",
                "expires_at": "2026-05-19T16:34:28Z",
                "session_id": "previous-goal-mode-session",
                "goal_mode_self_approval": {
                    "schema_version": 1,
                    "active_goal_excerpt": "Design deployment readiness and cockpit upgrade.",
                    "allowed_writes": [".azoth/proposals/old-seed.yaml"],
                },
            }
        ),
        encoding="utf-8",
    )

    goal_mode.write_self_approved_gates(tmp_path, _request(), now=NOW)

    scope = json.loads((azoth / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["session_id"] == "2026-05-19-deployment-readiness-seed"


def test_rejects_goal_mode_continuation_for_different_active_goal(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "goal-mode-self-approval",
                "expires_at": "2026-05-19T16:34:28Z",
                "session_id": "previous-goal-mode-session",
                "goal_mode_self_approval": {
                    "schema_version": 1,
                    "active_goal_excerpt": "Some other long-running goal.",
                    "allowed_writes": [".azoth/proposals/old-seed.yaml"],
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="active Goal"):
        goal_mode.write_self_approved_gates(tmp_path, _request(), now=NOW)


@pytest.mark.parametrize(
    "path",
    [
        "kernel/TRUST_CONTRACT.md",
        ".azoth/scope-gate.json",
        ".azoth/pipeline-gate.json",
        ".azoth/backlog.yaml",
        ".azoth/roadmap.yaml",
        ".azoth/roadmap-specs/v0.2.0/T-999.yaml",
        ".azoth/memory/episodes.jsonl",
        "scripts/azoth_init.py",
        "tests/test_goal_mode_self_approval.py",
        "docs/AZOTH_ARCHITECTURE.md",
    ],
)
def test_rejects_protected_or_non_planning_paths(path: str) -> None:
    with pytest.raises(goal_mode.GoalModeSelfApprovalError):
        _request(allowed_writes=[path])


def test_rejects_missing_active_goal() -> None:
    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="active_goal"):
        _request(active_goal="")


def test_rejects_kernel_target_layer_even_with_planning_path() -> None:
    with pytest.raises(goal_mode.GoalModeSelfApprovalError, match="requires human approval"):
        _request(target_layer="M1")


def test_cli_check_accepts_valid_request(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "active_goal": "Design deployment readiness and cockpit upgrade.",
                "session_id": "2026-05-19-deployment-readiness-seed",
                "goal": "Create planning-seed artifacts.",
                "allowed_writes": [".azoth/proposals/seed.yaml"],
            }
        ),
        encoding="utf-8",
    )

    assert goal_mode.main(["check", str(request_path)]) == 0
    assert "OK: Goal-mode request is self-approvable" in capsys.readouterr().out
