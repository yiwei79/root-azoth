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
from cockpit_command_surface import COCKPIT_COMMANDS, deploy_cockpit_command_surface  # noqa: E402


READBACK_FIELDS = {
    "project_pointer": "ras-or-ray",
    "authority_plane": "personal_cockpit",
    "selected_mode": "assisted",
    "readiness_state": "ready",
    "freshness_status": "current",
    "installed_asset_classes": ["skills", "command wrappers"],
    "missing_asset_classes": ["planning-bank seed", "autonomous control"],
    "approval_scope": "pointer_only_handoff",
    "active_write_claim": False,
    "next_safe_action": "Open a project session; project writes require a fresh project-scoped gate.",
    "stop_reason": "none",
}


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
    _write_text(root / ".codex" / "config.toml", "[features]\ncodex_hooks = false\n")
    _write_text(root / ".codex" / "hooks.json", '{"hooks": {}}\n')
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
| Run Personal Harness daily flow | `python3 /Users/yiwei/GithubRepos/root-azoth/scripts/personal_harness_daily_flow.py --cockpit-root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit --repo-root /Users/yiwei/GithubRepos/root-azoth --project ras-or-ray --goal "<goal>" --action focused_verification --tag context --summary` | No |
| Validate cockpit knowledge layout | `python3 /Users/yiwei/GithubRepos/root-azoth/scripts/personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit` | No |

## Cockpit Command Surface

"""
        + "\n".join(
            f"- `{command.display_name}` / `${command.skill_name}`" for command in COCKPIT_COMMANDS
        )
        + """
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
                    **READBACK_FIELDS,
                    "handoff_receipt_ref": receipt,
                    "validation_commands": [
                        f"git -C '{project_path}' status --short --branch",
                    ],
                }
            ],
        },
    )
    command_lines = "\n".join(
        f"- `{command.display_name}` / `${command.skill_name}`" for command in COCKPIT_COMMANDS
    )
    for rel_path in ("AGENTS.md", "CLAUDE.md"):
        path = root / rel_path
        path.write_text(
            path.read_text(encoding="utf-8") + f"\n## Cockpit Command Surface\n\n{command_lines}\n",
            encoding="utf-8",
        )
    deploy_cockpit_command_surface(root)
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


def test_bootstrap_verify_accepts_relocated_restore_drill(tmp_path: Path) -> None:
    live_root = tmp_path / "live" / "yiwei-azoth-cockpit"
    restore_root = tmp_path / "restore" / "restore-copy"
    _write_cockpit_bootstrap_fixture(live_root)
    _write_cockpit_bootstrap_fixture(restore_root)
    releases_path = restore_root / ".azoth" / "releases" / "applied.yaml"
    releases_doc = yaml.safe_load(releases_path.read_text(encoding="utf-8"))
    releases_doc["personal_deployments"][0]["target_repo"] = str(live_root)
    _write_yaml(releases_path, releases_doc)

    strict_errors = verify_cockpit_bootstrap(
        restore_root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )
    restore_errors = verify_cockpit_bootstrap(
        restore_root,
        include_git_status=False,
        run_deployed_menu_check=False,
        allow_relocated_restore=True,
    )

    assert any("missing T-052 cockpit deployment receipt" in error for error in strict_errors)
    assert restore_errors == []


def test_restore_drill_still_requires_t052_identity(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "restore-copy")
    releases_path = root / ".azoth" / "releases" / "applied.yaml"
    releases_doc = yaml.safe_load(releases_path.read_text(encoding="utf-8"))
    releases_doc["personal_deployments"][0]["deployment_id"] = "t-999-other"
    _write_yaml(releases_path, releases_doc)

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
        allow_relocated_restore=True,
    )

    assert any("missing T-052 cockpit deployment receipt" in error for error in errors)


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
    (
        root / ".azoth" / "projects" / "handoffs" / "t-055-first-use-ras-or-ray-2026-05-01.yaml"
    ).unlink()

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("missing T-055 first-use onboarding receipt" in error for error in errors)


def test_bootstrap_verify_requires_cockpit_command_wrappers(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    (root / ".agents" / "skills" / "azoth-cockpit" / "SKILL.md").unlink()

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("azoth-cockpit/SKILL.md: missing" in error for error in errors)


def test_bootstrap_verify_rejects_enabled_codex_hooks(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_text(root / ".codex" / "config.toml", "[features]\ncodex_hooks = true\n")

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("must keep codex_hooks disabled" in error for error in errors)


def test_bootstrap_verify_rejects_registered_prompt_hooks(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_text(
        root / ".codex" / "hooks.json",
        '{"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "true"}]}]}}\n',
    )

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any("must not register prompt hooks" in error for error in errors)


def test_bootstrap_verify_rejects_missing_root_only_hook_module(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_text(
        root / ".codex" / "hooks" / "user_prompt_submit_router.py",
        "from codex_control_plane import main\n",
    )

    errors = verify_cockpit_bootstrap(
        root,
        include_git_status=False,
        run_deployed_menu_check=False,
    )

    assert any(
        "references missing root-only module codex_control_plane.py" in error for error in errors
    )


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
