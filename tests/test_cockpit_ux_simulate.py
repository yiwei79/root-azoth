from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_ux_simulate import simulate_cockpit_ux  # noqa: E402
from test_cockpit_bootstrap_verify import _write_cockpit_bootstrap_fixture  # noqa: E402


def test_simulation_runs_all_cockpit_commands_without_writes(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")

    result = simulate_cockpit_ux(
        root,
        project_id="ras-or-ray",
        repo_root=ROOT,
        include_bootstrap_verify=False,
    )

    assert result.errors == []
    for heading in (
        "## Start cockpit",
        "## /cockpit",
        "## /cockpit-check",
        "## /cockpit-project ras-or-ray",
        "## /cockpit-daily",
        "## /cockpit-help",
        "## /cockpit-ux-simulate",
    ):
        assert heading in result.output
    assert "Release sync: OK" in result.output
    assert "ras-or-ray" in result.output
    assert "pointer_only" in result.output
    assert "Project-local context is authoritative" in result.output
    assert "$azoth-cockpit" in result.output
    assert "Build daily harness summary:" in result.output
    assert "$azoth-cockpit-daily" in result.output
    assert "personal_harness_daily_flow.py" in result.output
    assert '"ok": true' in result.output
    assert str(ROOT / "scripts" / "personal_harness_daily_flow.py") in result.output
    assert f"--repo-root {ROOT}" in result.output
    assert "--goal \"<today's intent>\"" in result.output
    assert "--summary" in result.output


def test_simulation_rejects_forbidden_context_leak(tmp_path: Path) -> None:
    root = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    onboarding = root / "docs" / "ONBOARDING.md"
    onboarding.write_text(
        onboarding.read_text(encoding="utf-8") + "\nsource_files\n",
        encoding="utf-8",
    )

    result = simulate_cockpit_ux(
        root,
        project_id="ras-or-ray",
        repo_root=ROOT,
        include_bootstrap_verify=False,
    )

    assert any("source_files" in error for error in result.errors)
