"""BL-082: consumer-safe Full release profile materialization."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import pytest
import yaml

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


def _load_readiness_compiler() -> Callable[[Path, Path], dict[str, object]]:
    from scripts.azoth_release_profile import compile_release_profile_readiness

    return compile_release_profile_readiness


def _load_release_profile_error() -> type[RuntimeError]:
    from scripts.azoth_release_profile import ReleaseProfileError

    return ReleaseProfileError


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


def _write_release_readiness_assets(source: Path) -> None:
    _write(source / "README.md", "# Azoth\n")
    _write(source / "azoth.yaml", "version: test\n")
    _write(source / "kernel" / "TRUST_CONTRACT.md", "# Trust\n")
    _write(source / "kernel" / "GOVERNANCE.md", "# Governance\n")
    _write(source / "docs" / "playbook" / "README.md", "# Playbook\n")
    _write(source / "agents" / "tier1-core" / "architect.agent.md", "# Architect\n")
    _write(source / ".codex" / "agents" / "architect.toml", "name = \"architect\"\n")
    _write(source / ".azoth" / "run-ledger.local.yaml.example", "schema_version: 1\n")
    _write(source / "pipelines" / "stage-summary.schema.yaml", "type: object\n")
    _write(source / "scripts" / "planning_bank_validate.py", "print('validate')\n")


def _write_project_local_receipt(source: Path, **overrides: object) -> None:
    handoff_ref = ".azoth/handoffs/project-local-mode.yaml"
    receipt: dict[str, object] = {
        "schema_version": 1,
        "artifact_type": "project_local_mode_receipt",
        "project_id": "consumer-project",
        "repo_path": str(source),
        "receipt_owner": "project_local",
        "selected_mode": "managed",
        "release_profile_ref": "full@v0.2.0",
        "readiness_state": "ready",
        "freshness_status": "current",
        "installed_asset_classes": [
            "roadmap seed",
            "backlog seed",
            "planning-bank seed",
            "validation helpers",
            "project-local receipt",
        ],
        "missing_asset_classes": [],
        "approval_scope": "managed_mode_project_local_gate",
        "active_write_claim": False,
        "next_safe_action": "hydrate planning state under the project-local managed-mode gate",
        "stop_reason": "none",
        "handoff_receipt_ref": handoff_ref,
    }
    receipt.update(overrides)
    _write(source / handoff_ref, "receipt: linked\n")
    _write(
        source / ".azoth" / "project-local-mode-receipt.yaml",
        yaml.safe_dump(receipt, sort_keys=False),
    )


def _write_mode_matrix(tmp_path: Path) -> Path:
    path = tmp_path / "mode-matrix.yaml"
    _write(
        path,
        """\
schema_version: 1
mode_matrix:
  guide:
    installed_asset_classes:
      - trust and governance reading surface
      - orientation or first prompt guidance
      - starter documentation/playbook
    explicit_exclusions:
      - agents
      - project-management state
    next_safe_action: read orientation
  assisted:
    installed_asset_classes:
      - skills
      - tier-1 agents or generated equivalents
      - command wrappers
      - runtime helper references
      - starter receipts
    explicit_exclusions:
      - roadmap hydration
      - no-human-gate autonomy
    next_safe_action: run read-only assisted checks
  managed:
    installed_asset_classes:
      - roadmap seed
      - backlog seed
      - planning-bank seed
      - validation helpers
      - project-local receipt
    explicit_exclusions:
      - branch-local no-human-gate autonomy
      - hidden hydration
    next_safe_action: hydrate or repair project-local planning state under a fresh gate
  governed_autonomy:
    installed_asset_classes:
      - run ledger
      - loop-state examples
      - stage-evidence requirements
      - stop-condition contract
      - bounded replay budget
    explicit_exclusions:
      - root self-development authority leaking into consumer projects
      - open-ended loops
    next_safe_action: open a bounded governed-autonomy campaign only with fresh authority
first_use_evidence_map:
  release_profile:
    pass_signal: profile and smoke evidence agree for the selected mode
