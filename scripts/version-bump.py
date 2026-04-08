#!/usr/bin/env python3
"""
version-bump.py — D53 version bump automation.

Maintains the 0.0.PHASE.PATCH version scheme across azoth.yaml and
.azoth/roadmap.yaml using regex-based line replacement throughout.
YAML comments and formatting are fully preserved.

Usage:
  python scripts/version-bump.py --patch   [--azoth-yaml PATH] [--roadmap-yaml PATH]
  python scripts/version-bump.py --phase   [--azoth-yaml PATH] [--roadmap-yaml PATH]
  python scripts/version-bump.py --release [--azoth-yaml PATH] [--roadmap-yaml PATH]

Flags:
  --patch    0.0.N.M → 0.0.N.M+1  (every session delivery)
  --phase    0.0.N.M → 0.0.N+1.1  (phase completion — empty pending_task_refs; next
              slice status planned or backlog → active + current_patch 1)
  --release  v0.0.7 active → close v0.0.7 + v0.1.0 in roadmap, azoth 0.1.0 + phase 8,
           activate v0.2.0 @ current_patch 1 (post–v0.1.0 slice; phases TBD)

--release is human-gated: updates azoth.yaml + .azoth/roadmap.yaml, prints the
manual git-tag command. The human must inspect, run tests, tag, and push.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_VERSION4_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$")
_VERSION3_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# ── File I/O helpers ──────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ── Version parsing ───────────────────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, int, int, int]:
    """Parse a 4-component version string or exit 1."""
    m = _VERSION4_RE.match(v.strip())
    if not m:
        _die(f"version '{v}' does not match required format \\d+.\\d+.\\d+.\\d+")
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def _parse_version_patchable(v: str) -> tuple[list[int], bool]:
    """Parse azoth.yaml version for --patch: 4-part pre-1.0 or 3-part post-1.0 semver."""
    s = v.strip()
    m4 = _VERSION4_RE.match(s)
    if m4:
        return [int(m4.group(i)) for i in range(1, 5)], True
    m3 = _VERSION3_RE.match(s)
    if m3:
        return [int(m3.group(i)) for i in range(1, 4)], False
    _die(
        f"version '{v}' must be \\d+.\\d+.\\d+.\\d+ (pre-release) or \\d+.\\d+.\\d+ (post-1.0 patch)"
    )


# ── Regex helpers ─────────────────────────────────────────────────────────────


def _extract_azoth_version(text: str) -> str:
    """Return the version value string from azoth.yaml text."""
    m = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
    if not m:
        _die("could not find 'version:' field in azoth.yaml")
    return m.group(1)


def _set_azoth_version(text: str, new_version: str) -> str:
    """Replace the version: line in azoth.yaml text."""
    return re.sub(
        r"^(version:\s*).*$",
        rf"\g<1>{new_version}",
        text,
        flags=re.MULTILINE,
    )


def _set_azoth_phase_line(text: str, new_phase: int, comment: str | None = None) -> str:
    """Replace the phase: line in azoth.yaml; optional full-line comment after #."""
    if comment is not None:
        line = f"phase: {new_phase}  # {comment}"
        return re.sub(r"^phase:\s*\d+.*$", line, text, flags=re.MULTILINE)
    return re.sub(r"^(phase:\s*)\d+", rf"\g<1>{new_phase}", text, flags=re.MULTILINE)


def _ensure_completed_date_in_block(text: str, version_id: str, iso_date: str) -> str:
    """Insert completed_date after status: complete if missing (within version block)."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    if re.search(r"^\s+completed_date:", block, re.MULTILINE):
        return text
    new_block = re.sub(
        r"(^(\s+status:\s*complete)\s*\n)",
        rf'\1    completed_date: "{iso_date}"\n',
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if new_block == block:
        _die(
            f"could not insert completed_date into block {version_id!r} (expected status: complete)"
        )
    return text[:start] + new_block + text[end:]


def _extract_active_version(text: str) -> str:
    """Return the active_version value from roadmap.yaml text."""
    m = re.search(r"^active_version:\s*(\S+)", text, re.MULTILINE)
    if not m:
        _die("could not find 'active_version:' field in roadmap.yaml")
    return m.group(1)


def _set_active_version(text: str, new_version: str) -> str:
    """Replace the top-level active_version: line."""
    return re.sub(
        r"^(active_version:\s*).*$",
        rf"\g<1>{new_version}",
        text,
        flags=re.MULTILINE,
    )


# ── Block-boundary helpers ────────────────────────────────────────────────────


def _find_block(text: str, version_id: str) -> tuple[int, int]:
    """Return (start, end) byte offsets of the version block for *version_id*.

    The block begins at the '  - id: {version_id}' line and ends just before
    the next '  - id:' line (or end-of-string).
    """
    # Match the exact block start: two-space indent + "- id: " + version_id
    start_pattern = re.compile(
        r"^(  - id: " + re.escape(version_id) + r"\n)",
        re.MULTILINE,
    )
    m = start_pattern.search(text)
    if not m:
        _die(f"could not find version block '  - id: {version_id}' in roadmap.yaml")
    block_start = m.start()

    # Find the next "  - id:" after this point
    next_block = re.search(r"^  - id:", text[m.end() :], re.MULTILINE)
    if next_block:
        block_end = m.end() + next_block.start()
    else:
        block_end = len(text)

    return block_start, block_end


def _replace_in_block(
    text: str,
    version_id: str,
    pattern: str,
    replacement: str,
    *,
    count: int = 1,
) -> str:
    """Apply a regex substitution only within the named version block."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    new_block = re.sub(pattern, replacement, block, count=count, flags=re.MULTILINE)
    return text[:start] + new_block + text[end:]


