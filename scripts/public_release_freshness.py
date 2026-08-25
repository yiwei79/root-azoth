#!/usr/bin/env python3
"""Validate public azoth release freshness claims against root workshop drift."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "PUBLIC-AZOTH-FRESHNESS-POLICY.yaml"
DEFAULT_PUBLIC_ROOT = Path("/Users/yiwei/GithubRepos/azoth")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_STATUSES = {"fresh", "intentionally_stale"}


@dataclass(frozen=True)
class FreshnessResult:
    status: str
    version: str
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _git_output(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        joined = " ".join(args)
        raise RuntimeError(
            f"git command failed ({result.returncode}): {joined}\n"
            f"cwd: {cwd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def _current_commit(repo: Path) -> str:
    return _git_output(["git", "rev-parse", "HEAD"], cwd=repo)


def _tag_target(repo: Path, tag: str) -> str:
    return _git_output(["git", "rev-parse", f"{tag}^{{}}"], cwd=repo)


def _status_lines(repo: Path) -> list[str]:
    return _git_output(["git", "status", "--short", "--branch"], cwd=repo).splitlines()


def _non_branch_status_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if not line.startswith("##")]


def _string_at(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    return value if isinstance(value, str) else ""


def _validate_policy_shape(
    policy: dict[str, Any], errors: list[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if policy.get("schema_version") != 1:
        errors.append("policy schema_version must be 1")
    if policy.get("kind") != "public_product_freshness_policy":
        errors.append("policy kind must be public_product_freshness_policy")

    release = policy.get("release")
    freshness = policy.get("freshness")
    if not isinstance(release, dict):
        errors.append("policy.release must be a mapping")
        release = {}
    if not isinstance(freshness, dict):
        errors.append("policy.freshness must be a mapping")
        freshness = {}
    return release, freshness


def evaluate_policy(
    policy: dict[str, Any],
    *,
    current_root_commit: str,
    public_commit: str | None,
    tag_target: str | None,
    public_status_lines: list[str] | None,
    evidence_text: str | None,
    require_fresh: bool = False,
) -> FreshnessResult:
    errors: list[str] = []
    release, freshness = _validate_policy_shape(policy, errors)

    version = _string_at(release, "version")
    tag = _string_at(release, "tag")
    recorded_public_commit = _string_at(release, "public_commit")
    root_evidence_commit = _string_at(release, "root_evidence_commit")
    evidence_ref = _string_at(release, "release_evidence_ref")
    status = _string_at(freshness, "status")

    if not version:
        errors.append("release.version is required")
    if not tag:
        errors.append("release.tag is required")
    if not HEX40_RE.match(recorded_public_commit):
        errors.append("release.public_commit must be a 40-character lowercase git commit")
    if not HEX40_RE.match(root_evidence_commit):
        errors.append("release.root_evidence_commit must be a 40-character lowercase git commit")
    if not evidence_ref:
        errors.append("release.release_evidence_ref is required")
    if status not in VALID_STATUSES:
        errors.append(f"freshness.status must be one of {sorted(VALID_STATUSES)}")

    if evidence_text is None:
        errors.append(f"release evidence is missing: {evidence_ref}")
    elif recorded_public_commit and recorded_public_commit not in evidence_text:
        errors.append("release evidence does not mention release.public_commit")
    elif version and version not in evidence_text:
        errors.append("release evidence does not mention release.version")

    if public_commit and recorded_public_commit and public_commit != recorded_public_commit:
        errors.append(
            f"public checkout HEAD {public_commit} does not match recorded public_commit {recorded_public_commit}"
        )
    if tag_target and recorded_public_commit and tag_target != recorded_public_commit:
        errors.append(
            f"public tag target {tag_target} does not match recorded public_commit {recorded_public_commit}"
        )
    if public_status_lines and _non_branch_status_lines(public_status_lines):
        errors.append("public azoth checkout is dirty; use a clean checkout for freshness checks")

    if require_fresh and status != "fresh":
        errors.append("fresh public release claim requires freshness.status=fresh")

    if status == "fresh" and current_root_commit != root_evidence_commit:
        errors.append(
            "fresh public release claim is stale: current root HEAD does not match root_evidence_commit"
        )
    if status == "intentionally_stale":
        if freshness.get("published_release_is_authority") is not True:
            errors.append("intentionally_stale policy must set published_release_is_authority=true")
        if freshness.get("root_workshop_drift_is_advisory_only") is not True:
            errors.append(
                "intentionally_stale policy must set root_workshop_drift_is_advisory_only=true"
            )
        if not _string_at(freshness, "rationale"):
            errors.append("intentionally_stale policy requires freshness.rationale")
        if not _string_at(freshness, "next_public_sync_gate"):
            errors.append("intentionally_stale policy requires freshness.next_public_sync_gate")

    return FreshnessResult(
        status=status or "unknown", version=version or "unknown", errors=tuple(errors)
    )


def check_public_release_freshness(
    *,
    root: Path = ROOT,
    public_root: Path = DEFAULT_PUBLIC_ROOT,
    policy_path: Path = DEFAULT_POLICY,
    require_fresh: bool = False,
    skip_public_git: bool = False,
) -> FreshnessResult:
    policy = _load_yaml_mapping(policy_path)
    release = policy.get("release") if isinstance(policy.get("release"), dict) else {}
    evidence_ref = _string_at(release, "release_evidence_ref")
    evidence_path = root / evidence_ref if evidence_ref else root / "__missing_release_evidence__"
    evidence_text = evidence_path.read_text(encoding="utf-8") if evidence_path.is_file() else None

    public_commit: str | None = None
    tag_target: str | None = None
    public_status_lines: list[str] | None = None
    if not skip_public_git:
        if not public_root.is_dir():
            return FreshnessResult(
                status="unknown",
                version=_string_at(release, "version") or "unknown",
                errors=(f"public repo not found: {public_root}",),
            )
        public_commit = _current_commit(public_root)
        tag = _string_at(release, "tag")
        tag_target = _tag_target(public_root, tag) if tag else None
        public_status_lines = _status_lines(public_root)

    current_root_commit = _current_commit(root)
    return evaluate_policy(
        policy,
        current_root_commit=current_root_commit,
        public_commit=public_commit,
        tag_target=tag_target,
        public_status_lines=public_status_lines,
        evidence_text=evidence_text,
        require_fresh=require_fresh,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--public-root", type=Path, default=DEFAULT_PUBLIC_ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument(
        "--require-fresh",
        action="store_true",
        help="Fail unless the policy marks the public product freshly synchronized with current root.",
    )
    parser.add_argument(
        "--skip-public-git",
        action="store_true",
        help="Skip live public checkout git checks; intended for focused unit tests only.",
    )
    args = parser.parse_args()

    try:
        result = check_public_release_freshness(
            root=args.root,
            public_root=args.public_root,
            policy_path=args.policy,
            require_fresh=args.require_fresh,
            skip_public_git=args.skip_public_git,
        )
    except (FileNotFoundError, RuntimeError, yaml.YAMLError) as exc:
        print(f"public release freshness FAILED: {exc}", file=sys.stderr)
        return 1

    if not result.ok:
        print("public release freshness FAILED", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"public release freshness OK: {result.version} status={result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
