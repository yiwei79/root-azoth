"""Shared Codex calm-flow fixture helpers for journey and router tests."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
PIPELINE_COMMANDS = {"auto", "dynamic-full-auto", "deliver", "deliver-full"}
START_ROUTED_COMMANDS = PIPELINE_COMMANDS | {"next"}


def future_timestamp(*, hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_router(router: Path, prompt: str, *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(router)],
        input=json.dumps({"prompt": prompt}),
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
    )
    assert proc.returncode == 0, proc.stderr
    text = proc.stdout.strip()
    return json.loads(text) if text else {}


def _copy_text(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def copy_codex_router_fixture(
    tmp_path: Path,
    *command_names: str,
    include_skills: bool = True,
    multi_agent: bool = True,
    include_orchestrator: bool = True,
) -> Path:
    """Copy the deployed Codex router and only the command/skill files a test needs."""

    for rel in (
        ".codex/hooks",
        ".codex/agents",
        ".claude/commands",
        ".agents/skills",
        "scripts",
        ".azoth",
    ):
        (tmp_path / rel).mkdir(parents=True, exist_ok=True)

    for rel in (
        ".codex/hooks/user_prompt_submit_router.py",
        "scripts/session_continuity.py",
        "scripts/codex_control_plane.py",
    ):
        _copy_text(REPO / rel, tmp_path / rel)

    (tmp_path / ".codex" / "config.toml").write_text(
        "[features]\n"
        f"multi_agent = {'true' if multi_agent else 'false'}\n",
        encoding="utf-8",
    )
    if include_orchestrator:
        (tmp_path / ".codex" / "agents" / "orchestrator.toml").write_text(
            "name = 'orchestrator'\n",
            encoding="utf-8",
        )

    requested = set(command_names)
    if requested & START_ROUTED_COMMANDS or "start" in requested:
        requested.add("start")

    for name in sorted(requested):
        source = REPO / ".claude" / "commands" / f"{name}.md"
        if source.is_file():
            _copy_text(source, tmp_path / ".claude" / "commands" / f"{name}.md")

    if not include_skills:
        return tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py"

    skill_names = set(command_names)
    if skill_names & START_ROUTED_COMMANDS or "start" in skill_names:
        skill_names.add("start")

    for name in sorted(skill_names):
        skill = REPO / ".agents" / "skills" / f"azoth-{name}" / "SKILL.md"
        if skill.is_file():
            _copy_text(skill, tmp_path / ".agents" / "skills" / f"azoth-{name}" / "SKILL.md")

    return tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py"


def seed_azoth_repo(
    repo_root: Path,
    *,
    azoth_version: str = "0.1.0",
    phase: int = 3,
    backlog_items: list[dict[str, Any]] | None = None,
    scope: dict[str, Any] | None = None,
    pipeline_gate: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    sessions: list[dict[str, Any]] | None = None,
    runs: list[dict[str, Any]] | None = None,
    write_claim: dict[str, Any] | None = None,
    episodes: list[dict[str, Any]] | None = None,
    roadmap: dict[str, Any] | None = None,
    session_orientation_text: str | None = None,
) -> Path:
    """Seed a minimal repo-local Azoth state surface for Codex UX tests."""

    azoth_dir = repo_root / ".azoth"
    (azoth_dir / "memory").mkdir(parents=True, exist_ok=True)

    (repo_root / "azoth.yaml").write_text(
        yaml.safe_dump(
            {
                "version": azoth_version,
                "phase": phase,
                "layers": {
                    "molecule": {"status": "complete"},
                    "mineral": {"status": "complete"},
                    "wave": {"status": "active"},
                    "current": {"status": "active"},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    write_yaml(
        azoth_dir / "backlog.yaml",
        {
            "schema_version": 1,
            "items": backlog_items or [],
        },
    )
    write_yaml(
        azoth_dir / "roadmap.yaml",
        roadmap
        or {
            "active_version": "v0.2.0-p1",
            "versions": [
                {
                    "id": "v0.2.0-p1",
                    "status": "active",
                    "current_patch": 1,
                    "tasks": [],
                    "completed_tasks": [],
                }
            ],
        },
    )
    write_jsonl(azoth_dir / "memory" / "episodes.jsonl", episodes or [])

    if scope is not None:
        write_json(azoth_dir / "scope-gate.json", scope)
    if pipeline_gate is not None:
        write_json(azoth_dir / "pipeline-gate.json", pipeline_gate)
    if session_state is not None:
        write_yaml(azoth_dir / "session-state.md", session_state)

    write_yaml(
        azoth_dir / "run-ledger.local.yaml",
        {
            "schema_version": 1,
            "runs": runs or [],
            **({"sessions": sessions} if sessions is not None else {}),
            **({"write_claim": write_claim} if write_claim is not None else {}),
        },
    )

    if session_orientation_text is not None:
        (azoth_dir / "session-orientation.txt").write_text(
            session_orientation_text,
            encoding="utf-8",
        )

    return repo_root
