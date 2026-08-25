#!/usr/bin/env python3
"""Run no-write Personal Harness OS practice scenarios."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml

from harness_profile import HarnessRequest
from personal_harness_context import build_personal_harness_context


DEFAULT_CASES = Path("examples/personal-harness/rehearsal-cases.yaml")
EXPLICIT_REHEARSAL_STATE = (
    Path(".azoth/memory/episodes.jsonl"),
    Path(".azoth/memory/patterns.yaml"),
)


def run_practice_rehearsal(
    *,
    repo_root: Path,
    cases_path: Path = DEFAULT_CASES,
) -> dict[str, Any]:
    """Run fixture-backed practice cases and return a JSON-ready report."""
    root = repo_root.resolve()
    resolved_cases = _resolve_cases_path(root, cases_path)
    tree_before = _tree_fingerprint(root, cases_path=resolved_cases)
    cases = _load_cases(resolved_cases)
    results = [_run_case(case, root) for case in cases]
    tree_after = _tree_fingerprint(root, cases_path=resolved_cases)
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_practice_rehearsal",
        "ok": all(result["status"] == "pass" for result in results) and tree_before == tree_after,
        "case_count": len(results),
        "cases": results,
        "no_write_contract": {
            "tree_sha256_before": tree_before,
            "tree_sha256_after": tree_after,
            "repo_mutated": tree_before != tree_after,
        },
    }


def _load_cases(path: Path) -> list[dict[str, Any]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema_version") != 1:
        raise ValueError(f"{path}: expected schema_version 1")
    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}: expected non-empty cases list")
    return [case for case in cases if isinstance(case, dict)]


def _run_case(
    case: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    request = HarnessRequest.from_mapping(case)
    packet = build_personal_harness_context(
        goal=request.goal,
        requested_actions=request.requested_actions,
        planned_paths=request.planned_paths,
        query_tags=_strings(case.get("query_tags")),
        repo_root=repo_root,
        project_readback=_mapping(case.get("project_readback")),
    )
    context = _mapping(packet.get("context_view")) or {}
    warnings = _strings(packet.get("warnings"))
    checks = _checks(case, context, warnings)
    route = _mapping(context.get("route_capsule")) or {}
    return {
        "id": str(case.get("id") or "unknown"),
        "domain": str(case.get("domain") or "unknown"),
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "profile": context.get("harness_profile"),
        "side_effect_class": route.get("side_effect_class"),
        "route_state": route.get("route_state"),
        "authority_plane": route.get("authority_plane"),
        "authority_required": route.get("authority_required"),
        "warnings": warnings,
    }


def _checks(
    case: Mapping[str, Any],
    context: Mapping[str, Any],
    warnings: list[str],
) -> list[dict[str, str]]:
    expected = _mapping(case.get("expected")) or {}
    route = _mapping(context.get("route_capsule")) or {}
    project = _mapping(context.get("project_context")) or {}
    return [
        _check("profile", context.get("harness_profile") == expected.get("profile")),
        _check(
            "side_effect_class",
            route.get("side_effect_class") == expected.get("side_effect_class"),
        ),
        _check("route_state", route.get("route_state") == expected.get("route_state")),
        _check(
            "authority_required",
            route.get("authority_required") is expected.get("authority_required"),
        ),
        _check("authority_plane", route.get("authority_plane") == expected.get("authority_plane")),
        _check(
            "project_context",
            not expected.get("project") or project.get("project") == expected.get("project"),
        ),
        _check(
            "warnings",
            all(
                any(expected_warning in actual for actual in warnings)
                for expected_warning in _strings(expected.get("warning_contains"))
            ),
        ),
    ]


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"id": check_id, "status": "pass" if passed else "fail"}


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _mapping(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _resolve_cases_path(root: Path, cases_path: Path) -> Path:
    """Resolve relative fixtures under the selected repository, never the process CWD."""
    if cases_path.is_absolute():
        return cases_path.resolve()
    resolved = (root / cases_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("relative rehearsal cases path must stay under repo_root") from exc
    return resolved


def _validated_git_path(raw: str) -> Path:
    if not raw or raw.startswith("/") or "\\" in raw:
        raise RuntimeError("Git reported an unsafe rehearsal-state path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError("Git reported a traversing rehearsal-state path")
    if path.parts[0] == ".git":
        raise RuntimeError("Git metadata cannot enter the rehearsal fingerprint")
    return Path(*path.parts)


def _git_output(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"could not inspect bounded Git rehearsal state: {detail}")
    return result.stdout


def _git_fingerprint_state(root: Path) -> tuple[set[Path], set[Path], bytes] | None:
    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root:
        return None

    def paths_from(output: bytes) -> set[Path]:
        return {
            _validated_git_path(item.decode("utf-8", errors="surrogateescape"))
            for item in output.split(b"\0")
            if item
        }

    tracked = paths_from(_git_output(root, "ls-files", "--cached", "-z"))
    untracked = paths_from(_git_output(root, "ls-files", "--others", "--exclude-standard", "-z"))
    status = _git_output(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=no",
    )
    return tracked, untracked, status


def _update_file_content_hash(digest: Any, path: Path, expected: os.stat_result) -> None:
    """Hash one verified regular file without ever opening a symlink target."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        digest.update(b"content-hash-unavailable-without-o-nofollow")
        return
    flags = os.O_RDONLY | no_follow | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        digest.update(f"open-error:{exc.errno}".encode("ascii"))
        return
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != expected.st_dev
            or opened.st_ino != expected.st_ino
        ):
            digest.update(b"entry-changed-before-open")
            return
        content_digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 64 * 1024)
            if not chunk:
                break
            content_digest.update(chunk)
        digest.update(content_digest.digest())
        after = os.fstat(fd)
        digest.update(f"{after.st_size}:{after.st_mtime_ns}:{after.st_ctime_ns}".encode("ascii"))
    finally:
        os.close(fd)


