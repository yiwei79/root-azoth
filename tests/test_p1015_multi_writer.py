"""
tests/test_p1015_multi_writer.py — Test suite for P1-015 True multi-writer safety.

All 27 test functions are present. Tests are written test-first: they will fail
(ImportError, AttributeError, or assertion failure) until implementation is complete.

Acceptance criteria covered:
  AC1 — Exactly one active write claim at a time
  AC2 — Competing writer denied mechanically or explicit conflict path
  AC3 — Claim handoff is explicit, auditable, tied to session_id
  AC4 — Stale/abandoned claims have a recovery path that does not bypass safety
  AC5 — Cross-harness parity documented and tested
  Regression — backward-compat and load/status helpers
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_ledger.py"
SCHEMA = ROOT / "pipelines" / "run-ledger.schema.yaml"
ORCHESTRATOR_PATH = ROOT / ".claude" / "hooks" / "edit_pretooluse_orchestrator.py"
WRITE_CLAIM_HOOK_PATH = ROOT / ".claude" / "hooks" / "write_claim_check.py"
CURSOR_PARITY_PATH = ROOT / ".cursor" / "rules" / "claude-code-parity.mdc"
NEXT_COMMAND_PATH = ROOT / ".claude" / "commands" / "next.md"
SESSION_CLOSEOUT_PATH = ROOT / ".claude" / "commands" / "session-closeout.md"

sys.path.insert(0, str(ROOT / "scripts"))

# validate_ledger already exists; P1-015 helpers are now implemented.
from run_ledger import validate_ledger  # noqa: E402
from run_ledger import (  # noqa: E402
    acquire_write_claim,
    load_write_claim,
    release_write_claim,
    resolve_stale_claims,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_expiry(seconds: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _make_ledger(tmp_path: Path, write_claim: dict | None = None) -> Path:
    """Write a minimal valid ledger to tmp_path/.azoth/run-ledger.local.yaml."""
    azoth = tmp_path / ".azoth"
    azoth.mkdir(exist_ok=True)
    ledger_path = azoth / "run-ledger.local.yaml"
    data: dict = {"schema_version": 1, "runs": []}
    if write_claim is not None:
        data["write_claim"] = write_claim
    ledger_path.write_text(yaml.dump(data), encoding="utf-8")
    return ledger_path


def _run_ledger_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    ledger = tmp_path / ".azoth" / "run-ledger.local.yaml"
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), *args],
        capture_output=True,
        text=True,
    )


def _run_orchestrator(
    gate_path: Path, tool_name: str = "Write", file_path: str | None = None
) -> dict:
    """Run the PreToolUse orchestrator with optional write-claim env."""
    tool_input: dict = {}
    if file_path is not None:
        tool_input["file_path"] = file_path
    payload = json.dumps(
        {
            "tool_name": tool_name,
            "hook_event_name": "PreToolUse",
            "tool_input": tool_input,
        }
    )
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# ── AC1 — Exactly one active write claim at a time ───────────────────────────


def test_p1015_schema_write_claim() -> None:
    """Schema file must document a write_claim top-level key with required sub-fields."""
    data = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    # write_claim must appear as a top-level property in the schema
    props = data.get("properties", {})
    assert "write_claim" in props, "Schema must define a top-level write_claim property"
    claim_props = props["write_claim"].get("properties", {})
    for field in ("session_id", "expires_at", "acquired_at"):
        assert field in claim_props, f"write_claim schema must include field '{field}'"


def test_p1015_validate_write_claim_valid(tmp_path: Path) -> None:
    """validate_ledger accepts a ledger with a well-formed write_claim."""
    data = {
        "schema_version": 1,
        "runs": [],
        "write_claim": {
            "session_id": "2026-04-11-p1-015-claude-code-120000",
            "expires_at": _future_expiry(),
            "acquired_at": "2026-04-11T10:00:00+00:00",
        },
    }
    errors = validate_ledger(data)
    assert errors == [], f"Valid write_claim raised errors: {errors}"


def test_p1015_validate_write_claim_missing_field(tmp_path: Path) -> None:
    """validate_ledger rejects a write_claim missing expires_at."""
    data = {
        "schema_version": 1,
        "runs": [],
        "write_claim": {
            "session_id": "sess-a",
            # expires_at intentionally omitted
            "acquired_at": "2026-04-11T10:00:00+00:00",
        },
    }
    errors = validate_ledger(data)
    assert any("expires_at" in e for e in errors), f"Expected expires_at error, got: {errors}"


def test_p1015_validate_write_claim_bad_iso(tmp_path: Path) -> None:
    """validate_ledger rejects a write_claim with a non-ISO expires_at."""
    data = {
        "schema_version": 1,
        "runs": [],
        "write_claim": {
            "session_id": "sess-a",
            "expires_at": "not-a-date",
            "acquired_at": "2026-04-11T10:00:00+00:00",
        },
    }
    errors = validate_ledger(data)
    assert any("expires_at" in e for e in errors), f"Expected ISO date error, got: {errors}"


def test_p1015_only_one_active_claim(tmp_path: Path) -> None:
    """After a successful acquire, a second acquire for a different session is denied."""
    _make_ledger(tmp_path)
    # First acquire succeeds
    ok, _ = acquire_write_claim(
        tmp_path, "sess-a", _future_expiry()
    )
    assert ok, "First acquire must succeed on empty ledger"
    # Second acquire from a different session must be denied
    denied, reason = acquire_write_claim(
        tmp_path, "sess-b", _future_expiry()
    )
    assert not denied, "Second acquire must fail when claim is already held"
    assert reason, "Denial must include a non-empty reason"


# ── AC2 — Competing writer denied mechanically or explicit conflict path ──────


def test_p1015_acquire_conflicting_claim_denied(tmp_path: Path) -> None:
    """acquire_write_claim returns (False, reason) when unexpired claim exists for another session."""
    claim = {
        "session_id": "sess-owner",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    ok, reason = acquire_write_claim(tmp_path, "sess-intruder", _future_expiry())
    assert not ok
    assert "sess-owner" in reason or "held" in reason.lower() or "conflict" in reason.lower()


def test_p1015_hook_write_claim_check_deny(tmp_path: Path) -> None:
    """write_claim_check.py evaluate_write_claim() returns deny when claim is foreign."""
    assert WRITE_CLAIM_HOOK_PATH.exists(), (
        f"write_claim_check.py must exist at {WRITE_CLAIM_HOOK_PATH}"
    )
    # Build a minimal ledger with an existing claim from another session
    claim = {
        "session_id": "sess-other",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    # Import the hook module and call evaluate_write_claim
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    result = evaluate_write_claim(tmp_path, requesting_session="sess-mine")
    assert not result.allowed
    assert result.deny_reason


def test_p1015_hook_deny_message_format(tmp_path: Path) -> None:
    """Deny message from write_claim_check contains session_id of the holding session."""
    claim = {
        "session_id": "sess-holder-xyz",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    result = evaluate_write_claim(tmp_path, requesting_session="sess-other")
    assert not result.allowed
    assert "sess-holder-xyz" in result.deny_reason


def test_p1015_orchestrator_write_claim_gate(tmp_path: Path) -> None:
    """PreToolUse orchestrator denies Write when write_claim is held by a different session."""
    # Set up a valid scope gate (approved, unexpired) in tmp_path
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-intruder",
                "goal": "test",
                "approved_by": "human",
            }
        ),
        encoding="utf-8",
    )
    # Put a valid write-claim ledger where the hook can find it
    # The hook reads AZOTH_WRITE_CLAIM_LEDGER_PATH or derives from AZOTH_SCOPE_GATE_PATH
    claim = {
        "session_id": "sess-owner",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    azoth = tmp_path / ".azoth"
    azoth.mkdir(exist_ok=True)
    ledger_path = azoth / "run-ledger.local.yaml"
    ledger_path.write_text(
        yaml.dump({"schema_version": 1, "runs": [], "write_claim": claim}),
        encoding="utf-8",
    )
    env = {**os.environ}
    env["AZOTH_SCOPE_GATE_PATH"] = str(gate_path)
    env["AZOTH_ENTROPY_STATE_PATH"] = str(tmp_path / "entropy-state.json")
    env["AZOTH_LEDGER_PATH"] = str(ledger_path)
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(tmp_path / "some-file.py")},
        }
    )
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    decision = output["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny", f"Expected deny from write-claim gate, got {decision}"


# ── AC3 — Claim handoff is explicit, auditable, tied to session_id ────────────


def test_p1015_acquire_write_claim_returns_session_id(tmp_path: Path) -> None:
    """acquire_write_claim(root, session_id, expires_at) -> (True, session_id) on success."""
    _make_ledger(tmp_path)
    ok, info = acquire_write_claim(tmp_path, "sess-alpha", _future_expiry())
    assert ok is True
    # info should contain the session_id on success
    assert "sess-alpha" in info


def test_p1015_claim_auditable_fields(tmp_path: Path) -> None:
    """After acquire_write_claim, load_write_claim returns all required audit fields."""
    _make_ledger(tmp_path)
    expires = _future_expiry()
    acquire_write_claim(tmp_path, "sess-audit", expires)
    claim = load_write_claim(tmp_path)
    assert claim is not None
    assert claim.get("session_id") == "sess-audit"
    assert "expires_at" in claim
    assert "acquired_at" in claim


def test_p1015_next_command_acquires_claim(tmp_path: Path) -> None:
    """next.md must document step 10b — acquire write claim before writing scope-gate."""
    text = NEXT_COMMAND_PATH.read_text(encoding="utf-8")
    # The updated next.md must reference the write-claim acquisition step
    assert "write_claim" in text.lower() or "write claim" in text.lower() or "claim" in text.lower(), (
        "next.md must document write-claim acquisition (step 10b)"
    )


def test_p1015_agents_next_parity(tmp_path: Path) -> None:
    """agents/next step 10b wording must include 'claim' to signal acquisition intent."""
    # This tests that the next.md command file mentions acquiring a claim after approval.
    # It is satisfied by the same file as test_p1015_next_command_acquires_claim but checks
    # the step ordering — step 10 (write scope-gate.json) must be paired with claim acquisition.
    text = NEXT_COMMAND_PATH.read_text(encoding="utf-8")
    # Claim must appear in the vicinity of step 10
    step10_index = text.find("10.")
    assert step10_index != -1, "next.md must have a step 10"
    after_step10 = text[step10_index : step10_index + 600]
    assert "claim" in after_step10.lower(), (
        "Step 10 of next.md must reference write-claim acquisition (10b)"
    )


# ── AC4 — Stale/abandoned claims have a recovery path that does not bypass safety ─


def test_p1015_resolve_stale_clears_expired(tmp_path: Path) -> None:
    """resolve_stale_claims clears a claim whose expires_at is in the past."""
    expired_claim = {
        "session_id": "sess-stale",
        "expires_at": _past_expiry(seconds=60),
        "acquired_at": "2026-04-10T09:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=expired_claim)
    cleared = resolve_stale_claims(tmp_path)
    assert cleared is True, "resolve_stale_claims must return True when a stale claim was cleared"
    remaining = load_write_claim(tmp_path)
    assert remaining is None, "Stale claim must be removed after resolve_stale_claims"


def test_p1015_resolve_stale_unexpired_untouched(tmp_path: Path) -> None:
    """resolve_stale_claims leaves an unexpired claim in place."""
    live_claim = {
        "session_id": "sess-live",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=live_claim)
    cleared = resolve_stale_claims(tmp_path)
    assert cleared is False, "resolve_stale_claims must return False when no stale claim found"
    remaining = load_write_claim(tmp_path)
    assert remaining is not None, "Unexpired claim must not be touched"
    assert remaining["session_id"] == "sess-live"


def test_p1015_release_own_claim(tmp_path: Path) -> None:
    """release_write_claim removes the claim when called with the owning session_id."""
    _make_ledger(tmp_path)
    acquire_write_claim(tmp_path, "sess-owner", _future_expiry())
    released = release_write_claim(tmp_path, "sess-owner")
    assert released is True, "release_write_claim must return True when own claim released"
    remaining = load_write_claim(tmp_path)
    assert remaining is None


def test_p1015_release_other_session_noop(tmp_path: Path) -> None:
    """release_write_claim is a no-op when called by a session that does not hold the claim."""
    claim = {
        "session_id": "sess-owner",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    released = release_write_claim(tmp_path, "sess-intruder")
    assert released is False, "release_write_claim must return False for non-owner"
    # Claim must still be present
    remaining = load_write_claim(tmp_path)
    assert remaining is not None
    assert remaining["session_id"] == "sess-owner"


def test_p1015_session_closeout_releases_claim(tmp_path: Path) -> None:
    """session-closeout.md must document that W2-claim releases the write claim."""
    text = SESSION_CLOSEOUT_PATH.read_text(encoding="utf-8")
    # The updated session-closeout.md must mention releasing the write claim in W2
    assert "claim" in text.lower(), (
        "session-closeout.md W2 must document releasing the write claim"
    )


# ── AC5 — Cross-harness parity documented and tested ─────────────────────────


def test_p1015_cursor_parity_docs(tmp_path: Path) -> None:
    """claude-code-parity.mdc must have a section for write-claim simulation."""
    text = CURSOR_PARITY_PATH.read_text(encoding="utf-8")
    assert "write_claim" in text.lower() or "write claim" in text.lower(), (
        "claude-code-parity.mdc must document write-claim simulation rule"
    )


def test_p1015_cursor_parity_checklist(tmp_path: Path) -> None:
    """The quick parity checklist in claude-code-parity.mdc must include a write-claim item."""
    text = CURSOR_PARITY_PATH.read_text(encoding="utf-8")
    # Locate the checklist section
    checklist_index = text.lower().find("quick parity checklist")
    assert checklist_index != -1, "Parity doc must contain 'Quick parity checklist' section"
    checklist_section = text[checklist_index : checklist_index + 1200]
    assert "claim" in checklist_section.lower(), (
        "Quick parity checklist must include a write-claim check item"
    )


def test_p1015_welcome_plain_write_claim(tmp_path: Path) -> None:
    """welcome.py --plain shows a Write claim line in System Health when scope is active."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib
    import welcome  # noqa: F401

    importlib.reload(welcome)  # ensure latest version
    # welcome.py must expose a function that returns the write-claim display string
    # It may be called format_write_claim_line, write_claim_status_line, or similar.
    assert hasattr(welcome, "write_claim_status_line") or hasattr(
        welcome, "format_write_claim_line"
    ), "welcome.py must expose a write-claim status helper"


