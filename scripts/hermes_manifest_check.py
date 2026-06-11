#!/usr/bin/env python3
"""Hermes manifest check — verifies Azoth's documented invariants against disk reality.

This is the runtime guard for the kernel's claims. It is mechanical, not a
prompt rule. Run in CI on trust-bearing hosts (Hermes, Codex, OpenCode);
run in best-effort warning mode on adapters (see kernel/TRUST_HOSTS.md).

Checks performed:
  1. All four kernel files exist (BOOTLOADER, TRUST_CONTRACT, GOVERNANCE, PROMOTION_RUBRIC).
  2. Kernel checksum file matches the four kernel files (when .azoth/kernel-checksums.sha256 exists).
  3. AGENTS.md uses scope-gated entropy wording (not stale per-session).
  4. tests/ directory exists with at least one test_*.py file.
  5. kernel/TRUST_HOSTS.md exists and parses.

Exit codes:
  0 — all invariants hold
  1 — one or more invariants failed (details in --json output)
  2 — usage error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


KERNEL_FILES = (
    "BOOTLOADER.md",
    "TRUST_CONTRACT.md",
    "GOVERNANCE.md",
    "PROMOTION_RUBRIC.md",
)


def _kernel_dir(repo_root: Path) -> Path:
    return repo_root / "kernel"


def _checksums_path(repo_root: Path) -> Path:
    return repo_root / ".azoth" / "kernel-checksums.sha256"


def _check_kernel_files_present(repo_root: Path) -> list[dict[str, object]]:
    kdir = _kernel_dir(repo_root)
    results: list[dict[str, object]] = []
    for name in KERNEL_FILES:
        path = kdir / name
        results.append(
            {
                "kind": "kernel_file",
                "name": name,
                "path": str(path),
                "present": path.is_file(),
            }
        )
    return results


def _check_kernel_checksum(repo_root: Path) -> tuple[bool, list[dict[str, object]]]:
    """Return (ok, results). ok=True iff checksums file matches reality (or absent)."""
    sums = _checksums_path(repo_root)
    if not sums.is_file():
        return True, [{"kind": "kernel_checksum", "status": "no_manifest", "ok": True}]
    expected: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        sha, path = parts
        expected[path.lstrip("*")] = sha
    kdir = _kernel_dir(repo_root)
    results: list[dict[str, object]] = []
    ok = True
    for name in KERNEL_FILES:
        path = kdir / name
        rel = f"kernel/{name}"
        if not path.is_file():
            results.append(
                {
                    "kind": "kernel_checksum_entry",
                    "name": name,
                    "ok": False,
                    "reason": "missing",
                }
            )
            ok = False
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = expected.get(rel) == actual
        if not match:
            ok = False
        results.append(
            {
                "kind": "kernel_checksum_entry",
                "name": name,
                "ok": match,
                "expected": expected.get(rel),
                "actual": actual,
            }
        )
    return ok, results


def _check_agents_md_parity(repo_root: Path) -> tuple[bool, dict[str, object]]:
    agents = repo_root / "AGENTS.md"
    if not agents.is_file():
        return False, {"kind": "agents_md_parity", "ok": False, "reason": "AGENTS.md missing"}
    text = agents.read_text(encoding="utf-8")
    if "per scope-gated session" not in text:
        return False, {
            "kind": "agents_md_parity",
            "ok": False,
            "reason": "missing 'per scope-gated session' wording",
        }
    bad = re.findall(r"per session(?! scope-gated)", text)
    if bad:
        return False, {
            "kind": "agents_md_parity",
            "ok": False,
            "reason": f"stale 'per session' wording: {bad}",
        }
    return True, {"kind": "agents_md_parity", "ok": True}


def _check_tests_directory(repo_root: Path) -> tuple[bool, dict[str, object]]:
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return False, {"kind": "tests_directory", "ok": False, "reason": "tests/ directory missing"}
    test_files = list(tests_dir.glob("test_*.py"))
    if not test_files:
        return False, {
            "kind": "tests_directory",
            "ok": False,
            "reason": "no test_*.py files",
        }
    return True, {"kind": "tests_directory", "ok": True, "count": len(test_files)}


def _check_trust_hosts_md(repo_root: Path) -> tuple[bool, dict[str, object]]:
    path = repo_root / "kernel" / "TRUST_HOSTS.md"
    if not path.is_file():
        return False, {
            "kind": "trust_hosts_md",
            "ok": False,
            "reason": "kernel/TRUST_HOSTS.md missing",
        }
    text = path.read_text(encoding="utf-8")
    if "<!-- trust_hosts:start -->" not in text or "<!-- trust_hosts:end -->" not in text:
        return False, {
            "kind": "trust_hosts_md",
            "ok": False,
            "reason": "fences missing",
        }
    return True, {"kind": "trust_hosts_md", "ok": True}


def run_check(repo_root: Path, *, strict: bool = False) -> dict[str, object]:
    kernel_present = _check_kernel_files_present(repo_root)
    kernel_ok = all(c["present"] for c in kernel_present)
    checksum_ok, checksum_results = _check_kernel_checksum(repo_root)
    parity_ok, parity_result = _check_agents_md_parity(repo_root)
    tests_ok, tests_result = _check_tests_directory(repo_root)
    trust_ok, trust_result = _check_trust_hosts_md(repo_root)

    checks: list[dict[str, object]] = []
    checks.extend(kernel_present)
    checks.extend(checksum_results)
    checks.append(parity_result)
    checks.append(tests_result)
    checks.append(trust_result)

    all_ok = kernel_ok and checksum_ok and parity_ok and tests_ok and trust_ok

    return {
        "ok": all_ok,
        "strict": strict,
        "kernel_checksum_ok": checksum_ok,
        "agents_md_parity_ok": parity_ok,
        "tests_directory_present": tests_ok,
        "trust_hosts_md_present": trust_ok,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args(argv)

    payload = run_check(args.repo_root.resolve(), strict=args.strict)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check in payload["checks"]:
            kind = str(check.get("kind", "?"))
            name = str(check.get("name", ""))
            ok = bool(check.get("ok", True))
            mark = "OK  " if ok else "FAIL"
            print(f"[{mark}] {kind:24s} {name}")
        print()
        print(f"overall: {'OK' if payload['ok'] else 'FAIL'}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
