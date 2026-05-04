"""BL-082: consumer-safe Full release profile materialization."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import pytest

PRIVATE_RUNTIME_STATE = (
    ".azoth/scope-gate.json",
    ".azoth/pipeline-gate.json",
    ".azoth/run-ledger.local.yaml",
    ".azoth/autonomous-loop-state.local.yaml",
    ".azoth/final-delivery-approvals.jsonl",
)

REQUIRED_PROFILE_PATHS = (
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
    ".claude/commands/roadmap.md",
    ".azoth/roadmap.yaml",
    ".azoth/backlog.yaml",
    ".azoth/roadmap-specs/v0.2.0/README.md",
    ".azoth/initiative-banks/.gitkeep",
    ".azoth/design-banks/.gitkeep",
    ".azoth/autonomous-loop-state.local.yaml.example",
)

RUNTIME_IGNORE_ALLOWANCES = (
    "!.azoth/scope-gate.json.example",
    "!.azoth/pipeline-gate.json.example",
    "!.azoth/run-ledger.local.yaml.example",
    "!.azoth/autonomous-loop-state.local.yaml.example",
)


def _load_materializer() -> Callable[[Path, Path], None]:
    from scripts.azoth_release_profile import materialize_full_profile

    return materialize_full_profile


def _write(path: Path, text: str = "seed\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_release_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    template_root = source / "kernel" / "templates" / "release-profile" / "full"

    _write(source / "commands" / "start" / "command.yaml", "name: start\n")
    _write(
        source / "commands" / "roadmap" / "command.yaml",
        "name: roadmap\nbody:\n  source_path: .claude/commands/roadmap.md\n",
    )
    _write(source / "pipelines" / "full.pipeline.yaml", "name: full\n")
    _write(source / "scripts" / "codex_control_plane.py", "print('control plane')\n")
    _write(source / "scripts" / "roadmap_dashboard.py", "print('roadmap')\n")
    _write(source / "scripts" / "autonomous_loop.py", "print('loop')\n")
    _write(source / ".agents" / "skills" / "azoth-start" / "SKILL.md", "# azoth-start\n")
    _write(source / ".agents" / "skills" / "azoth-roadmap" / "SKILL.md", "# azoth-roadmap\n")
    _write(
        source / ".agents" / "skills" / "azoth-autonomous-auto" / "SKILL.md",
        "# azoth-autonomous-auto\n",
    )

    _write(
        template_root / ".azoth" / "roadmap.yaml",
        "roadmap_schema_version: 1\nproject: consumer-project\nitems: []\n",
    )
    _write(
        template_root / ".azoth" / "backlog.yaml",
        "backlog_schema_version: 1\nitems: []\n",
    )
    _write(
        template_root / ".azoth" / "roadmap-specs" / "v0.2.0" / "README.md",
        "# Consumer roadmap specs\n",
    )
    _write(template_root / ".azoth" / "initiative-banks" / ".gitkeep", "")
    _write(template_root / ".azoth" / "design-banks" / ".gitkeep", "")
    _write(
        template_root / ".azoth" / "autonomous-loop-state.local.yaml.example",
        "vision:\n  declaration: consumer project autonomy example\n",
    )

    _write(source / ".azoth" / "roadmap.yaml", "project: root-azoth-private\n")
    _write(source / ".azoth" / "backlog.yaml", "private: root backlog\n")
    for private_path in PRIVATE_RUNTIME_STATE:
        _write(source / private_path, "private: must-not-copy\n")

    return source


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _assert_runtime_state_gitignore(gitignore_text: str) -> None:
    lines = {
        line.strip()
        for line in gitignore_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for private_path in PRIVATE_RUNTIME_STATE:
        assert private_path in lines
        assert sum(1 for line in lines if line == private_path) == 1
    assert any(allowance in lines for allowance in RUNTIME_IGNORE_ALLOWANCES)


def test_materialize_full_profile_generates_consumer_safe_runtime_state(
    tmp_path: Path,
) -> None:
    materialize_full_profile = _load_materializer()
    source = _make_release_source(tmp_path)
    target = tmp_path / "target"
    _write(target / ".gitignore", "# consumer project\n.env\n")

    materialize_full_profile(source, target)

    for required_path in REQUIRED_PROFILE_PATHS:
        assert (target / required_path).exists(), required_path

    roadmap = (target / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    backlog = (target / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    command_body = (target / ".claude" / "commands" / "roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "consumer-project" in roadmap
    assert "root-azoth-private" not in roadmap
    assert "private: root backlog" not in backlog
    assert "commands/roadmap/command.yaml" in command_body

    for private_path in PRIVATE_RUNTIME_STATE:
        assert not (target / private_path).exists(), private_path

    gitignore_text = (target / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore_text
    _assert_runtime_state_gitignore(gitignore_text)

    first_snapshot = _snapshot(target)
    materialize_full_profile(source, target)
    assert _snapshot(target) == first_snapshot


def test_materialize_full_profile_errors_when_runtime_bundle_source_is_missing(
    tmp_path: Path,
) -> None:
    materialize_full_profile = _load_materializer()
    source = _make_release_source(tmp_path)
    shutil.rmtree(source / "commands")

    with pytest.raises((FileNotFoundError, RuntimeError, ValueError), match="commands|runtime"):
        materialize_full_profile(source, tmp_path / "target")
