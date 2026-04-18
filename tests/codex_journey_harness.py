from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import welcome  # noqa: E402


def future_timestamp(*, hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")


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
    assert proc.stdout.strip(), "router did not emit a hook payload"
    return json.loads(proc.stdout)


def copy_codex_router_fixture(tmp_path: Path, *, with_agents: bool = False) -> Path:
    (tmp_path / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".azoth").mkdir(parents=True, exist_ok=True)
    router_path = tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py"
    router_path.write_text(
        (REPO / ".codex" / "hooks" / "user_prompt_submit_router.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for script_name in ("codex_control_plane.py", "session_continuity.py"):
        (tmp_path / "scripts" / script_name).write_text(
            (REPO / "scripts" / script_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    if with_agents:
        agents_dir = tmp_path / ".codex" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for name in ("orchestrator.toml", "builder.toml", "reviewer.toml"):
            (agents_dir / name).write_text("name = 'stub'\n", encoding="utf-8")
    return router_path


def seed_azoth_repo(
    tmp_path: Path,
    *,
    scope: dict[str, Any] | None = None,
    pipeline_gate: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    run_ledger: dict[str, Any] | None = None,
    backlog_items: list[dict[str, Any]] | None = None,
    final_delivery_approvals: list[dict[str, Any]] | None = None,
) -> None:
    backlog_id = str((scope or {}).get("backlog_id") or "BL-123")
    goal = str((scope or {}).get("goal") or f"{backlog_id}: Journey test")
    session_id = str((scope or {}).get("session_id") or "sess-journey")
    (tmp_path / "azoth.yaml").write_text(
        "version: 0.1.1.29\nphase: 1\nmemory:\n  episodes: 0\n",
        encoding="utf-8",
    )
    azoth_dir = tmp_path / ".azoth"
    (azoth_dir / "memory").mkdir(parents=True, exist_ok=True)
    (azoth_dir / "memory" / "episodes.jsonl").write_text("", encoding="utf-8")
    (azoth_dir / "session-orientation.txt").write_text("cached\n", encoding="utf-8")

    items = backlog_items or [
        {
            "id": backlog_id,
            "status": "active",
            "title": "Journey test",
            "target_layer": "application",
            "delivery_pipeline": "governed"
            if (scope or {}).get("governance_mode") == "governed"
            else "standard",
        }
    ]
    write_yaml(azoth_dir / "backlog.yaml", {"schema_version": 1, "items": items})
    write_yaml(
        azoth_dir / "roadmap.yaml",
        {
            "active_version": "v0.2.0-p1",
            "versions": [
                {
                    "id": "v0.2.0-p1",
                    "status": "active",
                    "current_patch": 29,
                    "tasks": [{"id": backlog_id, "title": "Journey test", "decision_ref": ["D52"]}],
                    "completed_tasks": [],
                }
            ],
        },
    )
    write_json(azoth_dir / "scope-gate.json", scope or {})
    write_json(azoth_dir / "pipeline-gate.json", pipeline_gate or {})
    if session_state is not None:
        write_yaml(azoth_dir / "session-state.md", session_state)
    default_run_ledger = {
        "schema_version": 1,
        "sessions": [
            {
                "session_id": session_id,
                "backlog_id": backlog_id,
                "goal": goal,
                "status": "active",
                "ide": "codex",
                "next_action": "Continue current scope",
                "updated_at": "2026-04-15T00:00:00+00:00",
            }
        ],
        "write_claim": {
            "session_id": session_id,
            "expires_at": future_timestamp(hours=2),
            "acquired_at": "2026-04-15T00:00:00+00:00",
        },
    }
    write_yaml(azoth_dir / "run-ledger.local.yaml", run_ledger or default_run_ledger)
    if final_delivery_approvals is not None:
        write_jsonl(azoth_dir / "final-delivery-approvals.jsonl", final_delivery_approvals)


def capture_plain_welcome(tmp_path: Path, monkeypatch: Any) -> str:
    buffer = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buffer, force_terminal=False, width=220))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    return buffer.getvalue()


def extract_start_block(output: str) -> str:
    start_marker = "── START (what to type) ──"
    end_marker = "════════"
    start = output.index(start_marker)
    end = output.index(end_marker, start)
    return output[start:end].strip()
