#!/usr/bin/env python3
"""
version-bump.py — D53/D55 version bump automation.

Maintains Azoth's delivery version across azoth.yaml and .azoth/roadmap.yaml
using regex-based line replacement throughout. YAML comments and formatting are
fully preserved.

Version eras:
  - Pre-release roadmap phases: 0.0.PHASE.PATCH
  - Pre-1.0 milestone working slices (for example v0.3.0-p1):
    0.(TARGET_MINOR-1).MILESTONE_PHASE.PATCH

Usage:
  python scripts/version-bump.py --patch   [--azoth-yaml PATH] [--roadmap-yaml PATH]
  python scripts/version-bump.py --phase   [--azoth-yaml PATH] [--roadmap-yaml PATH]
  python scripts/version-bump.py --release [--azoth-yaml PATH] [--roadmap-yaml PATH]

Flags:
  --patch    A.B.P.M → A.B.P.M+1  (every session delivery)
  --phase    0.0.N.M → 0.0.N+1.1  or  A.B.P.M → A.B.P+1.0
              (phase completion — empty pending_task_refs; next slice status planned
              or backlog → active + current_patch reset)
  --release  legacy v0.1.0 gate: v0.0.7 active → close v0.0.7 + v0.1.0, tag
              v0.1.0, then move the repo onto milestone phase 1 as azoth 0.1.1.0
              with active roadmap slice v0.2.0-p1

--release is human-gated: updates azoth.yaml + .azoth/roadmap.yaml, prints the
manual git-tag command. The human must inspect, run tests, tag, and push.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

_VERSION4_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$")
_MILESTONE_RE = re.compile(
    r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
)
_ACTIVE_WORKING_SLICE_RE = re.compile(
    r"^(?P<milestone>v\d+\.\d+\.\d+)-p(?P<phase>\d+)$"
)
_TASK_ID_POLICY_BLOCK = (
    "task_id_policy:\n"
    "  legacy_milestones:\n"
    "    - milestone: v0.2.0\n"
    "      prefix: P1\n"
    "      width: 3\n"
    "      frozen: true\n"
    "  future_default:\n"
    "    prefix: T\n"
    "    width: 3\n"
)

# ── File I/O helpers ──────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _settings_path_for(azoth_path: Path) -> Path:
    """Return the settings path paired with the selected azoth.yaml root."""
    return azoth_path.resolve().parent / ".claude" / "settings.json"


def _sync_settings_version(new_version: str, *, settings_path: Path) -> None:
    """Update AZOTH_VERSION in the paired .claude/settings.json if it exists."""
    if not settings_path.is_file():
        return
    text = settings_path.read_text(encoding="utf-8")
    updated = re.sub(
        r'"AZOTH_VERSION":\s*"[^"]*"',
        f'"AZOTH_VERSION": "{new_version}"',
        text,
    )
    if updated != text:
        settings_path.write_text(updated, encoding="utf-8")


def _sync_settings_phase(new_phase: int, *, settings_path: Path) -> None:
    """Update AZOTH_PHASE in the paired .claude/settings.json if it exists."""
    if not settings_path.is_file():
        return
    text = settings_path.read_text(encoding="utf-8")
    updated = re.sub(
        r'"AZOTH_PHASE":\s*"[^"]*"',
        f'"AZOTH_PHASE": "{new_phase}"',
        text,
    )
    if updated != text:
        settings_path.write_text(updated, encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ── Version parsing ───────────────────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, int, int, int]:
    """Parse a 4-component version string or exit 1."""
    m = _VERSION4_RE.match(v.strip())
    if not m:
        _die(f"version '{v}' does not match required format \\d+.\\d+.\\d+.\\d+")
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def _extract_working_slice(active_version: str) -> tuple[str, int] | None:
    """Return ``(milestone, phase)`` for any ``vX.Y.Z-pN`` working slice."""
    match = _ACTIVE_WORKING_SLICE_RE.match(active_version.strip())
    if not match:
        return None
    phase = int(match.group("phase"))
    if phase < 1:
        return None
    return match.group("milestone"), phase


def _expected_delivery_line(milestone: str) -> tuple[int, int]:
    """Return the private workshop delivery line for a pre-1.0 target milestone.

    D55 preserves D53's separation between public targets and the four-part
    workshop time series: work toward ``v0.N.0`` is recorded on
    ``0.(N-1).PHASE.PATCH``.
    """
    match = _MILESTONE_RE.match(milestone.strip())
    if not match:
        _die(f"milestone '{milestone}' does not match required format vMAJOR.MINOR.PATCH")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    if major != 0 or minor < 2 or patch != 0:
        _die(
            f"milestone '{milestone}' is outside the supported pre-1.0 v0.N.0 "
            "working-slice convention"
        )
    return major, minor - 1


# ── Regex helpers ─────────────────────────────────────────────────────────────


def _extract_azoth_version(text: str) -> str:
    """Return the version value string from azoth.yaml text."""
    m = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
    if not m:
        _die("could not find 'version:' field in azoth.yaml")
    return m.group(1)


def _extract_azoth_milestone(text: str) -> str:
    """Return the target milestone from azoth.yaml text."""
    match = re.search(r"^milestone:\s*(\S+)", text, re.MULTILINE)
    if not match:
        _die("could not find 'milestone:' field in azoth.yaml for active working slice")
    return match.group(1)


def _validate_working_slice_version(
    azoth_text: str,
    raw_version: str,
    active_version: str,
) -> tuple[str, int] | None:
    """Validate manifest, delivery line, phase, and roadmap slice as one contract."""
    working_slice = _extract_working_slice(active_version)
    if working_slice is None:
        return None

    roadmap_milestone, active_phase = working_slice
    manifest_milestone = _extract_azoth_milestone(azoth_text)
    if manifest_milestone != roadmap_milestone:
        _die(
            f"azoth.yaml milestone '{manifest_milestone}' does not match active_version "
            f"milestone '{roadmap_milestone}'"
        )

    expected_major, expected_minor = _expected_delivery_line(roadmap_milestone)
    major, minor, phase, _patch = _parse_version(raw_version)
    if (major, minor, phase) != (expected_major, expected_minor, active_phase):
        _die(
            f"version '{raw_version}' must use delivery line "
            f"{expected_major}.{expected_minor}.{active_phase}.N while active_version is "
            f"{active_version}"
        )
    return working_slice


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


def _set_roadmap_current_phase(text: str, new_phase: int) -> str:
    """Replace the top-level current_phase line in roadmap.yaml."""
    return re.sub(
        r"^(current_phase:\s*)\d+",
        rf"\g<1>{new_phase}",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def _set_roadmap_current_phase_title(text: str, milestone: str, new_phase: int) -> str:
    """Update current_phase_title while preserving existing wording when possible."""
    if re.search(r"\(milestone phase \d+\)", text):
        return re.sub(
            r"\(milestone phase \d+\)",
            f"(milestone phase {new_phase})",
            text,
            count=1,
        )
    return re.sub(
        r'^current_phase_title:\s*".*"\s*$',
        f'current_phase_title: "{milestone} — milestone phase {new_phase}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )


def _ensure_azoth_milestone_post_release(text: str) -> str:
    """After --release, ensure milestone v0.2.0 + lifecycle_phase for welcome strip (D48)."""
    if not re.search(r"^milestone:", text, re.MULTILINE):
        text = re.sub(
            r"^(phase:\s*\d+[^\n]*\n)",
            r"\1milestone: v0.2.0\n",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = re.sub(
            r"^milestone:\s*\S+.*$",
            "milestone: v0.2.0",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if not re.search(r"^lifecycle_phase:", text, re.MULTILINE):
        text = re.sub(
            r"^(milestone:.*\n)",
            r"\1lifecycle_phase: 8\n",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = re.sub(
            r"^lifecycle_phase:\s*\d+.*$",
            "lifecycle_phase: 8",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def _ensure_task_id_policy(text: str) -> str:
    """Ensure roadmap.yaml includes the machine-readable task-id namespace policy."""
    if re.search(r"^task_id_policy:\s*$", text, re.MULTILINE):
        return text
    return re.sub(
        r"^(active_version:\s*.*\n)",
        lambda m: m.group(1) + "\n" + _TASK_ID_POLICY_BLOCK,
        text,
        count=1,
        flags=re.MULTILINE,
    )


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

    The block begins at the version's ``- id:`` line and ends just before the
    next peer version block with the same indent (or end-of-string).
    """
    # Match the exact block start and preserve whatever indent the roadmap uses
    # for top-level version entries (some files use two spaces; others use none).
    start_pattern = re.compile(
        r"^(?P<indent>[ \t]*)- id: " + re.escape(version_id) + r"\n",
        re.MULTILINE,
    )
    m = start_pattern.search(text)
    if not m:
        _die(f"could not find version block '- id: {version_id}' in roadmap.yaml")
    block_start = m.start()
    block_indent = re.escape(m.group("indent"))

    # Find the next peer "- id:" after this point. Matching the captured indent
    # avoids confusing nested task entries with version blocks.
    next_block = re.search(rf"^{block_indent}- id:", text[m.end() :], re.MULTILINE)
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
    """Return the current_patch integer for the named active version block."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    m = re.search(r"^\s+current_patch:\s*(\d+)", block, re.MULTILINE)
    if not m:
        _die(f"could not find 'current_patch:' in block '{version_id}' of roadmap.yaml")
    return int(m.group(1))


def _get_patch_cursor_from_block(text: str, version_id: str) -> tuple[int, bool]:
    """Return the patch cursor and whether the named roadmap block is already closed."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    current = re.search(r"^\s+current_patch:\s*(\d+)", block, re.MULTILINE)
    if current:
        return int(current.group(1)), False
    status = re.search(r"^\s+status:\s*(\S+)", block, re.MULTILINE)
    final = re.search(r"^\s+final_patch:\s*(\d+)", block, re.MULTILINE)
    if (
        final
        and status
        and status.group(1).strip().strip("\"'").casefold() in {"complete", "completed"}
    ):
        return int(final.group(1)), True
    _die(f"could not find 'current_patch:' in block '{version_id}' of roadmap.yaml")


