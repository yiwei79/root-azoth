#!/usr/bin/env python3
"""Switch the local Codex operating mode across permission profile and hook overlay.

The repository's canonical default remains the calm Codex profile. A local
workspace can opt into:

- `.codex/permission_profile.local` = `seamless` for the Azoth low-friction,
  repo-local permission profile
- `.codex/hooks.mode.local` = `verbose` for the diagnostic hook overlay

Tracked deploy artifacts remain stable:

- `.codex/config.toml` = calm default
- `.codex/config.seamless.toml` = tracked seamless companion
- `.codex/hooks.json` = calm default
- `.codex/hooks.verbose.json` = tracked verbose companion

Usage:
  python3 scripts/codex_hooks_mode.py status
  python3 scripts/codex_hooks_mode.py set calm
  python3 scripts/codex_hooks_mode.py set seamless
  python3 scripts/codex_hooks_mode.py set verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CALM = "calm"
SEAMLESS = "seamless"
VERBOSE = "verbose"
VERBOSE_ALIAS = "verbo"
VALID_MODES = {CALM, SEAMLESS, VERBOSE}
PERMISSION_MODES = {CALM, SEAMLESS}
HOOK_MODE_MARKER = Path(".codex/hooks.mode.local")
PERMISSION_PROFILE_MARKER = Path(".codex/permission_profile.local")
HOOKS_DEST = Path(".codex/hooks.json")
CONFIG_DEST = Path(".codex/config.toml")
RULES_DEST = Path(".codex/rules/azoth-seamless.star")
SEAMLESS_CONFIG_DEST = Path(".codex/config.seamless.toml")
VERBOSE_HOOKS_DEST = Path(".codex/hooks.verbose.json")
CODEX_ADAPTER_DIR = Path("kernel/templates/platform-adapters/codex")
TEMPLATE_BY_MODE = {
    CALM: CODEX_ADAPTER_DIR / "hooks.json.template",
    VERBOSE: CODEX_ADAPTER_DIR / "hooks.verbose.json.template",
}
CONFIG_TEMPLATE_BY_PERMISSION = {
    CALM: CODEX_ADAPTER_DIR / "config.toml.template",
    SEAMLESS: CODEX_ADAPTER_DIR / "config.seamless.toml.template",
}
RULES_TEMPLATE = CODEX_ADAPTER_DIR / "azoth-seamless.star.template"


def repo_root_from(path: Path | None = None) -> Path:
    here = path or Path(__file__).resolve().parent.parent
    return here.resolve()


def detect_hook_mode(root: Path) -> str:
    marker = root / HOOK_MODE_MARKER
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == VERBOSE:
        return VERBOSE
    return CALM


def detect_permission_profile(root: Path) -> str:
    marker = root / PERMISSION_PROFILE_MARKER
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == SEAMLESS:
        return SEAMLESS
    return CALM


def hook_template_path(root: Path, mode: str) -> Path:
    return root / TEMPLATE_BY_MODE[mode]


def config_template_path(root: Path, profile: str) -> Path:
    return root / CONFIG_TEMPLATE_BY_PERMISSION[profile]


def hooks_path(root: Path) -> Path:
    return root / HOOKS_DEST


def config_path(root: Path) -> Path:
    return root / CONFIG_DEST


def rules_path(root: Path) -> Path:
    return root / RULES_DEST


def hook_marker_path(root: Path) -> Path:
    return root / HOOK_MODE_MARKER


def permission_marker_path(root: Path) -> Path:
    return root / PERMISSION_PROFILE_MARKER


def ensure_templates(root: Path) -> None:
    missing = [
        str(TEMPLATE_BY_MODE[mode])
        for mode in {CALM, VERBOSE}
        if not hook_template_path(root, mode).is_file()
    ]
    missing.extend(
        str(CONFIG_TEMPLATE_BY_PERMISSION[mode])
        for mode in PERMISSION_MODES
        if not config_template_path(root, mode).is_file()
    )
    if not (root / RULES_TEMPLATE).is_file():
        missing.append(str(RULES_TEMPLATE))
    if missing:
        raise FileNotFoundError(
            "missing Codex adapter templates: "
            + ", ".join(missing)
            + " — run from the Azoth repo root"
        )


def hooks_in_sync(root: Path, mode: str) -> bool:
    destination = hooks_path(root)
    if not destination.is_file():
        return False
    return destination.read_text(encoding="utf-8") == hook_template_path(root, mode).read_text(
        encoding="utf-8"
    )


def config_in_sync(root: Path, profile: str) -> bool:
    destination = config_path(root)
    if not destination.is_file():
        return False
    return destination.read_text(encoding="utf-8") == config_template_path(
        root, profile
    ).read_text(encoding="utf-8")


def rules_in_sync(root: Path) -> bool:
    destination = rules_path(root)
    if not destination.is_file():
        return False
    return destination.read_text(encoding="utf-8") == (root / RULES_TEMPLATE).read_text(
        encoding="utf-8"
    )


def _deploy_selected_files(root: Path, *, permission_profile: str, hook_mode: str) -> None:
    selected_config = config_template_path(root, permission_profile)
    config_destination = config_path(root)
    config_destination.parent.mkdir(parents=True, exist_ok=True)
    config_destination.write_text(selected_config.read_text(encoding="utf-8"), encoding="utf-8")

    selected_hooks = hook_template_path(root, hook_mode)
    hooks_destination = hooks_path(root)
    hooks_destination.parent.mkdir(parents=True, exist_ok=True)
    hooks_destination.write_text(selected_hooks.read_text(encoding="utf-8"), encoding="utf-8")

    rules_destination = rules_path(root)
    rules_destination.parent.mkdir(parents=True, exist_ok=True)
    rules_destination.write_text((root / RULES_TEMPLATE).read_text(encoding="utf-8"), encoding="utf-8")


def set_mode(root: Path, mode: str) -> int:
    ensure_templates(root)
    if mode == VERBOSE_ALIAS:
        mode = VERBOSE
    if mode not in VALID_MODES:
        print(f"ERROR: invalid mode {mode!r}; choose one of {sorted(VALID_MODES)}", file=sys.stderr)
        return 2

    permission_profile = detect_permission_profile(root)
    hook_mode = detect_hook_mode(root)

    if mode in PERMISSION_MODES:
        permission_profile = mode
        hook_mode = CALM
    else:
        hook_mode = VERBOSE

    _deploy_selected_files(root, permission_profile=permission_profile, hook_mode=hook_mode)

    permission_marker = permission_marker_path(root)
    if permission_profile == SEAMLESS:
        permission_marker.parent.mkdir(parents=True, exist_ok=True)
        permission_marker.write_text(f"{SEAMLESS}\n", encoding="utf-8")
    elif permission_marker.exists():
        permission_marker.unlink()

    hook_marker = hook_marker_path(root)
    if hook_mode == VERBOSE:
        hook_marker.parent.mkdir(parents=True, exist_ok=True)
        hook_marker.write_text(f"{VERBOSE}\n", encoding="utf-8")
    elif hook_marker.exists():
        hook_marker.unlink()

    print(f"Codex permission profile: {'azoth-seamless' if permission_profile == SEAMLESS else CALM}")
    print(f"Codex hooks mode: {hook_mode}")
    print(f"Config template: {config_template_path(root, permission_profile).relative_to(root)}")
    print(f"Hooks template: {hook_template_path(root, hook_mode).relative_to(root)}")
    print(f"Rules template: {RULES_TEMPLATE}")
    print(f"Deployed config: {config_path(root).relative_to(root)}")
    print(f"Tracked seamless companion: {SEAMLESS_CONFIG_DEST}")
    print(f"Deployed hooks: {hooks_path(root).relative_to(root)}")
    print(f"Tracked verbose companion: {VERBOSE_HOOKS_DEST}")
    print(f"Deployed rules: {rules_path(root).relative_to(root)}")
    if permission_profile == SEAMLESS:
        print("Permission marker: .codex/permission_profile.local")
    else:
        print("Permission marker cleared; calm profile restored.")
    if hook_mode == VERBOSE:
        print("Hook marker: .codex/hooks.mode.local")
    else:
        print("Hook marker cleared; calm hook profile active.")
    return 0


def show_status(root: Path) -> int:
    ensure_templates(root)
    permission_profile = detect_permission_profile(root)
    hook_mode = detect_hook_mode(root)
    config_sync = config_in_sync(root, permission_profile)
    hooks_sync = hooks_in_sync(root, hook_mode)
    rule_sync = rules_in_sync(root)
    print(
        f"Codex permission profile: {'azoth-seamless' if permission_profile == SEAMLESS else CALM}"
    )
    print(f"Selected config template: {config_template_path(root, permission_profile).relative_to(root)}")
    print(f"Config file: {config_path(root).relative_to(root)}")
    print(f"Config in sync: {'yes' if config_sync else 'no'}")
    print(f"Tracked seamless companion: {SEAMLESS_CONFIG_DEST}")
    print(f"Codex hooks mode: {hook_mode}")
    print(f"Selected hooks template: {hook_template_path(root, hook_mode).relative_to(root)}")
    print(f"Hooks file: {hooks_path(root).relative_to(root)}")
    print(f"Hooks in sync: {'yes' if hooks_sync else 'no'}")
    print(f"Tracked verbose companion: {VERBOSE_HOOKS_DEST}")
    print(f"Rules file: {rules_path(root).relative_to(root)}")
    print(f"Rules in sync: {'yes' if rule_sync else 'no'}")
    permission_marker = permission_marker_path(root)
    if permission_marker.is_file():
        print(f"Permission marker: {permission_marker.relative_to(root)}")
    else:
        print("Permission marker: none")
    hook_marker = hook_marker_path(root)
    if hook_marker.is_file():
        print(f"Hook marker: {hook_marker.relative_to(root)}")
    else:
        print("Hook marker: none")
    if hook_mode == VERBOSE:
        print("Verbose is a hook overlay; the selected permission profile remains active.")
    return 0 if config_sync and hooks_sync and rule_sync else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Switch the local Codex operating mode between calm, seamless, and verbose."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root to operate on. Defaults to this script's checkout root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show the active Codex operating mode and sync state.")

    set_parser = subparsers.add_parser("set", help="Apply one of the supported Codex modes.")
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