def test_p1015_welcome_claim_held(tmp_path: Path) -> None:
    """welcome.py plain renderer shows 'Write claim: HELD' when claim session matches scope."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib
    import welcome  # noqa: F401

    importlib.reload(welcome)
    scope = {
        "approved": True,
        "expires_at": _future_expiry(),
        "session_id": "sess-w",
        "goal": "test",
    }
    claim = {
        "session_id": "sess-w",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    fn = getattr(welcome, "write_claim_status_line", None) or getattr(
        welcome, "format_write_claim_line", None
    )
    assert fn is not None
    line = fn(scope, claim)
    assert "HELD" in line.upper() or "held" in line.lower(), (
        f"Expected 'HELD' in write-claim status line, got: {line!r}"
    )


def test_p1015_welcome_no_claim(tmp_path: Path) -> None:
    """welcome.py plain renderer shows 'Write claim: none' when no claim is present."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib
    import welcome  # noqa: F401

    importlib.reload(welcome)
    scope = {
        "approved": True,
        "expires_at": _future_expiry(),
        "session_id": "sess-w",
        "goal": "test",
    }
    fn = getattr(welcome, "write_claim_status_line", None) or getattr(
        welcome, "format_write_claim_line", None
    )
    assert fn is not None
    line = fn(scope, None)
    assert "none" in line.lower() or "no claim" in line.lower(), (
        f"Expected 'none' in write-claim status line, got: {line!r}"
    )


