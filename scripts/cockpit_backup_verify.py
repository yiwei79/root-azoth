#!/usr/bin/env python3
"""Verify the yiwei-azoth-cockpit private git backup by restoring it to temp."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REMOTE_URL = "https://github.com/Yeeway69/yiwei-azoth-cockpit.git"
DEFAULT_BRANCH = "main"
DEFAULT_PROJECT = "ras-or-ray"


@dataclass
class StepResult:
    name: str
    command: list[str]
    status: str
    stdout: str = ""
    stderr: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class BackupVerificationResult:
    remote_url: str
    branch: str
    restore_path: Path
    project: str
    remote_head: str = ""
    restored_head: str = ""
    status: str = "failed"
    steps: list[StepResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "remote_url": self.remote_url,
            "branch": self.branch,
            "restore_path": str(self.restore_path),
            "project": self.project,
            "remote_head": self.remote_head,
            "restored_head": self.restored_head,
            "steps": [step.as_dict() for step in self.steps],
        }


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _record_step(
    result: BackupVerificationResult,
    *,
    name: str,
    command: list[str],
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    completed = _run(command, cwd=cwd)
    result.steps.append(
        StepResult(
            name=name,
            command=command,
            status="passed" if completed.returncode == 0 else "failed",
            stdout=(completed.stdout or "").strip(),
            stderr=(completed.stderr or "").strip(),
        )
    )
    return completed


def _require_success(completed: subprocess.CompletedProcess[str], *, name: str) -> None:
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"{name} failed: {detail}")


def _remote_head(output: str, *, branch: str) -> str:
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == f"refs/heads/{branch}":
            return parts[0]
    return ""


def verify_backup(
    *,
    remote_url: str = DEFAULT_REMOTE_URL,
    branch: str = DEFAULT_BRANCH,
    project: str = DEFAULT_PROJECT,
    temp_parent: Path | None = None,
    keep_restore: bool = False,
) -> BackupVerificationResult:
    temp_parent = temp_parent.resolve() if temp_parent else Path(tempfile.gettempdir()).resolve()
    restore_path = Path(
        tempfile.mkdtemp(prefix="azoth-cockpit-backup-verify-", dir=temp_parent)
    ).resolve()
    result = BackupVerificationResult(
        remote_url=remote_url,
        branch=branch,
        restore_path=restore_path,
        project=project,
    )

    try:
        ls_remote = _record_step(
            result,
            name="remote_head",
            command=["git", "ls-remote", remote_url, f"refs/heads/{branch}"],
            cwd=ROOT,
        )
        _require_success(ls_remote, name="remote_head")
        result.remote_head = _remote_head(ls_remote.stdout or "", branch=branch)
        if not result.remote_head:
            result.steps[-1].status = "failed"
            result.steps[-1].stderr = f"refs/heads/{branch} was not found"
            raise RuntimeError(f"remote_head failed: refs/heads/{branch} was not found")

        restore_path.rmdir()
        clone = _record_step(
            result,
            name="remote_clone",
            command=[
                "git",
                "clone",
                "--branch",
                branch,
                "--single-branch",
                remote_url,
                str(restore_path),
            ],
            cwd=ROOT,
        )
        _require_success(clone, name="remote_clone")

        rev_parse = _record_step(
            result,
            name="restored_head",
            command=["git", "rev-parse", "HEAD"],
            cwd=restore_path,
        )
        _require_success(rev_parse, name="restored_head")
        result.restored_head = (rev_parse.stdout or "").strip()
        if result.restored_head != result.remote_head:
            raise RuntimeError(
                "restored_head failed: restored HEAD "
                f"{result.restored_head} != remote HEAD {result.remote_head}"
            )

        checks = (
            (
                "personal_knowledge_validate",
                [
                    sys.executable,
                    str(ROOT / "scripts" / "personal_knowledge_validate.py"),
                    "--root",
                    str(restore_path),
                    "--init-skeleton-dirs",
                ],
            ),
            (
                "cockpit_bootstrap_restore_drill",
                [
                    sys.executable,
                    str(ROOT / "scripts" / "cockpit_bootstrap_verify.py"),
                    "--root",
                    str(restore_path),
                    "--restore-drill",
                ],
            ),
            (
                "cockpit_menu_check",
                [sys.executable, str(restore_path / "scripts" / "cockpit_menu.py"), "--check"],
            ),
            (
                "cockpit_project_handoff",
                [
                    sys.executable,
                    str(restore_path / "scripts" / "cockpit_menu.py"),
                    "--project",
                    project,
                ],
            ),
        )
        for name, command in checks:
            completed = _record_step(result, name=name, command=command, cwd=restore_path)
            _require_success(completed, name=name)

        result.status = "passed"
        return result
    except Exception as exc:
        if result.status != "passed":
            result.steps.append(
                StepResult(
                    name="summary",
                    command=[],
                    status="failed",
                    stderr=str(exc),
                )
            )
        return result
    finally:
        if not keep_restore and restore_path.exists():
            shutil.rmtree(restore_path)


def format_report(result: BackupVerificationResult) -> str:
    lines = [
        f"cockpit backup verify {result.status}: {result.remote_url}",
        f"branch: {result.branch}",
        f"restore_path: {result.restore_path}",
    ]
    if result.remote_head:
        lines.append(f"remote_head: {result.remote_head}")
    if result.restored_head:
        lines.append(f"restored_head: {result.restored_head}")
    for step in result.steps:
        lines.append(f"- {step.name}: {step.status}")
        if step.status != "passed" and step.stderr:
            lines.append(f"  {step.stderr}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-url", default=DEFAULT_REMOTE_URL)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--temp-parent", type=Path)
    parser.add_argument(
        "--keep-restore",
        action="store_true",
        help="Leave the temporary restored checkout on disk for inspection.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    args = parser.parse_args(argv)

    result = verify_backup(
        remote_url=args.remote_url,
        branch=args.branch,
        project=args.project,
        temp_parent=args.temp_parent,
        keep_restore=args.keep_restore,
    )
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(format_report(result))
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
