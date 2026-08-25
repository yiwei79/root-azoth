"""Tests for scripts/sync_claude_memory.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import do_closeout  # noqa: E402
import sync_claude_memory  # noqa: E402


def _build_repo(tmp_path: Path) -> Path:
    (tmp_path / "azoth.yaml").write_text(
        "version: 0.1.3.5\nphase: 3\nmemory:\n  episodes: 322\n",
        encoding="utf-8",
    )
    azoth_dir = tmp_path / ".azoth"
    (azoth_dir / "memory").mkdir(parents=True)
    episode = {
        "id": "ep-322",
        "summary": "Closed BL-065 and deferred W3 mirror.",
        "goal": "BL-065: Worktree-upgrade external evidence refresh lane",
    }
    (azoth_dir / "memory" / "episodes.jsonl").write_text(
        json.dumps(episode) + "\n",
        encoding="utf-8",
    )
    (azoth_dir / "roadmap.yaml").write_text(
        "\n".join(
            [
                "active_version: v0.2.0-p3",
                "versions:",
                "  - id: v0.2.0-p3",
                "    current_patch: 5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (azoth_dir / "session-state.md").write_text(
        yaml.safe_dump(
            {
                "session_id": "sess-123",
                "state": "closed",
                "next_action": "Run `/next` to select the next scoped task.",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    pending = {
        "schema_version": 1,
        "status": "pending",
        "updated_at": "2026-04-22T14:50:00Z",
        "source": "session-closeout",
        "session_id": "sess-123",
        "goal": "AD-HOC: Codex W3 pending artifact + repo-local Claude-memory sync command",
        "latest_episode_id": "ep-322",
        "latest_episode_summary": "Closed BL-065 and deferred W3 mirror.",
        "next_action": "Replay Claude memory mirror, then run `/next`.",
        "target_dir": "/tmp/fake/.claude/projects/root/memory",
        "reason": "sandbox denied home write",
    }
    (tmp_path / do_closeout.CLAUDE_MEMORY_SYNC_PENDING).write_text(
        json.dumps(pending, indent=2) + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_sync_claude_memory_marks_pending_artifact_synced(tmp_path: Path, monkeypatch) -> None:
    repo_root = _build_repo(tmp_path)
    calls: list[tuple[Path, dict[str, object], str]] = []

    def _fake_w3(
        repo_root_arg: Path,
        *,
        latest_episode: dict[str, object] | None = None,
        next_action: str | None = None,
    ) -> None:
        calls.append((repo_root_arg, latest_episode or {}, next_action or ""))

    monkeypatch.setattr(do_closeout, "write_claude_memory_mirror", _fake_w3)

    exit_code = sync_claude_memory.main(["--repo-root", str(repo_root)])

    assert exit_code == 0
    assert calls == [
        (
            repo_root,
            {
                "id": "ep-322",
                "summary": "Closed BL-065 and deferred W3 mirror.",
                "goal": "BL-065: Worktree-upgrade external evidence refresh lane",
            },
            "Replay Claude memory mirror, then run `/next`.",
        )
    ]
    pending = json.loads(
        (repo_root / do_closeout.CLAUDE_MEMORY_SYNC_PENDING).read_text(encoding="utf-8")
    )
    assert pending["status"] == "synced"
    assert "synced_at" in pending