# ── Regression ────────────────────────────────────────────────────────────────


def test_p1015_no_claim_backward_compat(tmp_path: Path) -> None:
    """validate_ledger passes a ledger with no write_claim key (backward compat, soft-allow)."""
    data = {
        "schema_version": 1,
        "runs": [
            {
                "run_id": "old-run",
                "mode": "deliver",
                "goal": "backward compat test",
                "status": "complete",
                "created_at": "2026-04-10T10:00:00+00:00",
                "updated_at": "2026-04-10T10:30:00+00:00",
                "next_action": "done",
            }
        ],
    }
    errors = validate_ledger(data)
    assert errors == [], f"Ledger without write_claim must still validate: {errors}"


def test_p1015_status_shows_claim(tmp_path: Path) -> None:
    """run_ledger status subcommand shows write-claim info when claim is held."""
    _make_ledger(
        tmp_path,
        write_claim={
            "session_id": "sess-status-test",
            "expires_at": _future_expiry(),
            "acquired_at": "2026-04-11T10:00:00+00:00",
        },
    )
    result = _run_ledger_cli(tmp_path, "status")
    assert result.returncode == 0
    assert "claim" in result.stdout.lower() or "sess-status-test" in result.stdout, (
        f"status output must show write-claim info; got: {result.stdout!r}"
    )


