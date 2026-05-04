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
