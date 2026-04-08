"""P5-007: SessionStart hook contract for `.claude/settings.json` (Claude Code).

**Timeout (Claude Code hooks):** Hook entries may include a ``timeout`` field (duration in
**seconds**, per hooks documentation) that caps how long the hook subprocess may run before
Claude Code terminates it. If omitted, the product default applies. When adding ``SessionStart``
for ``session_start_welcome.py`` / ``welcome.py``, set an explicit timeout large enough for
cold Python startup and plain-text render (see human merge checklist for ``settings.json``).

This module validates the **live** repo ``.claude/settings.json`` (TDD: fails until
``SessionStart`` is merged) and includes **negative** cases on synthetic payloads to
guard against structural drift (missing keys, matchers that do not cover startup+resume).

**Review-independence:** subprocess smoke does not depend on Claude Code; it only checks
``python3 scripts/welcome.py`` exits 0 and prints a stable orientation marker.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

AZOTH_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = AZOTH_ROOT / ".claude" / "settings.json"
WELCOME_SCRIPT = AZOTH_ROOT / "scripts" / "welcome.py"
STABLE_STDOUT_MARKER = "AZOTH"


def _load_settings() -> dict[str, Any]:
    raw = SETTINGS_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


def _session_start_blocks(data: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    ss = hooks.get("SessionStart")
    if not isinstance(ss, list):
        return []
    return [b for b in ss if isinstance(b, dict)]


def matcher_covers_startup_and_resume(pattern: str) -> bool:
    """True if the Claude Code hook matcher regex matches both *startup* and *resume*."""
    if not pattern or not isinstance(pattern, str):
        return False
    try:
        compiled = re.compile(pattern)
    except re.error:
        return False
    return bool(compiled.fullmatch("startup")) and bool(compiled.fullmatch("resume"))


def session_start_contract_holds(data: dict[str, Any]) -> tuple[bool, str]:
    """Return (ok, reason) for SessionStart + welcome.py wiring."""
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False, "missing or invalid top-level hooks"
    ss = hooks.get("SessionStart")
    if ss is None:
        return False, "hooks.SessionStart missing"
    if not isinstance(ss, list) or len(ss) == 0:
        return False, "hooks.SessionStart must be a non-empty list"
    found_command = False
    found_matcher = False
    for block in ss:
        if not isinstance(block, dict):
            continue
        matcher = block.get("matcher")
        if isinstance(matcher, str) and matcher_covers_startup_and_resume(matcher):
            found_matcher = True
        hook_list = block.get("hooks")
        if not isinstance(hook_list, list):
            continue
        for h in hook_list:
            if not isinstance(h, dict):
                continue
            if h.get("type") != "command":
                continue
            cmd = h.get("command")
            if isinstance(cmd, str) and ("welcome.py" in cmd or "session_start_welcome.py" in cmd):
                found_command = True
    if not found_matcher:
        return False, "no SessionStart block with matcher covering startup and resume"
    if not found_command:
        return False, "no command hook invoking session_start_welcome.py or welcome.py"
    return True, ""


class TestSessionStartSettingsContract:
    """Live settings.json must wire SessionStart → welcome.py (P5-007)."""

    def test_parses_as_json_object(self) -> None:
        data = _load_settings()
        assert isinstance(data, dict)

    def test_hooks_session_start_exists_and_wires_welcome(self) -> None:
        data = _load_settings()
        ok, reason = session_start_contract_holds(data)
        assert ok, reason

    def test_session_start_matcher_accepts_literal_startup_resume_pattern(self) -> None:
        """Canonical pattern from P5-007: alternation startup|resume."""
        assert matcher_covers_startup_and_resume("startup|resume")

    def test_at_least_one_hook_entry_has_command_type(self) -> None:
        data = _load_settings()
        blocks = _session_start_blocks(data)
        assert blocks, "SessionStart must be present with at least one block"
        saw_command = False
        for block in blocks:
            for h in block.get("hooks") or []:
                if isinstance(h, dict) and h.get("type") == "command":
                    saw_command = True
                    break
        assert saw_command, "SessionStart must include a command-type hook"


class TestSessionStartNegativeCases:
    """Synthetic drift: missing keys or wrong matcher must not satisfy the contract."""

    @pytest.mark.parametrize(
        "bad,expected_substring",
        [
            ({}, "hooks"),
            ({"hooks": None}, "hooks"),
            ({"hooks": {}}, "SessionStart"),
            ({"hooks": {"SessionStart": []}}, "non-empty"),
            (
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "startup|resume",
                                "hooks": [{"type": "command", "command": "echo hi"}],
                            }
                        ]
                    }
                },
                "welcome.py",
            ),
            (
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "startup",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 scripts/welcome.py",
                                    }
                                ],
                            }
                        ]
                    }
                },
                "startup and resume",
            ),
        ],
    )
    def test_contract_rejects_invalid_shapes(self, bad: dict, expected_substring: str) -> None:
        ok, reason = session_start_contract_holds(bad)
        assert not ok
        assert expected_substring.lower() in reason.lower()


class TestWelcomePySubprocessSmoke:
    """Smoke: welcome dashboard runs from repo root (stable marker on stdout)."""

    def test_welcome_script_exists(self) -> None:
        assert WELCOME_SCRIPT.is_file()

    def test_welcome_py_exit_zero_and_marker(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(WELCOME_SCRIPT)],
            cwd=str(AZOTH_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert proc.returncode == 0, (proc.stderr or proc.stdout)[:2000]
        out = proc.stdout or ""
        assert STABLE_STDOUT_MARKER in out, (
            f"expected stdout to contain {STABLE_STDOUT_MARKER!r} for stable smoke detection"
        )


def test_session_start_hook_writes_orientation_file() -> None:
    """Wrapper tees plain welcome to .azoth/session-orientation.txt (optional verbatim Read)."""
    hook = AZOTH_ROOT / ".claude" / "hooks" / "session_start_welcome.py"
    proc = subprocess.run(
        [sys.executable, str(hook)],
        cwd=str(AZOTH_ROOT),
        input="{}",
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[:2000]
    path = AZOTH_ROOT / ".azoth" / "session-orientation.txt"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "AZOTH_SESSION_ORIENTATION_BEGIN" in text
    assert STABLE_STDOUT_MARKER in text


# Optional: when the kernel template gains SessionStart documentation, keep timeout in mind.
def test_settings_template_optional_timeout_note() -> None:
    """If ``settings.json.template`` ever documents SessionStart, it should mention timeout."""
    template = AZOTH_ROOT / "kernel" / "templates" / "settings.json.template"
    text = template.read_text(encoding="utf-8")
    if "SessionStart" not in text:
        pytest.skip("template does not yet include SessionStart; timeout note deferred")
    assert "timeout" in text.lower(), (
        "settings.json.template with SessionStart should mention hook timeout (seconds)"
    )
