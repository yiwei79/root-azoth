from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PIP_GUARD = REPO_ROOT / ".claude" / "hooks" / "pip-install-guard.py"
POSTTOOL_FILTER = REPO_ROOT / ".claude" / "hooks" / "posttooluse_terminal_filter.py"


def _run_hook(script: Path, payload: str) -> str:
    result = subprocess.run(
        ["python3", str(script)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_pip_install_guard_denies_vscode_terminal_payload() -> None:
    payload = json.dumps(
        {
            "tool_name": "run_in_terminal",
            "tool_input": {"command": "pip install requests"},
        }
    )
    out = json.loads(_run_hook(PIP_GUARD, payload))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "pip-install-guard" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pip_install_guard_allows_manifest_install_for_vscode_terminal() -> None:
    payload = json.dumps(
        {
            "tool_name": "terminal",
            "tool_input": {"command": "pip install -r requirements-dev.txt"},
        }
    )
    out = json.loads(_run_hook(PIP_GUARD, payload))
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_posttooluse_filter_emits_additional_context_for_vscode_payload() -> None:
    long_output = "\n".join(
        [f"line {i}" for i in range(110)]
        + ["FAILED tests/test_example.py::test_case - AssertionError", "Traceback details"]
    )
    payload = json.dumps(
        {
            "tool_name": "run_in_terminal",
            "tool_input": {"command": "pytest"},
            "tool_response": long_output,
        }
    )
    out = json.loads(_run_hook(POSTTOOL_FILTER, payload))
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Output filtered" in ctx
    assert "FAILED tests/test_example.py::test_case" in ctx


def test_posttooluse_filter_preserves_raw_small_output_fallback() -> None:
    out = _run_hook(POSTTOOL_FILTER, "ok\n")
    assert out == "ok\n"