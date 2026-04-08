"""requirements-dev.txt must exist at repo root with expected dev dependencies (BL-019)."""

from __future__ import annotations

from pathlib import Path

AZOTH_ROOT = Path(__file__).resolve().parent.parent


def test_requirements_dev_txt_exists_nonempty_and_lists_core_dev_deps() -> None:
    path = AZOTH_ROOT / "requirements-dev.txt"
    assert path.is_file(), "requirements-dev.txt must exist at repository root"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), "requirements-dev.txt must be non-empty"
    lowered = text.lower()
    assert "rich" in lowered
    assert "pyyaml" in lowered
    assert "pytest" in lowered
    assert "ruff" in lowered
