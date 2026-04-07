#!/usr/bin/env python3
"""Commit message policy for Azoth (P5-001 / D43).

Rejects commit messages that contain a ``Co-Authored-By:`` trailer line (Git
trailer syntax). Matches case-insensitive ``Co-Authored-By:`` at the start of a
line (after optional whitespace). Prose that merely mentions the phrase
without trailer syntax is allowed.

See CLAUDE.md (Git conventions) and docs/DECISIONS_INDEX.md (D43).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Line-anchored trailer: optional indent, Co-Authored-By, optional space, colon.
_CO_AUTHORED_LINE = re.compile(
    r"^\s*Co-Authored-By\s*:",
    re.IGNORECASE | re.MULTILINE,
)


class CommitPolicyError(Exception):
    """Raised when a commit message violates policy."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_commit_message(text: str) -> None:
    """Raise CommitPolicyError if the message violates policy."""
    if text.startswith("\ufeff"):
        text = text[1:]
    if _CO_AUTHORED_LINE.search(text):
        raise CommitPolicyError(
            "Commit message must not contain a Co-Authored-By trailer "
            "(see CLAUDE.md Git conventions / D43)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Azoth commit message policy checker.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check", help="Validate a commit message file")
    check.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Path to commit message file (git passes this to commit-msg)",
    )
    args = parser.parse_args()
    if args.cmd == "check":
        content = args.path.read_text(encoding="utf-8")
        try:
            validate_commit_message(content)
        except CommitPolicyError as e:
            print(e.message, file=sys.stderr)
            return 1
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
