from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_command_surface import (  # noqa: E402
    COCKPIT_COMMANDS,
    check_cockpit_command_docs,
    check_cockpit_command_surface,
    command_by_name,
    deploy_cockpit_command_surface,
    render_openai_metadata,
    render_skill,
)


def _write_minimal_docs(root: Path) -> None:
    command_lines = "\n".join(
        f"- `{command.display_name}` / `${command.skill_name}`" for command in COCKPIT_COMMANDS
    )
    text = f"""# Yiwei Azoth Cockpit

Start cockpit.

## Cockpit Command Surface

{command_lines}
"""
    for rel_path in ("docs/ONBOARDING.md", "AGENTS.md", "CLAUDE.md"):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_renders_all_minimal_cockpit_command_wrappers() -> None:
    expected = {
        "cockpit",
        "cockpit-check",
        "cockpit-project",
        "cockpit-help",
        "cockpit-ux-simulate",
    }

    assert {command.name for command in COCKPIT_COMMANDS} == expected
    for command in COCKPIT_COMMANDS:
        skill = render_skill(command)
        metadata = yaml.safe_load(render_openai_metadata(command))

        assert f"name: {command.skill_name}" in skill
        assert command.display_name in skill
        assert "safe-open cockpit command" in skill
        assert "must not write cockpit files" in skill
        assert metadata["interface"]["display_name"] == command.display_name
        assert metadata["interface"]["default_prompt"].startswith(f"${command.skill_name}")
        assert metadata["policy"]["allow_implicit_invocation"] is False


def test_deploy_and_check_command_surface(tmp_path: Path) -> None:
    _write_minimal_docs(tmp_path)

    assert deploy_cockpit_command_surface(tmp_path) == []
    assert check_cockpit_command_surface(tmp_path) == []

    for command in COCKPIT_COMMANDS:
        assert (tmp_path / command.skill_dir / "SKILL.md").is_file()
        assert (tmp_path / command.skill_dir / "agents" / "openai.yaml").is_file()


def test_check_fails_when_wrapper_missing(tmp_path: Path) -> None:
    _write_minimal_docs(tmp_path)
    deploy_cockpit_command_surface(tmp_path)
    missing = tmp_path / command_by_name("cockpit").skill_dir / "SKILL.md"  # type: ignore[union-attr]
    missing.unlink()

    errors = check_cockpit_command_surface(tmp_path)

    assert any("azoth-cockpit/SKILL.md: missing" in error for error in errors)


def test_check_docs_require_cockpit_command_surface(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ONBOARDING.md").write_text("Start cockpit.\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("Start cockpit.\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("Start cockpit.\n", encoding="utf-8")

    errors = check_cockpit_command_docs(tmp_path)

    assert any("docs/ONBOARDING.md" in error for error in errors)
    assert any("/cockpit" in error for error in errors)
