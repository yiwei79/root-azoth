"""Tests for scripts/azoth_extract_product.py (P4-004 mechanical extraction)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "azoth_extract_product.py"


def test_expected_pipeline_constant_matches_sync_config() -> None:
    cfg = yaml.safe_load((REPO / "sync-config.yaml").read_text(encoding="utf-8"))
    pe = cfg["product_extraction"]
    assert tuple(pe["extraction_pipeline"]) == (
        "copy_tree_respecting_excludes",
        "apply_transforms",
        "apply_sanitize_strip_patterns",
    )


def test_path_is_excluded() -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("azoth_extract_product", SCRIPT)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    ex = [".azoth/", ".github/", "tests/"]
    assert mod.path_is_excluded(".azoth/backlog.yaml", ex)
    assert mod.path_is_excluded(".github/workflows/ci.yml", ex)
    assert mod.path_is_excluded("tests/foo.py", ex)
    assert not mod.path_is_excluded("skills/x/SKILL.md", ex)
    assert not mod.path_is_excluded("kernel/GOVERNANCE.md", ex)


def test_validate_only_ok() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--validate-only"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "validate-only: OK" in r.stdout


def test_extract_minimal_tree(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "sync-config.yaml").write_text(
        (REPO / "sync-config.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    shutil.copytree(REPO / "kernel" / "templates", src / "kernel" / "templates")
    (src / "skills").mkdir()
    (src / "skills" / "probe.md").write_text("x SupplyGrowth y\n", encoding="utf-8")
    (src / ".azoth").mkdir()
    (src / ".azoth" / "secret.yaml").write_text("nope", encoding="utf-8")
    (src / "tests").mkdir()
    (src / "tests" / "t.py").write_text("# t", encoding="utf-8")
    (src / "CLAUDE.md").write_text("# old", encoding="utf-8")
    (src / "azoth.yaml").write_text(
        "name: x\nscope:\n  mode: scaffold\n  is_development_workshop: true\n",
        encoding="utf-8",
    )

    out = tmp_path / "out"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(src),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout

    rels = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert not any(rp.startswith(".azoth/") for rp in rels)
    assert not any(rp.startswith("tests/") for rp in rels)
    assert "skills/probe.md" in rels

    probe = (out / "skills" / "probe.md").read_text(encoding="utf-8")
    assert "SupplyGrowth" not in probe
    assert "{{REDACTED}}" in probe

    az = yaml.safe_load((out / "azoth.yaml").read_text(encoding="utf-8"))
    assert az["scope"]["mode"] == "project"
    assert az["scope"]["is_development_workshop"] is False

    claude = (out / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{" not in claude
    assert "Azoth" in claude

    assert ".github/workflows/ci.yml" in rels
    assert "README.md" in rels


def test_bad_pipeline_rejected(tmp_path: Path) -> None:
    cfg_path = tmp_path / "sync-config.yaml"
    cfg_path.write_text(
        "sanitize:\n  strip_patterns: []\n"
        "product_extraction:\n"
        "  target_repo: z\n  mode: x\n"
        "  extraction_pipeline: [only_one]\n"
        "  exclude_paths: []\n"
        "  transform:\n"
        "    - source: CLAUDE.md\n"
        "      action: regenerate-from-template\n"
        "      template: kernel/templates/CLAUDE.md.template\n"
        "    - source: azoth.yaml\n"
        "      action: set-scope-mode\n"
        "      value: project\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(REPO),
            "--out",
            str(tmp_path / "o"),
            "--config",
            str(cfg_path),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "extraction_pipeline" in r.stderr
