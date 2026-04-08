#!/usr/bin/env python3
"""SessionStart hook: run welcome dashboard from repo root regardless of process cwd.

Claude Code passes SessionStart JSON on stdin; we read it to avoid blocking, then
execute scripts/welcome.py with cwd set to the repository root (parent of .claude/).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_HOOK_FILE = Path(__file__).resolve()
_HOOKS = _HOOK_FILE.parent
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))
# .claude/hooks/this_file.py -> repo root is three levels up
ROOT = _HOOK_FILE.parent.parent.parent


def main() -> int:
    raw = sys.stdin.read()
    if raw.strip():
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            pass
    welcome = ROOT / "scripts" / "welcome.py"
    if not welcome.is_file():
        print(f"session_start_welcome: missing {welcome}", file=sys.stderr)
        return 1
    os.chdir(ROOT)
    azoth_dir = ROOT / ".azoth"
    azoth_dir.mkdir(parents=True, exist_ok=True)
    out_path = azoth_dir / "session-orientation.txt"

    proc = subprocess.run(
        [sys.executable, str(welcome), "--plain"],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0 and proc.stdout:
        try:
            out_path.write_text(proc.stdout, encoding="utf-8")
        except OSError:
            pass
        try:
            from session_telemetry import record_session_lifecycle

            record_session_lifecycle(
                ROOT,
                event="session_orientation",
                session_id="",
                detail="welcome --plain ok",
            )
        except Exception:
            pass
        sys.stdout.write(proc.stdout)
    else:
        err = (proc.stderr or proc.stdout or "")[:2000]
        print(err, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
