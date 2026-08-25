"""Tests for the repeatable T-036 product release smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "product_release_smoke.py"
sys.path.insert(0, str(REPO / "scripts"))

import product_release_smoke  # noqa: E402

FULL_CONSUMER_RUNTIME_PATHS = (
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
    ".azoth/roadmap.yaml",
    ".azoth/backlog.yaml",
    ".azoth/roadmap-specs/v0.1.0/README.md",
    ".azoth/initiative-banks/.gitkeep",
    ".azoth/design-banks/.gitkeep",
    ".azoth/autonomous-loop-state.local.yaml.example",
)

PRIVATE_RUNTIME_STATE = (
    ".azoth/scope-gate.json",
    ".azoth/pipeline-gate.json",
    ".azoth/run-ledger.local.yaml",
    ".azoth/autonomous-loop-state.local.yaml",
    ".azoth/final-delivery-approvals.jsonl",
)


def _write(path: Path, text: str = "seed\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _consumer_path_from_stdout(stdout: str) -> Path:
    for line in stdout.splitlines():
        if line.startswith("consumer_bash: "):
            return Path(line.removeprefix("consumer_bash: ").strip())
    raise AssertionError(f"missing consumer_bash path in output:\n{stdout}")


def _write_minimal_consumer_install(root: Path, *, setup_level: str | None = None) -> None:
    required_paths = list(product_release_smoke.BASE_CONSUMER_PATHS)
    if setup_level in {"2", "3"}:
        required_paths.extend(product_release_smoke.STANDARD_CONSUMER_PATHS)
    for required_path in required_paths:
        path = root / required_path
        if path.suffix:
            _write(path, "seed\n")
        else:
            path.mkdir(parents=True, exist_ok=True)

    (root / "azoth.yaml").write_text(
        "name: azoth\nplatforms:\n  - copilot\n",
        encoding="utf-8",
    )


def _write_full_runtime_bundle(root: Path) -> None:
    for required_path in FULL_CONSUMER_RUNTIME_PATHS:
        _write(root / required_path, "seed\n")


def _assert_full_runtime_bundle(root: Path) -> None:
    missing = [path for path in FULL_CONSUMER_RUNTIME_PATHS if not (root / path).exists()]
    assert not missing, f"missing Full consumer runtime paths: {missing}"


def _assert_private_runtime_state_absent(root: Path) -> None:
    leaked = [path for path in PRIVATE_RUNTIME_STATE if (root / path).exists()]
    assert not leaked, f"private runtime state leaked into consumer install: {leaked}"


def test_product_release_smoke_checks_extract_without_install(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(tmp_path / "product"),
            "--skip-install",
            "--skip-ruff",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "product_release_smoke: OK" in result.stdout
    assert (tmp_path / "product" / "README.md").is_file()
    product_readme = (tmp_path / "product" / "README.md").read_text(encoding="utf-8")
    assert "AZOTH_PLATFORMS=copilot" in product_readme
    assert (tmp_path / "product" / ".github" / "workflows" / "ci.yml").is_file()
    assert (tmp_path / "product" / ".github" / "copilot-instructions.md").is_file()
    assert (tmp_path / "product" / ".github" / "prompts" / "auto.prompt.md").is_file()
    assert (tmp_path / "product" / ".github" / "agents" / "orchestrator.agent.md").is_file()
    builder_agent = tmp_path / "product" / ".github" / "agents" / "builder.agent.md"
    assert "tools:" in builder_agent.read_text(encoding="utf-8")
    assert not (tmp_path / "product" / ".azoth").exists()
    assert not (tmp_path / "product" / ".venv").exists()


@pytest.mark.parametrize("setup_level", ("1", "2"))
def test_product_release_smoke_validates_minimal_and_standard_installs(
    tmp_path: Path,
    setup_level: str,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(tmp_path / f"product-{setup_level}"),
            "--setup-level",
            setup_level,
            "--skip-ruff",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    consumer = _consumer_path_from_stdout(result.stdout)
    product_release_smoke.assert_consumer_install(consumer, setup_level=setup_level)
    if setup_level == "1":
        assert not (consumer / "skills").exists()
        assert not (consumer / "agents").exists()
    else:
        assert (consumer / "skills").is_dir()
        assert (consumer / "agents").is_dir()


def test_product_release_smoke_setup_level_3_materializes_full_runtime(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(tmp_path / "product"),
            "--setup-level",
            "3",
            "--skip-ruff",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    consumer = _consumer_path_from_stdout(result.stdout)
    _assert_full_runtime_bundle(consumer)
    _assert_private_runtime_state_absent(consumer)


def test_assert_consumer_install_rejects_private_runtime_state_leakage(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _write_minimal_consumer_install(consumer)
    _write_full_runtime_bundle(consumer)
    _write(consumer / ".azoth" / "scope-gate.json", "{}\n")

    with pytest.raises(product_release_smoke.SmokeError, match="scope-gate.json"):
        product_release_smoke.assert_consumer_install(consumer)


def test_assert_consumer_install_rejects_missing_installed_runtime_reference(
    tmp_path: Path,
) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _write_minimal_consumer_install(consumer, setup_level="3")
    _write_full_runtime_bundle(consumer)
    _write(consumer / ".gitignore", "\n".join(product_release_smoke.FULL_RUNTIME_GITIGNORE_RULES))
    _write(
        consumer / ".agents" / "skills" / "azoth-roadmap" / "SKILL.md",
        "Execution contract:\n- Read `.claude/commands/roadmap.md` before continuing.\n",
    )

    with pytest.raises(product_release_smoke.SmokeError, match="roadmap.md"):
        product_release_smoke.assert_consumer_install(consumer, setup_level="3")


def test_assert_sanitized_ignores_redaction_placeholder(tmp_path: Path) -> None:
    product = tmp_path / "product"
    product.mkdir()
    (product / "sync-config.yaml").write_text(
        "sanitize:\n  strip_patterns:\n    - '{{REDACTED}}'\n",
        encoding="utf-8",
    )

    product_release_smoke.assert_sanitized(product, ["{{REDACTED}}"])


def test_assert_sanitized_still_blocks_real_source_patterns(tmp_path: Path) -> None:
    product = tmp_path / "product"
    product.mkdir()
    (product / "README.md").write_text("contains source-org-token\n", encoding="utf-8")

    with pytest.raises(product_release_smoke.SmokeError, match="source-org-token"):
        product_release_smoke.assert_sanitized(product, ["{{REDACTED}}", "source-org-token"])
