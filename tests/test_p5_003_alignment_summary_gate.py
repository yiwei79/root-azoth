"""P5-003: alignment-summary PreToolUse gate for .azoth/handoffs stage YAML (BL-012)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GATE = _REPO_ROOT / ".claude" / "hooks" / "alignment_summary_gate.py"
_ORCHESTRATOR = _REPO_ROOT / ".claude" / "hooks" / "edit_pretooluse_orchestrator.py"


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _run_orchestrator(
    stdin_payload: str,
    *,
    gate_path: Path,
    repo_root: Path,
) -> dict:
    workspace = gate_path.parent
    env = {
        **os.environ,
        "AZOTH_SCOPE_GATE_PATH": str(gate_path),
        "AZOTH_ENTROPY_STATE_PATH": str(workspace / "entropy-state.json"),
        "AZOTH_REPO_ROOT": str(repo_root.resolve()),
    }
    result = subprocess.run(
        ["python3", str(_ORCHESTRATOR)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _orch_decision(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecision"]


def _orch_reason(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecisionReason"]


def _run_gate(
    stdin_payload: str,
    *,
    repo_root: Path,
) -> dict:
    env = {**os.environ, "AZOTH_REPO_ROOT": str(repo_root.resolve())}
    result = subprocess.run(
        ["python3", str(_GATE)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _decision(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecision"]


def _reason(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecisionReason"]


def _handoff_file(repo_root: Path, name: str = "h.yaml") -> Path:
    p = repo_root / ".azoth" / "handoffs" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _write_payload(path: Path, content: str) -> str:
    return json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(path.resolve()), "content": content},
        }
    )


def _edit_payload(path: Path, old_string: str, new_string: str) -> str:
    return json.dumps(
        {
            "tool_name": "Edit",
            "hook_event_name": "PreToolUse",
            "tool_input": {
                "file_path": str(path.resolve()),
                "old_string": old_string,
                "new_string": new_string,
            },
        }
    )


def _write_payload_rel(file_path_rel: str, content: str) -> str:
    return json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": file_path_rel, "content": content},
        }
    )


_VALID_MINIMAL_YAML = """stage_summary_version: 1
pipeline: deliver-full
stage_id: deliver_full_s5
agent: builder
stage_kind: build
status: complete
entropy: GREEN
"""


def test_malformed_stdin_allow(tmp_path: Path) -> None:
    env = {**os.environ, "AZOTH_REPO_ROOT": str(tmp_path.resolve())}
    result = subprocess.run(
        ["python3", str(_GATE)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert _decision(out) == "allow"


def test_non_handoff_write_unchanged_allow(tmp_path: Path) -> None:
    target = tmp_path / "src" / "other.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _write_payload(target, "print('x')\n")
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_non_handoff_edit_unchanged_allow(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("alpha\n", encoding="utf-8")
    payload = _edit_payload(target, "alpha", "beta")
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_other_tool_allow(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "hook_event_name": "PreToolUse",
            "tool_input": {"command": "echo hi"},
        }
    )
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_write_handoff_invalid_deny(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "bad.yaml")
    bad_yaml = "stage_summary_version: 1\npipeline: deliver-full\n"
    payload = _write_payload(hf, bad_yaml)
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "deny"
    r = _reason(out).lower()
    assert "alignment" in r or "stage" in r or "summary" in r or "handoff" in r


def test_write_handoff_valid_allow(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "ok.yaml")
    payload = _write_payload(hf, _VALID_MINIMAL_YAML)
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_write_handoff_multi_doc_deny(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "multi.yaml")
    two_docs = _VALID_MINIMAL_YAML + "\n---\n" + _VALID_MINIMAL_YAML.replace(
        "deliver_full_s5", "deliver_full_s6"
    )
    payload = _write_payload(hf, two_docs)
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "deny"
    assert "multi" in _reason(out).lower() or "document" in _reason(out).lower()


def test_edit_handoff_invalid_deny(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "edit_bad.yaml")
    hf.write_text(_VALID_MINIMAL_YAML, encoding="utf-8")
    payload = _edit_payload(
        hf,
        "pipeline: deliver-full",
        "pipeline: not-a-real-pipeline",
    )
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "deny"


def test_edit_handoff_old_string_missing_deny(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "edit_miss.yaml")
    hf.write_text(_VALID_MINIMAL_YAML, encoding="utf-8")
    payload = _edit_payload(hf, "NOT_PRESENT_IN_FILE", "x")
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "deny"
    assert "[alignment-summary]" in _reason(out)
    assert "not found" in _reason(out).lower()


def test_edit_handoff_old_string_duplicate_deny(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "edit_dup.yaml")
    hf.write_text("dup\npipeline: deliver-full\ndup\n", encoding="utf-8")
    payload = _edit_payload(hf, "dup", "once")
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "deny"
    assert "[alignment-summary]" in _reason(out)
    assert "exactly once" in _reason(out).lower()


def test_edit_handoff_valid_allow(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "edit_ok.yaml")
    incomplete = """stage_summary_version: 1
pipeline: deliver-full
stage_id: deliver_full_s5
agent: builder
stage_kind: build
entropy: GREEN
"""
    hf.write_text(incomplete, encoding="utf-8")
    payload = _edit_payload(
        hf,
        "stage_kind: build\nentropy:",
        "stage_kind: build\nstatus: complete\nentropy:",
    )
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_handoff_yml_extension_allow(tmp_path: Path) -> None:
    hf = _handoff_file(tmp_path, "legacy.yml")
    payload = _write_payload(hf, _VALID_MINIMAL_YAML)
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_orchestrator_malformed_stdin_allow(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    env = {
        **os.environ,
        "AZOTH_SCOPE_GATE_PATH": str(gate_path),
        "AZOTH_ENTROPY_STATE_PATH": str(workspace / "entropy-state.json"),
        "AZOTH_REPO_ROOT": str(tmp_path.resolve()),
    }
    result = subprocess.run(
        ["python3", str(_ORCHESTRATOR)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert _orch_decision(out) == "allow"


def test_write_handoff_relative_path_allow(tmp_path: Path) -> None:
    _handoff_file(tmp_path, "rel.yaml")
    rel = ".azoth/handoffs/rel.yaml"
    payload = _write_payload_rel(rel, _VALID_MINIMAL_YAML)
    out = _run_gate(payload, repo_root=tmp_path)
    assert _decision(out) == "allow"


def test_orchestrator_handoff_invalid_deny_before_entropy(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-orch-align",
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-orch-align",
                "cumulative_entropy": 0.0,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    hf = _handoff_file(tmp_path, "bad.yaml")
    bad_yaml = "stage_summary_version: 1\npipeline: deliver-full\n"
    payload = _write_payload(hf, bad_yaml)
    out = _run_orchestrator(payload, gate_path=gate_path, repo_root=tmp_path)
    assert _orch_decision(out) == "deny"
    assert "alignment" in _orch_reason(out).lower()


def test_orchestrator_handoff_valid_then_entropy_allow(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-orch-ok",
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-orch-ok",
                "cumulative_entropy": 0.0,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    hf = _handoff_file(tmp_path, "ok.yaml")
    payload = _write_payload(hf, _VALID_MINIMAL_YAML)
    out = _run_orchestrator(payload, gate_path=gate_path, repo_root=tmp_path)
    assert _orch_decision(out) == "allow"
