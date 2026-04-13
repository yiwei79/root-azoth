"""Unit tests for posttooluse_terminal_filter.py — BL-035.

Covers: _looks_like_terminal_payload, _response_text, _filter_output,
main() with JSON/raw stdin, and edge cases.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from posttooluse_terminal_filter import (  # noqa: E402
    _filter_output,
    _looks_like_terminal_payload,
    _response_text,
)


# --- _looks_like_terminal_payload -----------------------------------------


class TestLooksLikeTerminalPayload:
    @pytest.mark.parametrize(
        "tool_name",
        ["Bash", "terminal", "run_in_terminal", "terminal_command", "execute", "BASH"],
    )
    def test_recognized_tool_names(self, tool_name: str) -> None:
        assert _looks_like_terminal_payload({"tool_name": tool_name}) is True

    @pytest.mark.parametrize("tool_name", ["Write", "Read", "Edit", "ListDir"])
    def test_non_terminal_tool_names(self, tool_name: str) -> None:
        assert _looks_like_terminal_payload({"tool_name": tool_name}) is False

    def test_fallback_to_command_in_tool_input(self) -> None:
        payload = {"tool_name": "custom", "tool_input": {"command": "ls -la"}}
        assert _looks_like_terminal_payload(payload) is True

    def test_tool_input_without_command_key(self) -> None:
        payload = {"tool_name": "custom", "tool_input": {"path": "/tmp"}}
        assert _looks_like_terminal_payload(payload) is False

    def test_missing_tool_name(self) -> None:
        assert _looks_like_terminal_payload({}) is False

    def test_none_tool_name(self) -> None:
        assert _looks_like_terminal_payload({"tool_name": None}) is False

    def test_hyphenated_tool_name(self) -> None:
        # "run-in-terminal" normalizes to "run_in_terminal"
        assert _looks_like_terminal_payload({"tool_name": "run-in-terminal"}) is True


# --- _response_text -------------------------------------------------------


class TestResponseText:
    def test_string_response(self) -> None:
        assert _response_text({"tool_response": "hello"}) == "hello"

    def test_dict_response_stdout(self) -> None:
        assert _response_text({"tool_response": {"stdout": "out"}}) == "out"

    def test_dict_response_output(self) -> None:
        assert _response_text({"tool_response": {"output": "data"}}) == "data"

    def test_dict_response_priority_order(self) -> None:
        # stdout takes priority over output
        resp = {"tool_response": {"stdout": "first", "output": "second"}}
        assert _response_text(resp) == "first"

    def test_dict_response_empty_values_skipped(self) -> None:
        assert _response_text({"tool_response": {"stdout": "", "output": "used"}}) == "used"

    def test_dict_response_fallback_json_dumps(self) -> None:
        result = _response_text({"tool_response": {"custom_key": 42}})
        assert '"custom_key": 42' in result

    def test_list_response(self) -> None:
        assert _response_text({"tool_response": ["a", "b"]}) == "a\nb"

    def test_list_response_filters_non_strings(self) -> None:
        assert _response_text({"tool_response": ["a", 42, "b"]}) == "a\nb"

    def test_none_response(self) -> None:
        assert _response_text({"tool_response": None}) == ""

    def test_missing_response(self) -> None:
        assert _response_text({}) == ""


# --- _filter_output -------------------------------------------------------


class TestFilterOutput:
    def test_short_output_returns_empty(self) -> None:
        text = "\n".join(f"line {i}" for i in range(50))
        assert _filter_output(text) == ""

    def test_exactly_max_lines_returns_empty(self) -> None:
        text = "\n".join(f"line {i}" for i in range(100))
        assert _filter_output(text) == ""

    def test_long_output_with_errors_filters(self) -> None:
        lines = [f"line {i}" for i in range(110)]
        lines[55] = "ERROR: something failed"
        text = "\n".join(lines)
        result = _filter_output(text)
        assert "Output filtered" in result
        assert "ERROR: something failed" in result

    def test_long_output_no_errors_shows_tail(self) -> None:
        lines = [f"clean line {i}" for i in range(150)]
        text = "\n".join(lines)
        result = _filter_output(text)
        assert "no errors detected" in result
        assert "Last 10 lines" in result
        assert "clean line 149" in result

    def test_error_context_includes_surrounding_lines(self) -> None:
        lines = [f"context {i}" for i in range(120)]
        lines[60] = "Traceback (most recent call last):"
        text = "\n".join(lines)
        result = _filter_output(text)
        # Should include line before the error (context window)
        assert "context 59" in result
        assert "Traceback" in result

    @pytest.mark.parametrize(
        "keyword",
        ["error", "FAIL", "Exception", "traceback", "AssertionError", "warning:"],
    )
    def test_regex_matches_various_error_keywords(self, keyword: str) -> None:
        lines = [f"line {i}" for i in range(110)]
        lines[50] = f"something {keyword} here"
        text = "\n".join(lines)
        result = _filter_output(text)
        assert "Output filtered" in result
        assert keyword in result

    def test_many_errors_capped_at_max(self) -> None:
        lines = [f"ERROR line {i}" for i in range(200)]
        text = "\n".join(lines)
        result = _filter_output(text)
        result_lines = result.splitlines()
        # Header + up to _MAX_EMITTED_LINES content lines
        assert len(result_lines) <= 151  # 1 header + 150 max


# --- main() integration (via subprocess for isolation) --------------------


class TestMainIntegration:
    """Subprocess tests to validate main() entry point behavior."""

    def _run(self, stdin_data: str) -> str:
        import subprocess

        result = subprocess.run(
            [sys.executable, str(_HOOKS / "posttooluse_terminal_filter.py")],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def test_non_terminal_json_emits_empty_context(self) -> None:
        payload = json.dumps({"tool_name": "Write", "tool_input": {"path": "foo.py"}})
        out = json.loads(self._run(payload))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert ctx == ""

    def test_terminal_short_output_emits_empty_context(self) -> None:
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "tool_response": "hi\n",
            }
        )
        out = json.loads(self._run(payload))
        assert out["hookSpecificOutput"]["additionalContext"] == ""

    def test_raw_invalid_json_short_passes_through(self) -> None:
        out = self._run("not json at all\n")
        assert out == "not json at all\n"

    def test_raw_invalid_json_long_output_filtered(self) -> None:
        text = "\n".join(f"line {i}" for i in range(120))
        text += "\nERROR: boom"
        out = self._run(text)
        assert "Output filtered" in out
        assert "ERROR: boom" in out
