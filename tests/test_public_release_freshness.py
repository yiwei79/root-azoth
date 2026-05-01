from __future__ import annotations

import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "public_release_freshness.py"
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40


def _load_module():
    spec = spec_from_file_location("public_release_freshness", SCRIPT)
    mod = module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _policy(status: str = "intentionally_stale") -> dict:
    return {
        "schema_version": 1,
        "kind": "public_product_freshness_policy",
        "release": {
            "version": "v0.2.0",
            "tag": "v0.2.0",
            "public_commit": COMMIT_A,
            "root_evidence_commit": COMMIT_A,
            "release_evidence_ref": "release.md",
        },
        "freshness": {
            "status": status,
            "published_release_is_authority": True,
            "root_workshop_drift_is_advisory_only": True,
            "rationale": "Root has approved post-release workshop drift.",
            "next_public_sync_gate": "Run extraction and publish a new approved release.",
        },
    }


def test_intentionally_stale_policy_allows_advisory_root_drift() -> None:
    mod = _load_module()

    result = mod.evaluate_policy(
        _policy(),
        current_root_commit=COMMIT_B,
        public_commit=COMMIT_A,
        tag_target=COMMIT_A,
        public_status_lines=["## main"],
        evidence_text=f"v0.2.0 {COMMIT_A}",
    )

    assert result.ok
    assert result.status == "intentionally_stale"


def test_require_fresh_rejects_intentionally_stale_policy() -> None:
    mod = _load_module()

    result = mod.evaluate_policy(
        _policy(),
        current_root_commit=COMMIT_B,
        public_commit=COMMIT_A,
        tag_target=COMMIT_A,
        public_status_lines=["## main"],
        evidence_text=f"v0.2.0 {COMMIT_A}",
        require_fresh=True,
    )

    assert not result.ok
    assert "requires freshness.status=fresh" in "\n".join(result.errors)


def test_fresh_policy_fails_when_root_moved_past_extraction_evidence() -> None:
    mod = _load_module()

    result = mod.evaluate_policy(
        _policy(status="fresh"),
        current_root_commit=COMMIT_B,
        public_commit=COMMIT_A,
        tag_target=COMMIT_A,
        public_status_lines=["## main"],
        evidence_text=f"v0.2.0 {COMMIT_A}",
    )

    assert not result.ok
    assert "current root HEAD does not match root_evidence_commit" in "\n".join(result.errors)


def test_intentionally_stale_requires_advisory_flag() -> None:
    mod = _load_module()
    policy = _policy()
    policy["freshness"]["root_workshop_drift_is_advisory_only"] = False

    result = mod.evaluate_policy(
        policy,
        current_root_commit=COMMIT_B,
        public_commit=COMMIT_A,
        tag_target=COMMIT_A,
        public_status_lines=["## main"],
        evidence_text=f"v0.2.0 {COMMIT_A}",
    )

    assert not result.ok
    assert "root_workshop_drift_is_advisory_only=true" in "\n".join(result.errors)


def test_live_policy_passes_without_public_git() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-public-git"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "status=intentionally_stale" in result.stdout


def test_policy_file_is_valid_yaml() -> None:
    policy_path = (
        ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "PUBLIC-AZOTH-FRESHNESS-POLICY.yaml"
    )
    loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    assert loaded["kind"] == "public_product_freshness_policy"