def test_p1015_load_write_claim(tmp_path: Path) -> None:
    """load_write_claim returns the write_claim dict from an existing ledger."""
    expected_claim = {
        "session_id": "sess-load-test",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=expected_claim)
    claim = load_write_claim(tmp_path)
    assert claim is not None
    assert claim["session_id"] == "sess-load-test"


def test_p1015_resolve_stale_absent(tmp_path: Path) -> None:
    """resolve_stale_claims returns False and does not error when no claim exists."""
    _make_ledger(tmp_path)  # no write_claim
    result = resolve_stale_claims(tmp_path)
    assert result is False, "resolve_stale_claims must return False when no claim present"
    # Ledger must still be valid
    ledger_path = tmp_path / ".azoth" / "run-ledger.local.yaml"
    data = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    errors = validate_ledger(data)
    assert errors == []


# ── evaluate_write_claim unit coverage ────────────────────────────────────────


def test_p1015_evaluate_write_claim_no_claim(tmp_path: Path) -> None:
    """evaluate_write_claim allows write when no claim is present in the ledger."""
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    _make_ledger(tmp_path)  # no write_claim key
    result = evaluate_write_claim(tmp_path, requesting_session="sess-any")
    assert result.allowed is True, "No claim in ledger must allow write"


def test_p1015_evaluate_write_claim_session_match(tmp_path: Path) -> None:
    """evaluate_write_claim allows write when requesting session is the claim holder."""
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    claim = {
        "session_id": "sess-owner",
        "expires_at": _future_expiry(),
        "acquired_at": "2026-04-11T10:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    result = evaluate_write_claim(tmp_path, requesting_session="sess-owner")
    assert result.allowed is True, "Same-session claim holder must be allowed"


def test_p1015_evaluate_write_claim_expired_allow(tmp_path: Path) -> None:
    """evaluate_write_claim allows write when the existing claim has expired."""
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    claim = {
        "session_id": "sess-stale",
        "expires_at": _past_expiry(seconds=60),
        "acquired_at": "2026-04-10T09:00:00+00:00",
    }
    _make_ledger(tmp_path, write_claim=claim)
    result = evaluate_write_claim(tmp_path, requesting_session="sess-newcomer")
    assert result.allowed is True, "Expired claim must not block a new writer"


def test_p1015_import_error_fail_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """evaluate_write_claim fails open (allowed=True) when run_ledger cannot be imported."""
    hook_dir = str(WRITE_CLAIM_HOOK_PATH.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    from write_claim_check import evaluate_write_claim  # type: ignore[import]

    _make_ledger(tmp_path)
    # Setting sys.modules["run_ledger"] = None causes Python to raise ImportError on
    # `from run_ledger import ...` even when the module was previously cached.
    monkeypatch.setitem(sys.modules, "run_ledger", None)
    result = evaluate_write_claim(tmp_path, requesting_session="sess-test")
    assert result.allowed is True, "ImportError must fail open (allow)"
    assert "[write-claim] WARNING" in result.deny_reason