def _get_pending_task_refs(text: str, version_id: str) -> list[str]:
    """Return the pending_task_refs list for the named version block."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    m = re.search(r"^\s+pending_task_refs:\s*(.*)", block, re.MULTILINE)
    if not m:
        return []
    raw = m.group(1).strip()
    if raw in ("[]", ""):
        return []
    # Parse inline list: [BL-009, P3-004] or ["BL-009"]
    inner = raw.strip("[]")
    refs = [r.strip().strip('"').strip("'") for r in inner.split(",") if r.strip()]
    return refs


def _get_current_patch_from_block(text: str, version_id: str) -> int:
    """Return the current_patch integer for the named version block."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    m = re.search(r"^\s+current_patch:\s*(\d+)", block, re.MULTILINE)
    if not m:
        _die(f"could not find 'current_patch:' in block '{version_id}' of roadmap.yaml")
    return int(m.group(1))


# ── Error helper ──────────────────────────────────────────────────────────────


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


# ── Bump operations ───────────────────────────────────────────────────────────


def do_patch(azoth_path: Path, roadmap_path: Path) -> None:
    """Increment patch: 0.0.N.M → 0.0.N.M+1, or post-1.0 0.1.M → 0.1.M+1; roadmap current_patch +1."""
    azoth_text = _read(azoth_path)
    roadmap_text = _read(roadmap_path)

    raw_version = _extract_azoth_version(azoth_text)
    parts, is_four = _parse_version_patchable(raw_version)
    if is_four:
        new_version = f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3] + 1}"
    else:
        new_version = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"

    active_version = _extract_active_version(roadmap_text)

    current_patch = _get_current_patch_from_block(roadmap_text, active_version)
    new_patch = current_patch + 1
    new_roadmap = _replace_in_block(
        roadmap_text,
        active_version,
        r"^(\s+current_patch:\s*)\d+",
        rf"\g<1>{new_patch}",
    )

    _write(azoth_path, _set_azoth_version(azoth_text, new_version))
    _write(roadmap_path, new_roadmap)

    print(f"version bumped {raw_version} → {new_version}")


