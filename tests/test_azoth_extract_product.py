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


def test_copy_tree_always_skips_dot_git(tmp_path: Path) -> None:
    """Never copy .git/ even when exclude_paths omits it (defense-in-depth)."""
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("azoth_extract_product", SCRIPT)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    src = tmp_path / "src"
    src.mkdir()
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (src / "visible.txt").write_text("ok\n", encoding="utf-8")

    dest = tmp_path / "dest"
    dest.mkdir()
    n = mod.copy_tree_respecting_excludes(src, dest, exclude_paths=[], dry_run=False)
    assert n == 1
    assert (dest / "visible.txt").is_file()
    assert not (dest / ".git").exists()


def test_copy_tree_always_skips_local_runtime_artifacts(tmp_path: Path) -> None:
    """Ignored workstation artifacts must never leak into a public product extract."""
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("azoth_extract_product", SCRIPT)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    src = tmp_path / "src"
    src.mkdir()
    (src / "visible.txt").write_text("ok\n", encoding="utf-8")
    (src / ".DS_Store").write_text("finder\n", encoding="utf-8")
    (src / ".venv" / "bin").mkdir(parents=True)
    (src / ".venv" / "bin" / "python").write_text("binary-ish\n", encoding="utf-8")
    (src / ".pytest_cache").mkdir()
    (src / ".pytest_cache" / "lastfailed").write_text("{}\n", encoding="utf-8")
    (src / ".ruff_cache" / "0.15").mkdir(parents=True)
    (src / ".ruff_cache" / "0.15" / "cache").write_text("x\n", encoding="utf-8")
    (src / "pkg" / "__pycache__").mkdir(parents=True)
    (src / "pkg" / "__pycache__" / "mod.cpython-313.pyc").write_bytes(b"pyc")
    (src / "nested").mkdir()
    (src / "nested" / ".DS_Store").write_text("finder\n", encoding="utf-8")
    (src / ".claude" / "worktrees" / "local").mkdir(parents=True)
    (src / ".claude" / "worktrees" / "local" / "state.json").write_text("{}", encoding="utf-8")

    dest = tmp_path / "dest"
    dest.mkdir()
    n = mod.copy_tree_respecting_excludes(src, dest, exclude_paths=[], dry_run=False)
    assert n == 1
    assert (dest / "visible.txt").is_file()
    assert not (dest / ".DS_Store").exists()
    assert not (dest / ".venv").exists()
    assert not (dest / ".pytest_cache").exists()
    assert not (dest / ".ruff_cache").exists()
    assert not (dest / "pkg").exists()
    assert not (dest / "nested" / ".DS_Store").exists()
    assert not (dest / ".claude" / "worktrees").exists()


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
    (src / ".claude" / "hooks").mkdir(parents=True)
    (src / ".claude" / "hooks" / "secret_hook.py").write_text("print('nope')\n", encoding="utf-8")
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (src / "research_antigravity_parity").mkdir()
    (src / "research_antigravity_parity" / "notes.md").write_text(
        "internal research\n", encoding="utf-8"
    )
    (src / "tests").mkdir()
    (src / "tests" / "t.py").write_text("# t", encoding="utf-8")
    (src / "LICENSE").write_text("PolyForm Noncommercial 1.0.0\n", encoding="utf-8")
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
    assert not any(rp.startswith(".claude/hooks/") for rp in rels)
    assert not any(rp.startswith(".git/") for rp in rels)
    assert not any(rp.startswith("research_antigravity_parity/") for rp in rels)
    assert not any(rp.startswith("tests/") for rp in rels)
    assert "LICENSE" in rels
    assert "skills/probe.md" in rels
    assert "kernel/templates/CLAUDE.md.template" in rels

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


def test_extract_removes_pre_existing_out_directory(tmp_path: Path) -> None:
    """--out must be wiped before extract so stale files cannot survive."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "sync-config.yaml").write_text(
        (REPO / "sync-config.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    shutil.copytree(REPO / "kernel" / "templates", src / "kernel" / "templates")
    (src / "skills").mkdir()
    (src / "skills" / "probe.md").write_text("plain\n", encoding="utf-8")
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
    out.mkdir(parents=True)
    (out / "STALE_PRE_EXISTING.txt").write_text("must be removed\n", encoding="utf-8")
    nested = out / "old_nested"
    nested.mkdir()
    (nested / "junk").write_text("x", encoding="utf-8")

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
    assert not (out / "STALE_PRE_EXISTING.txt").exists()
    assert not (out / "old_nested").exists()
    assert (out / "skills" / "probe.md").is_file()
    assert (out / "README.md").is_file()


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


def test_dry_run_banner_states_step1_only(tmp_path: Path) -> None:
    """BL-032: --dry-run output must clearly state it only runs step 1."""
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--source",
            str(REPO),
            "--out",
            str(tmp_path / "unused"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "step 1 only" in r.stdout
    assert "done (dry-run)" in r.stdout


def test_azoth_version_coupled_to_azoth_yaml() -> None:
    """BL-033: AZOTH_VERSION used in extract must match azoth.yaml version."""
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("azoth_extract_product", SCRIPT)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    live_version = mod._read_azoth_version(REPO)
    azoth_data = yaml.safe_load((REPO / "azoth.yaml").read_text(encoding="utf-8"))
    assert live_version == str(azoth_data["version"])
