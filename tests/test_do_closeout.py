"""Tests for scripts/do_closeout.py governed closeout enforcement."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import do_closeout  # noqa: E402


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _build_repo(
    tmp_path: Path,
    *,
    delivery_pipeline: str = "governed",
    session_id: str = "sess-123",
    backlog_id: str = "BL-123",
    include_session_state: bool = False,
    include_sessions_registry: bool = True,
    include_resumable_run: bool = False,
) -> Path:
    (tmp_path / "azoth.yaml").write_text(
        "version: 0.1.1.29\nphase: 1\nmemory:\n  episodes: 0\n", encoding="utf-8"
    )
    azoth_dir = tmp_path / ".azoth"
    (azoth_dir / "memory").mkdir(parents=True)
    (azoth_dir / "memory" / "episodes.jsonl").write_text("", encoding="utf-8")
    (azoth_dir / "session-orientation.txt").write_text("cached\n", encoding="utf-8")
    (azoth_dir / "roadmap.yaml").write_text(
        "\n".join(
            [
                "active_version: v0.2.0-p1",
                "versions:",
                "  - id: v0.2.0-p1",
                "    status: active",
                "    current_patch: 29",
                "    tasks:",
                f"      - id: {backlog_id}",
                '        title: "Governed closeout"',
                "        decision_ref: [D50]",
                "    completed_tasks:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    scope_gate = {
        "approved": True,
        "approved_by": "human",
        "expires_at": _future(),
        "session_id": session_id,
        "goal": f"{backlog_id}: Governed closeout",
        "backlog_id": backlog_id,
        "delivery_pipeline": delivery_pipeline,
    }
    (azoth_dir / "scope-gate.json").write_text(json.dumps(scope_gate), encoding="utf-8")

    (azoth_dir / "backlog.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "items:",
                f'  - id: "{backlog_id}"',
                "    status: active",
                '    title: "Governed closeout"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    run_ledger: dict[str, object] = {
        "schema_version": 1,
        "runs": [],
        "write_claim": {
            "session_id": session_id,
            "expires_at": _future(),
            "acquired_at": "2026-04-15T00:00:00+00:00",
        },
    }
    if include_sessions_registry:
        session_entry: dict[str, object] = {
            "session_id": session_id,
            "backlog_id": backlog_id,
            "goal": f"{backlog_id}: Governed closeout",
            "status": "active",
            "ide": "codex",
            "next_action": "Continue current scope",
            "updated_at": "2026-04-15T00:00:00+00:00",
        }
        if include_resumable_run:
            session_entry["active_run_id"] = "run-123"
            run_ledger["runs"] = [
                {
                    "run_id": "run-123",
                    "session_id": session_id,
                    "backlog_id": backlog_id,
                    "ide": "codex",
                    "mode": "auto",
                    "goal": f"{backlog_id}: Governed closeout",
                    "status": "paused",
                    "created_at": "2026-04-15T00:00:00+00:00",
                    "updated_at": "2026-04-15T00:00:00+00:00",
                    "next_action": "Resume wave 2 review.",
                    "stages_completed": ["planner"],
                    "active_stage_id": "architect_review",
                    "pending_stage_ids": ["builder_apply", "reviewer_gate"],
                    "pause_reason": "human-gate",
                    "waves": [],
                    "branches": [],
                }
            ]
        run_ledger["sessions"] = [session_entry]
    (azoth_dir / "run-ledger.local.yaml").write_text(
        yaml.safe_dump(run_ledger, sort_keys=False),
        encoding="utf-8",
    )
    if include_session_state:
        session_state: dict[str, object] = {
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2026-04-15T00:00:00+00:00",
            "active_task": "In progress",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": f"{backlog_id}: Governed closeout",
            "next_action": "Continue current scope",
        }
        if include_resumable_run:
            session_state.update(
                {
                    "pipeline": "auto",
                    "pipeline_position": 2,
                    "current_stage_id": "architect_review",
                    "completed_stages": ["planner"],
                    "pending_stages": ["builder_apply", "reviewer_gate"],
                    "pause_reason": "human-gate",
                    "active_run_id": "run-123",
                }
            )
        (azoth_dir / "session-state.md").write_text(
            yaml.safe_dump(session_state, sort_keys=False),
            encoding="utf-8",
        )
    return tmp_path


def _write_approvals(repo_root: Path, *records: dict[str, object]) -> str:
    text = "".join(json.dumps(record) + "\n" for record in records)
    (repo_root / ".azoth" / "final-delivery-approvals.jsonl").write_text(text, encoding="utf-8")
    return text


def _update_backlog_item(repo_root: Path, backlog_id: str, **fields: object) -> None:
    backlog_path = repo_root / ".azoth" / "backlog.yaml"
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    for item in backlog["items"]:
        if item["id"] == backlog_id:
            item.update(fields)
            break
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")


def _set_version_tasks(repo_root: Path, version_id: str, tasks: list[dict[str, object]]) -> None:
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    for version in roadmap["versions"]:
        if version["id"] == version_id:
            version["tasks"] = tasks
            break
    roadmap_path.write_text(yaml.safe_dump(roadmap, sort_keys=False), encoding="utf-8")


def test_governed_closeout_requires_approval_evidence_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    version_bump_calls: list[tuple[list[str], Path]] = []

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)

    with pytest.raises(do_closeout.ApprovalEvidenceError):
        do_closeout.run_closeout(repo_root)
    assert version_bump_calls == []
    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""
    assert (
        json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))[
            "approved"
        ]
        is True
    )
    assert "status: active" in (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    assert "write_claim:" in (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(
        encoding="utf-8"
    )
    assert (repo_root / ".azoth" / "session-orientation.txt").exists()


def test_governed_closeout_rejects_malformed_approval_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    (repo_root / ".azoth" / "final-delivery-approvals.jsonl").write_text(
        '{"session_id":"sess-123","gate":"final-delivery"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(do_closeout.ApprovalEvidenceError, match="Invalid JSON"):
        do_closeout.run_closeout(repo_root)

    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("records", "expected_message"),
    [
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "agent",
                    "approved": True,
                }
            ],
            "actor_type=human",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": False,
                    "decision": "denied",
                },
            ],
            "actor_type=human and approved=true",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "decision": "approved",
                },
            ],
            "actor_type=human and approved=true",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": False,
                    "decision": "approved",
                },
            ],
            "actor_type=human and approved=true",
        ),
    ],
)
def test_governed_closeout_fails_closed_on_invalid_latest_approval_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: list[dict[str, object]],
    expected_message: str,
) -> None:
    repo_root = _build_repo(tmp_path)
    _write_approvals(repo_root, *records)
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(do_closeout.ApprovalEvidenceError, match=expected_message):
        do_closeout.run_closeout(repo_root)

    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""


def test_governed_closeout_accepts_matching_human_approval_without_consuming_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=True)
    expected_verbatim_payload = json.loads(
        (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8")
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    approvals_before = _write_approvals(
        repo_root,
        {
            "session_id": "other-session",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
        },
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    version_bump_calls: list[tuple[list[str], Path, bool]] = []

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd, check))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)
    monkeypatch.setenv("HOME", str(fake_home))
    do_closeout.run_closeout(repo_root)

    episode_lines = (
        (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(episode_lines) == 1
    episode = json.loads(episode_lines[0])
    assert episode["session_id"] == "sess-123"
    assert episode["goal"] == "BL-123: Governed closeout"
    assert ".azoth/backlog.yaml" in episode["context"]["files_changed"]
    assert ".azoth/roadmap.yaml" in episode["context"]["files_changed"]
    assert ".azoth/run-ledger.local.yaml" in episode["context"]["files_changed"]
    assert ".azoth/bootloader-state.md" in episode["context"]["files_changed"]
    assert ".azoth/session-state.md" in episode["context"]["files_changed"]
    assert episode["context"]["verbatim_source"] == "scope-gate.json"
    assert episode["context"]["verbatim_payload"] == expected_verbatim_payload

    scope = json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["approved"] is False
    assert "closed_at" in scope
    backlog_text = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    assert "status: active" not in backlog_text
    assert "status: complete" in backlog_text
    assert "completed_date:" in backlog_text
    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "      - id: BL-123\n" not in roadmap_text
    assert '{id: BL-123, title: "Governed closeout", completed_date:' in roadmap_text
    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    assert "write_claim" not in ledger
    session_entry = ledger["sessions"][0]
    assert session_entry["status"] == "closed"
    assert session_entry["next_action"] == do_closeout.default_next_action()
    assert "updated_at" in session_entry
    assert "closed_at" in session_entry
    assert "active_run_id" not in session_entry
    assert (repo_root / ".azoth" / "final-delivery-approvals.jsonl").read_text(
        encoding="utf-8"
    ) == approvals_before
    assert not (repo_root / ".azoth" / "session-orientation.txt").exists()
    session_state = (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    assert "state: closed" in session_state
    assert "last_ide: codex" in session_state
    assert f"next_action: {do_closeout.default_next_action()}" in session_state
    bootloader_state = (repo_root / ".azoth" / "bootloader-state.md").read_text(encoding="utf-8")
    assert "sess-123" in bootloader_state
    assert "ep-001" in bootloader_state
    assert do_closeout.default_next_action() in bootloader_state
    memory_dir = do_closeout.claude_project_memory_dir(repo_root)
    project_status = (memory_dir / "project_status.md").read_text(encoding="utf-8")
    memory_index = (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
    assert "Toolkit version: 0.1.1.29" in project_status
    assert "Roadmap active_version: v0.2.0-p1" in project_status
    assert "Last episode: ep-001" in project_status
    assert f"Next action: {do_closeout.default_next_action()}" in project_status
    assert "Project Status" in memory_index
    assert version_bump_calls == [
        ([sys.executable, "scripts/version-bump.py", "--patch"], repo_root, True)
    ]


def test_exploratory_light_closeout_closes_session_without_version_bump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _build_repo(tmp_path, delivery_pipeline="standard", include_session_state=True)
    (repo_root / ".azoth" / "scope-gate.json").write_text("{}", encoding="utf-8")
    (repo_root / ".azoth" / "session-gate.json").write_text(
        json.dumps(
            {
                "session_id": "sess-123",
                "goal": "Explore closeout UX",
                "session_mode": "exploratory",
                "opened_at": "2026-04-20T10:00:00+00:00",
                "updated_at": "2026-04-20T10:00:00+00:00",
                "status": "active",
                "approved_by": "system",
            }
        ),
        encoding="utf-8",
    )
    expected_verbatim_payload = json.loads(
        (repo_root / ".azoth" / "session-gate.json").read_text(encoding="utf-8")
    )
    version_bump_calls: list[tuple[list[str], Path, bool]] = []
    monkeypatch.setattr(
        do_closeout.subprocess,
        "run",
        lambda cmd, cwd, check: version_bump_calls.append((cmd, cwd, check)),
    )

    do_closeout.run_closeout(repo_root)

    episodes = [
        json.loads(line)
        for line in (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert episodes
    episode = episodes[-1]
    assert episode["context"]["verbatim_source"] == "session-gate.json"
    assert episode["context"]["verbatim_payload"] == expected_verbatim_payload
    session_gate = json.loads((repo_root / ".azoth" / "session-gate.json").read_text(encoding="utf-8"))
    assert session_gate["status"] == "closed"
    session_state = yaml.safe_load((repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8"))
    assert session_state["session_mode"] == "exploratory"
    assert session_state["approved_scope"] == "Exploratory session (no write scope)"
    assert version_bump_calls == []


def test_exploratory_light_closeout_wins_over_stale_approved_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _build_repo(tmp_path, delivery_pipeline="standard", include_session_state=True)
    stale_scope = {
        "approved": True,
        "expires_at": "2020-01-01T00:00:00+00:00",
        "session_id": "sess-stale",
        "goal": "BL-123: stale scope",
        "backlog_id": "BL-123",
        "delivery_pipeline": "standard",
    }
    (repo_root / ".azoth" / "scope-gate.json").write_text(
        json.dumps(stale_scope),
        encoding="utf-8",
    )
    (repo_root / ".azoth" / "session-gate.json").write_text(
        json.dumps(
            {
                "session_id": "sess-123",
                "goal": "Explore closeout UX",
                "session_mode": "exploratory",
                "opened_at": "2026-04-20T10:00:00+00:00",
                "updated_at": "2026-04-20T10:00:00+00:00",
                "status": "active",
                "approved_by": "system",
            }
        ),
        encoding="utf-8",
    )
    version_bump_calls: list[tuple[list[str], Path, bool]] = []
    monkeypatch.setattr(
        do_closeout.subprocess,
        "run",
        lambda cmd, cwd, check: version_bump_calls.append((cmd, cwd, check)),
    )

    do_closeout.run_closeout(repo_root)

    session_gate = json.loads((repo_root / ".azoth" / "session-gate.json").read_text(encoding="utf-8"))
    assert session_gate["status"] == "closed"
    session_state = yaml.safe_load((repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8"))
    assert session_state["session_mode"] == "exploratory"
    assert version_bump_calls == []


def test_governed_closeout_keeps_last_version_completion_inside_versions_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=True)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8")
        + "\n".join(
            [
                "initiatives:",
                "  - id: INI-RST-001",
                '    title: "Declarative swarm / eval-wave specification"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    version = roadmap["versions"][0]
    assert {entry["id"] for entry in version["completed_tasks"]} == {"BL-123"}
    assert roadmap["initiatives"][0]["id"] == "INI-RST-001"
    assert roadmap["initiatives"][0]["title"] == "Declarative swarm / eval-wave specification"


def test_governed_closeout_skips_initiative_roadmap_ref_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _build_repo(tmp_path, backlog_id="BL-040")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _update_backlog_item(
        repo_root,
        "BL-040",
        roadmap_ref="INI-RST-001",
        initiative_ref="INI-RST-001",
        target_version="v0.2.0-p1",
    )
    _set_version_tasks(
        repo_root,
        "v0.2.0-p1",
        [{"id": "P1-002", "title": "Declarative swarm", "decision_ref": ["D23"]}],
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    before = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    do_closeout.run_closeout(repo_root)
    out = capsys.readouterr().out

    backlog_text = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "status: complete" in backlog_text
    assert roadmap_text == before
    assert "W2c:" in out
    assert "INI-RST-001" in out


def test_governed_closeout_skips_narrative_roadmap_ref_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _build_repo(tmp_path, backlog_id="BL-018")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _update_backlog_item(
        repo_root,
        "BL-018",
        roadmap_ref="intake-ep-087",
        target_version="v0.2.0-p1",
    )
    _set_version_tasks(
        repo_root,
        "v0.2.0-p1",
        [{"id": "P1-004", "title": "Control-plane surfacing", "decision_ref": ["D52"]}],
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    before = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    do_closeout.run_closeout(repo_root)
    out = capsys.readouterr().out

    backlog_text = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "status: complete" in backlog_text
    assert roadmap_text == before
    assert "W2c:" in out
    assert "intake-ep-087" in out


def test_governed_closeout_skips_unknown_roadmap_ref_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _build_repo(tmp_path, backlog_id="BL-999")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _update_backlog_item(
        repo_root,
        "BL-999",
        roadmap_ref="P9-999",
        target_version="v0.2.0-p1",
    )
    _set_version_tasks(
        repo_root,
        "v0.2.0-p1",
        [{"id": "P1-024", "title": "Projection refactor", "decision_ref": ["D46"]}],
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    before = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    do_closeout.run_closeout(repo_root)
    out = capsys.readouterr().out

    backlog_text = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "status: complete" in backlog_text
    assert roadmap_text == before
    assert "W2c:" in out
    assert "P9-999" in out


def test_governed_closeout_completes_real_roadmap_ref_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, backlog_id="BL-041")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _update_backlog_item(
        repo_root,
        "BL-041",
        roadmap_ref="P1-017",
        target_version="v0.2.0-p1",
    )
    _set_version_tasks(
        repo_root,
        "v0.2.0-p1",
        [{"id": "P1-017", "title": "Reinforcement automation", "decision_ref": ["D11"]}],
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "      - id: P1-017\n" not in roadmap_text
    assert '{id: P1-017, title: "Governed closeout", completed_date:' in roadmap_text


def test_governed_closeout_retargets_initiative_alias_to_next_pending_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, backlog_id="BL-041")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _update_backlog_item(
        repo_root,
        "BL-041",
        roadmap_ref="T-008",
        initiative_ref="INI-EVI-001",
        target_version="v0.2.0-p1",
    )
    (repo_root / ".azoth" / "roadmap.yaml").write_text(
        "\n".join(
            [
                "active_version: v0.2.0-p1",
                "versions:",
                "  - id: v0.2.0-p1",
                "    status: active",
                "    current_patch: 29",
                "    tasks:",
                "      - id: T-008",
                '        title: "Minimal bounded research sufficiency gate"',
                "        decision_ref: [D23, D44]",
                "    completed_tasks: []",
                "initiatives:",
                "  - id: INI-EVI-001",
                '    title: "Evidence-grounded external knowledge"',
                "    category: pipeline",
                "    theme: B",
                "    phase: v0.2.0-p1",
                "    task_ref: T-008",
                '    spec_ref: ".azoth/roadmap-specs/v0.2.0/T-008.yaml"',
                "    dimensions:",
                "      themes: [B, C, D]",
                "      categories: [pipeline, memory, platform]",
                "      tracks: [research-sufficiency, evidence-capsules, freshness]",
                "    slices:",
                "      - task_ref: T-008",
                '        spec_ref: ".azoth/roadmap-specs/v0.2.0/T-008.yaml"',
                "        phase: v0.2.0-p1",
                "        status: active",
                "        role: primary",
                "      - task_ref: T-009",
                '        spec_ref: ".azoth/roadmap-specs/v0.2.0/T-009.yaml"',
                "        phase: v0.2.0-p1",
                "        status: planned",
                "        role: follow-on",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    roadmap = yaml.safe_load((repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8"))
    initiative = roadmap["initiatives"][0]
    assert initiative["task_ref"] == "T-009"
    assert initiative["spec_ref"] == ".azoth/roadmap-specs/v0.2.0/T-009.yaml"
    assert initiative["phase"] == "v0.2.0-p1"
    assert initiative["slices"] == [
        {
            "task_ref": "T-008",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-008.yaml",
            "phase": "v0.2.0-p1",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-009",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-009.yaml",
            "phase": "v0.2.0-p1",
            "status": "active",
            "role": "primary",
        },
    ]


def test_governed_closeout_rejects_unknown_reinforcement_id_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
    episodes_path.write_text(
        json.dumps(
            {
                "id": "ep-010",
                "session_id": "older-session",
                "reinforcement_count": 0,
                "context": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scope_before = (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8")
    backlog_before = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    episodes_before = episodes_path.read_text(encoding="utf-8")
    version_bump_calls: list[tuple[list[str], Path, bool]] = []

    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd, check))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)

    with pytest.raises(do_closeout.ReinforcementValidationError, match="unknown reinforce"):
        do_closeout.run_closeout(repo_root, reinforce_episode_ids=["ep-010", "ep-999"])

    assert version_bump_calls == []
    assert episodes_path.read_text(encoding="utf-8") == episodes_before
    assert (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8") == scope_before
    assert (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8") == backlog_before
    assert "write_claim:" in (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(
        encoding="utf-8"
    )
    assert (repo_root / ".azoth" / "session-orientation.txt").exists()


def test_governed_closeout_rejects_ambiguous_reinforcement_id_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
    episodes_path.write_text(
        "\n".join(
            [
                json.dumps({"id": "ep-010", "session_id": "older-a", "reinforcement_count": 0, "context": {}}),
                json.dumps({"id": "ep-010", "session_id": "older-b", "reinforcement_count": 1, "context": {}}),
                "",
            ]
        ),
        encoding="utf-8",
    )
    scope_before = (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8")
    backlog_before = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    episodes_before = episodes_path.read_text(encoding="utf-8")
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(do_closeout.ReinforcementValidationError, match="ambiguous reinforce"):
        do_closeout.run_closeout(repo_root, reinforce_episode_ids=["ep-010"])

    assert episodes_path.read_text(encoding="utf-8") == episodes_before
    assert (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8") == scope_before
    assert (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8") == backlog_before


def test_governed_closeout_can_reinforce_exact_prior_episode_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    (repo_root / ".azoth" / "memory" / "episodes.jsonl").write_text(
        json.dumps(
            {
                "id": "ep-010",
                "session_id": "older-session",
                "goal": "Prior lesson",
                "summary": "Older reinforced lesson.",
                "reinforcement_count": 0,
                "context": {
                    "verbatim_source": "scope-gate.json",
                    "verbatim_payload": {
                        "session_id": "older-session",
                        "goal": "Prior lesson",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root, reinforce_episode_ids=["ep-010", "ep-010"])

    episodes = [
        json.loads(line)
        for line in (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    prior = episodes[0]
    new_episode = episodes[1]

    assert prior["reinforcement_count"] == 1
    assert prior["context"]["reinforced_by_sessions"] == ["sess-123"]
    assert prior["context"]["verbatim_source"] == "scope-gate.json"
    assert prior["context"]["verbatim_payload"] == {
        "session_id": "older-session",
        "goal": "Prior lesson",
    }
    assert new_episode["reinforcement_count"] == 0


def test_governed_closeout_uses_resumable_run_next_action_for_w2_and_w3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    expected_next_action = "Resume wave 2 review."
    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    session_entry = ledger["sessions"][0]
    assert session_entry["status"] == "parked"
    assert session_entry["active_run_id"] == "run-123"
    assert session_entry["next_action"] == expected_next_action
    assert "closed_at" not in session_entry

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "parked"
    assert session_state["active_task"] == "Parked — BL-123: Governed closeout"
    assert session_state["approved_scope"] == "BL-123: Governed closeout"
    assert session_state["next_action"] == expected_next_action

    bootloader_state = (repo_root / ".azoth" / "bootloader-state.md").read_text(encoding="utf-8")
    assert expected_next_action in bootloader_state

    memory_dir = do_closeout.claude_project_memory_dir(repo_root)
    project_status = (memory_dir / "project_status.md").read_text(encoding="utf-8")
    assert f"Next action: {expected_next_action}" in project_status


def test_governed_closeout_preserves_checkpoint_fields_in_session_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["pipeline"] == "auto"
    assert session_state["pipeline_position"] == 2
    assert session_state["current_stage_id"] == "architect_review"
    assert session_state["completed_stages"] == ["planner"]
    assert session_state["pending_stages"] == ["builder_apply", "reviewer_gate"]
    assert session_state["pause_reason"] == "human-gate"
    assert session_state["active_run_id"] == "run-123"


def test_governed_administrative_finalize_closes_resumable_session_without_version_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    version_bump_calls: list[tuple[list[str], Path, bool]] = []

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd, check))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root, administrative_finalize=True)

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    session_entry = ledger["sessions"][0]
    assert session_entry["status"] == "closed"
    assert session_entry["next_action"] == (
        "Administrative finalize complete — run `/next` to select the next scoped task."
    )
    assert "active_run_id" not in session_entry
    assert "closed_at" in session_entry
    assert "write_claim" not in ledger

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "closed"
    assert session_state["next_action"] == session_entry["next_action"]
    assert "active_run_id" not in session_state

    assert version_bump_calls == []


def test_governed_closeout_closes_stale_active_run_instead_of_parking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"][0]["status"] = "active"
    ledger["runs"][0]["pause_reason"] = None
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    updated = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    session_entry = updated["sessions"][0]
    run_entry = updated["runs"][0]

    assert session_entry["status"] == "closed"
    assert "active_run_id" not in session_entry
    assert "closed_at" in session_entry
    assert run_entry["status"] == "complete"
    assert run_entry["next_action"] == "Run `/next` to select the next scoped task."
    assert "active_stage_id" not in run_entry
    assert "pending_stage_ids" not in run_entry

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "closed"
    assert "active_run_id" not in session_state


def test_governed_closeout_creates_session_registry_entry_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_sessions_registry=False,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    session_entry = ledger["sessions"][0]
    assert session_entry["session_id"] == "sess-123"
    assert session_entry["status"] == "closed"
    assert session_entry["backlog_id"] == "BL-123"
    assert session_entry["goal"] == "BL-123: Governed closeout"


def test_governed_closeout_skips_session_state_when_file_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    assert not (repo_root / ".azoth" / "session-state.md").exists()
    assert (repo_root / ".azoth" / "bootloader-state.md").exists()

    episode_lines = (
        (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    episode = json.loads(episode_lines[0])
    assert ".azoth/session-state.md" not in episode["context"]["files_changed"]


def test_governed_closeout_runs_w3_before_w4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=True)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    order: list[str] = []

    def _fake_w3(*args: object, **kwargs: object) -> None:
        order.append("W3")

    def _fake_w4(*args: object, **kwargs: object) -> None:
        order.append("W4")

    monkeypatch.setattr(do_closeout, "write_claude_memory_mirror", _fake_w3)
    monkeypatch.setattr(do_closeout, "run_version_bump", _fake_w4)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    assert order == ["W3", "W4"]