def do_phase(azoth_path: Path, roadmap_path: Path) -> None:
    """Advance to next phase: 0.0.N.M → 0.0.N+1.1."""
    azoth_text = _read(azoth_path)
    roadmap_text = _read(roadmap_path)

    raw_version = _extract_azoth_version(azoth_text)
    a, b, c, d = _parse_version(raw_version)

    active_version = _extract_active_version(roadmap_text)

    # Guard: v0.0.7 is the last 0.0.x slice — use --release for 0.1.0
    if active_version == "v0.0.7":
        _die("--phase refused: active_version is v0.0.7; use --release to advance to v0.1.0")

    # Guard: pending_task_refs must be empty
    pending = _get_pending_task_refs(roadmap_text, active_version)
    if pending:
        refs_str = ", ".join(pending)
        _die(f"--phase refused: pending_task_refs is non-empty for {active_version}: {refs_str}")

    # Compute next version identifiers
    new_phase_num = c + 1
    next_active_id = f"v0.0.{new_phase_num}"
    new_azoth_version = f"{a}.{b}.{new_phase_num}.1"

    # Mutations on roadmap_text — applied in sequence

    # 1. In old active block: rename current_patch → final_patch
    roadmap_text = _replace_in_block(
        roadmap_text,
        active_version,
        r"^(\s+)current_patch:(\s*\d+)",
        r"\g<1>final_patch:\g<2>",
    )

    # 2. In old active block: status active → complete
    roadmap_text = _replace_in_block(
        roadmap_text,
        active_version,
        r"^(\s+status:\s*)active",
        r"\g<1>complete",
    )

    # 3. Top-level active_version → next
    roadmap_text = _set_active_version(roadmap_text, next_active_id)

    # 4. Activate new version block: planned|backlog → active + current_patch: 1
    start, end = _find_block(roadmap_text, next_active_id)
    block = roadmap_text[start:end]
    new_block = re.sub(
        r"^(    status: (?:planned|backlog)\n)",
        "    status: active\n    current_patch: 1\n",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if new_block == block:
        _die(
            f"--phase refused: could not activate version block {next_active_id!r}: "
            "expected leading '    status: planned' or '    status: backlog'"
        )
    roadmap_text = roadmap_text[:start] + new_block + roadmap_text[end:]

    # Write both files
    _write(azoth_path, _set_azoth_version(azoth_text, new_azoth_version))
    _write(roadmap_path, roadmap_text)

    print(f"version bumped {raw_version} → {new_azoth_version} (phase advance)")


def do_release(azoth_path: Path, roadmap_path: Path) -> None:
    """Close v0.0.7 + v0.1.0, set azoth 0.1.0 / phase 8, activate v0.2.0 slice (roadmap TBD).

    Human-gated: prints the manual git-tag command; verify, tag, and push locally.
    """
    azoth_text = _read(azoth_path)
    roadmap_text = _read(roadmap_path)

    raw_version = _extract_azoth_version(azoth_text)
    active_version = _extract_active_version(roadmap_text)

    if active_version != "v0.0.7":
        _die(f"--release refused: active_version is {active_version}; must be v0.0.7")

    completed = date.today().isoformat()

    # v0.0.7: current_patch → final_patch, active → complete, completed_date
    roadmap_text = _replace_in_block(
        roadmap_text,
        "v0.0.7",
        r"^(\s+)current_patch:",
        r"\g<1>final_patch:",
    )
    roadmap_text = _replace_in_block(
        roadmap_text,
        "v0.0.7",
        r"^(\s+status:\s*)active",
        r"\g<1>complete",
    )
    roadmap_text = _ensure_completed_date_in_block(roadmap_text, "v0.0.7", completed)

    # v0.1.0: target → complete
    roadmap_text = _replace_in_block(
        roadmap_text,
        "v0.1.0",
        r"^(\s+status:\s*)target",
        r"\g<1>complete",
    )
    roadmap_text = _ensure_completed_date_in_block(roadmap_text, "v0.1.0", completed)

    # Legacy roadmap header: phase 8 placeholder until next roadmap is defined
    roadmap_text = re.sub(
        r"^current_phase:\s*\d+\s*$",
        "current_phase: 8",
        roadmap_text,
        count=1,
        flags=re.MULTILINE,
    )
    roadmap_text = re.sub(
        r'^current_phase_title:\s*".*"\s*$',
        'current_phase_title: "Next — roadmap TBD"',
        roadmap_text,
        count=1,
        flags=re.MULTILINE,
    )

    # Activate v0.2.0 (backlog → active + current_patch 1)
    roadmap_text = _set_active_version(roadmap_text, "v0.2.0")
    start, end = _find_block(roadmap_text, "v0.2.0")
    block = roadmap_text[start:end]
    new_block = re.sub(
        r"^(    status: (?:planned|backlog)\n)",
        "    status: active\n    current_patch: 1\n",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if new_block == block:
        _die(
            "--release refused: v0.2.0 block must start with '    status: backlog' or "
            "'    status: planned' to activate the post-1.0 slice"
        )
    roadmap_text = roadmap_text[:start] + new_block + roadmap_text[end:]

    azoth_text = _set_azoth_version(azoth_text, "0.1.0")
    azoth_text = _set_azoth_phase_line(
        azoth_text,
        8,
        "Phases 1–7 + v0.1.0 release complete; next roadmap slice v0.2.0 (TBD)",
    )

    _write(azoth_path, azoth_text)
    _write(roadmap_path, roadmap_text)

    print(f"version bumped {raw_version} → 0.1.0 (release)")
    print(
        'Next step (human): git tag -a v0.1.0 -m "Azoth v0.1.0 public release" '
        "&& git push origin v0.1.0"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Azoth D53 version bump automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--patch", action="store_true", help="Increment 4th version component")
    group.add_argument("--phase", action="store_true", help="Advance to next phase")
    group.add_argument("--release", action="store_true", help="Write 0.1.0 (requires v0.0.7)")

    parser.add_argument(
        "--azoth-yaml",
        type=Path,
        default=ROOT / "azoth.yaml",
        help="Path to azoth.yaml (default: repo root)",
    )
    parser.add_argument(
        "--roadmap-yaml",
        type=Path,
        default=ROOT / ".azoth" / "roadmap.yaml",
        help="Path to roadmap.yaml (default: .azoth/roadmap.yaml)",
    )

    args = parser.parse_args()

    if args.patch:
        do_patch(args.azoth_yaml, args.roadmap_yaml)
    elif args.phase:
        do_phase(args.azoth_yaml, args.roadmap_yaml)
    elif args.release:
        do_release(args.azoth_yaml, args.roadmap_yaml)


if __name__ == "__main__":
    main()
