#!/usr/bin/env python3
"""Validate kernel D2 invariants and optionally GOVERNANCE §4 checksums (BL-017 / GOV-B2)."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# D2 — docs/DECISIONS_INDEX.md, docs/AZOTH_ARCHITECTURE.md
D2_MAX_FILES = 10
D2_MAX_LOC = 2000

# kernel/GOVERNANCE.md §4 — lexicographic order, stable tooling output
CHECKSUM_REL = (
    "kernel/BOOTLOADER.md",
    "kernel/GOVERNANCE.md",
    "kernel/PROMOTION_RUBRIC.md",
    "kernel/TRUST_CONTRACT.md",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def check_d2(root: Path) -> list[str]:
    errors: list[str] = []
    kernel = root / "kernel"
    if not kernel.is_dir():
        return [f"D2: kernel/ not found: {kernel}"]
    mds = sorted(kernel.glob("*.md"))
    n_files = len(mds)
    if n_files > D2_MAX_FILES:
        errors.append(f"D2: {n_files} kernel/*.md files exceed cap {D2_MAX_FILES}")
    total_loc = 0
    for path in mds:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"D2: cannot read {path.relative_to(root)}: {exc}")
            continue
        total_loc += line_count(text)
    if total_loc > D2_MAX_LOC:
        errors.append(f"D2: total LOC {total_loc} exceeds cap {D2_MAX_LOC}")
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksum_lines(content: str) -> dict[str, str]:
    """Map normalized relpath -> lowercase hex digest."""
    out: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, path_part = parts[0], parts[1].lstrip("*").strip()
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            continue
        key = path_part.replace("\\", "/")
        out[key] = digest.lower()
    return out


def check_checksums(root: Path) -> list[str]:
    errors: list[str] = []
    sums_path = root / ".azoth" / "kernel-checksums.sha256"
    if not sums_path.is_file():
        return [
            f"§4: checksum file missing: {sums_path.relative_to(root)} "
            "(generate per kernel/GOVERNANCE.md §4 Integrity Check Mechanism)"
        ]
    expected = _parse_checksum_lines(sums_path.read_text(encoding="utf-8"))
    for rel in CHECKSUM_REL:
        path = root / rel
        if not path.is_file():
            errors.append(f"§4: missing file {rel}")
            continue
        candidates = {rel, rel.removeprefix("kernel/"), path.name}
        digest = None
        for key, val in expected.items():
            kn = key.replace("\\", "/")
            if kn in candidates or kn.endswith("/" + path.name):
                digest = val
                break
        if digest is None:
            errors.append(f"§4: no checksum entry for {rel} in {sums_path.relative_to(root)}")
            continue
        actual = sha256_file(path).lower()
        if actual != digest:
            errors.append(
                f"§4: checksum mismatch for {rel} (expected {digest[:12]}…, got {actual[:12]}…)"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Azoth kernel integrity: D2 caps on kernel/*.md; optional §4 SHA-256 verify.",
    )
    parser.add_argument(
        "--verify-checksums",
        action="store_true",
        help="Verify GOVERNANCE §4 four-file checksums against .azoth/kernel-checksums.sha256",
    )
    args = parser.parse_args()
    root = repo_root()
    errs = check_d2(root)
    if args.verify_checksums:
        errs.extend(check_checksums(root))
    if errs:
        for msg in errs:
            print(msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
