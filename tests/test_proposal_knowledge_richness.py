from __future__ import annotations

import importlib
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

    assert result["score"] >= 70
    assert result["dimensions"]["source_quality"]["score"] >= 10
    assert result["dimensions"]["validation_readiness"]["score"] >= 7
    assert "source_quality" not in result["gaps"]


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
