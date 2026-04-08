"""P5-004: session telemetry append-only log (D14)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"


@pytest.fixture()
def telemetry_env(tmp_path: Path) -> Path:
    os.environ["AZOTH_TELEMETRY_DIR"] = str(tmp_path)
    yield tmp_path
    del os.environ["AZOTH_TELEMETRY_DIR"]


def test_append_increments_turn_per_session(telemetry_env: Path) -> None:
    sys_path_insert = str(_HOOKS)
    import sys

    if sys_path_insert not in sys.path:
        sys.path.insert(0, sys_path_insert)
    from session_telemetry import record_pretooluse_write_edit

    fake_root = telemetry_env
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "a.txt", "content": "x"},
    }
    record_pretooluse_write_edit(
        fake_root,
        payload=payload,
        session_id="sess-a",
        outcome="allowed",
        entropy_delta=1.0,
        cumulative_entropy=2.0,
        entropy_zone="GREEN",
    )
    record_pretooluse_write_edit(
        fake_root,
        payload=payload,
        session_id="sess-a",
        outcome="allowed",
    )
    log = telemetry_env / "session-log.jsonl"
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    j0 = json.loads(lines[0])
    j1 = json.loads(lines[1])
    assert j0["turn"] == 1
    assert j1["turn"] == 2
    assert j0["session_id"] == "sess-a"


def test_corrupt_telemetry_seq_does_not_raise(telemetry_env: Path) -> None:
    import sys

    if str(_HOOKS) not in sys.path:
        sys.path.insert(0, str(_HOOKS))
    from session_telemetry import record_pretooluse_write_edit

    (telemetry_env / "telemetry_seq.json").write_text("not json {{{", encoding="utf-8")
    fake_root = telemetry_env
    record_pretooluse_write_edit(
        fake_root,
        payload={"tool_name": "Write", "tool_input": {"file_path": "a.txt"}},
        session_id="sess-x",
        outcome="allowed",
    )
    log = telemetry_env / "session-log.jsonl"
    assert log.is_file()
    assert len(log.read_text(encoding="utf-8").strip().splitlines()) >= 1


def test_telemetry_seq_rewritten_after_corrupt_read(telemetry_env: Path) -> None:
    """Corrupt seq file is replaced with valid JSON on next successful append."""
    import sys

    if str(_HOOKS) not in sys.path:
        sys.path.insert(0, str(_HOOKS))
    from session_telemetry import record_pretooluse_write_edit

    seq_path = telemetry_env / "telemetry_seq.json"
    seq_path.write_text("not json {{{", encoding="utf-8")
    fake_root = telemetry_env
    record_pretooluse_write_edit(
        fake_root,
        payload={"tool_name": "Write", "tool_input": {"file_path": "c.txt"}},
        session_id="sess-z",
        outcome="allowed",
    )
    data = json.loads(seq_path.read_text(encoding="utf-8"))
    assert data == {"session_id": "sess-z", "seq": 1}


def test_non_numeric_seq_resets_safely(telemetry_env: Path) -> None:
    import sys

    if str(_HOOKS) not in sys.path:
        sys.path.insert(0, str(_HOOKS))
    from session_telemetry import record_pretooluse_write_edit

    (telemetry_env / "telemetry_seq.json").write_text(
        json.dumps({"session_id": "sess-y", "seq": "bogus"}, sort_keys=True),
        encoding="utf-8",
    )
    fake_root = telemetry_env
    record_pretooluse_write_edit(
        fake_root,
        payload={"tool_name": "Write", "tool_input": {"file_path": "b.txt"}},
        session_id="sess-y",
        outcome="allowed",
    )
    log = telemetry_env / "session-log.jsonl"
    line = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
    assert line["turn"] == 1


def test_scope_deny_logs_without_session_id(telemetry_env: Path) -> None:
    import sys

    if str(_HOOKS) not in sys.path:
        sys.path.insert(0, str(_HOOKS))
    from session_telemetry import record_pretooluse_write_edit

    fake_root = telemetry_env
    record_pretooluse_write_edit(
        fake_root,
        payload={"tool_name": "Edit", "tool_input": {"file_path": "x.py"}},
        session_id="",
        outcome="denied",
        denial_stage="scope",
        reason="no gate",
    )
    log = telemetry_env / "session-log.jsonl"
    j = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
    assert j["outcome"] == "denied"
    assert j["denial_stage"] == "scope"
