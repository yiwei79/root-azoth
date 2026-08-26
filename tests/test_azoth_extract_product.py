"""Tests for scripts/azoth_extract_product.py (P4-004 mechanical extraction)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "azoth_extract_product.py"
SYNC_CONFIG = yaml.safe_load((REPO / "sync-config.yaml").read_text(encoding="utf-8"))
PRODUCT_EXTRACTION = SYNC_CONFIG["product_extraction"]
PUBLIC_VERSION = PRODUCT_EXTRACTION["public_version"]
PUBLIC_TEST_PATHS = tuple(PRODUCT_EXTRACTION["public_test_paths"])


def _write_public_test_fixtures(source: Path) -> None:
    for rel_path in PUBLIC_TEST_PATHS:
        target = source / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_public_fixture():\n    assert True\n", encoding="utf-8")


def _commit_fixture_repo(source: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Azoth Test",
            "-c",
            "user.email=azoth-test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=source,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_extract_fixture(source: Path) -> str:
    source.mkdir()
    (source / "sync-config.yaml").write_text(
        (REPO / "sync-config.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    shutil.copytree(REPO / "kernel" / "templates", source / "kernel" / "templates")
    (source / "skills").mkdir()
    for name in ("probe.md", "staged.md", "unstaged.md"):
        (source / "skills" / name).write_text(f"committed {name}\n", encoding="utf-8")
    (source / ".gitignore").write_text("skills/ignored.md\n", encoding="utf-8")
    _write_public_test_fixtures(source)
    (source / "LICENSE").write_text("PolyForm Noncommercial 1.0.0\n", encoding="utf-8")
    (source / "CLAUDE.md").write_text("# old\n", encoding="utf-8")
    (source / "azoth.yaml").write_text(
        "name: root-azoth\nversion: 0.2.1.9\nscope:\n  mode: scaffold\n"
        "  is_development_workshop: true\n",
        encoding="utf-8",
    )
    return _commit_fixture_repo(source)


def _load_extractor():
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("azoth_extract_product", SCRIPT)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    (src / "research_antigravity_parity").mkdir()
    (src / "research_antigravity_parity" / "notes.md").write_text(
        "internal research\n", encoding="utf-8"
    )
    (src / "tests").mkdir()
    (src / "tests" / "t.py").write_text("# t", encoding="utf-8")
    _write_public_test_fixtures(src)
    (src / "LICENSE").write_text("PolyForm Noncommercial 1.0.0\n", encoding="utf-8")
    (src / "CLAUDE.md").write_text("# old", encoding="utf-8")
    (src / "azoth.yaml").write_text(
        "name: root-azoth\nversion: 0.2.1.7\nscope:\n  mode: scaffold\n"
        "  is_development_workshop: true\n",
        encoding="utf-8",
    )
    source_revision = _commit_fixture_repo(src)

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
    assert "tests/t.py" not in rels
    assert set(PUBLIC_TEST_PATHS).issubset(rels)
    assert "LICENSE" in rels
    assert "skills/probe.md" in rels
    assert "kernel/templates/CLAUDE.md.template" in rels

    probe = (out / "skills" / "probe.md").read_text(encoding="utf-8")
    assert "SupplyGrowth" not in probe
    assert "source operations framework" in probe

    az = yaml.safe_load((out / "azoth.yaml").read_text(encoding="utf-8"))
    assert az["name"] == "azoth"
    assert az["version"] == PUBLIC_VERSION
    assert az["release_channel"] == "preview"
    assert az["scope"]["mode"] == "product"
    assert az["scope"]["is_development_workshop"] is False
    assert az["provenance"]["source_revision"] == source_revision
    assert "milestone" not in az

    claude = (out / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{" not in claude
    assert "Azoth" in claude

    assert ".github/workflows/ci.yml" in rels
    assert "README.md" in rels
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert f"`v{PUBLIC_VERSION}`" in readme
    assert "{{PUBLIC_VERSION}}" not in readme
    validator = (out / "scripts" / "validate_public_product.py").read_text(encoding="utf-8")
    assert f'EXPECTED_VERSION = "{PUBLIC_VERSION}"' in validator
    assert 'Path(f"release-notes/v{EXPECTED_VERSION}.md")' in validator


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
    _write_public_test_fixtures(src)
    (src / "CLAUDE.md").write_text("# old", encoding="utf-8")
    (src / "azoth.yaml").write_text(
        "name: root-azoth\nversion: 0.2.1.8\nscope:\n  mode: scaffold\n"
        "  is_development_workshop: true\n",
        encoding="utf-8",
    )
    _commit_fixture_repo(src)

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
    src = tmp_path / "src"
    src.mkdir()
    cfg_path = src / "configs" / "bad-sync-config.yaml"
    cfg_path.parent.mkdir()
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
    _commit_fixture_repo(src)
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(src),
            "--out",
            str(tmp_path / "o"),
            "--config",
            "configs/bad-sync-config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "extraction_pipeline" in r.stderr


def test_external_config_override_is_rejected(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _write_extract_fixture(src)
    external = tmp_path / "external.yaml"
    external.write_text("product_extraction: {}\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(src),
            "--out",
            str(tmp_path / "out"),
            "--config",
            str(external),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stderr.strip() == "--config must identify a path inside --source"


def test_extract_ignores_all_live_and_index_only_states(tmp_path: Path) -> None:
    src = tmp_path / "src"
    source_revision = _write_extract_fixture(src)
    (src / "sync-config.yaml").write_text("product_extraction: staged-only\n", encoding="utf-8")
    (src / "skills" / "staged.md").write_text("staged-only\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "sync-config.yaml", "skills/staged.md"],
        cwd=src,
        check=True,
    )
    (src / "skills" / "unstaged.md").write_text("unstaged-only\n", encoding="utf-8")
    (src / "skills" / "untracked.md").write_text("untracked-only\n", encoding="utf-8")
    (src / "skills" / "ignored.md").write_text("ignored-only\n", encoding="utf-8")
    readme_template = src / "kernel" / "templates" / "README.public.azoth.md"
    readme_template.write_text("WORKTREE_ONLY_TEMPLATE\n", encoding="utf-8")

    dry_dest = tmp_path / "dry-out"
    dry_run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(src),
            "--out",
            str(dry_dest),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    assert dry_run.returncode == 0, dry_run.stderr + dry_run.stdout
    assert "skills/staged.md" in dry_run.stdout
    assert "skills/untracked.md" not in dry_run.stdout
    assert "skills/ignored.md" not in dry_run.stdout
    assert not dry_dest.exists()

    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(src), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (out / "skills" / "staged.md").read_text(encoding="utf-8") == ("committed staged.md\n")
    assert (out / "skills" / "unstaged.md").read_text(encoding="utf-8") == (
        "committed unstaged.md\n"
    )
    assert not (out / "skills" / "untracked.md").exists()
    assert not (out / "skills" / "ignored.md").exists()
    assert "WORKTREE_ONLY_TEMPLATE" not in (out / "README.md").read_text(encoding="utf-8")
    manifest = yaml.safe_load((out / "azoth.yaml").read_text(encoding="utf-8"))
    assert manifest["provenance"]["source_revision"] == source_revision


def test_resolved_sha_survives_concurrent_worktree_change(tmp_path: Path, monkeypatch) -> None:
    mod = _load_extractor()
    src = tmp_path / "src"
    source_revision = _write_extract_fixture(src)
    original_source_revision = mod._source_revision

    def resolve_then_mutate(source_root: Path) -> str:
        resolved = original_source_revision(source_root)
        (src / "skills" / "probe.md").write_text("concurrent live mutation\n", encoding="utf-8")
        (src / "kernel" / "templates" / "README.public.azoth.md").write_text(
            "CONCURRENT_TEMPLATE\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", "skills/probe.md", "kernel/templates/README.public.azoth.md"],
            cwd=src,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Azoth Test",
                "-c",
                "user.email=azoth-test@example.invalid",
                "commit",
                "-qm",
                "concurrent head advance",
            ],
            cwd=src,
            check=True,
        )
        return resolved

    monkeypatch.setattr(mod, "_source_revision", resolve_then_mutate)
    out = tmp_path / "out"

    assert (
        mod.extract_product(
            source=src,
            dest=out,
            config_path=Path("sync-config.yaml"),
            dry_run=False,
        )
        == 0
    )
    assert (out / "skills" / "probe.md").read_text(encoding="utf-8") == "committed probe.md\n"
    assert "CONCURRENT_TEMPLATE" not in (out / "README.md").read_text(encoding="utf-8")
    manifest = yaml.safe_load((out / "azoth.yaml").read_text(encoding="utf-8"))
    assert manifest["provenance"]["source_revision"] == source_revision


@pytest.mark.parametrize("path", ["../escape", "/absolute", "safe/../../escape", "safe\\escape"])
def test_archive_member_path_rejects_traversal_and_platform_aliases(path: str) -> None:
    mod = _load_extractor()

    with pytest.raises(RuntimeError):
        mod._archive_member_path(path)


def test_committed_symlink_is_never_materialized_or_followed(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _write_extract_fixture(src)
    outside = tmp_path / "private.txt"
    outside.write_text("must never be read\n", encoding="utf-8")
    (src / "skills" / "escape.md").symlink_to(outside)
    subprocess.run(["git", "add", "skills/escape.md"], cwd=src, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Azoth Test",
            "-c",
            "user.email=azoth-test@example.invalid",
            "commit",
            "-qm",
            "add symlink",
        ],
        cwd=src,
        check=True,
    )
    out = tmp_path / "out"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(src), "--out", str(out)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stderr.strip() == "Git archive contains unsupported link entry: skills/escape.md"
    assert not out.exists()


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
