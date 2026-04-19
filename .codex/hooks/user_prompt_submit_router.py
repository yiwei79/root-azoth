#!/usr/bin/env python3
"""UserPromptSubmit hook for Azoth calm-flow routing in Codex."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from codex_control_plane import main as control_plane_main  # noqa: E402


def main() -> int:
    return control_plane_main()


if __name__ == "__main__":
    raise SystemExit(main())
