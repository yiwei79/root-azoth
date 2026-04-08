#!/usr/bin/env python3
"""
Interactive onboarding for Azoth (D5, D36).

- project:  install kernel/skills/agents into the current directory from this checkout.
- scaffold: you develop root-azoth (this repo); prints next steps — does not run install.

Usage:
  python3 scripts/azoth_init.py
  python3 scripts/azoth_init.py --project -y
  python3 scripts/azoth_init.py --scaffold -y
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_windows() -> bool:
    return platform.system() == "Windows" or os.name == "nt"


def _prompt_mode() -> str:
    print("Azoth init — where are you working?\n")
    print("  [1] Project  — Install Azoth into this directory (consumer app).")
    print("  [2] Scaffold — I develop the toolkit (root-azoth checkout).\n")
    choice = input("Choice [1/2] (default: 1): ").strip() or "1"
    return "project" if choice == "1" else "scaffold"


def _run_project_install(azoth_root: Path, cwd: Path) -> int:
    install_sh = azoth_root / "install.sh"
    install_ps1 = azoth_root / "install.ps1"
    if not install_sh.is_file():
        print(f"ERROR: missing installer script: {install_sh}", file=sys.stderr)
        return 1

    if cwd.resolve() == azoth_root.resolve():
        print(
            "ERROR: cannot install into the Azoth repository itself. "
            "cd to your app first, then run this again.",
            file=sys.stderr,
        )
        return 1

    if _is_windows():
        ps = shutil.which("pwsh") or shutil.which("powershell")
        if not ps:
            print("ERROR: PowerShell (pwsh or powershell) not found.", file=sys.stderr)
            return 1
        if not install_ps1.is_file():
            print(f"ERROR: missing {install_ps1}", file=sys.stderr)
            return 1
        cmd = [ps, "-ExecutionPolicy", "Bypass", "-File", str(install_ps1)]
    else:
        bash = shutil.which("bash") or "/bin/bash"
        cmd = [bash, str(install_sh)]

    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        return e.returncode

    return 0


def _scaffold_guidance(azoth_root: Path, cwd: Path) -> None:
    if cwd.resolve() != azoth_root.resolve():
        print(
            "Note: Scaffold mode is for the root-azoth repository. "
            "Your current directory is not this checkout's root.\n"
        )
    print("Root-azoth workshop — suggested next steps:\n")
    print("  • Read CLAUDE.md and docs/AZOTH_ARCHITECTURE.md")
    print("  • pip install -r requirements-dev.txt   # from repo root; dev deps")
    print("  • python3 -m pytest tests/")
    print("  • After editing skills/agents/commands: python3 scripts/azoth-deploy.py")
    print("  • Session entry: python3 scripts/welcome.py  or  /start in Claude Code\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Azoth init — interactive onboarding (scaffold vs project)."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scaffold",
        action="store_true",
        help="Workshop mode: develop root-azoth (does not run install).",
    )
    mode.add_argument(
        "--project",
        action="store_true",
        help="Install Azoth into the current directory from this checkout.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive: requires --scaffold or --project.",
    )
    args = parser.parse_args()

    azoth_root = _repo_root()
    cwd = Path.cwd()

    if args.yes and not args.scaffold and not args.project:
        print("ERROR: -y requires --scaffold or --project.", file=sys.stderr)
        return 2

    if args.scaffold:
        mode = "scaffold"
    elif args.project:
        mode = "project"
    elif args.yes:
        print("ERROR: -y requires --scaffold or --project.", file=sys.stderr)
        return 2
    else:
        mode = _prompt_mode()

    if mode == "project":
        return _run_project_install(azoth_root, cwd)

    _scaffold_guidance(azoth_root, cwd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
