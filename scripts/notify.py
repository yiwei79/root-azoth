#!/usr/bin/env python3
"""
notify.py — Cross-platform notification utility for Copilot CLI sessions.

Provides sound alerts and system notifications when the agent needs human
attention. Mirrors the Claude Code Stop/Notification hooks for Copilot CLI
where no native hook system exists.

Usage:
    python3 scripts/notify.py                          # default notification
    python3 scripts/notify.py --title "Pipeline" --message "Stage complete"
    python3 scripts/notify.py --sound-only             # just the sound
    python3 scripts/notify.py --quiet                  # suppress stdout
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────

MACOS_SOUND: Path = Path("/System/Library/Sounds/Glass.aiff")
MACOS_SOUND_NAME: str = "Glass"

DEFAULT_TITLE: str = "Copilot CLI"
DEFAULT_MESSAGE: str = "Copilot needs your attention"


# ── Sound ────────────────────────────────────────────────────────────────


def play_sound(*, quiet: bool = False) -> None:
    """Play a platform-appropriate alert sound (non-blocking)."""
    os_name = platform.system()

    if os_name == "Darwin" and MACOS_SOUND.exists():
        # Fire-and-forget so the script doesn't block on playback
        subprocess.Popen(
            ["afplay", str(MACOS_SOUND)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not quiet:
            print("🔔 Sound played (Glass.aiff)")
        return

    if os_name == "Windows":
        ps = shutil.which("powershell")
        if ps:
            subprocess.Popen(
                [ps, "-NoProfile", "-Command", "[console]::beep(800,300)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not quiet:
                print("🔔 Sound played (PowerShell beep)")
            return

    # Linux / generic fallback — terminal bell
    sys.stderr.write("\a")
    sys.stderr.flush()
    if not quiet:
        print("🔔 Sound played (terminal bell)")


# ── Notification ─────────────────────────────────────────────────────────


def send_notification(title: str, message: str, *, quiet: bool = False) -> None:
    """Send a platform-appropriate system notification."""
    os_name = platform.system()

    if os_name == "Darwin":
        _notify_macos(title, message, quiet=quiet)
        return

    if os_name == "Linux":
        _notify_linux(title, message, quiet=quiet)
        return

    if os_name == "Windows":
        _notify_windows(title, message, quiet=quiet)
        return

    if not quiet:
        print(f"📢 [{title}] {message}")


def _notify_macos(title: str, message: str, *, quiet: bool = False) -> None:
    """macOS notification via osascript with sound."""
    escaped_msg = message.replace("\\", "\\\\").replace('"', '\\"')
    escaped_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        f'display notification "{escaped_msg}" '
        f'with title "{escaped_title}" '
        f'sound name "{MACOS_SOUND_NAME}"'
    )
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if not quiet:
            print(f"📢 Notification sent: [{title}] {message}")
    except (OSError, subprocess.TimeoutExpired):
        if not quiet:
            print(f"📢 [{title}] {message}")


def _notify_linux(title: str, message: str, *, quiet: bool = False) -> None:
    """Linux notification via notify-send, falling back to stdout."""
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if not quiet:
                print(f"📢 Notification sent: [{title}] {message}")
            return
        except (OSError, subprocess.TimeoutExpired):
            pass

    if not quiet:
        print(f"📢 [{title}] {message}")


def _notify_windows(title: str, message: str, *, quiet: bool = False) -> None:
    """Windows notification via PowerShell toast, falling back to stdout."""
    ps = shutil.which("powershell")
    if ps:
        escaped_msg = message.replace("'", "''")
        escaped_title = title.replace("'", "''")
        toast_script = (
            "[Windows.UI.Notifications.ToastNotificationManager, "
            "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
            "$template = [Windows.UI.Notifications.ToastNotificationManager]"
            "::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]"
            "::ToastText02); "
            "$textNodes = $template.GetElementsByTagName('text'); "
            f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{escaped_title}')) | Out-Null; "
            f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{escaped_msg}')) | Out-Null; "
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
            "[Windows.UI.Notifications.ToastNotificationManager]"
            f"::CreateToastNotifier('{escaped_title}').Show($toast)"
        )
        try:
            subprocess.run(
                [ps, "-NoProfile", "-Command", toast_script],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if not quiet:
                print(f"📢 Notification sent: [{title}] {message}")
            return
        except (OSError, subprocess.TimeoutExpired):
            pass

    if not quiet:
        print(f"📢 [{title}] {message}")


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-platform notification utility for Copilot CLI sessions.",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_TITLE,
        help=f"Notification title (default: {DEFAULT_TITLE!r})",
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help=f"Notification body (default: {DEFAULT_MESSAGE!r})",
    )
    parser.add_argument(
        "--sound-only",
        action="store_true",
        help="Play sound without showing a notification popup",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all stdout output",
    )
    args = parser.parse_args()

    try:
        if args.sound_only:
            play_sound(quiet=args.quiet)
        else:
            send_notification(args.title, args.message, quiet=args.quiet)
            play_sound(quiet=args.quiet)
    except Exception:
        # Notification is best-effort — never block the pipeline
        pass


if __name__ == "__main__":
    main()
