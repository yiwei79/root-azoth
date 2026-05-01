from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_bootstrap_verify import (  # noqa: E402
    format_report,
    verify_cockpit_bootstrap,
)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _startup_text(label: str = "AGENTS.md") -> str:
    return f"""# {label} - Yiwei Azoth Cockpit

This repo is Yiwei's personal Azoth cockpit.

## Startup

Start cockpit.

```bash
python3 scripts/cockpit_menu.py --check
python3 scripts/cockpit_menu.py
```

## Context Firewall

Do not import project source, code summaries, dependency inventories, secrets,
retrieval indexes, or project instructions into the cockpit.
"""


def _write_cockpit_bootstrap_fixture(root: Path) -> Path:
    project_path = root.parent / "ras or ray"
    project_path.mkdir(parents=True)
    _write_yaml(
        root / "azoth.yaml",
        {
            "name": "azoth",
            "version": "0.1.4.0",
            "project": "yiwei-azoth-cockpit",
            "deployment_role": "personal-cockpit",
            "previous_project": "personal-azoth-root",
        },
    )
    _write_text(root / "README.md", "# Yiwei Azoth Cockpit\n\n## Start Here\n")
    _write_text(root / "AGENTS.md", _startup_text("AGENTS.md"))
    _write_text(root / "CLAUDE.md", _startup_text("CLAUDE.md"))
    _write_text(root / "scripts" / "cockpit_menu.py", "# deployed menu\n")
    _write_text(
        root / "docs" / "ONBOARDING.md",
        """# Yiwei Azoth Cockpit Onboarding

Start cockpit.

## Command Reference

| Goal | Command | Writes Files |
| --- | --- | --- |
| Validate cockpit metadata | `python3 scripts/cockpit_menu.py --check` | No |
| Open main cockpit menu | `python3 scripts/cockpit_menu.py` | No |
| Open deterministic plain menu | `python3 scripts/cockpit_menu.py --plain` | No |
| Render `ras-or-ray` handoff | `python3 scripts/cockpit_menu.py --project ras-or-ray` | No |
| Render any project handoff | `python3 scripts/cockpit_menu.py --project <project_id>` | No |
| Validate cockpit knowledge layout | `python3 /Users/yiwei/GithubRepos/root-azoth/scripts/personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit` | No |
""",
    )
    _write_yaml(
        root / ".azoth" / "releases" / "applied.yaml",
        {
            "version": 1,
            "applied_releases": [
                {
                    "product": "azoth",
                    "version": "v0.2.0",
                    "commit": "0e93832ea5a9caff499128a84e4b046b8d44ac34",
                }
            ],
            "personal_deployments": [
                {
                    "deployment_id": "t-052-personal-cockpit-deployment-2026-05-01",
                    "target_repo": str(root),
                    "target_panel": "yiwei-azoth-cockpit",
                }
            ],
        },
    )
    receipt = ".azoth/projects/handoffs/t-049-ras-or-ray-2026-05-01.yaml"
    _write_yaml(root / receipt, {"schema_version": 1, "receipt_id": "t-049"})
    _write_yaml(
        root / ".azoth" / "projects" / "handoffs" / "t-055-first-use-ras-or-ray-2026-05-01.yaml",
        {
            "schema_version": 1,
            "receipt_id": "t-055-first-use-ras-or-ray-2026-05-01",
            "task_ref": "T-055",
            "source_panel": "yiwei-azoth-cockpit",
            "target_panel": "ras-or-ray",
            "operation": "first_use_onboarding_and_no_write_handoff_pilot",
            "safe_open_contract": {
                "cockpit_menu_writes_files": False,
                "cockpit_imports_project_context": False,
                "project_session_required_for_project_writes": True,
            },
            "pilot_project": {"project_id": "ras-or-ray"},
        },
    )
    _write_yaml(
        root / ".azoth" / "projects" / "index.yaml",
        {
            "version": 1,
            "projects": [
                {
                    "project_id": "ras-or-ray",
                    "title": "ras or ray",
                    "repo_path": str(project_path),
                    "default_branch": "main",
                    "tracking_ref": "origin/main",
                    "privacy_class": "local-only",
                    "profile_mode": "pointer_only",
                    "handoff_receipt_ref": receipt,
                    "validation_commands": [
                        f"git -C '{project_path}' status --short --branch",
                    ],
                }
            ],
        },
    )
    return root


def test_bootstrap_verify_accepts_minimum_cockpit_fixture(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert errors == []
    assert "cockpit bootstrap verify OK" in format_report(root, errors)


def test_bootstrap_verify_rejects_stale_startup_identity(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_text(
        root / "AGENTS.md",
        "# personal-azoth-root\n\n- **Name**: personal-azoth-root\n",
    )

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("AGENTS.md: stale personal-azoth-root startup identity" in error for error in errors)
    assert any("AGENTS.md: missing required startup text" in error for error in errors)


def test_bootstrap_verify_requires_first_use_receipt(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    (root / ".azoth" / "projects" / "handoffs" / "t-055-first-use-ras-or-ray-2026-05-01.yaml").unlink()

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("missing T-055 first-use onboarding receipt" in error for error in errors)


def test_bootstrap_verify_reuses_pointer_firewall_checks(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    index_path = root / ".azoth" / "projects" / "index.yaml"
    index_doc = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index_doc["projects"][0]["source_files"] = ["app.py"]
    _write_yaml(index_path, index_doc)

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("forbidden context field source_files" in error for error in errors)