def _load_roadmap_mapping(text: str) -> dict:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        _die(f"could not parse roadmap.yaml for phase guard: {exc}")
    if not isinstance(data, dict):
        _die("roadmap.yaml root must be a mapping")
    return data


def _roadmap_version_entry(data: dict, version_id: str) -> dict:
    versions = data.get("versions")
    if not isinstance(versions, list):
        _die("roadmap.yaml must contain versions: []")
    for version in versions:
        if isinstance(version, dict) and str(version.get("id") or "") == version_id:
            return version
    _die(f"roadmap.yaml missing active version block {version_id!r}")


def _active_version_open_tasks(data: dict, version_id: str) -> list[str]:
    version = _roadmap_version_entry(data, version_id)
    tasks = version.get("tasks")
    if not isinstance(tasks, list):
        return []
    ids: list[str] = []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("id") or "").strip()
        if task_id:
            ids.append(task_id)
    return ids


def _slice_is_live(slice_item: dict) -> bool:
    status = str(slice_item.get("status") or "").strip().casefold()
    role = str(slice_item.get("role") or "").strip().casefold()
    return status not in {"complete", "completed"} and role != "historical"


def _scheduled_live_initiatives(data: dict, version_id: str) -> list[str]:
    live: list[str] = []
    initiatives = data.get("initiatives")
    if not isinstance(initiatives, list):
        return live
    for initiative in initiatives:
        if not isinstance(initiative, dict):
            continue
        if str(initiative.get("phase") or "").strip() != version_id:
            continue
        initiative_id = str(initiative.get("id") or "").strip() or "?"
        slices = initiative.get("slices")
        if isinstance(slices, list) and slices:
            if any(isinstance(item, dict) and _slice_is_live(item) for item in slices):
                live.append(initiative_id)
            continue
        alias = str(initiative.get("task_ref") or "").strip()
        status = str(initiative.get("status") or "").strip().casefold()
        if alias or status not in {"complete", "completed"}:
            live.append(initiative_id)
    return live


