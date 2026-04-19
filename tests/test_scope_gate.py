from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ORCHESTRATOR_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "edit_pretooluse_orchestrator.py"
)

SCOPE_GATE_THIN_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "scope-gate.py"
)


def _run(
    tool_name: str,
    gate_path: Path,
    file_path: str | None = None,
    pipeline_gate_path: Path | None = None,
    write_claim: dict | None = None,
    tool_input_override: dict | None = None,
) -> dict:
    tool_input: dict = dict(tool_input_override or {})
    if file_path is not None and "file_path" not in tool_input:
        tool_input["file_path"] = file_path
    stdin_payload = json.dumps(
        {
            "tool_name": tool_name,
            "hook_event_name": "PreToolUse",
            "tool_input": tool_input,
        }
    )
    workspace = gate_path.parent
    azoth_dir = workspace / ".azoth"
    azoth_dir.mkdir(exist_ok=True)
    if write_claim is not None:
        (azoth_dir / "run-ledger.local.yaml").write_text(
            json.dumps({"schema_version": 1, "runs": [], "write_claim": write_claim}),
            encoding="utf-8",
        )
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_REPO_ROOT"] = str(workspace)
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(azoth_dir / "run-ledger.local.yaml")
    if pipeline_gate_path is not None:
        env["AZOTH_PIPELINE_GATE_PATH"] = str(pipeline_gate_path)
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    return json.loads(result.stdout)


