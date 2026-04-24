#!/usr/bin/env python3
"""Score advisory knowledge richness for Azoth architecture proposals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


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


def load_proposal(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"proposal_knowledge_richness: root must be a mapping: {path}")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description="Score proposal knowledge richness.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = evaluate_proposal_knowledge_richness(load_proposal(args.path))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(f"score: {result['score']}/{result['max']} ({result['rating']})")
    if result["gaps"]:
        print("gaps: " + ", ".join(result["gaps"]))
    for name, row in result["dimensions"].items():
        print(f"- {name}: {row['score']}/{row['max']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
