#!/usr/bin/env python3
"""
Extract the public `azoth` product tree from root-azoth per `sync-config.yaml`
`product_extraction` (D38 / P4-004).

Pipeline (mandatory order — must not skip steps):
  1. copy_tree_respecting_excludes
  2. apply_transforms
  3. apply_sanitize_strip_patterns

Then emits public CI + README from kernel templates (same contract as sync-config comments).

If ``--out`` already exists, it is removed with ``shutil.rmtree`` before writing — never
use a live git clone as ``--out``; extract to staging and copy/rsync into the target.

Not azoth-sync.py (Tier 1→2 only).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

import yaml

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_PIPELINE: tuple[str, ...] = (
    "copy_tree_respecting_excludes",
    "apply_transforms",
    "apply_sanitize_strip_patterns",
)

TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".toml"}

ALWAYS_EXCLUDE_PARTS = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
ALWAYS_EXCLUDE_FILE_SUFFIXES = (".pyc", ".pyo")
ALWAYS_EXCLUDE_PREFIXES = (".claude/worktrees/",)

PUBLIC_CI_TEMPLATE = Path("kernel/templates/github/workflows/ci-public-azoth.yml")
PUBLIC_README_TEMPLATE = Path("kernel/templates/README.public.azoth.md")
PUBLIC_SCRIPT_TEMPLATES = (
    Path("kernel/templates/public-scripts/personal_knowledge_recall.py"),
    Path("kernel/templates/public-scripts/personal_knowledge_review.py"),
    Path("kernel/templates/public-scripts/validate_public_product.py"),
)

DEFAULT_CLAUDE_SUBSTITUTIONS: dict[str, str] = {
    "PROJECT_NAME": "Azoth",
    "GITHUB_USER": "your-org",
    "LANGUAGE": "Python",
    "DESCRIPTION": "An inspectable toolkit for governed AI-assisted software delivery.",
    "SOURCE_DIR": "src",
    "TEST_DIR": "tests",
    "FORMATTER": "ruff format + ruff check",
    "TEST_FRAMEWORK": "pytest",
    "AZOTH_VERSION": "0.1.0",  # fallback; overridden at extract time by _read_azoth_version
    "INSTALLED_SKILLS": "see skills/",
    "INSTALLED_AGENTS": "see agents/",
    "INSTALLED_PIPELINES": "see pipelines/",
}


def _read_azoth_version(source_root: Path) -> str:
    """Read the version field from azoth.yaml in the source tree."""
    azoth_path = source_root / "azoth.yaml"
    if not azoth_path.is_file():
        return DEFAULT_CLAUDE_SUBSTITUTIONS["AZOTH_VERSION"]
    data = yaml.safe_load(azoth_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "version" in data:
        return str(data["version"])
    return DEFAULT_CLAUDE_SUBSTITUTIONS["AZOTH_VERSION"]


def _build_claude_substitutions(
    source_root: Path,
    public_version: str | None = None,
) -> dict[str, str]:
    """Build CLAUDE.md substitutions for the public product identity."""
    subs = dict(DEFAULT_CLAUDE_SUBSTITUTIONS)
    subs["AZOTH_VERSION"] = public_version or _read_azoth_version(source_root)
    return subs


README_SUBSTITUTIONS: dict[str, str] = {
    "PRODUCT_NAME": "Azoth",
    "DESCRIPTION": "Portable agentic toolkit: skills, agents, pipelines, and governance patterns.",
}


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body text."""
    if not text.startswith("---"):
        return {}, text
    try:
        end = text.index("\n---", 3)
    except ValueError:
        return {}, text
    meta = yaml.safe_load(text[3:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return meta, body


def render_frontmatter(data: dict[str, Any]) -> str:
    return (
        "---\n"
        + yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        + "---\n\n"
    )


def _description(meta: dict[str, Any]) -> str:
    return str(meta.get("description") or meta.get("role") or meta.get("name") or "")


def transform_agent_copilot(agent_path: Path) -> tuple[str, str]:
    meta, body = parse_frontmatter(agent_path.read_text(encoding="utf-8"))
    name = str(meta.get("name") or agent_path.stem.removesuffix(".agent"))
    frontmatter: dict[str, Any] = {"name": name, "description": _description(meta)}
    if tools := meta.get("tools"):
        frontmatter["tools"] = tools
    if "model" in meta:
        frontmatter["model"] = meta["model"]
    return name, render_frontmatter(frontmatter) + body


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        _die(f"config not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _die("sync-config root must be a mapping")
    return data


def _validated_repo_path(
    value: str,
    *,
    label: str,
    allow_git_metadata: bool = False,
) -> str:
    """Return a normalized repository-relative POSIX path or fail closed."""
    raw = value.strip().replace("\\", "/")
    if not raw or raw.startswith("/"):
        raise RuntimeError(f"{label} must be a non-empty repository-relative path")
    normalized = raw.rstrip("/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError(f"{label} must not contain absolute or traversal components")
    if path.parts[0] == ".git" and not allow_git_metadata:
        raise RuntimeError(f"{label} must not address Git metadata")
    return path.as_posix()


def _config_repo_path(source_root: Path, config_path: Path) -> Path:
    """Map a caller-supplied config path to the same logical path in a snapshot."""
    candidate = config_path if config_path.is_absolute() else source_root / config_path
    # abspath is intentionally lexical: following a worktree symlink here would let
    # an external live file choose which committed path is read later.
    candidate = Path(os.path.abspath(candidate))
    try:
        rel = candidate.relative_to(source_root)
    except ValueError as exc:
        raise RuntimeError("--config must identify a path inside --source") from exc
    return Path(_validated_repo_path(rel.as_posix(), label="--config"))


def _source_revision(source_root: Path) -> str:
    """Resolve one immutable commit and require ``source_root`` to be its Git root."""
    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=source_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if top_level.returncode != 0:
        detail = (top_level.stderr or top_level.stdout or "Git repository unavailable").strip()
        raise RuntimeError(f"public extraction requires a Git repository: {detail}")
    if Path(top_level.stdout.strip()).resolve() != source_root:
        raise RuntimeError("--source must be the Git repository root")

    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=source_root,
        text=True,
        capture_output=True,
        check=False,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or not re_full_sha(revision):
        detail = (result.stderr or result.stdout or "Git revision unavailable").strip()
        raise RuntimeError(f"public extraction requires an exact source commit SHA: {detail}")
    return revision


def _archive_member_path(name: str) -> Path:
    """Validate a Git archive member before it is materialized."""
    raw = name.rstrip("/")
    if not raw or "\\" in raw:
        raise RuntimeError("Git archive contains an unsafe empty or backslash path")
    normalized = _validated_repo_path(raw, label="Git archive member")
    return Path(*PurePosixPath(normalized).parts)


def _materialize_commit(source_root: Path, revision: str, snapshot_root: Path) -> None:
    """Materialize regular files from one commit without using tar extraction APIs."""
    process = subprocess.Popen(
        ["git", "archive", "--format=tar", revision],
        cwd=source_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    seen: set[str] = set()
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                rel = _archive_member_path(member.name)
                rel_posix = rel.as_posix()
                if rel_posix in seen:
                    raise RuntimeError(f"Git archive contains duplicate path: {rel_posix}")
                seen.add(rel_posix)
                if member.isdir():
                    continue
                if member.issym() or member.islnk():
                    raise RuntimeError(f"Git archive contains unsupported link entry: {rel_posix}")
                if not member.isfile():
                    raise RuntimeError(
                        f"Git archive contains unsupported special entry: {rel_posix}"
                    )
                target = snapshot_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                source_file = archive.extractfile(member)
                if source_file is None:
                    raise RuntimeError(f"Git archive member has no blob content: {rel_posix}")
                with source_file, target.open("xb") as output_file:
                    shutil.copyfileobj(source_file, output_file)
                target.chmod(member.mode & 0o777)
    except Exception:
        process.kill()
        process.wait()
        raise
    finally:
        process.stdout.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
    returncode = process.wait()
    process.stderr.close()
    if returncode != 0:
        raise RuntimeError(f"could not materialize committed source snapshot: {stderr}")


@contextmanager
def _committed_snapshot(source_root: Path, revision: str) -> Iterator[Path]:
    """Yield a temporary tree containing only blobs from ``revision``."""
    with tempfile.TemporaryDirectory(prefix="azoth-public-snapshot-") as temp_dir:
        snapshot_root = Path(temp_dir) / "tree"
        snapshot_root.mkdir()
        _materialize_commit(source_root, revision, snapshot_root)
        yield snapshot_root


def get_product_extraction(cfg: dict[str, Any]) -> dict[str, Any]:
    pe = cfg.get("product_extraction")
    if not isinstance(pe, dict):
        _die("sync-config missing product_extraction mapping")
    return pe


def validate_pipeline(pe: dict[str, Any]) -> None:
    pipe = pe.get("extraction_pipeline")
    if not isinstance(pipe, list):
        _die("product_extraction.extraction_pipeline must be a list")
    got = tuple(str(x) for x in pipe)
    if got != EXPECTED_PIPELINE:
        _die(f"extraction_pipeline must be exactly {EXPECTED_PIPELINE!r}, got {got!r}")


def path_is_excluded(rel_posix: str, exclude_paths: list[str]) -> bool:
    """True if rel path (posix, relative to source root) matches any exclude prefix."""
    parts = set(rel_posix.split("/"))
    if parts & ALWAYS_EXCLUDE_PARTS:
        return True
    if rel_posix.endswith(ALWAYS_EXCLUDE_FILE_SUFFIXES):
        return True
    if any(
        rel_posix == raw.rstrip("/") or rel_posix.startswith(raw) for raw in ALWAYS_EXCLUDE_PREFIXES
    ):
        return True
    for raw in exclude_paths:
        pat = raw.replace("\\", "/").rstrip("/")
        if rel_posix == pat or rel_posix.startswith(pat + "/"):
            return True
    return False


def path_is_included(rel_posix: str, include_paths: list[str] | None) -> bool:
    """Return true when a path is inside the explicit public extraction surface."""
    if include_paths is None:
        return True
    for raw in include_paths:
        pattern = raw.replace("\\", "/").rstrip("/")
        if rel_posix == pattern or rel_posix.startswith(pattern + "/"):
            return True
    return False


def sanitize_content(
    content: str,
    strip_patterns: list[str],
    rewrite_patterns: dict[str, str] | None = None,
) -> str:
    """Same substitution contract as scripts/azoth-sync.py sanitize_content."""
    for source, replacement in (rewrite_patterns or {}).items():
        content = content.replace(source, replacement)
    for pattern in strip_patterns:
        content = content.replace(pattern, "{{REDACTED}}")
    return content


def _read_utf8_text(path: Path) -> str | None:
    """Read a public-tree file only when it is ordinary UTF-8 text."""
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def copy_tree_respecting_excludes(
    source: Path,
    dest: Path,
    exclude_paths: list[str],
    include_paths: list[str] | None = None,
    *,
    dry_run: bool,
) -> int:
    copied = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        # Defense-in-depth: never copy VCS metadata even if exclude_paths is misconfigured.
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if not path_is_included(rel, include_paths):
            continue
        if path_is_excluded(rel, exclude_paths):
            continue
        target = dest / path.relative_to(source)
        if dry_run:
            print(f"  [dry-run] copy {rel} -> {target.relative_to(dest)}")
            copied += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def apply_regenerate_claude(
    source_root: Path,
    dest_root: Path,
    template_rel: str,
    subs: dict[str, str],
    *,
    dry_run: bool,
) -> None:
    tpl_path = source_root / template_rel
    if not tpl_path.is_file():
        raise RuntimeError(f"CLAUDE template missing: {tpl_path}")
    text = tpl_path.read_text(encoding="utf-8")
    for key, val in subs.items():
        text = text.replace("{{" + key + "}}", val)
    if "{{" in text and "}}" in text:
        raise RuntimeError(
            "CLAUDE.md template still contains unresolved {{placeholders}} after substitution"
        )
    out = dest_root / "CLAUDE.md"
    if dry_run:
        print(f"  [dry-run] write CLAUDE.md from template ({len(text)} chars)")
        return
    out.write_text(text, encoding="utf-8")


def apply_set_public_manifest(
    source_root: Path,
    dest_root: Path,
    public_version: str,
    release_channel: str,
    source_revision: str,
    *,
    dry_run: bool,
) -> None:
    azoth_path = dest_root / "azoth.yaml"
    if not azoth_path.is_file():
        raise RuntimeError(f"azoth.yaml missing in output after copy: {azoth_path}")
    source_manifest_path = source_root / "azoth.yaml"
    source_manifest = yaml.safe_load(source_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(source_manifest, dict):
        raise RuntimeError("source azoth.yaml must be a mapping")
    pipeline_presets = source_manifest.get("pipeline_presets")
    if not isinstance(pipeline_presets, list):
        pipeline_presets = []
    data = {
        "schema_version": 1,
        "name": "azoth",
        "version": public_version,
        "description": source_manifest.get("description") or "An inspectable toolkit for governed AI-assisted software delivery",
        "release_channel": release_channel,
        "provenance": {
            "source_delivery_version": str(source_manifest.get("version") or "unknown"),
            "source_revision": source_revision,
        },
        "scope": {
            "mode": "product",
            "is_development_workshop": False,
        },
        "platforms": ["claude_code", "opencode", "copilot", "codex"],
        "pipeline_presets": [str(item) for item in pipeline_presets],
    }
    if dry_run:
        print(
            "  [dry-run] set public azoth.yaml "
            f"version={public_version!r}, release_channel={release_channel!r}"
        )
        return
    azoth_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def re_full_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def apply_transforms(
    source_root: Path,
    dest_root: Path,
    transforms: list[dict[str, Any]],
    public_version: str,
    release_channel: str,
    source_revision: str,
    *,
    dry_run: bool,
) -> None:
    if not transforms:
        raise RuntimeError("product_extraction.transform must be non-empty (no silent no-op)")
    for spec in transforms:
        if not isinstance(spec, dict):
            raise RuntimeError("each transform entry must be a mapping")
        src_name = spec.get("source")
        action = spec.get("action")
        if not isinstance(src_name, str) or not isinstance(action, str):
            raise RuntimeError("transform entries require source: str and action: str")
        if action == "regenerate-from-template":
            tpl = spec.get("template")
            if not isinstance(tpl, str):
                raise RuntimeError("regenerate-from-template requires template: str")
            if src_name != "CLAUDE.md":
                raise RuntimeError(f"unsupported regenerate-from-template source: {src_name!r}")
            tpl = _validated_repo_path(tpl, label="regenerate-from-template template")
            subs = _build_claude_substitutions(source_root, public_version)
            apply_regenerate_claude(
                source_root,
                dest_root,
                tpl,
                subs,
                dry_run=dry_run,
            )
        elif action == "set-public-manifest":
            if src_name != "azoth.yaml":
                raise RuntimeError(f"unsupported set-public-manifest source: {src_name!r}")
            apply_set_public_manifest(
                source_root,
                dest_root,
                public_version,
                release_channel,
                source_revision,
                dry_run=dry_run,
            )
        else:
            raise RuntimeError(f"unknown transform action: {action!r}")


def apply_sanitize_strip_patterns(
    dest_root: Path,
    strip_patterns: list[str],
    rewrite_patterns: dict[str, str] | None = None,
    *,
    dry_run: bool,
) -> int:
    if not strip_patterns and not rewrite_patterns:
        return 0
    touched = 0
    for path in sorted(dest_root.rglob("*")):
        if not path.is_file():
            continue
        text = _read_utf8_text(path)
        if text is None:
            continue
        new_text = sanitize_content(text, strip_patterns, rewrite_patterns)
        if new_text != text:
            touched += 1
            if dry_run:
                print(f"  [dry-run] sanitize {path.relative_to(dest_root)}")
            else:
                path.write_text(new_text, encoding="utf-8")
    return touched


def emit_public_assets(
    source_root: Path,
    dest_root: Path,
    public_test_paths: list[str],
    *,
    dry_run: bool,
) -> None:
    ci_tpl = source_root / PUBLIC_CI_TEMPLATE
    if not ci_tpl.is_file():
        raise RuntimeError(f"public CI template missing: {ci_tpl}")
    readme_tpl = source_root / PUBLIC_README_TEMPLATE
    if not readme_tpl.is_file():
        raise RuntimeError(f"public README template missing: {readme_tpl}")

    ci_dest = dest_root / ".github" / "workflows" / "ci.yml"
    readme_dest = dest_root / "README.md"

    if dry_run:
        print(f"  [dry-run] emit {ci_dest.relative_to(dest_root)}")
        print(f"  [dry-run] emit {readme_dest.relative_to(dest_root)}")
        print("  [dry-run] emit .github/copilot-instructions.md")
        print("  [dry-run] copy .github/prompts/ when present")
        print("  [dry-run] emit .github/agents/ from canonical agents/**/*.agent.md")
        print("  [dry-run] emit public script templates and public-test-paths.txt")
        return

    ci_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ci_tpl, ci_dest)
    (dest_root / "public-test-paths.txt").write_text(
        "".join(f"{path}\n" for path in public_test_paths),
        encoding="utf-8",
    )

    scripts_dest = dest_root / "scripts"
    scripts_dest.mkdir(parents=True, exist_ok=True)
    public_version = _public_manifest_value(dest_root, "version")
    release_channel = _public_manifest_value(dest_root, "release_channel")
    for template_rel in PUBLIC_SCRIPT_TEMPLATES:
        template_path = source_root / template_rel
        if not template_path.is_file():
            raise RuntimeError(f"public script template missing: {template_path}")
        text = template_path.read_text(encoding="utf-8")
        text = text.replace("{{PUBLIC_VERSION}}", public_version)
        text = text.replace("{{RELEASE_CHANNEL}}", release_channel)
        text = text.replace("{{PUBLIC_TEST_PATHS_LINES}}", "\n".join(public_test_paths))
        if "{{PUBLIC_" in text:
            raise RuntimeError(f"unresolved public-script template placeholder: {template_path}")
        (scripts_dest / template_path.name).write_text(text, encoding="utf-8")

    rtext = readme_tpl.read_text(encoding="utf-8")
    for k, v in README_SUBSTITUTIONS.items():
        rtext = rtext.replace("{{" + k + "}}", v)
    rtext = rtext.replace("{{PUBLIC_VERSION}}", public_version)
    rtext = rtext.replace("{{RELEASE_CHANNEL}}", release_channel)
    if "{{" in rtext:
        raise RuntimeError("README template has unresolved placeholders")
    readme_dest.write_text(rtext, encoding="utf-8")

    copilot_template = source_root / "kernel" / "templates" / "copilot-instructions.md.template"
    if copilot_template.is_file():
        ctext = copilot_template.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", "azoth")
        (dest_root / ".github" / "copilot-instructions.md").write_text(
            ctext,
            encoding="utf-8",
        )

    prompts_src = source_root / ".github" / "prompts"
    prompts_dst = dest_root / ".github" / "prompts"
    if prompts_src.is_dir():
        if prompts_dst.exists():
            shutil.rmtree(prompts_dst)
        shutil.copytree(prompts_src, prompts_dst)

    agents_dst = dest_root / ".github" / "agents"
    agents_src = sorted((source_root / "agents").glob("**/*.agent.md"))
    if agents_src:
        if agents_dst.exists():
            shutil.rmtree(agents_dst)
        agents_dst.mkdir(parents=True, exist_ok=True)
        for agent in agents_src:
            name, content = transform_agent_copilot(agent)
            (agents_dst / f"{name}.agent.md").write_text(content, encoding="utf-8")


def _public_manifest_value(dest_root: Path, key: str) -> str:
    manifest = yaml.safe_load((dest_root / "azoth.yaml").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get(key), str):
        raise RuntimeError(f"public manifest missing string field: {key}")
    return str(manifest[key])


def _validate_snapshot(source: Path, config_path: Path) -> int:
    """Validate one already-materialized committed source tree."""
    cfg = load_config(config_path)
    pe = get_product_extraction(cfg)
    validate_pipeline(pe)
    _public_identity(pe)
    _public_include_paths(pe)
    _public_test_paths(pe, source)
    for rel in (PUBLIC_CI_TEMPLATE, PUBLIC_README_TEMPLATE, *PUBLIC_SCRIPT_TEMPLATES):
        p = source / rel
        if not p.is_file():
            _die(f"required template missing: {rel.as_posix()}")
    tpl = pe.get("transform")
    if isinstance(tpl, list):
        for spec in tpl:
            if not isinstance(spec, dict):
                continue
            if spec.get("action") == "regenerate-from-template":
                tr = spec.get("template")
                if isinstance(tr, str):
                    try:
                        template_rel = _validated_repo_path(tr, label="transform template")
                    except RuntimeError as exc:
                        _die(str(exc))
                    if not (source / template_rel).is_file():
                        _die(f"transform template not found: {template_rel}")
    print("validate-only: OK (config, public surface, pipeline, templates)")
    return 0


def validate_only(source: Path, config_path: Path) -> int:
    """Validate config and templates from one committed snapshot; write no output."""
    source_root = source.resolve()
    if not source_root.is_dir():
        _die("--source is not a directory")
    config_rel = _config_repo_path(source_root, config_path)
    revision = _source_revision(source_root)
    with _committed_snapshot(source_root, revision) as snapshot_root:
        return _validate_snapshot(snapshot_root, snapshot_root / config_rel)


def _public_identity(pe: dict[str, Any]) -> tuple[str, str]:
    public_version = pe.get("public_version")
    release_channel = pe.get("release_channel")
    if not isinstance(public_version, str) or not public_version.strip():
        _die("product_extraction.public_version must be a non-empty string")
    if release_channel not in {"preview", "stable"}:
        _die("product_extraction.release_channel must be preview or stable")
    return public_version.strip(), str(release_channel)


def _public_include_paths(pe: dict[str, Any]) -> list[str]:
    include_paths = pe.get("include_paths")
    if (
        not isinstance(include_paths, list)
        or not include_paths
        or not all(isinstance(item, str) and item.strip() for item in include_paths)
    ):
        _die("product_extraction.include_paths must be a non-empty list of strings")
    try:
        return [
            _validated_repo_path(str(item), label="product_extraction.include_paths entry")
            for item in include_paths
        ]
    except RuntimeError as exc:
        _die(str(exc))


def _public_test_paths(pe: dict[str, Any], source_root: Path) -> list[str]:
    test_paths = pe.get("public_test_paths")
    if (
        not isinstance(test_paths, list)
        or not test_paths
        or not all(isinstance(item, str) and item.startswith("tests/") for item in test_paths)
    ):
        _die("product_extraction.public_test_paths must be a non-empty list of tests/* paths")
    try:
        normalized = [
            _validated_repo_path(str(path), label="product_extraction.public_test_paths entry")
            for path in test_paths
        ]
    except RuntimeError as exc:
        _die(str(exc))
    if not all(path.startswith("tests/") for path in normalized):
        _die("product_extraction.public_test_paths must contain only tests/* paths")
    missing = [path for path in normalized if not (source_root / path).is_file()]
    if missing:
        _die(f"public test paths do not exist: {missing}")
    return normalized


def extract_product(
    *,
    source: Path,
    dest: Path,
    config_path: Path,
    dry_run: bool,
) -> int:
    source_root = source.resolve()
    if not source_root.is_dir():
        _die("--source is not a directory")
    config_rel = _config_repo_path(source_root, config_path)
    revision = _source_revision(source_root)
    with _committed_snapshot(source_root, revision) as snapshot_root:
        return _extract_product_snapshot(
            source=snapshot_root,
            dest=dest,
            config_path=snapshot_root / config_rel,
            source_revision=revision,
            dry_run=dry_run,
        )


def _extract_product_snapshot(
    *,
    source: Path,
    dest: Path,
    config_path: Path,
    source_revision: str,
    dry_run: bool,
) -> int:
    cfg = load_config(config_path)
    pe = get_product_extraction(cfg)
    validate_pipeline(pe)
    public_version, release_channel = _public_identity(pe)
    include_paths = _public_include_paths(pe)
    public_test_paths = _public_test_paths(pe, source)
    exclude_paths = pe.get("exclude_paths")
    if not isinstance(exclude_paths, list) or not all(isinstance(x, str) for x in exclude_paths):
        _die("product_extraction.exclude_paths must be a list of strings")
    try:
        exclude_paths = [
            _validated_repo_path(
                path,
                label="product_extraction.exclude_paths entry",
                allow_git_metadata=True,
            )
            for path in exclude_paths
        ]
    except RuntimeError as exc:
        _die(str(exc))

    sanitize_cfg = cfg.get("sanitize", {})
    strip_patterns = sanitize_cfg.get("strip_patterns", [])
    if not isinstance(strip_patterns, list) or not all(isinstance(x, str) for x in strip_patterns):
        _die("sanitize.strip_patterns must be a list of strings")
    rewrite_patterns = sanitize_cfg.get("rewrite_patterns", {})
    if not isinstance(rewrite_patterns, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in rewrite_patterns.items()
    ):
        _die("sanitize.rewrite_patterns must be a string-to-string mapping")

    transforms = pe.get("transform")
    if transforms is None:
        _die("product_extraction.transform is required")
    if not isinstance(transforms, list):
        _die("product_extraction.transform must be a list")

    if dry_run:
        print(
            "dry-run: step 1 only (listing copies); transforms need a real tree — use full extract or --validate-only"
        )
        n = copy_tree_respecting_excludes(
            source,
            dest,
            exclude_paths,
            include_paths,
            dry_run=True,
        )
        print(f"   would copy {n} files")
        print("done (dry-run).")
        return 0

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    print("1. copy_tree_respecting_excludes …")
    n = copy_tree_respecting_excludes(
        source,
        dest,
        exclude_paths,
        include_paths,
        dry_run=False,
    )
    print(f"   copied {n} files")

    print("2. apply_transforms …")
    apply_transforms(
        source,
        dest,
        transforms,
        public_version,
        release_channel,
        source_revision,
        dry_run=False,
    )

    print("3. apply_sanitize_strip_patterns …")
    sn = apply_sanitize_strip_patterns(
        dest,
        strip_patterns,
        rewrite_patterns,
        dry_run=False,
    )
    print(f"   sanitized {sn} files (content changed)")

    print("4. emit public CI + README …")
    emit_public_assets(source, dest, public_test_paths, dry_run=False)

    print("done.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract public azoth product tree per sync-config.yaml product_extraction.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT,
        help="Scaffold root (default: repo root)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output directory for extracted product (required unless --validate-only). "
            "Destructive: if this path already exists, it is deleted entirely "
            "(shutil.rmtree), then recreated — do not point at a git clone or any "
            "directory you need to keep; use a staging path and rsync into the target."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Repository-relative path to committed sync-config.yaml "
            "(default: <source>/sync-config.yaml)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be copied (step 1 only); no output tree",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Verify config, pipeline order, and template paths; no writes",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    config_path = args.config or Path("sync-config.yaml")

    try:
        if args.validate_only:
            return validate_only(source, config_path)

        if args.out is None:
            parser.error("--out is required unless --validate-only")

        dest = args.out.resolve()
        return extract_product(
            source=source,
            dest=dest,
            config_path=config_path,
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        _die(str(exc))


if __name__ == "__main__":
    sys.exit(main())
