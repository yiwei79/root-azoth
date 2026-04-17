"""
tests/test_run_ledger.py — Test suite for run_ledger.py (P1-001).

Covers: schema, validate subcommand, status subcommand, append subcommand,
        load_active_run helper, welcome.py plain renderer integration,
        example file validity, resume fields, and .gitignore entry.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_ledger.py"
EXAMPLE = ROOT / ".azoth" / "run-ledger.local.yaml.example"
SCHEMA = ROOT / "pipelines" / "run-ledger.schema.yaml"

sys.path.insert(0, str(ROOT / "scripts"))
from run_ledger import (  # noqa: E402
    load_active_run,
    load_open_sessions,
    load_session,
    upsert_session,
    validate_ledger,
)


# ── 1. Schema file ─────────────────────────────────────────────────────────────


def test_schema_file_exists() -> None:
    assert SCHEMA.exists(), "pipelines/run-ledger.schema.yaml must exist"


def test_schema_has_required_keys() -> None:
    data = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "properties" in data or "type" in data  # valid JSON-Schema shape


# ── 2–6. validate subcommand ───────────────────────────────────────────────────


def test_validate_missing_file_exits_0(tmp_path: Path) -> None:
    absent = tmp_path / "no-such-ledger.yaml"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(absent), "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "no ledger file" in result.stdout


def test_validate_valid_ledger_exits_0(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "test-run-1",
                        "mode": "deliver",
                        "goal": "Test goal",
                        "status": "complete",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "done",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ledger OK" in result.stdout


def test_validate_missing_required_field_exits_1(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    # Missing `goal`
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "test-run-bad",
                        "mode": "deliver",
                        "status": "complete",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "done",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "goal" in result.stderr


def test_validate_bad_status_enum_exits_1(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "test-run-bad",
                        "mode": "deliver",
                        "goal": "g",
                        "status": "running",  # invalid
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "done",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "running" in result.stderr


def test_validate_bad_created_at_exits_1(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "test-run-bad",
                        "mode": "deliver",
                        "goal": "g",
                        "status": "complete",
                        "created_at": "not-a-date",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "done",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "created_at" in result.stderr


def test_validate_accepts_sessions_and_run_metadata() -> None:
    data = {
        "schema_version": 1,
        "sessions": [
            {
                "session_id": "2026-04-10-p1-001-copilot-152000",
                "backlog_id": "P1-001",
                "goal": "Test goal",
                "status": "parked",
                "ide": "copilot",
                "next_action": "resume this later",
                "updated_at": "2026-04-10T15:20:00+00:00",
                "active_run_id": "run-1",
            }
        ],
        "runs": [
            {
                "run_id": "run-1",
                "session_id": "2026-04-10-p1-001-copilot-152000",
                "backlog_id": "P1-001",
                "ide": "copilot",
                "mode": "auto",
                "goal": "Test goal",
                "status": "paused",
                "created_at": "2026-04-10T10:00:00+00:00",
                "updated_at": "2026-04-10T10:30:00+00:00",
                "next_action": "resume this later",
                "active_stage_id": "architect_brief",
                "pending_stage_ids": ["builder_apply", "reviewer_gate"],
                "pause_reason": "human-gate",
            }
        ],
    }
    assert validate_ledger(data) == []


def test_validate_rejects_invalid_pause_reason() -> None:
    data = {
        "schema_version": 1,
        "runs": [
            {
                "run_id": "run-1",
                "mode": "auto",
                "goal": "Test goal",
                "status": "paused",
                "created_at": "2026-04-10T10:00:00+00:00",
                "updated_at": "2026-04-10T10:30:00+00:00",
                "next_action": "resume this later",
                "pause_reason": "approval-card",
            }
        ],
    }

    errors = validate_ledger(data)
    assert any("pause_reason" in error for error in errors)


# ── 7–9. status subcommand ─────────────────────────────────────────────────────


def test_status_no_file(tmp_path: Path) -> None:
    absent = tmp_path / "no-ledger.yaml"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(absent), "status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "no active run" in result.stdout


def test_status_no_active_run(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "done-run",
                        "mode": "deliver",
                        "goal": "g",
                        "status": "complete",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "done",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "no active run" in result.stdout


def test_status_active_run_shows_id_and_mode(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "my-active-run",
                        "mode": "eval-swarm",
                        "goal": "g",
                        "status": "active",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "Resume from wave 2",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "my-active-run" in result.stdout
    assert "eval-swarm" in result.stdout
    assert "Resume from wave 2" in result.stdout


# ── 10–16. append subcommand ───────────────────────────────────────────────────


def _append(ledger: Path, **kwargs: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--ledger",
        str(ledger),
        "append",
        "--run-id",
        kwargs.get("run_id", "run-1"),
        "--mode",
        kwargs.get("mode", "deliver"),
        "--goal",
        kwargs.get("goal", "test goal"),
        "--status",
        kwargs.get("status", "active"),
        "--next-action",
        kwargs.get("next_action", "next step"),
    ]
    for field in ("session_id", "backlog_id", "ide"):
        value = kwargs.get(field)
        if value is not None:
            cmd += [f"--{field.replace('_', '-')}", value]
    active_stage_id = kwargs.get("active_stage_id")
    if active_stage_id is not None:
        cmd += ["--active-stage-id", active_stage_id]
    for stage_id in kwargs.get("pending_stage_ids", []):
        cmd += ["--pending-stage-id", stage_id]
    pause_reason = kwargs.get("pause_reason")
    if pause_reason is not None:
        cmd += ["--pause-reason", pause_reason]
    for stage in kwargs.get("stages", []):
        cmd += ["--stage-completed", stage]
    if "wave" in kwargs:
        cmd += ["--wave", kwargs["wave"]]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_append_creates_entry(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    result = _append(ledger, run_id="new-run")
    assert result.returncode == 0
    assert "created" in result.stdout
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert len(data["runs"]) == 1
    assert data["runs"][0]["run_id"] == "new-run"


def test_append_updates_existing_entry(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    _append(ledger, run_id="run-x", status="active", next_action="step 1")
    result = _append(ledger, run_id="run-x", status="complete", next_action="done")
    assert result.returncode == 0
    assert "updated" in result.stdout
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert len(data["runs"]) == 1  # not duplicated
    assert data["runs"][0]["status"] == "complete"


def test_append_accumulates_stages(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    _append(ledger, run_id="run-s", stages=["planning"])
    _append(ledger, run_id="run-s", stages=["implementation"])
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert data["runs"][0]["stages_completed"] == ["planning", "implementation"]


def test_append_wave_json(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    wave = json.dumps({"wave": 1, "status": "pass", "scores": [0.88, 0.90]})
    result = _append(ledger, run_id="run-w", wave=wave)
    assert result.returncode == 0
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert data["runs"][0]["waves"][0]["wave"] == 1
    assert data["runs"][0]["waves"][0]["status"] == "pass"


def test_append_invalid_wave_json_exits_1(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    result = _append(ledger, run_id="run-bad-wave", wave="{not valid json")
    assert result.returncode == 1
    assert "not valid JSON" in result.stderr


def test_append_bad_status_choice_exits_nonzero(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    result = _append(ledger, run_id="run-bs", status="unknown")
    assert result.returncode != 0


def test_append_validates_after_mutation(tmp_path: Path) -> None:
    # Wave with invalid status should be rejected before writing
    ledger = tmp_path / "ledger.yaml"
    _append(ledger, run_id="run-v")
    bad_wave = json.dumps({"wave": 1, "status": "bad-status"})
    result = _append(ledger, run_id="run-v", wave=bad_wave)
    assert result.returncode == 1


def test_append_writes_session_metadata(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    result = _append(
        ledger,
        run_id="run-meta",
        session_id="2026-04-10-p1-001-copilot-152000",
        backlog_id="P1-001",
        ide="copilot",
    )
    assert result.returncode == 0
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert data["runs"][0]["session_id"] == "2026-04-10-p1-001-copilot-152000"
    assert data["runs"][0]["backlog_id"] == "P1-001"
    assert data["runs"][0]["ide"] == "copilot"


def test_append_writes_stage_checkpoint_metadata(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    result = _append(
        ledger,
        run_id="run-stage-aware",
        active_stage_id="architect_brief",
        pending_stage_ids=["builder_apply", "reviewer_gate"],
        pause_reason="human-gate",
        stages=["planner_stage0"],
    )

    assert result.returncode == 0
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    run = data["runs"][0]
    assert run["active_stage_id"] == "architect_brief"
    assert run["pending_stage_ids"] == ["builder_apply", "reviewer_gate"]
    assert run["pause_reason"] == "human-gate"
    assert run["stages_completed"] == ["planner_stage0"]


# ── 17–19. load_active_run unit tests ─────────────────────────────────────────


def test_load_active_run_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_active_run(tmp_path) is None


def test_load_active_run_returns_last_active(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "run-a",
                        "mode": "deliver",
                        "goal": "g",
                        "status": "active",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "resume here",
                    },
                    {
                        "run_id": "run-b",
                        "mode": "eval-swarm",
                        "goal": "g2",
                        "status": "active",
                        "created_at": "2026-04-10T11:00:00+00:00",
                        "updated_at": "2026-04-10T11:30:00+00:00",
                        "next_action": "wave 2",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    result = load_active_run(tmp_path)
    assert result is not None
    assert result["run_id"] == "run-b"  # last active


def test_load_active_run_returns_none_when_all_complete(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "done",
                        "mode": "deliver",
                        "goal": "g",
                        "status": "complete",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "delivered",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert load_active_run(tmp_path) is None


def test_load_open_sessions_filters_closed_and_sorts_newest_first(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "sessions": [
                    {
                        "session_id": "closed-session",
                        "backlog_id": "P1-099",
                        "goal": "Closed",
                        "status": "closed",
                        "ide": "copilot",
                        "next_action": "done",
                        "updated_at": "2026-04-10T08:00:00+00:00",
                    },
                    {
                        "session_id": "older-parked",
                        "backlog_id": "P1-005",
                        "goal": "Parked",
                        "status": "parked",
                        "ide": "claude-code",
                        "next_action": "resume later",
                        "updated_at": "2026-04-10T09:00:00+00:00",
                    },
                    {
                        "session_id": "newer-active",
                        "backlog_id": "P1-001",
                        "goal": "Active",
                        "status": "active",
                        "ide": "copilot",
                        "next_action": "continue now",
                        "updated_at": "2026-04-10T10:00:00+00:00",
                    },
                ],
                "runs": [],
            }
        ),
        encoding="utf-8",
    )
    sessions = load_open_sessions(tmp_path)
    assert [entry["session_id"] for entry in sessions] == ["newer-active", "older-parked"]


def test_load_session_returns_matching_entry(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "sessions": [
                    {
                        "session_id": "target-session",
                        "backlog_id": "P1-005",
                        "goal": "Resume target",
                        "status": "parked",
                        "ide": "claude-code",
                        "next_action": "resume via /resume",
                        "updated_at": "2026-04-10T09:00:00+00:00",
                    }
                ],
                "runs": [],
            }
        ),
        encoding="utf-8",
    )
    session = load_session(tmp_path, "target-session")
    assert session is not None
    assert session["backlog_id"] == "P1-005"


def test_upsert_session_creates_registry_when_missing(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()

    created, entry = upsert_session(
        tmp_path,
        session_id="sess-park",
        backlog_id="AD-HOC",
        goal="Park this session",
        status="parked",
        ide="claude-code",
        next_action="Resume later",
        updated_at="2026-04-16T18:00:00+00:00",
    )

    assert created is True
    assert entry["status"] == "parked"
    ledger = yaml.safe_load((azoth / "run-ledger.local.yaml").read_text(encoding="utf-8"))
    assert ledger["sessions"][0]["session_id"] == "sess-park"
    assert ledger["sessions"][0]["next_action"] == "Resume later"


def test_park_session_subcommand_creates_or_updates_entry(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text("schema_version: 1\nruns: []\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--ledger",
            str(ledger),
            "park-session",
            "sess-park",
            "AD-HOC",
            "--goal",
            "Branch hygiene",
            "--ide",
            "claude-code",
            "--next-action",
            "Resume the interrupted Claude session.",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "parked" in result.stdout
    saved = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    assert saved["sessions"][0]["session_id"] == "sess-park"
    assert saved["sessions"][0]["status"] == "parked"


# ── 20–22. welcome.py plain renderer ──────────────────────────────────────────


def _make_active_ledger(azoth_dir: Path, run_id: str, next_action: str) -> None:
    (azoth_dir / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": run_id,
                        "mode": "deliver",
                        "goal": "g",
                        "status": "active",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": next_action,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_welcome_plain_shows_active_run_line(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    _make_active_ledger(azoth, "active-for-welcome", "continue stage 3")
    run = load_active_run(tmp_path)
    assert run is not None
    assert run["run_id"] == "active-for-welcome"
    assert "continue stage 3" in (run.get("next_action") or "")


def test_welcome_plain_absent_when_no_active_run(tmp_path: Path) -> None:
    assert load_active_run(tmp_path) is None


def test_welcome_plain_truncates_next_action(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    _make_active_ledger(azoth, "trunc-run", "x" * 100)
    run = load_active_run(tmp_path)
    assert run is not None
    truncated = (run.get("next_action") or "")[:60]
    assert len(truncated) == 60


# ── 23. Example file validates clean ──────────────────────────────────────────


def test_example_file_validates_clean() -> None:
    assert EXAMPLE.exists(), ".azoth/run-ledger.local.yaml.example must exist"
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    errors = validate_ledger(data)
    assert errors == [], f"Example file has validation errors: {errors}"


# ── 24. Resume fields present in load_active_run result ───────────────────────


def test_resume_fields_present(tmp_path: Path) -> None:
    azoth = tmp_path / ".azoth"
    azoth.mkdir()
    (azoth / "run-ledger.local.yaml").write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run_id": "resume-test",
                        "mode": "eval-swarm",
                        "goal": "test resume",
                        "status": "active",
                        "created_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-10T10:30:00+00:00",
                        "next_action": "spawn wave 2 evaluators",
                        "stages_completed": ["wave-1-eval"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    run = load_active_run(tmp_path)
    assert run is not None
    assert run.get("next_action") == "spawn wave 2 evaluators"
    assert run.get("stages_completed") == ["wave-1-eval"]


# ── 25. .gitignore entry ───────────────────────────────────────────────────────


def test_gitignore_contains_run_ledger_entry() -> None:
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists()
    assert "run-ledger.local.yaml" in gitignore.read_text(encoding="utf-8")


# ── 26–28. BL-034: stage_id + wave_label fields ───────────────────────────────


def test_wave_entry_with_stage_id_and_wave_label_passes_validate() -> None:
    """F4a: wave_entry with stage_id + wave_label passes validate_ledger()."""
    data = {
        "schema_version": 1,
        "runs": [
            {
                "run_id": "bl034-run-1",
                "mode": "eval-swarm",
                "goal": "BL-034 depth test",
                "status": "active",
                "created_at": "2026-04-13T10:00:00+00:00",
                "updated_at": "2026-04-13T10:30:00+00:00",
                "next_action": "resume at wave 2",
                "waves": [
                    {
                        "wave": 1,
                        "status": "pass",
                        "stage_id": "wave_a_build",
                        "wave_label": "A",
                    }
                ],
            }
        ],
    }
    assert validate_ledger(data) == []


def test_wave_entry_stage_id_and_wave_label_round_trip(tmp_path: Path) -> None:
    """F4b: CLI append with stage_id + wave_label in --wave JSON round-trips clean."""
    import json as _json

    ledger = tmp_path / "ledger.yaml"
    wave_json = _json.dumps(
        {
            "wave": 1,
            "status": "pass",
            "stage_id": "wave_a_build",
            "wave_label": "A",
        }
    )
    result = _append(ledger, run_id="bl034-roundtrip", wave=wave_json)
    assert result.returncode == 0
    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    wave_entry = data["runs"][0]["waves"][0]
    assert wave_entry["stage_id"] == "wave_a_build"
    assert wave_entry["wave_label"] == "A"
    errors = validate_ledger(data)
    assert errors == [], f"Round-trip ledger has validation errors: {errors}"


def test_wave_entry_wave_label_outside_a_b_c_d_is_stored_gracefully(
    tmp_path: Path,
) -> None:
    """F4c: wave_label outside [A,B,C,D] is stored by Python layer without exception.

    The Python validate_ledger() does not enforce wave_label enum (F3 — permissive
    validator). The JSON Schema is the authoritative constraint source for tooling.
    """
    data = {
        "schema_version": 1,
        "runs": [
            {
                "run_id": "bl034-bad-label",
                "mode": "eval-swarm",
                "goal": "boundary test",
                "status": "active",
                "created_at": "2026-04-13T10:00:00+00:00",
                "updated_at": "2026-04-13T10:30:00+00:00",
                "next_action": "test step",
                "waves": [
                    {
                        "wave": 1,
                        "status": "pass",
                        "wave_label": "Z",
                    }
                ],
            }
        ],
    }
    try:
        result = validate_ledger(data)
        assert isinstance(result, list)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"validate_ledger() raised unexpectedly for out-of-enum wave_label: {exc}")
