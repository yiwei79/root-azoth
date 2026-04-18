#!/usr/bin/env python3
"""UserPromptSubmit hook for Azoth workflow token routing in Codex."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_control_plane import directive_for_prompt  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    directive = directive_for_prompt(ROOT, prompt)
    if directive is None:
        return 0

    print(json.dumps(directive.as_hook_output()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
