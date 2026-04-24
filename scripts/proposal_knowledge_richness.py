#!/usr/bin/env python3
"""Score advisory knowledge richness for Azoth architecture proposals."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


ArtifactScorer = Callable[[dict[str, Any], Optional[str]], dict[str, Any]]


@dataclass(frozen=True)
class ArtifactRichnessAdapter:
    artifact_type: str
    dimension_max: dict[str, int]
    evaluate: ArtifactScorer


DIMENSION_MAX = {
    "evidence_breadth": 18,
    "source_quality": 14,
    "claim_traceability": 14,
    "alternatives_and_challenge": 14,
    "operational_specificity": 14,
    "validation_readiness": 10,
    "freshness_and_staleness": 8,
    "empirical_replay": 8,
}

INITIATIVE_BANK_DIMENSION_MAX = {
    "evidence_source_quality": 18,
    "insight_traceability": 18,
    "outcome_opportunity_solution_alignment": 18,
    "assumption_coverage": 16,
    "decision_context_and_alternatives": 16,
    "freshness_and_lifecycle_state": 14,
}

INITIATIVE_BANK_NON_TRANSFERABLE_DIMENSIONS = [
    "operational_specificity",
    "validation_readiness",
    "empirical_replay",
]


def _list_at(data: dict[str, Any], *keys: str) -> list[Any]:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def _dict_at(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _contains_text(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle.casefold() in value.casefold()
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return False


def _cap(points: int, maximum: int) -> int:
    return max(0, min(points, maximum))


def _dimension(score: int, maximum: int, reasons: list[str]) -> dict[str, Any]:
    return {"score": _cap(score, maximum), "max": maximum, "reasons": reasons}


def _candidate_for(doc: dict[str, Any], candidate_id: str | None) -> dict[str, Any]:
    candidates = _list_at(doc, "candidate_slices")
    if candidate_id:
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
                return candidate
        return {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return {}


def _candidate_metadata(
    doc: dict[str, Any], candidate: dict[str, Any], candidate_id: str | None
) -> dict[str, Any]:
    return {
        "initiative_id": doc.get("initiative_id"),
        "candidate_id": candidate.get("candidate_id") or candidate_id,
        "candidate_status": candidate.get("status"),
        "candidate_task_ref": candidate.get("proposed_task_id"),
        "candidate_title": candidate.get("title"),
        "target_layer": candidate.get("target_layer"),
        "delivery_pipeline": candidate.get("delivery_pipeline"),
    }


def _score_evidence_breadth(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    refined = _dict_at(details, "refined_contract")
    external_sources = _list_at(refined, "external_source_alignment", "sources")
    candidate_surfaces = _list_at(details, "candidate_surfaces")
    decision_refs = doc.get("decision_refs") if isinstance(doc.get("decision_refs"), list) else []
    research_questions = _list_at(details, "suggested_future_research_session", "questions")
    local_pack_refs = _list_at(refined, "external_source_alignment", "implications")

    score = 0
    reasons: list[str] = []
    score += _cap(len(external_sources) * 2, 8)
    reasons.append(f"{len(external_sources)} external source(s)")
    score += _cap(len(candidate_surfaces), 5)
    reasons.append(f"{len(candidate_surfaces)} repo surface(s)")
    score += 3 if len(decision_refs) >= 3 else len(decision_refs)
    reasons.append(f"{len(decision_refs)} decision ref(s)")
    score += 2 if research_questions else 0
    if research_questions:
        reasons.append("future research questions present")
    score += 2 if local_pack_refs else 0
    if local_pack_refs:
        reasons.append("source implications recorded")
    return _dimension(score, DIMENSION_MAX["evidence_breadth"], reasons)


def _score_source_quality(doc: dict[str, Any]) -> dict[str, Any]:
    sources = _list_at(doc, "details", "refined_contract", "external_source_alignment", "sources")
    reasons: list[str] = []
    score = 0
    urls = [str(item.get("url") or "") for item in sources if isinstance(item, dict)]
    titled = [item for item in sources if isinstance(item, dict) and _has_text(item.get("title"))]
    findings = [item for item in sources if isinstance(item, dict) and _has_text(item.get("finding"))]
    http_urls = [url for url in urls if url.startswith(("https://", "http://"))]
    officialish = [
        url
        for url in http_urls
        if any(host in url for host in ("atlassian.com", "cloud.google.com", "producttalk.org"))
    ]
    score += _cap(len(http_urls) * 2, 6)
    score += _cap(len(titled), 3)
    score += _cap(len(findings), 3)
    score += _cap(len(officialish), 3)
    reasons.append(f"{len(http_urls)} http source url(s)")
    reasons.append(f"{len(findings)} source finding(s)")
    reasons.append(f"{len(officialish)} recognized primary or domain-authoritative source(s)")
    return _dimension(score, DIMENSION_MAX["source_quality"], reasons)


def _score_claim_traceability(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    refined = _dict_at(details, "refined_contract")
    score = 0
    reasons: list[str] = []
    if _list_at(details, "candidate_surfaces"):
        score += 4
        reasons.append("candidate surfaces named")
    if _list_at(refined, "external_source_alignment", "implications"):
        score += 4
        reasons.append("external implications connected to proposal")
    if _dict_at(refined, "artifact_boundary"):
        score += 3
        reasons.append("artifact boundary records claim ownership")
    if _dict_at(refined, "hydration_handoff"):
        score += 2
        reasons.append("hydration handoff grounded in existing tool paths")
    if _list_at(details, "suggested_future_research_session", "questions"):
        score += 2
        reasons.append("open questions are explicit")
    return _dimension(score, DIMENSION_MAX["claim_traceability"], reasons)


def _score_alternatives(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    command_options = _dict_at(details, "command_surface_options")
    refined = _dict_at(details, "refined_contract")
    score = 0
    reasons: list[str] = []
    option_count = len([key for key in command_options if key.startswith("option_")])
    score += _cap(option_count * 2, 6)
    reasons.append(f"{option_count} command option(s)")
    score += _cap(len(_list_at(details, "challenge_points")) * 2, 4)
    score += _cap(len(_list_at(details, "non_goals")), 3)
    if _list_at(_dict_at(refined, "initiative_candidate_criteria"), "non_candidates"):
        score += 2
        reasons.append("non-candidate criteria present")
    return _dimension(score, DIMENSION_MAX["alternatives_and_challenge"], reasons)


def _score_operational_specificity(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    refined = _dict_at(details, "refined_contract")
    score = 0
    reasons: list[str] = []
    score += _cap(len(_dict_at(details, "lifecycle")), 4)
    reasons.append(f"{len(_dict_at(details, 'lifecycle'))} lifecycle step(s)")
    score += 3 if _dict_at(details, "artifact_contract") else 0
    score += 3 if _dict_at(details, "governance") else 0
    score += 3 if _dict_at(refined, "command_policy") else 0
    score += 2 if _dict_at(refined, "hydration_handoff") else 0
    return _dimension(score, DIMENSION_MAX["operational_specificity"], reasons)


def _score_validation_readiness(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    refined = _dict_at(details, "refined_contract")
    readiness_schema = _dict_at(refined, "readiness_report_schema")
    score = 0
    reasons: list[str] = []
    fields = _list_at(readiness_schema, "minimal_fields")
    score += _cap(len(fields) // 2, 5)
    reasons.append(f"{len(fields)} readiness field(s)")
    score += _cap(len(_list_at(readiness_schema, "fail_closed_rules")), 3)
    score += 2 if _list_at(details, "readiness_rubric", "pass_conditions") else 0
    if "human_decision" in fields:
        reasons.append("human decision captured in readiness schema")
    return _dimension(score, DIMENSION_MAX["validation_readiness"], reasons)


def _score_freshness(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    refined = _dict_at(details, "refined_contract")
    source_alignment = _dict_at(refined, "external_source_alignment")
    readiness_schema = _dict_at(refined, "readiness_report_schema")
    score = 0
    reasons: list[str] = []
    if _has_text(source_alignment.get("observed_at")):
        score += 3
        reasons.append("external observed_at recorded")
    if "freshness_status" in _list_at(readiness_schema, "minimal_fields"):
        score += 3
        reasons.append("freshness status is a readiness field")
    if _contains_text(readiness_schema, "stale"):
        score += 2
        reasons.append("stale evidence fail rule present")
    if _contains_text(doc, "contradiction"):
        score += 2
        reasons.append("contradiction handling present")
    return _dimension(score, DIMENSION_MAX["freshness_and_staleness"], reasons)


def _score_empirical_replay(doc: dict[str, Any]) -> dict[str, Any]:
    details = _dict_at(doc, "details")
    score = 0
    reasons: list[str] = []
    replay = details.get("validation_replay")
    worked_examples = details.get("worked_examples")
    example_scenarios = details.get("example_scenarios")
    if isinstance(replay, list):
        score += _cap(len(replay) * 3, 6)
        reasons.append(f"{len(replay)} validation replay item(s)")
    if isinstance(worked_examples, list):
        score += _cap(len(worked_examples) * 3, 6)
        reasons.append(f"{len(worked_examples)} worked example(s)")
    if isinstance(example_scenarios, list):
        score += _cap(len(example_scenarios) * 2, 4)
        reasons.append(f"{len(example_scenarios)} example scenario(s)")
    if not reasons:
        reasons.append("no validation replay or worked examples found")
    return _dimension(score, DIMENSION_MAX["empirical_replay"], reasons)


def evaluate_proposal_knowledge_richness(doc: dict[str, Any]) -> dict[str, Any]:
    """Return an advisory richness score for a parsed architecture proposal."""
    dimensions = {
        "evidence_breadth": _score_evidence_breadth(doc),
        "source_quality": _score_source_quality(doc),
        "claim_traceability": _score_claim_traceability(doc),
        "alternatives_and_challenge": _score_alternatives(doc),
        "operational_specificity": _score_operational_specificity(doc),
        "validation_readiness": _score_validation_readiness(doc),
        "freshness_and_staleness": _score_freshness(doc),
        "empirical_replay": _score_empirical_replay(doc),
    }
    total = sum(row["score"] for row in dimensions.values())
    maximum = sum(row["max"] for row in dimensions.values())
    if total >= 85:
        rating = "excellent"
    elif total >= 70:
        rating = "rich"
    elif total >= 50:
        rating = "adequate"
    else:
        rating = "thin"

    gaps = [
        name
        for name, row in dimensions.items()
        if row["score"] < int(row["max"] * 0.65)
    ]
    return {
        "score": total,
        "max": maximum,
        "rating": rating,
        "dimensions": dimensions,
        "gaps": gaps,
    }


def _score_initiative_evidence_source_quality(
    doc: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    research_refs = _list_at(doc, "research_refs")
    source_sessions = _list_at(doc, "source_sessions")
    research_questions = _list_at(doc, "research_questions")
    local_findings = _list_at(doc, "local_findings")
    external_findings = _list_at(doc, "external_findings")
    candidate_refs = candidate.get("research_evidence_refs")
    if not isinstance(candidate_refs, list):
        candidate_refs = []
    completion_refs = _list_at(doc, "research_completion_assessment", "source_pack_refs")
    score = 0
    reasons: list[str] = []
    score += _cap(len(research_refs) * 3, 6)
    score += _cap(len(source_sessions) * 2, 4)
    score += _cap(len(candidate_refs) * 2, 6)
    score += _cap(len(completion_refs) * 2, 4)
    score += 2 if local_findings else 0
    score += 2 if external_findings else 0
    score += 2 if research_questions else 0
    reasons.append(f"{len(research_refs)} research ref(s)")
    reasons.append(f"{len(candidate_refs)} candidate evidence ref(s)")
    reasons.append(f"{len(source_sessions)} source session(s)")
    if completion_refs:
        reasons.append("research completion source packs recorded")
    return _dimension(score, INITIATIVE_BANK_DIMENSION_MAX["evidence_source_quality"], reasons)


def _score_initiative_insight_traceability(
    doc: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    local_findings = _list_at(doc, "local_findings")
    external_findings = _list_at(doc, "external_findings")
    research_questions = _list_at(doc, "research_questions")
    candidate_refs = candidate.get("research_evidence_refs")
    if not isinstance(candidate_refs, list):
        candidate_refs = []
    linked_local = [
        item
        for item in local_findings
        if isinstance(item, dict) and _list_at(item, "evidence_refs")
    ]
    linked_questions = [
        item
        for item in research_questions
        if isinstance(item, dict) and _list_at(item, "evidence_refs")
    ]
    linked_external = [
        item
        for item in external_findings
        if isinstance(item, dict) and _has_text(item.get("source_ref"))
    ]
    score = 0
    reasons: list[str] = []
    score += _cap(len(linked_local) * 2, 6)
    score += _cap(len(linked_external) * 2, 6)
    score += _cap(len(linked_questions) * 2, 6)
    score += _cap(len(candidate_refs), 4)
    score += 2 if _has_text(candidate.get("summary")) else 0
    reasons.append(f"{len(linked_local)} local finding(s) with evidence refs")
    reasons.append(f"{len(linked_external)} external finding(s) with source refs")
    reasons.append(f"{len(linked_questions)} research question(s) with evidence refs")
    return _dimension(score, INITIATIVE_BANK_DIMENSION_MAX["insight_traceability"], reasons)


def _score_initiative_alignment(doc: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    readiness = _dict_at(doc, "readiness")
    acceptance = candidate.get("acceptance_criteria")
    non_goals = candidate.get("known_non_goals")
    open_questions = candidate.get("open_questions")
    score = 0
    reasons: list[str] = []
    if _has_text(doc.get("title")) and _has_text(candidate.get("title")):
        score += 3
        reasons.append("initiative and candidate titles present")
    if _has_text(candidate.get("summary")):
        score += 3
        reasons.append("candidate summary present")
    if isinstance(acceptance, list) and acceptance:
        score += _cap(len(acceptance) * 2, 6)
        reasons.append(f"{len(acceptance)} acceptance criteria item(s)")
    if isinstance(non_goals, list) and non_goals:
        score += 2
        reasons.append("candidate non-goals present")
    if isinstance(open_questions, list) and not open_questions:
        score += 2
        reasons.append("candidate open questions are closed")
    if _has_text(candidate.get("target_layer")) and _has_text(candidate.get("delivery_pipeline")):
        score += 2
        reasons.append("delivery layer and pipeline recorded")
    if readiness.get("candidate_first_slice") == candidate.get("candidate_id"):
        score += 2
        reasons.append("readiness points to selected candidate")
    return _dimension(
        score,
        INITIATIVE_BANK_DIMENSION_MAX["outcome_opportunity_solution_alignment"],
        reasons,
    )


def _score_initiative_assumption_coverage(
    doc: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    assumptions = _list_at(doc, "assumptions")
    contradictions = _list_at(doc, "contradictions")
    challenge_log = _list_at(doc, "challenge_log")
    known_non_goals = candidate.get("known_non_goals")
    open_questions = candidate.get("open_questions")
    score = 0
    reasons: list[str] = []
    score += _cap(len(assumptions) * 3, 6)
    score += _cap(len(challenge_log) * 2, 6)
    if isinstance(known_non_goals, list) and known_non_goals:
        score += 3
        reasons.append("candidate non-goals constrain assumptions")
    if isinstance(open_questions, list) and not open_questions:
        score += 2
        reasons.append("candidate open questions are explicitly closed")
    if contradictions:
        score += 2
        reasons.append("contradiction register present")
    reasons.append(f"{len(assumptions)} assumption(s)")
    reasons.append(f"{len(challenge_log)} challenge log item(s)")
    return _dimension(score, INITIATIVE_BANK_DIMENSION_MAX["assumption_coverage"], reasons)


def _score_initiative_decision_context(
    doc: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    readiness = _dict_at(doc, "readiness")
    hydration_plan = _dict_at(candidate, "hydration_plan")
    hydration_history = _list_at(doc, "hydration_history")
    challenge_log = _list_at(doc, "challenge_log")
    score = 0
    reasons: list[str] = []
    if _has_text(readiness.get("human_decision")):
        score += 3
        reasons.append("human decision recorded")
    if _has_text(readiness.get("hydration_recommendation")):
        score += 3
        reasons.append("hydration recommendation recorded")
    if _list_at(hydration_plan, "pre_hydration_requirements"):
        score += 3
        reasons.append("pre-hydration requirements recorded")
    if _has_text(hydration_plan.get("hydrated_task_ref")):
        score += 2
        reasons.append("hydrated task ref recorded")
    if hydration_history:
        score += _cap(len(hydration_history) * 2, 4)
        reasons.append(f"{len(hydration_history)} hydration history item(s)")
    if challenge_log:
        score += 2
        reasons.append("challenge log preserves alternatives")
    return _dimension(
        score,
        INITIATIVE_BANK_DIMENSION_MAX["decision_context_and_alternatives"],
        reasons,
    )


def _score_initiative_freshness(doc: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    readiness = _dict_at(doc, "readiness")
    completion = _dict_at(doc, "research_completion_assessment")
    score = 0
    reasons: list[str] = []
    if _has_text(doc.get("updated_at")):
        score += 3
        reasons.append("initiative updated_at recorded")
    if _has_text(readiness.get("evaluated_at")):
        score += 3
        reasons.append("readiness evaluated_at recorded")
    if _has_text(readiness.get("freshness_status")):
        score += 3
        reasons.append("freshness status recorded")
    if _has_text(completion.get("completed_at")):
        score += 2
        reasons.append("research completion timestamp recorded")
    if _has_text(candidate.get("status")):
        score += 2
        reasons.append("candidate lifecycle status recorded")
    if _list_at(doc, "hydration_history"):
        score += 2
        reasons.append("hydration lifecycle history present")
    return _dimension(
        score,
        INITIATIVE_BANK_DIMENSION_MAX["freshness_and_lifecycle_state"],
        reasons,
    )


def evaluate_initiative_bank_knowledge_richness(
    doc: dict[str, Any], candidate_id: str | None = None
) -> dict[str, Any]:
    """Return a soft-fail advisory richness report for an initiative bank."""
    candidate = _candidate_for(doc, candidate_id)
    dimensions = {
        "evidence_source_quality": _score_initiative_evidence_source_quality(doc, candidate),
        "insight_traceability": _score_initiative_insight_traceability(doc, candidate),
        "outcome_opportunity_solution_alignment": _score_initiative_alignment(doc, candidate),
        "assumption_coverage": _score_initiative_assumption_coverage(doc, candidate),
        "decision_context_and_alternatives": _score_initiative_decision_context(doc, candidate),
        "freshness_and_lifecycle_state": _score_initiative_freshness(doc, candidate),
    }
    total = sum(row["score"] for row in dimensions.values())
    maximum = sum(row["max"] for row in dimensions.values())
    if total >= 85:
        rating = "excellent"
    elif total >= 70:
        rating = "rich"
    elif total >= 50:
        rating = "adequate"
    else:
        rating = "thin"

    gaps = [
        name
        for name, row in dimensions.items()
        if row["score"] < int(row["max"] * 0.65)
    ]
    if not candidate:
        gaps.append("candidate_metadata")
    if doc.get("bank_type") != "initiative":
        gaps.append("bank_type")
    if not _has_text(doc.get("initiative_id")):
        gaps.append("initiative_id")

    return {
        "artifact_type": "initiative_bank",
        "advisory_only": True,
        "blocking": False,
        "score": total,
        "max": maximum,
        "rating": rating,
        "dimensions": dimensions,
        "non_transferable_dimensions": INITIATIVE_BANK_NON_TRANSFERABLE_DIMENSIONS,
        "gaps": sorted(set(gaps), key=gaps.index),
        "candidate": _candidate_metadata(doc, candidate, candidate_id),
    }


def evaluate_artifact_knowledge_richness(
    doc: dict[str, Any],
    *,
    artifact_type: str = "proposal",
    candidate_id: str | None = None,
) -> dict[str, Any]:
    normalized_type = artifact_type.replace("-", "_")
    adapter = ARTIFACT_RICHNESS_ADAPTERS.get(normalized_type)
    if adapter is None:
        supported = ", ".join(sorted(ARTIFACT_RICHNESS_ADAPTERS))
        raise ValueError(f"unsupported artifact_type {artifact_type!r}; expected one of: {supported}")
    return adapter.evaluate(doc, candidate_id)


def _score_proposal_adapter(doc: dict[str, Any], candidate_id: str | None = None) -> dict[str, Any]:
    del candidate_id
    return evaluate_proposal_knowledge_richness(doc)


ARTIFACT_RICHNESS_ADAPTERS = {
    "proposal": ArtifactRichnessAdapter(
        artifact_type="proposal",
        dimension_max=DIMENSION_MAX,
        evaluate=_score_proposal_adapter,
    ),
    "initiative_bank": ArtifactRichnessAdapter(
        artifact_type="initiative_bank",
        dimension_max=INITIATIVE_BANK_DIMENSION_MAX,
        evaluate=evaluate_initiative_bank_knowledge_richness,
    ),
}


def load_proposal(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"proposal_knowledge_richness: root must be a mapping: {path}")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description="Score proposal knowledge richness.")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--artifact-type",
        choices=("proposal", "initiative-bank"),
        default="proposal",
        help="Artifact scorer to use. Defaults to proposal.",
    )
    parser.add_argument(
        "--candidate-id",
        help="Candidate slice id for initiative-bank scoring.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = evaluate_artifact_knowledge_richness(
        load_proposal(args.path),
        artifact_type=args.artifact_type,
        candidate_id=args.candidate_id,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(f"score: {result['score']}/{result['max']} ({result['rating']})")
    if result.get("advisory_only"):
        print("advisory-only: true")
    if result.get("artifact_type"):
        print(f"artifact_type: {result['artifact_type']}")
    candidate = result.get("candidate")
    if isinstance(candidate, dict) and candidate.get("candidate_id"):
        print(f"candidate_id: {candidate['candidate_id']}")
    if result["gaps"]:
        print("gaps: " + ", ".join(result["gaps"]))
    for name, row in result["dimensions"].items():
        print(f"- {name}: {row['score']}/{row['max']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
