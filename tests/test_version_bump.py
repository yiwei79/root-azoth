"""
Tests for scripts/version-bump.py — D53 version bump automation.

These tests are written BEFORE the script exists; they must fail until
the script is implemented.

Coverage:
- --patch: increments 4th component in azoth.yaml and roadmap current_patch
- --phase: resets patch, writes final_patch, advances active_version
- --release: closes v0.0.7/v0.1.0, activates v0.2.0-p1, azoth 0.1.1.0 + milestone phase 1 + lifecycle 8
- --patch: post-1.0 uses 0.1.<phase>.<patch>
- Guard rails: wrong version format, non-empty pending_task_refs, wrong phase
- Comment preservation in both YAML files
- Command reference presence in .claude/commands/ files
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "version-bump.py"
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_env(
    base: Path,
    *,
    azoth_version: str = "0.0.3.5",
    active_version: str = "v0.0.3",
    current_patch: int = 5,
    pending_task_refs: list[str] | None = None,
) -> tuple[Path, Path]:
    """Write minimal azoth.yaml and roadmap.yaml fixtures into *base* and return
    their paths as (azoth_p, roadmap_p)."""
    base.mkdir(parents=True, exist_ok=True)

    # Build pending_task_refs string for YAML literal
    if not pending_task_refs:
        pending_task_refs_str = "[]"
    else:
        items = ", ".join(pending_task_refs)
        pending_task_refs_str = f"[{items}]"

    azoth_content = textwrap.dedent(f"""\
        # comment preserved
        version: {azoth_version}
        description: Test
    """)

    roadmap_content = textwrap.dedent(f"""\
        # D53 bump rules comment
        active_version: {active_version}

        versions:
          - id: v0.0.3
            status: active
            current_patch: {current_patch}
            goal: "Phase 3"
            pending_task_refs: {pending_task_refs_str}

          - id: v0.0.4
            status: planned
            goal: "Phase 4"

          - id: v0.0.5
            status: planned
            goal: "Phase 5"

          - id: v0.0.6
            status: planned
            goal: "Phase 6"

          - id: v0.0.7
            status: planned
            goal: "Phase 7"

          - id: v0.1.0
            status: target
            goal: "Public release"
    """)

    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"

    azoth_p.write_text(azoth_content)
    roadmap_p.write_text(roadmap_content)

    return azoth_p, roadmap_p


def _run(flag: str, azoth_p: Path, roadmap_p: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "python3",
            str(SCRIPT),
            flag,
            "--azoth-yaml",
            str(azoth_p),
            "--roadmap-yaml",
            str(roadmap_p),
        ],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# T1 — --patch increments 4th version component in azoth.yaml
# ---------------------------------------------------------------------------


def test_patch_increments_azoth_version(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(tmp_path / "t1", azoth_version="0.0.3.5", current_patch=5)
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 0, result.stderr

    data = yaml.safe_load(azoth_p.read_text())
    assert data["version"] == "0.0.3.6", (
        f"Expected 0.0.3.6 after --patch on 0.0.3.5, got {data['version']!r}"
    )


# ---------------------------------------------------------------------------
# T2 — --patch updates current_patch in roadmap.yaml
# ---------------------------------------------------------------------------


def test_patch_updates_roadmap_current_patch(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(tmp_path / "t2", current_patch=5)
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 0, result.stderr

    data = yaml.safe_load(roadmap_p.read_text())
    v003 = next(v for v in data["versions"] if v["id"] == "v0.0.3")
    assert v003["current_patch"] == 6, (
        f"Expected current_patch=6 after --patch, got {v003['current_patch']!r}"
    )


# ---------------------------------------------------------------------------
# T3 — --patch prints "version bumped X → Y" to stdout
# ---------------------------------------------------------------------------


def test_patch_prints_bump_message(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(tmp_path / "t3", azoth_version="0.0.3.5", current_patch=5)
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 0, result.stderr

    combined = result.stdout + result.stderr
    assert "0.0.3.5" in combined and "0.0.3.6" in combined, (
        f"Expected 'version bumped 0.0.3.5 → 0.0.3.6' in output; got: {combined!r}"
    )
    assert "bumped" in combined.lower(), f"Expected word 'bumped' in output; got: {combined!r}"


# ---------------------------------------------------------------------------
# T4 — --phase resets patch, writes final_patch, advances active_version;
#       azoth.yaml version becomes 0.0.4.1
# ---------------------------------------------------------------------------


def test_phase_advances_version(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(
        tmp_path / "t4",
        azoth_version="0.0.3.5",
        active_version="v0.0.3",
        current_patch=5,
        pending_task_refs=[],
    )
    result = _run("--phase", azoth_p, roadmap_p)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    # azoth.yaml version becomes 0.0.4.1
    azoth_data = yaml.safe_load(azoth_p.read_text())
    assert azoth_data["version"] == "0.0.4.1", (
        f"Expected azoth version 0.0.4.1 after --phase, got {azoth_data['version']!r}"
    )

    roadmap_data = yaml.safe_load(roadmap_p.read_text())

    # active_version advances to v0.0.4
    assert roadmap_data["active_version"] == "v0.0.4", (
        f"Expected active_version v0.0.4, got {roadmap_data['active_version']!r}"
    )

    # v0.0.3 block has final_patch written
    v003 = next(v for v in roadmap_data["versions"] if v["id"] == "v0.0.3")
    assert "final_patch" in v003, "Expected final_patch written to v0.0.3 block"
    assert v003["final_patch"] == 5, (
        f"Expected final_patch=5 (last patch before phase advance), got {v003['final_patch']!r}"
    )

    # new active version (v0.0.4) should have current_patch == 1
    v004 = next(v for v in roadmap_data["versions"] if v["id"] == "v0.0.4")
    assert v004.get("current_patch") == 1, (
        f"Expected current_patch=1 on new active version v0.0.4, got {v004.get('current_patch')!r}"
    )


# ---------------------------------------------------------------------------
# T4b — --phase activates next slice when status was backlog
# ---------------------------------------------------------------------------


def test_phase_activates_backlog_version_block(tmp_path: Path) -> None:
    base = tmp_path / "t4b"
    base.mkdir(parents=True)
    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"
    azoth_p.write_text("version: 0.0.3.1\n", encoding="utf-8")
    roadmap_p.write_text(
        textwrap.dedent(
            """\
            active_version: v0.0.3

            versions:
              - id: v0.0.3
                status: active
                current_patch: 1
                goal: "Phase 3"
                pending_task_refs: []

              - id: v0.0.4
                status: backlog
                goal: "Phase 4"
            """
        ),
        encoding="utf-8",
    )
    result = _run("--phase", azoth_p, roadmap_p)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    roadmap_data = yaml.safe_load(roadmap_p.read_text())
    v004 = next(v for v in roadmap_data["versions"] if v["id"] == "v0.0.4")
    assert v004["status"] == "active", f"Expected status active, got {v004['status']!r}"
    assert v004.get("current_patch") == 1, (
        f"Expected current_patch=1 after backlog→active, got {v004.get('current_patch')!r}"
    )


# ---------------------------------------------------------------------------
# T5 — --phase exits 1 when pending_task_refs is non-empty; output contains "refused"
# ---------------------------------------------------------------------------


def test_phase_refused_when_pending_tasks(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(
        tmp_path / "t5",
        pending_task_refs=["BL-009", "P3-004"],
    )
    result = _run("--phase", azoth_p, roadmap_p)
    assert result.returncode == 1, (
        f"Expected exit 1 when pending_task_refs non-empty; got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert "refused" in combined.lower(), f"Expected 'refused' in output; got: {combined!r}"


# ---------------------------------------------------------------------------
# T6 — --phase exits 1 when active_version is v0.0.7; message contains "v0.0.7"
# ---------------------------------------------------------------------------


def test_phase_refused_at_v007(tmp_path: Path) -> None:
    base = tmp_path / "t6"
    base.mkdir(parents=True)
    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"
    azoth_p.write_text("version: 0.0.7.3\n", encoding="utf-8")
    roadmap_p.write_text(
        textwrap.dedent(
            """\
            active_version: v0.0.7

            versions:
              - id: v0.0.7
                status: active
                current_patch: 3
                goal: "Phase 7"
                pending_task_refs: []

              - id: v0.1.0
                status: target
                goal: "Public release"
            """
        ),
        encoding="utf-8",
    )
    result = _run("--phase", azoth_p, roadmap_p)
    assert result.returncode == 1, (
        f"Expected exit 1 when active_version is v0.0.7; got {result.returncode}"
    )
    combined = result.stdout + result.stderr
    assert "v0.0.7" in combined, f"Expected 'v0.0.7' in output; got: {combined!r}"


# ---------------------------------------------------------------------------
# T7 — --release writes version "0.1.1.0" to azoth.yaml when active_version is v0.0.7
# ---------------------------------------------------------------------------


def test_release_writes_phased_post_release_version(tmp_path: Path) -> None:
    base = tmp_path / "t7"
    base.mkdir(parents=True)
    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"
    azoth_p.write_text("version: 0.0.7.4\nphase: 7\n", encoding="utf-8")
    roadmap_p.write_text(
        textwrap.dedent(
            """\
            current_phase: 7
            current_phase_title: "Publishing"

            active_version: v0.0.7

            versions:
              - id: v0.0.7
                status: active
                current_patch: 4
                goal: "Phase 7"
                pending_task_refs: []

              - id: v0.1.0
                status: target
                goal: "Public release"

              - id: v0.2.0
                status: backlog
                goal: "Milestone target"
                phase_scope: []

              - id: v0.2.0-p1
                status: backlog
                goal: "Milestone phase 1"
                phase_scope: [1]
             """
        ),
        encoding="utf-8",
    )
    result = _run("--release", azoth_p, roadmap_p)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    data = yaml.safe_load(azoth_p.read_text())
    assert data["version"] == "0.1.1.0", (
        f"Expected version 0.1.1.0 after --release, got {data['version']!r}"
    )
    assert int(data["phase"]) == 1, f"Expected phase 1 after --release, got {data.get('phase')!r}"
    assert data.get("milestone") == "v0.2.0"
    assert int(data.get("lifecycle_phase", 0)) == 8

    rdata = yaml.safe_load(roadmap_p.read_text())
    assert rdata["active_version"] == "v0.2.0-p1"
    assert rdata["current_phase"] == 1
    assert int(rdata.get("lifecycle_phase", 0)) == 8
    v007 = next(x for x in rdata["versions"] if x["id"] == "v0.0.7")
    assert v007["status"] == "complete"
    assert v007.get("final_patch") == 4
    v010 = next(x for x in rdata["versions"] if x["id"] == "v0.1.0")
    assert v010["status"] == "complete"
    v020 = next(x for x in rdata["versions"] if x["id"] == "v0.2.0")
    assert v020["status"] == "target"
    v021 = next(x for x in rdata["versions"] if x["id"] == "v0.2.0-p1")
    assert v021["status"] == "active"
    assert v021.get("current_patch") == 0


# ---------------------------------------------------------------------------
# T8 — --release exits 1 unless active_version is v0.0.7 (test with v0.0.3)
# ---------------------------------------------------------------------------


def test_release_refused_unless_v007(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(
        tmp_path / "t8",
        azoth_version="0.0.3.5",
        active_version="v0.0.3",
        current_patch=5,
    )
    result = _run("--release", azoth_p, roadmap_p)
    assert result.returncode == 1, (
        f"Expected exit 1 when active_version is not v0.0.7; got {result.returncode}"
    )


# ---------------------------------------------------------------------------
# T9 — YAML comments survive a --patch bump
# ---------------------------------------------------------------------------


def test_patch_preserves_yaml_comments(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(tmp_path / "t9", azoth_version="0.0.3.5", current_patch=5)
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 0, result.stderr

    azoth_text = azoth_p.read_text()
    assert "# comment preserved" in azoth_text, (
        f"Expected '# comment preserved' to survive --patch in azoth.yaml; got:\n{azoth_text}"
    )

    roadmap_text = roadmap_p.read_text()
    assert "# D53 bump rules comment" in roadmap_text, (
        f"Expected '# D53 bump rules comment' to survive --patch in roadmap.yaml; got:\n{roadmap_text}"
    )


# ---------------------------------------------------------------------------
# T10 — Version with wrong format (fewer than 3 components) → exit 1
# ---------------------------------------------------------------------------


def test_patch_rejects_malformed_version(tmp_path: Path) -> None:
    azoth_p, roadmap_p = _make_env(
        tmp_path / "t10",
        azoth_version="1.2",  # two components — invalid
        current_patch=5,
    )
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 1, (
        f"Expected exit 1 for malformed version '1.2'; got {result.returncode}"
    )


# ---------------------------------------------------------------------------
# T10b — Post-release phased patch: 0.1.1.0 → 0.1.1.1 + roadmap current_patch
# ---------------------------------------------------------------------------


def test_patch_post_release_phased_version(tmp_path: Path) -> None:
    base = tmp_path / "t10b"
    base.mkdir(parents=True)
    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"
    azoth_p.write_text("version: 0.1.1.0\n", encoding="utf-8")
    roadmap_p.write_text(
        textwrap.dedent(
            """\
            active_version: v0.2.0-p1

            versions:
              - id: v0.2.0-p1
                status: active
                current_patch: 0
                goal: "Next"
            """
        ),
        encoding="utf-8",
    )
    result = _run("--patch", azoth_p, roadmap_p)
    assert result.returncode == 0, result.stderr
    assert yaml.safe_load(azoth_p.read_text())["version"] == "0.1.1.1"
    r = yaml.safe_load(roadmap_p.read_text())
    v = next(x for x in r["versions"] if x["id"] == "v0.2.0-p1")
    assert v["current_patch"] == 1


# ---------------------------------------------------------------------------
# T10c — Post-release phase bump: 0.1.1.4 → 0.1.2.0 and v0.2.0-p1 → v0.2.0-p2
# ---------------------------------------------------------------------------


def test_phase_advances_post_release_working_slice(tmp_path: Path) -> None:
    base = tmp_path / "t10c"
    base.mkdir(parents=True)
    azoth_p = base / "azoth.yaml"
    roadmap_p = base / "roadmap.yaml"
    azoth_p.write_text("version: 0.1.1.4\nphase: 1\nmilestone: v0.2.0\n", encoding="utf-8")
    roadmap_p.write_text(
        textwrap.dedent(
            """\
            current_phase: 1
            current_phase_title: "v0.2.0 — milestone phase 1"
            active_version: v0.2.0-p1

            versions:
              - id: v0.2.0
                status: target
                goal: "Milestone target"

              - id: v0.2.0-p1
                status: active
                current_patch: 4
                goal: "Milestone phase 1"
                pending_task_refs: []

              - id: v0.2.0-p2
                status: backlog
                goal: "Milestone phase 2"
            """
        ),
        encoding="utf-8",
    )

    result = _run("--phase", azoth_p, roadmap_p)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    azoth_data = yaml.safe_load(azoth_p.read_text())
    assert azoth_data["version"] == "0.1.2.0"
    assert int(azoth_data["phase"]) == 2

    roadmap_data = yaml.safe_load(roadmap_p.read_text())
    assert roadmap_data["active_version"] == "v0.2.0-p2"
    assert roadmap_data["current_phase"] == 2
    v021 = next(v for v in roadmap_data["versions"] if v["id"] == "v0.2.0-p1")
    assert v021["status"] == "complete"
    assert v021["final_patch"] == 4
    v022 = next(v for v in roadmap_data["versions"] if v["id"] == "v0.2.0-p2")
    assert v022["status"] == "active"
    assert v022["current_patch"] == 0


# ---------------------------------------------------------------------------
# T11 — session-closeout.md contains "version-bump.py --patch" and "W4"
# ---------------------------------------------------------------------------


def test_session_closeout_references_version_bump() -> None:
    closeout = COMMANDS_DIR / "session-closeout.md"
    assert closeout.exists(), f"Missing {closeout}"
    text = closeout.read_text()
    assert "version-bump.py --patch" in text, (
        "session-closeout.md must reference 'version-bump.py --patch'"
    )
    assert "W4" in text, "session-closeout.md must contain a W4 checkpoint for version bumping"


# ---------------------------------------------------------------------------
# T12 — deliver-full.md contains "version-bump.py --patch"
# ---------------------------------------------------------------------------


def test_deliver_full_references_version_bump() -> None:
    deliver_full = COMMANDS_DIR / "deliver-full.md"
    assert deliver_full.exists(), f"Missing {deliver_full}"
    text = deliver_full.read_text()
    assert "version-bump.py --patch" in text, (
        "deliver-full.md must reference 'version-bump.py --patch'"
    )


# ---------------------------------------------------------------------------
# T13 — deliver-full.md does NOT contain "--release"
# ---------------------------------------------------------------------------


def test_deliver_full_does_not_reference_release() -> None:
    deliver_full = COMMANDS_DIR / "deliver-full.md"
    assert deliver_full.exists(), f"Missing {deliver_full}"
    text = deliver_full.read_text()
    assert "--release" not in text, (
        "deliver-full.md must NOT reference '--release' (release is a human-gated manual step)"
    )