""",
    )
    return path


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
    command_body = (target / ".claude" / "commands" / "roadmap.md").read_text(encoding="utf-8")
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


def test_compile_release_profile_readiness_reports_truthful_mode_states(
    tmp_path: Path,
) -> None:
    compile_readiness = _load_readiness_compiler()
    source = _make_release_source(tmp_path)
    _write_release_readiness_assets(source)

    report = compile_readiness(source, _write_mode_matrix(tmp_path))

    assert report["schema_version"] == 1
    modes = report["modes"]
    assert set(modes) == {"guide", "assisted", "managed", "governed_autonomy"}

    guide = modes["guide"]
    assert guide["readiness_state"] == "ready"
    assert guide["missing_asset_classes"] == []
    assert "trust and governance reading surface" in guide["installed_asset_classes"]
    assert guide["explicit_exclusions"] == ["agents", "project-management state"]
    assert guide["next_safe_action"] == "read orientation"

    managed = modes["managed"]
    assert managed["readiness_state"] == "requires_authority"
    assert managed["authority_required"] is True
    assert "project-local receipt" in managed["missing_asset_classes"]
    assert "project-local approval" in " ".join(managed["authority_notes"])

    governed = modes["governed_autonomy"]
    assert governed["readiness_state"] == "requires_authority"
    assert governed["authority_required"] is True
    assert "fresh autonomy budget" in " ".join(governed["authority_notes"])


def test_compile_release_profile_readiness_accepts_valid_project_local_receipt(
    tmp_path: Path,
) -> None:
    compile_readiness = _load_readiness_compiler()
    source = _make_release_source(tmp_path)
    _write_release_readiness_assets(source)
    _write_project_local_receipt(source)

    report = compile_readiness(source, _write_mode_matrix(tmp_path))

    managed = report["modes"]["managed"]
    assert managed["readiness_state"] == "requires_authority"
    assert managed["authority_required"] is True
    assert "project-local receipt" not in managed["missing_asset_classes"]
    assert managed["blocking_missing_asset_classes"] == []
    assert managed["unsafe_claims"] == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"receipt_owner": "root_azoth"}, "receipt_owner must be project_local"),
        ({"freshness_status": "stale"}, "freshness_status must be current"),
        ({"approval_scope": "pointer_only_handoff"}, "approval_scope must authorize managed"),
        (
            {"selected_mode": "assisted", "approval_scope": "pointer_only_handoff"},
            "selected_mode assisted must match expected mode managed",
        ),
        (
            {"handoff_receipt_ref": ".azoth/handoffs/missing.yaml"},
            "handoff_receipt_ref must resolve to an existing file",
        ),
    ],
)
def test_compile_release_profile_readiness_fails_closed_for_unsafe_project_local_receipt(
    tmp_path: Path, overrides: dict[str, object], expected: str
) -> None:
    compile_readiness = _load_readiness_compiler()
    source = _make_release_source(tmp_path)
    _write_release_readiness_assets(source)
    _write_project_local_receipt(source, **overrides)

    report = compile_readiness(source, _write_mode_matrix(tmp_path))

    managed = report["modes"]["managed"]
    assert "project-local receipt" in managed["missing_asset_classes"]
    assert any(expected in claim for claim in managed["unsafe_claims"])


def test_compile_release_profile_readiness_blocks_missing_mode_assets(
    tmp_path: Path,
) -> None:
    compile_readiness = _load_readiness_compiler()
    source = _make_release_source(tmp_path)
    _write_release_readiness_assets(source)
    shutil.rmtree(source / "commands" / "start")
    shutil.rmtree(source / ".agents" / "skills" / "azoth-start")

    report = compile_readiness(source, _write_mode_matrix(tmp_path))

    guide = report["modes"]["guide"]
    assert guide["readiness_state"] == "blocked"
    assert "orientation or first prompt guidance" in guide["missing_asset_classes"]


def test_compile_release_profile_readiness_fails_closed_for_malformed_matrix(
    tmp_path: Path,
) -> None:
    compile_readiness = _load_readiness_compiler()
    release_error = _load_release_profile_error()
    source = _make_release_source(tmp_path)
    matrix = tmp_path / "malformed-mode-matrix.yaml"
    _write(matrix, "mode_matrix:\n  guide:\n    installed_asset_classes: []\n")

    with pytest.raises(release_error, match="mode_matrix.*assisted"):
        compile_readiness(source, matrix)


def test_compile_release_profile_readiness_wraps_yaml_parse_errors(
    tmp_path: Path,
) -> None:
    compile_readiness = _load_readiness_compiler()
    release_error = _load_release_profile_error()
    source = _make_release_source(tmp_path)
    matrix = tmp_path / "syntax-error-mode-matrix.yaml"
    _write(matrix, "mode_matrix:\n  guide: [unterminated\n")

    with pytest.raises(release_error, match="failed to parse mode matrix"):
        compile_readiness(source, matrix)