def _update_entry_fingerprint(
    digest: Any,
    *,
    logical_path: str,
    path: Path,
    hash_content: bool,
    anchor: Path,
) -> None:
    digest.update(logical_path.encode("utf-8", errors="surrogateescape"))
    digest.update(b"\0")
    try:
        rel = path.relative_to(anchor)
    except ValueError:
        digest.update(b"path-outside-anchor\0")
        return
    current = anchor
    for part in rel.parts[:-1]:
        current /= part
        try:
            parent = os.lstat(current)
        except OSError as exc:
            digest.update(f"parent-error:{exc.errno}\0".encode("ascii"))
            return
        if stat.S_ISLNK(parent.st_mode):
            digest.update(b"symlink-parent\0")
            return
        if not stat.S_ISDIR(parent.st_mode):
            digest.update(b"non-directory-parent\0")
            return
    try:
        entry = os.lstat(path)
    except OSError as exc:
        digest.update(f"entry-error:{exc.errno}\0".encode("ascii"))
        return
    digest.update(
        f"{stat.S_IFMT(entry.st_mode)}:{stat.S_IMODE(entry.st_mode)}:"
        f"{entry.st_size}:{entry.st_mtime_ns}:{entry.st_ctime_ns}".encode("ascii")
    )
    digest.update(b"\0")
    if stat.S_ISLNK(entry.st_mode):
        try:
            target = os.readlink(path)
        except OSError as exc:
            digest.update(f"readlink-error:{exc.errno}".encode("ascii"))
        else:
            digest.update(target.encode("utf-8", errors="surrogateescape"))
    elif stat.S_ISREG(entry.st_mode) and hash_content:
        _update_file_content_hash(digest, path, entry)


def _tree_fingerprint(root: Path, *, cases_path: Path) -> str:
    """Hash bounded repository state without reading ignored or symlink targets."""
    digest = hashlib.sha256()
    git_state = _git_fingerprint_state(root)
    entries: dict[str, tuple[Path, bool, Path]] = {}
    if git_state is not None:
        tracked, untracked, status = git_state
        digest.update(b"git\0")
        digest.update(status)
        for rel in tracked:
            entries[rel.as_posix()] = (root / rel, True, root)
        for rel in untracked:
            entries.setdefault(rel.as_posix(), (root / rel, False, root))
    else:
        digest.update(b"bounded-non-git\0")

    for rel in EXPLICIT_REHEARSAL_STATE:
        entries[rel.as_posix()] = (root / rel, True, root)
    try:
        cases_rel = cases_path.relative_to(root)
    except ValueError:
        entries["<explicit-rehearsal-cases>"] = (
            cases_path,
            True,
            cases_path.parent,
        )
    else:
        entries[cases_rel.as_posix()] = (cases_path, True, root)

    for logical_path, (path, hash_content, anchor) in sorted(entries.items()):
        _update_entry_fingerprint(
            digest,
            logical_path=logical_path,
            path=path,
            hash_content=hash_content,
            anchor=anchor,
        )
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("practice rehearsal output requires --json")

    report = run_practice_rehearsal(
        repo_root=args.repo_root,
        cases_path=args.cases,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
