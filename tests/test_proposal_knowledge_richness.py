from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module():
    return importlib.import_module("proposal_knowledge_richness")


def _minimal_doc() -> dict:
    return {
        "proposal_schema_version": 1,
        "created_at": "2026-04-24T00:00:00+00:00",
        "session_id": "test",
        "backlog_id": "P6-003",
        "title": "Thin proposal",
        "summary": "Thin proposal.",
        "status": "draft",
        "decision_refs": ["D47"],
        "scope_layers": ["docs"],
        "details": {},
    }


def test_minimal_proposal_scores_thin() -> None:
    result = _load_module().evaluate_proposal_knowledge_richness(_minimal_doc())

    assert result["rating"] == "thin"
    assert result["score"] < 50
    assert "evidence_breadth" in result["gaps"]


def test_initiative_discovery_proposal_scores_rich() -> None:
    proposal = yaml.safe_load(
        (ROOT / ".azoth" / "proposals" / "initiative-discovery-to-roadmap-hydration.yaml")
        .read_text(encoding="utf-8")
    )

    result = _load_module().evaluate_proposal_knowledge_richness(proposal)

    assert result["score"] == 100
    assert result["max"] == 100
    assert result["rating"] == "excellent"
    assert list(result["dimensions"]) == [
        "evidence_breadth",
        "source_quality",
        "claim_traceability",
        "alternatives_and_challenge",
        "operational_specificity",
        "validation_readiness",
        "freshness_and_staleness",
        "empirical_replay",
    ]
    assert result["gaps"] == []


def test_initiative_bank_adapter_reports_advisory_dimensions() -> None:
    bank = yaml.safe_load(
        (ROOT / ".azoth" / "initiative-banks" / "INI-EVI-002.yaml").read_text(encoding="utf-8")
    )

    result = _load_module().evaluate_artifact_knowledge_richness(
        bank,
        artifact_type="initiative_bank",
        candidate_id="slice-evi-002-b",
    )

    assert result["artifact_type"] == "initiative_bank"
    assert result["advisory_only"] is True
    assert result["blocking"] is False
    assert list(result["dimensions"]) == [
        "evidence_source_quality",
        "insight_traceability",
        "outcome_opportunity_solution_alignment",
        "assumption_coverage",
        "decision_context_and_alternatives",
        "freshness_and_lifecycle_state",
    ]
    assert result["candidate"] == {
        "initiative_id": "INI-EVI-002",
        "candidate_id": "slice-evi-002-b",
        "candidate_status": "complete",
        "candidate_task_ref": "T-019",
        "candidate_title": "Generalize proposal richness scoring into artifact-class adapters",
        "target_layer": "infrastructure",
        "delivery_pipeline": "standard",
    }
    assert result["non_transferable_dimensions"] == [
        "operational_specificity",
        "validation_readiness",
        "empirical_replay",
    ]


def test_initiative_bank_adapter_soft_fails_thin_docs() -> None:
    result = _load_module().evaluate_artifact_knowledge_richness(
        {"bank_type": "initiative"},
        artifact_type="initiative_bank",
        candidate_id="missing-candidate",
    )

    assert result["advisory_only"] is True
    assert result["blocking"] is False
    assert result["rating"] == "thin"
    assert result["score"] < 50
    assert "candidate_metadata" in result["gaps"]
    assert "initiative_id" in result["gaps"]


def test_cli_emits_summary(tmp_path: Path) -> None:
    path = tmp_path / "proposal.yaml"
    path.write_text(yaml.safe_dump(_minimal_doc()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "proposal_knowledge_richness.py"), str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "score:" in result.stdout
    assert "evidence_breadth" in result.stdout


def test_cli_emits_initiative_bank_json_report() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "proposal_knowledge_richness.py"),
            str(ROOT / ".azoth" / "initiative-banks" / "INI-EVI-002.yaml"),
            "--artifact-type",
            "initiative-bank",
            "--candidate-id",
            "slice-evi-002-b",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["artifact_type"] == "initiative_bank"
    assert report["candidate"]["candidate_id"] == "slice-evi-002-b"
    assert report["advisory_only"] is True
