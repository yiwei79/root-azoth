#!/usr/bin/env python3
"""Switch the local Codex hook profile between calm and verbose.

The repository's canonical default remains the calm Codex hook profile, but a
local workspace can opt into the verbose profile through a git-ignored marker:
`.codex/hooks.mode.local`.

Usage:
  python3 scripts/codex_hooks_mode.py status
  python3 scripts/codex_hooks_mode.py set calm
  python3 scripts/codex_hooks_mode.py set verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CALM = "calm"
VERBOSE = "verbose"
VERBOSE_ALIAS = "verbo"
VALID_MODES = {CALM, VERBOSE}
MODE_MARKER = Path(".codex/hooks.mode.local")
HOOKS_DEST = Path(".codex/hooks.json")
CODEX_ADAPTER_DIR = Path("kernel/templates/platform-adapters/codex")
TEMPLATE_BY_MODE = {
    CALM: CODEX_ADAPTER_DIR / "hooks.json.template",
    VERBOSE: CODEX_ADAPTER_DIR / "hooks.verbose.json.template",
}


def repo_root_from(path: Path | None = None) -> Path:
    here = path or Path(__file__).resolve().parent.parent
    return here.resolve()


def detect_mode(root: Path) -> str:
    marker = root / MODE_MARKER
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == VERBOSE:
        return VERBOSE
    return CALM


def template_path(root: Path, mode: str) -> Path:
    return root / TEMPLATE_BY_MODE[mode]


def hooks_path(root: Path) -> Path:
    return root / HOOKS_DEST


def marker_path(root: Path) -> Path:
    return root / MODE_MARKER


def ensure_templates(root: Path) -> None:
    missing = [str(TEMPLATE_BY_MODE[mode]) for mode in VALID_MODES if not template_path(root, mode).is_file()]
    if missing:
        raise FileNotFoundError(
            "missing Codex hook templates: " + ", ".join(missing) + " — run from the Azoth repo root"
        )


def hooks_in_sync(root: Path, mode: str) -> bool:
    destination = hooks_path(root)
    if not destination.is_file():
        return False
    return destination.read_text(encoding="utf-8") == template_path(root, mode).read_text(
        encoding="utf-8"
    )


def set_mode(root: Path, mode: str) -> int:
    ensure_templates(root)
    if mode == VERBOSE_ALIAS:
        mode = VERBOSE
    if mode not in VALID_MODES:
        print(f"ERROR: invalid mode {mode!r}; choose one of {sorted(VALID_MODES)}", file=sys.stderr)
        return 2

    selected_template = template_path(root, mode)
    destination = hooks_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(selected_template.read_text(encoding="utf-8"), encoding="utf-8")

    marker = marker_path(root)
    if mode == VERBOSE:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{VERBOSE}\n", encoding="utf-8")
    elif marker.exists():
        marker.unlink()

    print(f"Codex hooks mode: {mode}")
    print(f"Template: {selected_template.relative_to(root)}")
    print(f"Deployed: {destination.relative_to(root)}")
    if mode == VERBOSE:
        print("Local override marker: .codex/hooks.mode.local")
    else:
        print("Local override marker cleared; canonical calm default restored.")
    return 0


def show_status(root: Path) -> int:
    ensure_templates(root)
    mode = detect_mode(root)
    selected_template = template_path(root, mode)
    sync = hooks_in_sync(root, mode)
    print(f"Codex hooks mode: {mode}")
    print(f"Selected template: {selected_template.relative_to(root)}")
    print(f"Hooks file: {hooks_path(root).relative_to(root)}")
    print(f"Hooks in sync: {'yes' if sync else 'no'}")
    marker = marker_path(root)
    if marker.is_file():
        print(f"Local override marker: {marker.relative_to(root)}")
    else:
        print("Local override marker: none")
    return 0 if sync else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Switch the local Codex hook profile between calm and verbose."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root to operate on. Defaults to this script's checkout root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show the active Codex hook mode and sync state.")

    set_parser = subparsers.add_parser("set", help="Apply one of the supported Codex hook modes.")
    set_parser.add_argument("mode", choices=sorted(VALID_MODES | {VERBOSE_ALIAS}))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root_from(args.root)

    if args.command == "status":
        return show_status(root)
    if args.command == "set":
        return set_mode(root, args.mode)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