def _activate_version_block(
    text: str,
    version_id: str,
    *,
    current_patch: int,
) -> str:
    """Activate a roadmap version block and set its current_patch."""
    start, end = _find_block(text, version_id)
    block = text[start:end]
    new_block = re.sub(
        r"^(    status: (?:planned|backlog|target)\n)",
        f"    status: active\n    current_patch: {current_patch}\n",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if new_block == block:
        _die(
            f"could not activate version block {version_id!r}: expected leading "
            "'    status: planned', '    status: backlog', or '    status: target'"
        )
    return text[:start] + new_block + text[end:]


# ── Error helper ──────────────────────────────────────────────────────────────


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


# ── Bump operations ───────────────────────────────────────────────────────────


def do_patch(azoth_path: Path, roadmap_path: Path) -> None:
    """Increment patch for the active delivery line and mirror roadmap current_patch."""
    azoth_text = _read(azoth_path)
    roadmap_text = _read(roadmap_path)

    raw_version = _extract_azoth_version(azoth_text)
    active_version = _extract_active_version(roadmap_text)
    _validate_working_slice_version(
        azoth_text,
        raw_version,
        active_version,
    )
    major, minor, phase, patch = _parse_version(raw_version)
    new_version = f"{major}.{minor}.{phase}.{patch + 1}"

    current_patch, closed_version = _get_patch_cursor_from_block(roadmap_text, active_version)
    if patch != current_patch:
        cursor_name = "final_patch" if closed_version else "current_patch"
        _die(
            f"version '{raw_version}' patch component does not match roadmap "
            f"{cursor_name} {current_patch} for {active_version}"
        )
    if closed_version:
        print(
            f"version {raw_version} already at closed roadmap final_patch "
            f"{current_patch} for {active_version}; no patch bump"
        )
        return

    new_patch = current_patch + 1
    new_roadmap = _replace_in_block(
        roadmap_text,
        active_version,
        r"^(\s+current_patch:\s*)\d+",
        rf"\g<1>{new_patch}",
    )

    _write(azoth_path, _set_azoth_version(azoth_text, new_version))
    _write(roadmap_path, new_roadmap)

    settings_path = _settings_path_for(azoth_path)
    _sync_settings_version(new_version, settings_path=settings_path)
    print(f"version bumped {raw_version} → {new_version}")


def do_phase(azoth_path: Path, roadmap_path: Path) -> None:
    """Advance to the next phase in either the pre-release or post-release era."""
    azoth_text = _read(azoth_path)
    roadmap_text = _read(roadmap_path)

    raw_version = _extract_azoth_version(azoth_text)
    a, b, c, d = _parse_version(raw_version)

    active_version = _extract_active_version(roadmap_text)
    active_working_slice = _validate_working_slice_version(
        azoth_text,
        raw_version,
        active_version,
    )
    active_post_release_phase = active_working_slice[1] if active_working_slice else None

    # Guard: v0.0.7 is the last 0.0.x slice — use --release for 0.1.0
    if active_version == "v0.0.7":
        _die("--phase refused: active_version is v0.0.7; use --release to advance to v0.1.0")

    roadmap_data = _load_roadmap_mapping(roadmap_text)

    # Guard: versions[].tasks is the canonical open-work list for phase advancement.
    open_tasks = _active_version_open_tasks(roadmap_data, active_version)
    if open_tasks:
        refs_str = ", ".join(open_tasks)
        _die(
            f"--phase refused: active version {active_version} still has open "
            f"tasks in versions[].tasks: {refs_str}"
        )

    live_initiatives = _scheduled_live_initiatives(roadmap_data, active_version)
    if live_initiatives:
        refs_str = ", ".join(live_initiatives)
        _die(
            f"--phase refused: active version {active_version} still has scheduled "
            f"live initiative(s): {refs_str}"
        )

    if active_post_release_phase is not None:
        milestone = active_working_slice[0]
        new_phase_num = active_post_release_phase + 1
        next_active_id = f"{milestone}-p{new_phase_num}"
        new_azoth_version = f"{a}.{b}.{new_phase_num}.0"
        next_current_patch = 0
    else:
        new_phase_num = c + 1
        next_active_id = f"v0.0.{new_phase_num}"
        new_azoth_version = f"{a}.{b}.{new_phase_num}.1"
        next_current_patch = 1

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

    # 4. Activate new version block.
    roadmap_text = _activate_version_block(
        roadmap_text,
        next_active_id,
        current_patch=next_current_patch,
    )

    if active_post_release_phase is not None:
        roadmap_text = _set_roadmap_current_phase(roadmap_text, new_phase_num)
        roadmap_text = _set_roadmap_current_phase_title(
            roadmap_text,
            milestone,
            new_phase_num,
        )
        azoth_text = _set_azoth_phase_line(azoth_text, new_phase_num)
        roadmap_text = _ensure_task_id_policy(roadmap_text)

    # Write both files
    _write(azoth_path, _set_azoth_version(azoth_text, new_azoth_version))
    _write(roadmap_path, roadmap_text)

    settings_path = _settings_path_for(azoth_path)
    _sync_settings_version(new_azoth_version, settings_path=settings_path)
    if active_post_release_phase is not None:
        _sync_settings_phase(new_phase_num, settings_path=settings_path)
    print(f"version bumped {raw_version} → {new_azoth_version} (phase advance)")


def do_release(azoth_path: Path, roadmap_path: Path) -> None:
    """Close v0.0.7 + v0.1.0, then start milestone phase 1 as azoth 0.1.1.0 on v0.2.0-p1.

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

    # Roadmap header: milestone-local phase 1 for v0.2.0 + lifecycle strip marker
    roadmap_text = _set_roadmap_current_phase(roadmap_text, 1)
    roadmap_text = re.sub(
        r'^current_phase_title:\s*".*"\s*$',
        'current_phase_title: "v0.2.0 — milestone phase 1"',
        roadmap_text,
        count=1,
        flags=re.MULTILINE,
    )
    if re.search(r"^lifecycle_phase:", roadmap_text, re.MULTILINE):
        roadmap_text = re.sub(
            r"^lifecycle_phase:\s*\d+\s*$",
            "lifecycle_phase: 8",
            roadmap_text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        roadmap_text = re.sub(
            r'(^current_phase_title:\s*".*"\s*\n)',
            r"\1lifecycle_phase: 8\n",
            roadmap_text,
            count=1,
            flags=re.MULTILINE,
        )

    # Mark the milestone container as the target release and activate the phase-1 working slice.
    roadmap_text = _replace_in_block(
        roadmap_text,
        "v0.2.0",
        r"^(\s+status:\s*)(?:planned|backlog|active)",
        r"\g<1>target",
    )
    roadmap_text = _set_active_version(roadmap_text, "v0.2.0-p1")
    roadmap_text = _activate_version_block(roadmap_text, "v0.2.0-p1", current_patch=0)
    roadmap_text = _ensure_task_id_policy(roadmap_text)

    azoth_text = _set_azoth_version(azoth_text, "0.1.1.0")
    azoth_text = _set_azoth_phase_line(
        azoth_text,
        1,
        "Milestone v0.2.0 — local phase 1; version uses 0.1.<phase>.<patch>",
    )
    azoth_text = _ensure_azoth_milestone_post_release(azoth_text)

    _write(azoth_path, azoth_text)
    _write(roadmap_path, roadmap_text)

    settings_path = _settings_path_for(azoth_path)
    _sync_settings_version("0.1.1.0", settings_path=settings_path)
    _sync_settings_phase(1, settings_path=settings_path)
    print(f"version bumped {raw_version} → 0.1.1.0 (release)")
    print(
        'Next step (human): git tag -a v0.1.0 -m "Azoth v0.1.0 public release" '
        "&& git push origin v0.1.0"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Azoth D53/D55 version bump automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--patch", action="store_true", help="Increment the delivery patch")
    group.add_argument("--phase", action="store_true", help="Advance to the next development phase")
    group.add_argument(
        "--release",
        action="store_true",
        help="Complete the legacy v0.1.0 gate and open 0.1.1.0 / v0.2.0-p1",
    )

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
