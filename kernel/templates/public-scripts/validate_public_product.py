#!/usr/bin/env python3
"""Fail-closed validation for an extracted Azoth public product tree."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "{{PUBLIC_VERSION}}"
EXPECTED_CHANNEL = "{{RELEASE_CHANNEL}}"
EXPECTED_TEST_PATHS = """{{PUBLIC_TEST_PATHS_LINES}}""".splitlines()
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".toml"}
REQUIRED_PATHS = (
    "README.md",
    "azoth.yaml",
    "public-test-paths.txt",
    "docs/PERSONAL_HARNESS_OS.md",
    "docs/case-studies/narrow-success-broad-failure.md",
    "examples/personal-harness/rehearsal-cases.yaml",
    "release-notes/v0.3.0-rc.1.md",
    "kernel/templates/release-profiles/deployment-mode-matrix.yaml",
    "scripts/harness_profile.py",
    "scripts/context_view.py",
    "scripts/personal_harness_context.py",
    "scripts/personal_harness_practice_rehearsal.py",
    "scripts/personal_knowledge_recall.py",
    "scripts/personal_knowledge_review.py",
)
FORBIDDEN_PREFIXES = (
    ".azoth/",
    ".vscode/",
    "docs/personal-control-plane/",
    "docs/superpowers/",
    "meta" + "_session_research/",
    "research_antigravity_parity/",
    "skills/orientation/",
    ".agents/skills/orientation/",
    ".opencode/skills/orientation/",
)
FORBIDDEN_FILES = (
    "sync-config.yaml",
    "scripts/azoth_extract_product.py",
    "scripts/product_release_smoke.py",
    "scripts/public_release_freshness.py",
    "scripts/cockpit_backup_verify.py",
    "scripts/cockpit_bootstrap_verify.py",
    "scripts/cockpit_command_surface.py",
    "scripts/cockpit_menu.py",
    "scripts/cockpit_ux_simulate.py",
    "scripts/personal_harness_daily_flow.py",
    "scripts/personal_knowledge_inventory.py",
    "scripts/personal_knowledge_validate.py",
)
FORBIDDEN_TOKENS = (
    "root" + "-azoth",
    "yiwei" + "-azoth-cockpit",
    "personal" + "-azoth-root",
    "meta" + "_session_research",
    "/Users/" + "yiwei/",
    "t-059" + "-deployment-readiness-mode-matrix.yaml",
    "dhub" + "-glovo",
    "fulfillment" + "-dwh",
    "glovo" + "app",
    "glovo" + ".com",
)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PRIVATE_KEY_HEADER = "-----BEGIN " + "PRIVATE KEY-----"
TOKEN_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
)
TOKEN_ASSIGNMENT = re.compile(
    r"(?im)^\s*(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*[\"']?([^\s\"']+)"
)
PLACEHOLDER_MARKERS = ("example", "placeholder", "redacted", "your_", "${", "{{", "<")
REDACTION_SENTINEL = "{{" + "REDACTED}}"
RELEASE_EVIDENCE_PATH = Path("release-notes/v0.3.0-rc.1.md")
ANGLE_BRACKET_EVIDENCE_PLACEHOLDER = re.compile(r"<[^<>\r\n]+>")


class ProductBoundaryError(RuntimeError):
    pass


def _files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*") if path.is_file())


def _read_utf8_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def validate_required_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise ProductBoundaryError(f"missing required public paths: {missing}")


def validate_forbidden_paths() -> None:
    rel_files = [path.relative_to(ROOT).as_posix() for path in _files()]
    leaked = [
        rel
        for rel in rel_files
        if rel in FORBIDDEN_FILES or any(rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
    ]
    if leaked:
        raise ProductBoundaryError(f"root-only paths leaked into public product: {leaked[:20]}")


def validate_manifest() -> None:
    manifest = yaml.safe_load((ROOT / "azoth.yaml").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ProductBoundaryError("azoth.yaml must be a mapping")
    expected = {
        "name": "azoth",
        "version": EXPECTED_VERSION,
        "release_channel": EXPECTED_CHANNEL,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ProductBoundaryError(f"azoth.yaml {key} must be {value!r}")
    if manifest.get("scope") != {"mode": "product", "is_development_workshop": False}:
        raise ProductBoundaryError("azoth.yaml scope must identify a non-workshop product")
    provenance = manifest.get("provenance")
    revision = provenance.get("source_revision") if isinstance(provenance, dict) else None
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ProductBoundaryError(
            "azoth.yaml provenance.source_revision must be a full commit SHA"
        )
    root_only_keys = {
        "phase",
        "milestone",
        "lifecycle_phase",
        "decisions",
        "layers",
        "memory",
        "sync",
    }
    leaked_keys = sorted(root_only_keys & set(manifest))
    if leaked_keys:
        raise ProductBoundaryError(f"root workshop manifest keys leaked: {leaked_keys}")


def validate_public_tests() -> None:
    actual = [
        line.strip()
        for line in (ROOT / "public-test-paths.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if actual != EXPECTED_TEST_PATHS:
        raise ProductBoundaryError("public-test-paths.txt does not match the release allowlist")
    missing = [path for path in actual if not (ROOT / path).is_file()]
    if missing:
        raise ProductBoundaryError(f"public tests are missing: {missing}")


def validate_content() -> None:
    hits: list[str] = []
    for path in _files():
        text = _read_utf8_text(path)
        if text is None:
            continue
        folded_text = text.casefold()
        for token in FORBIDDEN_TOKENS:
            if token.casefold() in folded_text:
                hits.append(f"{path.relative_to(ROOT)}:{token}")
        if REDACTION_SENTINEL in text:
            hits.append(f"{path.relative_to(ROOT)}:redaction-placeholder")
        if PRIVATE_KEY_HEADER in text:
            hits.append(f"{path.relative_to(ROOT)}:private-key-header")
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)}:credential-token")
        for match in TOKEN_ASSIGNMENT.finditer(text):
            value = match.group(1).casefold()
            if len(value) >= 12 and not any(marker in value for marker in PLACEHOLDER_MARKERS):
                hits.append(f"{path.relative_to(ROOT)}:credential-assignment")
    if hits:
        raise ProductBoundaryError(f"forbidden public content: {hits[:20]}")


def validate_release_evidence() -> None:
    """Reject unresolved angle-bracket evidence placeholders in release notes."""
    path = ROOT / RELEASE_EVIDENCE_PATH
    text = path.read_text(encoding="utf-8")
    placeholders = ANGLE_BRACKET_EVIDENCE_PLACEHOLDER.findall(text)
    if placeholders:
        raise ProductBoundaryError(
            "unresolved release-evidence placeholders: "
            f"{[placeholder[:120] for placeholder in placeholders[:20]]}"
        )


def _heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = re.sub(r"<[^>]+>", "", match.group(1)).strip().casefold()
        slug = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
        slug = re.sub(r"[\s]+", "-", slug).strip("-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    for match in re.finditer(
        r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']",
        path.read_text(encoding="utf-8", errors="replace"),
        re.I,
    ):
        anchors.add(match.group(1))
    return anchors


def _markdown_link_targets(text: str) -> list[str]:
    """Return Markdown link targets outside fenced code examples."""
    visible_lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = (
            "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        )
        if marker is not None:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            visible_lines.append(line)
    return MARKDOWN_LINK.findall("\n".join(visible_lines))


def _validate_reference(source: Path, target: str, broken: list[str]) -> None:
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return
    decoded = unquote(target)
    path_text, _, anchor = decoded.partition("#")
    resolved = (source.parent / path_text).resolve() if path_text else source.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        broken.append(f"{source.relative_to(ROOT)} -> {target}")
        return
    if not resolved.exists():
        broken.append(f"{source.relative_to(ROOT)} -> {target}")
        return
    if anchor and resolved.is_file() and resolved.suffix.lower() == ".md":
        if anchor not in _heading_anchors(resolved):
            broken.append(f"{source.relative_to(ROOT)} -> {target} (missing anchor)")


def validate_references() -> None:
    broken: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for raw_target in _markdown_link_targets(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            _validate_reference(path, target, broken)
    sys.path.insert(0, str(ROOT / "scripts"))
    from harness_profile import HarnessRequest, classify_harness_request

    decision = classify_harness_request(
        HarnessRequest(goal="Explain the Azoth operating modes.", requested_actions=("read",))
    )
    for source_ref in decision.source_refs:
        _validate_reference(ROOT / "README.md", source_ref, broken)
    if broken:
        raise ProductBoundaryError(f"broken public references: {broken[:20]}")


def main() -> int:
    try:
        validate_required_paths()
        validate_forbidden_paths()
        validate_manifest()
        validate_public_tests()
        validate_content()
        validate_release_evidence()
        validate_references()
    except ProductBoundaryError as exc:
        print(f"public product validation failed: {exc}", file=sys.stderr)
        return 1
    print("public product validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
