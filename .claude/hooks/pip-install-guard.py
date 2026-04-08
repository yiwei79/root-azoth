#!/usr/bin/env python3
"""
pip-install-guard.py — Block bare `pip install <package>` invocations.

Allowed:
  pip install -r requirements.txt       (requirements file)
  pip install -r requirements-dev.txt
  pip install -e .                       (editable local install)
  pip install .                          (local pyproject.toml / setup.py)
  pip install --upgrade pip              (pip self-upgrade)

Blocked:
  pip install requests                   (no requirements file)
  pip install requests boto3             (multiple packages, no -r)

Why: direct package installs bypass the project's dependency manifest.
Every dependency should be declared in a requirements file so the install
is reproducible and auditable.
"""

from __future__ import annotations

import json
import re
import sys


_REMINDER = (
    "[pip-install-guard] Blocked: bare `pip install` without a requirements file.\n"
    "\n"
    "Add the package to a requirements file first, then install with:\n"
    "    pip install -r requirements.txt\n"
    "    pip install -r requirements-dev.txt   # root-azoth workshop dev deps\n"
    "\n"
    "Exceptions allowed without a requirements file:\n"
    "  pip install -e .          (editable local install)\n"
    "  pip install .             (local package)\n"
    "  pip install --upgrade pip (pip self-upgrade)"
)

# Anchored at the start of the command string. Using match() (not search()) means
# we only trigger when pip/pip3/python -m pip IS the command being run — not when
# those words appear inside a string argument (python3 -c "...pip install...") or
# a heredoc body. Compound commands like "git status && pip install X" slip through,
# but that edge case is acceptable — the guard targets direct invocations.
_PIP_INSTALL = re.compile(r"^(?:python3?\s+-m\s+pip|pip3?)\s+install\b")

# Matches the start of a heredoc: << 'EOF', << "EOF", or << EOF
_HEREDOC_START = re.compile(r"<<\s*['\"]?(\w+)['\"]?")


def _first_command(command: str) -> str:
    """Return the command with heredoc body content stripped.

    Heredoc bodies are data — stripping them prevents the edge case where
    a heredoc body line happens to start with 'pip install'.
    """
    lines = command.splitlines()
    result: list[str] = []
    delimiter: str | None = None
    for line in lines:
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            continue
        m = _HEREDOC_START.search(line)
        if m:
            delimiter = m.group(1)
        result.append(line)
    return "\n".join(result).strip()


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def _allow() -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "",
                }
            }
        )
    )
    sys.exit(0)


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Fail-open on malformed stdin (e.g. testing without a real payload).
        _allow()
        return

    if payload.get("tool_name") != "Bash":
        _allow()
        return

    command: str = _first_command(payload.get("tool_input", {}).get("command", ""))

    if not _PIP_INSTALL.match(command):
        _allow()
        return

    # Allow: requirements file flag
    if re.search(r"\s(-r|--requirement)\s", command):
        _allow()
        return

    # Allow: local directory installs (editable or direct)
    if re.search(r"\binstall\s+(?:-e\s+)?\.(?:\s|$)", command):
        _allow()
        return

    # Allow: pip self-upgrade
    if re.search(r"\binstall\s+--upgrade\s+pip\b", command):
        _allow()
        return

    _deny(_REMINDER)


if __name__ == "__main__":
    main()