def _decision(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecision"]


def _reason(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecisionReason"]


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _past_expiry() -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()


def _governed_scope_gate(*, expiry: str, session_id: str = "sess-governed") -> dict:
    return {
        "approved": True,
        "expires_at": expiry,
        "session_id": session_id,
        "target_layer": "M1",
    }


def _pipeline_gate(
    *,
    expiry: str,
    session_id: str = "sess-governed",
    research_required: bool = False,
    research_evidence: dict | None = None,
    pipeline: str = "deliver-full",
) -> dict:
    gate = {
        "approved": True,
        "session_id": session_id,
        "expires_at": expiry,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "research_required": research_required,
    }
    if research_evidence is not None:
        gate["research_evidence"] = research_evidence
    return gate


def _write_research_capsule(
    repo_root: Path,
    rel_path: str,
    *,
    source_session_id: str = "sess-governed",
    fresh_until: str | None = None,
    question_status: str = "answered",
    capsule_overrides: dict | None = None,
) -> Path:
    capsule_path = repo_root / rel_path
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    capsule = {
        "schema_version": 1,
        "source_session_id": source_session_id,
        "goal": "T-009: Local research capsule bank + sufficiency checker",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "volatility": "bounded",
        "limitations": [],
        "questions": [
            {
                "question_id": "phase-1-reuse",
                "question": "Can this repo-local research capsule be reused?",
                "status": question_status,
                "answered_at": datetime.now(timezone.utc).isoformat(),
                "fresh_until": fresh_until or _future_expiry(),
            }
        ],
    }
    if capsule_overrides:
        capsule.update(capsule_overrides)
    capsule_path.write_text(json.dumps(capsule), encoding="utf-8")
    return capsule_path


# T1: non-write/edit tool with absent gate file — must allow
def test_t1_non_write_tool_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Read", gate_path)
    assert _decision(output) == "allow"


# T2: Write with absent gate file — must deny with scope-gate message
def test_t2_write_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T3: Edit with absent gate file — must deny with scope-gate message
def test_t3_edit_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Edit", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t3b_create_file_gate_absent_vscode_payload(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    stdin_payload = json.dumps(
        {
            "tool_name": "create_file",
            "hook_event_name": "PreToolUse",
            "tool_input": {
                "filePath": str(tmp_path / "vscode-created.txt"),
                "content": "hello\n",
            },
        }
    )
    workspace = gate_path.parent
    azoth_dir = workspace / ".azoth"
    azoth_dir.mkdir(exist_ok=True)
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(azoth_dir / "run-ledger.local.yaml")
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t3c_replace_string_gate_absent_vscode_payload(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    target = tmp_path / "vscode-edit.txt"
    target.write_text("alpha\n", encoding="utf-8")
    stdin_payload = json.dumps(
        {
            "tool_name": "replace_string_in_file",
            "hook_event_name": "PreToolUse",
            "tool_input": {
                "filePath": str(target),
                "oldString": "alpha",
                "newString": "beta",
            },
        }
    )
    workspace = gate_path.parent
    azoth_dir = workspace / ".azoth"
    azoth_dir.mkdir(exist_ok=True)
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(azoth_dir / "run-ledger.local.yaml")
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T4: Write, approved=false, future expiry — must deny
def test_t4_write_approved_false(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": False, "expires_at": _future_expiry()}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T5: Write, approved=true, expired — must deny
def test_t5_write_approved_expired(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": _past_expiry()}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T6: Write, approved=true, 1hr future expiry — must allow
def test_t6_write_approved_valid(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": _future_expiry(), "session_id": "sess-valid"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T7: Write, malformed JSON gate file — must deny with "malformed"
def test_t7_write_malformed_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text("this is not json {{{", encoding="utf-8")
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "malformed" in _reason(output)


# T8: Write, approved=true, expires_at is not a valid date — must deny
def test_t8_write_invalid_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "not-a-date", "session_id": "sess-invalid"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "invalid ISO 8601" in _reason(output)


# T9: Write, approved=true, future naive expires_at (no tz) — hook normalizes to UTC, must allow
def test_t9_write_naive_future_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "2099-12-31T23:59:59", "session_id": "sess-naive"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T10: Write, approved=true, future expires_at with Z suffix — must allow
def test_t10_write_z_suffix_future_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "2099-12-31T23:59:59Z", "session_id": "sess-z"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T11: Write with file_path == gate_path, gate absent — must allow (bootstrap exception)
def test_t11_write_to_gate_path_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Write", gate_path, file_path=str(gate_path))
    assert _decision(output) == "allow"


# T12: Edit with file_path == gate_path, gate absent — must allow (bootstrap exception)
def test_t12_edit_to_gate_path_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Edit", gate_path, file_path=str(gate_path))
    assert _decision(output) == "allow"


def test_t12b_create_file_to_gate_path_allowed_vscode_payload(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    stdin_payload = json.dumps(
        {
            "tool_name": "create_file",
            "hook_event_name": "PreToolUse",
            "tool_input": {"filePath": str(gate_path), "content": "{}\n"},
        }
    )
    workspace = gate_path.parent
    azoth_dir = workspace / ".azoth"
    azoth_dir.mkdir(exist_ok=True)
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(azoth_dir / "run-ledger.local.yaml")
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert _decision(output) == "allow"


# T13–T16: governed scope + pipeline-gate.json (M1 / delivery_pipeline mechanical layer)


def test_t13_governed_scope_write_denied_without_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "src.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t14_governed_scope_write_allowed_with_valid_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expiry,
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": expiry,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "pipeline": "deliver-full",
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "src.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "allow"


def test_t15_governed_scope_write_to_pipeline_gate_path_allowed_without_prior_gate(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(pg_path), pipeline_gate_path=pg_path)
    assert _decision(output) == "allow"


def test_t15b_pipeline_gate_write_denied_without_scope_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    output = _run("Write", gate_path, file_path=str(pg_path), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t16_target_layer_m1_triggers_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-m1",
                "target_layer": "M1",
                "delivery_pipeline": "standard",
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "x.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"


def test_t16b_governed_scope_write_denied_with_pipeline_gate_session_mismatch(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expiry,
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-other",
                "expires_at": expiry,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "pipeline": "deliver-full",
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16c_governed_scope_write_denied_with_invalid_pipeline_name(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expiry,
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": expiry,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "pipeline": "ship-it",
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16d_governed_scope_write_denied_with_opened_at_after_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expiry,
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": expiry,
                "opened_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
                "pipeline": "deliver-full",
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16da_governed_scope_write_denied_without_research_required_flag(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": expiry,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "pipeline": "deliver-full",
            }
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16db_governed_scope_write_denied_with_non_boolean_research_required(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            {
                **_pipeline_gate(expiry=expiry),
                "research_required": "yes",
            }
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dc_governed_scope_write_allowed_with_research_required_false(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(json.dumps(_pipeline_gate(expiry=expiry)), encoding="utf-8")

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "allow"


def test_t16dd_governed_scope_write_allowed_with_same_session_repo_local_research_evidence(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": ".azoth/research/sess-governed.json",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "allow"


def test_t16dde_governed_scope_write_allows_advisory_capsule_content_in_phase1(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    evidence_path = ".azoth/research/sess-governed.json"
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    _write_research_capsule(
        tmp_path,
        evidence_path,
        fresh_until=_past_expiry(),
        question_status="conflicting",
    )
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": evidence_path,
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "allow"


def test_t16ddf_governed_scope_write_allows_missing_required_questions_in_phase1(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    evidence_path = ".azoth/research/sess-governed.json"
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    _write_research_capsule(
        tmp_path,
        evidence_path,
        capsule_overrides={"questions": []},
    )
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": evidence_path,
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "allow"


def test_t16ddg_governed_scope_write_allows_malformed_capsule_content_in_phase1(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    evidence_path = ".azoth/research/sess-governed.json"
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    _write_research_capsule(
        tmp_path,
        evidence_path,
        capsule_overrides={"questions": None},
    )
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": evidence_path,
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "allow"


def test_t16de_governed_scope_write_denied_when_research_evidence_missing(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(_pipeline_gate(expiry=expiry, research_required=True)),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16df_governed_scope_write_denied_when_research_evidence_is_not_an_object(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            {
                **_pipeline_gate(expiry=expiry, research_required=True),
                "research_evidence": ["repo-local"],
            }
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dg_governed_scope_write_denied_when_research_evidence_missing_field(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dh_governed_scope_write_denied_when_research_evidence_kind_is_not_repo_local(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "web",
                    "session_id": "sess-governed",
                    "path": ".azoth/research/sess-governed.json",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16di_governed_scope_write_denied_when_research_evidence_session_mismatches(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-other",
                    "path": ".azoth/research/sess-governed.json",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dj_governed_scope_write_denied_when_research_evidence_path_is_absolute(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": str((tmp_path / "evidence.md").resolve()),
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dja_governed_scope_write_denied_when_research_evidence_path_uses_windows_drive(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": r"C:\evidence.md",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dk_governed_scope_write_denied_when_research_evidence_path_traverses_parent(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": "../outside.md",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dl_governed_scope_write_denied_when_research_evidence_path_has_uri_scheme(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": "file:///tmp/evidence.md",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16dlb_governed_scope_write_denied_when_research_evidence_path_has_non_file_uri_scheme(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(json.dumps(_governed_scope_gate(expiry=expiry)), encoding="utf-8")
    pg_path.write_text(
        json.dumps(
            _pipeline_gate(
                expiry=expiry,
                research_required=True,
                research_evidence={
                    "kind": "repo-local",
                    "session_id": "sess-governed",
                    "path": "mailto:evidence",
                },
            )
        ),
        encoding="utf-8",
    )

    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"), pipeline_gate_path=pg_path)

    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t16e_pipeline_gate_bootstrap_bypasses_foreign_write_claim(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    output = _run(
        "Write",
        gate_path,
        file_path=str(pg_path),
        pipeline_gate_path=pg_path,
        write_claim={
            "session_id": "sess-foreign",
            "expires_at": _future_expiry(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert _decision(output) == "allow"


def test_t16f_mixed_pipeline_gate_and_repo_targets_do_not_bypass_write_claim(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    output = _run(
        "Write",
        gate_path,
        pipeline_gate_path=pg_path,
        write_claim={
            "session_id": "sess-foreign",
            "expires_at": _future_expiry(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        },
        tool_input_override={
            "files": [
                {"filePath": str(pg_path)},
                {"filePath": str(tmp_path / "src.txt")},
            ],
            "content": "hello\n",
        },
    )
    assert _decision(output) == "deny"
    assert "write claim" in _reason(output).lower()


def test_t16g_non_memory_claude_home_write_is_not_exempt(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run(
        "Write",
        gate_path,
        file_path=str(Path.home() / ".claude" / "not-memory.txt"),
    )
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t16h_approved_scope_without_session_id_denies(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(tmp_path / "src.txt"))
    assert _decision(output) == "deny"
    assert "missing session_id" in _reason(output)


def test_t17_scope_gate_thin_cli_write_denied_without_gate(tmp_path: Path) -> None:
    """Regression: scope-gate.py thin CLI (scope-only) must run without NameError."""
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    azoth_dir = workspace / ".azoth"
    azoth_dir.mkdir(exist_ok=True)
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(azoth_dir / "run-ledger.local.yaml")
    stdin_payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(tmp_path / "x.txt")},
        }
    )
    result = subprocess.run(
        ["python3", str(SCOPE_GATE_THIN_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t18_scope_gate_thin_malformed_stdin_allow(tmp_path: Path) -> None:
    """Parity with test_p5_002 test_a1: invalid JSON stdin must allow (fail-open)."""
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    result = subprocess.run(
        ["python3", str(SCOPE_GATE_THIN_PATH)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert _decision(out) == "allow"


def test_t19_write_to_claude_home_allowed_when_gate_closed(tmp_path: Path) -> None:
    """Writes to ~/.claude/…/memory must still require a valid scope gate."""
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": False, "expires_at": _future_expiry()}),
        encoding="utf-8",
    )
    claude_target = str(
        Path.home() / ".claude" / "projects" / "test-project" / "memory" / "project_status.md"
    )
    output = _run("Write", gate_path, file_path=claude_target)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t20_write_to_claude_home_allowed_when_gate_absent(tmp_path: Path) -> None:
    """Writes to ~/.claude/…/memory are denied when no scope gate file exists."""
    gate_path = tmp_path / "scope-gate.json"  # does not exist
    claude_target = str(
        Path.home() / ".claude" / "projects" / "test-project" / "memory" / "MEMORY.md"
    )
    output = _run("Write", gate_path, file_path=claude_target)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t20b_governed_memory_write_requires_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    claude_target = str(
        Path.home() / ".claude" / "projects" / "test-project" / "memory" / "MEMORY.md"
    )
    output = _run("Write", gate_path, file_path=claude_target)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t20c_governed_memory_write_still_hits_write_claim(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    expiry = _future_expiry()
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expiry,
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": expiry,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "pipeline": "deliver-full",
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )
    claude_target = str(
        Path.home() / ".claude" / "projects" / "test-project" / "memory" / "MEMORY.md"
    )
    output = _run(
        "Write",
        gate_path,
        file_path=claude_target,
        pipeline_gate_path=pg_path,
        write_claim={
            "session_id": "sess-foreign",
            "expires_at": _future_expiry(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert _decision(output) == "deny"
    assert "write claim" in _reason(output).lower()


def test_t20d_entropy_state_write_still_hits_write_claim(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-standard",
            }
        ),
        encoding="utf-8",
    )
    entropy_target = tmp_path / "entropy-state.json"
    output = _run(
        "Write",
        gate_path,
        file_path=str(entropy_target),
        write_claim={
            "session_id": "sess-foreign",
            "expires_at": _future_expiry(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert _decision(output) == "deny"
    assert "write claim" in _reason(output).lower()
