#!/usr/bin/env python3
"""
Extract the public `azoth` product tree from root-azoth per `sync-config.yaml`
`product_extraction` (D38 / P4-004).

Pipeline (mandatory order — must not skip steps):
  1. copy_tree_respecting_excludes
  2. apply_transforms
  3. apply_sanitize_strip_patterns

Then emits public CI + README from kernel templates (same contract as sync-config comments).

Not azoth-sync.py (Tier 1→2 only).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_PIPELINE: tuple[str, ...] = (
    "copy_tree_respecting_excludes",
    "apply_transforms",
    "apply_sanitize_strip_patterns",
)

TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".toml"}

PUBLIC_CI_TEMPLATE = Path("kernel/templates/github/workflows/ci-public-azoth.yml")
PUBLIC_README_TEMPLATE = Path("kernel/templates/README.public.azoth.md")

DEFAULT_CLAUDE_SUBSTITUTIONS: dict[str, str] = {
    "PROJECT_NAME": "Azoth",
    "GITHUB_USER": "your-org",
    "LANGUAGE": "Python",
    "DESCRIPTION": "The Universal Agentic Toolkit — agentic development discipline for AI-assisted projects.",
    "SOURCE_DIR": "src",
    "TEST_DIR": "tests",
    "FORMATTER": "ruff format + ruff check",
    "TEST_FRAMEWORK": "pytest",
    "AZOTH_VERSION": "0.0.7",
    "INSTALLED_SKILLS": "see skills/",
    "INSTALLED_AGENTS": "see agents/",
    "INSTALLED_PIPELINES": "see pipelines/",
}

README_SUBSTITUTIONS: dict[str, str] = {
    "PRODUCT_NAME": "Azoth",
    "DESCRIPTION": "Portable agentic toolkit: skills, agents, pipelines, and governance patterns.",
}


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
        _die(
            f"extraction_pipeline must be exactly {EXPECTED_PIPELINE!r}, got {got!r}"
        )


def path_is_excluded(rel_posix: str, exclude_paths: list[str]) -> bool:
    """True if rel path (posix, relative to source root) matches any exclude prefix."""
    for raw in exclude_paths:
        pat = raw.replace("\\", "/").rstrip("/")
        if rel_posix == pat or rel_posix.startswith(pat + "/"):
            return True
    return False


def sanitize_content(content: str, strip_patterns: list[str]) -> str:
    """Same substitution contract as scripts/azoth-sync.py sanitize_content."""
    for pattern in strip_patterns:
        content = content.replace(pattern, "{{REDACTED}}")
    return content


def copy_tree_respecting_excludes(
    source: Path,
    dest: Path,
    exclude_paths: list[str],
    *,
    dry_run: bool,
) -> int:
    copied = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
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


def apply_set_scope_mode(
    dest_root: Path,
    value: str,
    *,
    dry_run: bool,
) -> None:
    azoth_path = dest_root / "azoth.yaml"
    if not azoth_path.is_file():
        raise RuntimeError(f"azoth.yaml missing in output after copy: {azoth_path}")
    data = yaml.safe_load(azoth_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("azoth.yaml must be a mapping")
    scope = data.setdefault("scope", {})
    if not isinstance(scope, dict):
        raise RuntimeError("azoth.yaml scope must be a mapping")
    scope["mode"] = value
    scope["is_development_workshop"] = False
    if dry_run:
        print(f"  [dry-run] set azoth.yaml scope.mode={value!r}, is_development_workshop=false")
        return
    azoth_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def apply_transforms(
    source_root: Path,
    dest_root: Path,
    transforms: list[dict[str, Any]],
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
                raise RuntimeError(
                    f"unsupported regenerate-from-template source: {src_name!r}"
                )
            apply_regenerate_claude(
                source_root,
                dest_root,
                tpl,
                DEFAULT_CLAUDE_SUBSTITUTIONS,
                dry_run=dry_run,
            )
        elif action == "set-scope-mode":
            val = spec.get("value")
            if not isinstance(val, str):
                raise RuntimeError("set-scope-mode requires value: str")
            if src_name != "azoth.yaml":
                raise RuntimeError(f"unsupported set-scope-mode source: {src_name!r}")
            apply_set_scope_mode(dest_root, val, dry_run=dry_run)
        else:
            raise RuntimeError(f"unknown transform action: {action!r}")


def apply_sanitize_strip_patterns(
    dest_root: Path,
    strip_patterns: list[str],
    *,
    dry_run: bool,
) -> int:
    if not strip_patterns:
        return 0
    touched = 0
    for path in sorted(dest_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        new_text = sanitize_content(text, strip_patterns)
        if new_text != text:
            touched += 1
            if dry_run:
                print(f"  [dry-run] sanitize {path.relative_to(dest_root)}")
            else:
                path.write_text(new_text, encoding="utf-8")
    return touched


def emit_public_assets(source_root: Path, dest_root: Path, *, dry_run: bool) -> None:
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
        return

    ci_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ci_tpl, ci_dest)

    rtext = readme_tpl.read_text(encoding="utf-8")
    for k, v in README_SUBSTITUTIONS.items():
        rtext = rtext.replace("{{" + k + "}}", v)
    if "{{" in rtext:
        raise RuntimeError("README template has unresolved placeholders")
    readme_dest.write_text(rtext, encoding="utf-8")


def validate_only(source: Path, config_path: Path) -> int:
    """Load config, pipeline, and required templates — no writes (CI smoke)."""
    cfg = load_config(config_path)
    pe = get_product_extraction(cfg)
    validate_pipeline(pe)
    for rel in (PUBLIC_CI_TEMPLATE, PUBLIC_README_TEMPLATE):
        p = source / rel
        if not p.is_file():
            _die(f"required template missing: {p}")
    tpl = pe.get("transform")
    if isinstance(tpl, list):
        for spec in tpl:
            if not isinstance(spec, dict):
                continue
            if spec.get("action") == "regenerate-from-template":
                tr = spec.get("template")
                if isinstance(tr, str) and not (source / tr).is_file():
                    _die(f"transform template not found: {source / tr}")
    print("validate-only: OK (config, pipeline, templates)")
    return 0


def extract_product(
    *,
    source: Path,
    dest: Path,
    config_path: Path,
    dry_run: bool,
) -> int:
    cfg = load_config(config_path)
    pe = get_product_extraction(cfg)
    validate_pipeline(pe)
    exclude_paths = pe.get("exclude_paths")
    if not isinstance(exclude_paths, list) or not all(
        isinstance(x, str) for x in exclude_paths
    ):
        _die("product_extraction.exclude_paths must be a list of strings")

    sanitize_cfg = cfg.get("sanitize", {})
    strip_patterns = sanitize_cfg.get("strip_patterns", [])
    if not isinstance(strip_patterns, list) or not all(
        isinstance(x, str) for x in strip_patterns
    ):
        _die("sanitize.strip_patterns must be a list of strings")

    transforms = pe.get("transform")
    if transforms is None:
        _die("product_extraction.transform is required")
    if not isinstance(transforms, list):
        _die("product_extraction.transform must be a list")

    if not source.is_dir():
        _die(f"--source is not a directory: {source}")

    if dry_run:
        print("dry-run: step 1 only (listing copies); transforms need a real tree — use full extract or --validate-only")
        n = copy_tree_respecting_excludes(source, dest, exclude_paths, dry_run=True)
        print(f"   would copy {n} files")
        print("done (dry-run).")
        return 0

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    print("1. copy_tree_respecting_excludes …")
    n = copy_tree_respecting_excludes(source, dest, exclude_paths, dry_run=False)
    print(f"   copied {n} files")

    print("2. apply_transforms …")
    apply_transforms(source, dest, transforms, dry_run=False)

    print("3. apply_sanitize_strip_patterns …")
    sn = apply_sanitize_strip_patterns(dest, strip_patterns, dry_run=False)
    print(f"   sanitized {sn} files (content changed)")

    print("4. emit public CI + README …")
    emit_public_assets(source, dest, dry_run=False)

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
        help="Output directory for extracted product (required unless --validate-only)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to sync-config.yaml (default: <source>/sync-config.yaml)",
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
    config_path = (args.config or (source / "sync-config.yaml")).resolve()

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


if __name__ == "__main__":
    sys.exit(main())
