#!/usr/bin/env python3
"""Deterministic zero-dependency recall quality scorer for M3/M2 memory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from episode_store import EpisodeStoreError, load_episode_records
from yaml_helpers import safe_load_yaml_path


SCHEMA_VERSION = 1
QUERY_PACKET_TYPE = "context_recall_quality_query"
FIXTURE_PACKET_TYPE = "context_recall_quality_fixture_eval"
ADVISORY_AUTHORITY = "advisory_context_not_governing_instruction"
DEFAULT_EPISODES_PATH = Path(".azoth/memory/episodes.jsonl")
DEFAULT_PATTERNS_PATH = Path(".azoth/memory/patterns.yaml")
TOKEN_WEIGHT = 0.6
M2_TAG_WEIGHT = 0.5
M3_TAG_WEIGHT = 2.0
M2_TRIGGER_WEIGHT = 3.0
REINFORCEMENT_WEIGHT = 0.5
EPOCH = datetime(1970, 1, 1)
COMPONENT_KEYS = (
    "tag_overlap",
    "token_overlap",
    "recency_bonus",
    "reinforcement_bonus",
    "pattern_trigger_bonus",
    "total",
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "or",
    "session",
    "sessions",
    "the",
    "to",
    "with",
}


class RecallQualityError(RuntimeError):
    """Raised when recall-quality fixtures or inputs are invalid."""


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if not token or token in STOPWORDS:
            continue
        tokens.add(token)
        if len(token) <= 4:
            continue
        if token.endswith("ions"):
            tokens.add(token[:-4])
        elif token.endswith("ion"):
            tokens.add(token[:-3])
        elif token.endswith("ing"):
            tokens.add(token[:-3])
        elif token.endswith("ed"):
            tokens.add(token[:-2])
        elif token.endswith("s"):
            tokens.add(token[:-1])
    return tokens


def _normalize_tag(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _parse_datetime(value: Any, *, field_name: str) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RecallQualityError(f"invalid {field_name}: {value!r}") from exc
    else:
        return None

    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_as_of(as_of: str | datetime | date | None) -> tuple[datetime, str]:
    if as_of is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return now, now.replace(microsecond=0).isoformat() + "Z"
    parsed = _parse_datetime(as_of, field_name="as_of")
    if parsed is None:
        raise RecallQualityError("as_of must be non-empty when provided")
    if isinstance(as_of, str):
        return parsed, as_of.strip()
    return parsed, parsed.isoformat()


def _days_since(timestamp: datetime | None, as_of: datetime) -> int | None:
    if timestamp is None:
        return None
    return (as_of.date() - timestamp.date()).days


def _recency_bonus(timestamp: datetime | None, as_of: datetime) -> float:
    days = _days_since(timestamp, as_of)
    if days is None:
        return 0.0
    return 1.0 / max(days, 0.5)


def _timestamp_sort_value(timestamp: datetime | None) -> float:
    if timestamp is None:
        return 0.0
    return (timestamp - EPOCH).total_seconds()


def _round_score(value: float) -> float:
    return round(value, 6)


def _component_total(components: dict[str, float]) -> float:
    return _round_score(
        float(components["tag_overlap"])
        + float(components["token_overlap"])
        + float(components["recency_bonus"])
        + float(components["reinforcement_bonus"])
        + float(components["pattern_trigger_bonus"])
    )


def _candidate_text(values: list[Any]) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value if isinstance(item, (str, int, float)))
    return " ".join(parts)


def _positive_reasons(components: dict[str, float]) -> list[str]:
    reasons = [key for key in COMPONENT_KEYS if key != "total" and components.get(key, 0.0) > 0]
    return reasons


def _freshness_status(record: dict[str, Any]) -> str:
    context = record.get("context")
    if isinstance(context, dict) and context.get("freshness_status"):
        return str(context["freshness_status"])
    status = str(record.get("status") or "").strip().lower()
    if status in {"archived", "archive", "stale", "superseded"}:
        return status
    return "current"


def _conflict_status(record: dict[str, Any]) -> str:
    context = record.get("context")
    if isinstance(context, dict) and context.get("conflict_status"):
        return str(context["conflict_status"])
    superseded_by = None
    if isinstance(context, dict):
        superseded_by = context.get("superseded_by") or context.get("corrected_by")
    if superseded_by:
        return f"superseded_by:{superseded_by}"
    return "none"


def _base_score_components() -> dict[str, float]:
    return {key: 0.0 for key in COMPONENT_KEYS}


def _score_m3_episode(
    record: dict[str, Any],
    *,
    query_tokens: set[str],
    query_tags: set[str],
    as_of: datetime,
    source_ref: str,
) -> dict[str, Any] | None:
    timestamp_text = str(record.get("timestamp") or "")
    timestamp = _parse_datetime(timestamp_text, field_name=f"{record.get('id')} timestamp")
    if timestamp is not None and timestamp > as_of:
        return None

    tags = _as_string_list(record.get("tags"))
    normalized_tags = {_normalize_tag(tag) for tag in tags}
    tag_overlap_count = len(query_tags & normalized_tags)
    text = _candidate_text(
        [
            record.get("goal"),
            record.get("summary"),
            record.get("lessons"),
            tags,
            record.get("type"),
        ]
    )
    token_overlap_count = len(query_tokens & _tokens(text))
    if tag_overlap_count == 0 and token_overlap_count < 2:
        return None

    components = _base_score_components()
    components["tag_overlap"] = _round_score(tag_overlap_count * M3_TAG_WEIGHT)
    components["token_overlap"] = _round_score(token_overlap_count * TOKEN_WEIGHT)
    components["recency_bonus"] = _round_score(_recency_bonus(timestamp, as_of))
    components["reinforcement_bonus"] = _round_score(
        int(record.get("reinforcement_count") or 0) * REINFORCEMENT_WEIGHT
    )
    components["total"] = _component_total(components)

    return {
        "source_type": "m3_episode",
        "id": str(record.get("id") or ""),
        "source_ref": f"{source_ref}#{record.get('id')}",
        "summary": str(record.get("summary") or ""),
        "timestamp": timestamp_text,
        "timestamp_sort": _timestamp_sort_value(timestamp),
        "tags": tags,
        "score_total": components["total"],
        "score_components": components,
        "match_reasons": _positive_reasons(components),
        "freshness_status": _freshness_status(record),
        "conflict_status": _conflict_status(record),
        "advisory_authority": ADVISORY_AUTHORITY,
    }


def _pattern_timestamp(pattern: dict[str, Any]) -> tuple[str, datetime | None]:
    timestamp_text = str(
        pattern.get("approved_date") or pattern.get("updated_at") or pattern.get("timestamp") or ""
    )
    return timestamp_text, _parse_datetime(timestamp_text, field_name=f"{pattern.get('id')} date")


def _score_m2_pattern(
    pattern: dict[str, Any],
    *,
    query_tokens: set[str],
    query_tags: set[str],
    as_of: datetime,
    source_ref: str,
) -> dict[str, Any] | None:
    timestamp_text, timestamp = _pattern_timestamp(pattern)
    if timestamp is not None and timestamp > as_of:
        return None

    pattern_id = str(pattern.get("id") or "").strip()
    trigger = str(pattern.get("trigger") or "")
    tags = _as_string_list(pattern.get("tags"))
    text = _candidate_text(
        [
            trigger,
            pattern.get("summary"),
            pattern.get("why_it_matters"),
            pattern.get("how_to_apply"),
            tags,
        ]
    )
    normalized_text = _normalize_tag(text)
    trigger_text = _normalize_tag(trigger)
    trigger_match = any(tag and tag in trigger_text for tag in query_tags)
    tag_overlap_count = sum(1 for tag in query_tags if tag and tag in normalized_text)
    token_overlap_count = len(query_tokens & _tokens(text))
    if not trigger_match and tag_overlap_count == 0 and token_overlap_count < 2:
        return None

    reinforced_by = pattern.get("reinforced_by")
    reinforcement_count = len(reinforced_by) if isinstance(reinforced_by, list) else 0
    components = _base_score_components()
    semantic_bridge = trigger_match or tag_overlap_count > 0
    if not trigger_match:
        components["tag_overlap"] = _round_score(tag_overlap_count * M2_TAG_WEIGHT)
        components["token_overlap"] = _round_score(token_overlap_count * TOKEN_WEIGHT)
    components["reinforcement_bonus"] = _round_score(
        reinforcement_count * REINFORCEMENT_WEIGHT if semantic_bridge else 0.0
    )
    components["pattern_trigger_bonus"] = _round_score(M2_TRIGGER_WEIGHT if trigger_match else 0.0)
    components["total"] = _component_total(components)

    freshness = "current" if pattern.get("approved", True) else "archive_context_only"
    return {
        "source_type": "m2_pattern",
        "id": pattern_id,
        "source_ref": f"{source_ref}#{pattern_id}",
        "summary": str(pattern.get("summary") or ""),
        "timestamp": timestamp_text,
        "timestamp_sort": _timestamp_sort_value(timestamp),
        "tags": tags,
        "score_total": components["total"],
        "score_components": components,
        "match_reasons": _positive_reasons(components),
        "freshness_status": freshness,
        "conflict_status": str(pattern.get("conflict_status") or "none"),
        "advisory_authority": ADVISORY_AUTHORITY,
    }


def _load_patterns(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], [f"patterns file not found: {path}"]
    loaded = safe_load_yaml_path(path) or {}
    if not isinstance(loaded, dict):
        raise RecallQualityError(f"patterns root must be a mapping: {path}")
    patterns = loaded.get("patterns", [])
    if patterns is None:
        return [], []
    if not isinstance(patterns, list):
        raise RecallQualityError(f"patterns must be a list: {path}")
    usable: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, pattern in enumerate(patterns, start=1):
        if isinstance(pattern, dict):
            usable.append(pattern)
        else:
            warnings.append(f"skipped non-mapping pattern at index {index}: {path}")
    return usable, warnings


def _rank_results(candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    candidates.sort(
        key=lambda item: (
            -float(item["score_total"]),
            -float(item["timestamp_sort"]),
            str(item["source_type"]),
            str(item["id"]),
        )
    )
    results: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates[:top_k], start=1):
        result = dict(candidate)
        result.pop("timestamp_sort", None)
        result["rank"] = rank
        ordered = {
            "rank": result["rank"],
            "source_type": result["source_type"],
            "id": result["id"],
            "source_ref": result["source_ref"],
            "summary": result["summary"],
            "timestamp": result["timestamp"],
            "tags": result["tags"],
            "score_total": result["score_total"],
            "score_components": result["score_components"],
            "match_reasons": result["match_reasons"],
            "freshness_status": result["freshness_status"],
            "conflict_status": result["conflict_status"],
            "advisory_authority": result["advisory_authority"],
        }
        results.append(ordered)
    return results


def build_recall_packet(
    *,
    query: str | None = None,
    query_tags: list[str] | None = None,
    top_k: int = 3,
    as_of: str | datetime | date | None = None,
    episodes_path: Path = DEFAULT_EPISODES_PATH,
    patterns_path: Path = DEFAULT_PATTERNS_PATH,
    episodes_source_ref: str | None = None,
    patterns_source_ref: str | None = None,
) -> dict[str, Any]:
    """Return the stable JSON recall packet for one query."""
    if top_k < 1:
        raise RecallQualityError("top_k must be >= 1")

    query_text = (query or "").strip()
    tags = [tag for tag in (query_tags or []) if str(tag).strip()]
    if not query_text and not tags:
        raise RecallQualityError("query mode requires --query or --tags")

    as_of_datetime, as_of_text = _parse_as_of(as_of)
    query_token_text = " ".join([query_text, *tags])
    query_tokens = _tokens(query_token_text)
    normalized_query_tags = {_normalize_tag(tag) for tag in tags}
    episode_records = load_episode_records(episodes_path)
    patterns, warnings = _load_patterns(patterns_path)
    episodes_ref = episodes_source_ref or str(episodes_path)
    patterns_ref = patterns_source_ref or str(patterns_path)

    candidates: list[dict[str, Any]] = []
    for record in episode_records:
        candidate = _score_m3_episode(
            record,
            query_tokens=query_tokens,
            query_tags=normalized_query_tags,
            as_of=as_of_datetime,
            source_ref=episodes_ref,
        )
        if candidate is not None:
            candidates.append(candidate)
    for pattern in patterns:
        candidate = _score_m2_pattern(
            pattern,
            query_tokens=query_tokens,
            query_tags=normalized_query_tags,
            as_of=as_of_datetime,
            source_ref=patterns_ref,
        )
        if candidate is not None:
            candidates.append(candidate)

    results = _rank_results(candidates, top_k)
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_type": QUERY_PACKET_TYPE,
        "query": query_text,
        "query_tags": tags,
        "as_of": as_of_text,
        "top_k": top_k,
        "corpus": {
            "m3_episode_count": len(episode_records),
            "m2_pattern_count": len(patterns),
            "episodes_path": episodes_ref,
            "patterns_path": patterns_ref,
        },
        "results": results,
        "warnings": warnings,
        "no_match": not results,
        "advisory_authority": ADVISORY_AUTHORITY,
    }


def _load_fixture_doc(path: Path) -> dict[str, Any]:
    loaded = safe_load_yaml_path(path)
    if not isinstance(loaded, dict):
        raise RecallQualityError(f"fixture file root must be a mapping: {path}")
    return loaded


def _write_fixture_corpus(fixture: dict[str, Any], tmp_root: Path) -> tuple[Path, Path, str, str]:
    corpus = fixture.get("corpus")
    if not isinstance(corpus, dict):
        raise RecallQualityError("fixture file must include corpus for deterministic eval")
    episodes = corpus.get("episodes")
    patterns = corpus.get("patterns")
    if not isinstance(episodes, list) or not isinstance(patterns, list):
        raise RecallQualityError("fixture corpus must include episodes and patterns lists")

    episodes_path = tmp_root / "episodes.jsonl"
    patterns_path = tmp_root / "patterns.yaml"
    episodes_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in episodes),
        encoding="utf-8",
    )
    patterns_path.write_text(
        json.dumps({"patterns": patterns}, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    source_refs = corpus.get("source_refs") if isinstance(corpus.get("source_refs"), dict) else {}
    episodes_ref = str(source_refs.get("episodes") or "fixture_corpus#episodes")
    patterns_ref = str(source_refs.get("patterns") or "fixture_corpus#patterns")
    return episodes_path, patterns_path, episodes_ref, patterns_ref


def _expected_identity(value: Any) -> tuple[str | None, str]:
    if isinstance(value, dict):
        return (
            str(value.get("source_type")).strip() if value.get("source_type") else None,
            str(value.get("id") or "").strip(),
        )
    return None, str(value or "").strip()


def _result_matches(result: dict[str, Any], expected: Any) -> bool:
    source_type, item_id = _expected_identity(expected)
    if not item_id:
        return False
    if source_type and result.get("source_type") != source_type:
        return False
    return result.get("id") == item_id


def _ids_in_top(results: list[dict[str, Any]], expected: list[Any], top_n: int) -> bool:
    top_results = results[:top_n]
    for expected_item in expected:
        if not any(_result_matches(result, expected_item) for result in top_results):
            return False
    return True


def _evaluate_one_fixture(packet: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    fixture_id = str(fixture.get("fixture_id") or "")
    results = packet["results"]
    failure_reasons: list[str] = []
    expected_empty = fixture.get("expected_results") == []

    if expected_empty:
        top1_pass = packet["no_match"] is True and results == []
        top3_pass = top1_pass
        if not top1_pass:
            failure_reasons.append("expected empty no-match results")
    else:
        expected_top1 = fixture.get("expected_top1")
        if expected_top1 is not None:
            top1_pass = bool(results) and _result_matches(results[0], expected_top1)
        elif fixture.get("expected_order_prefix"):
            expected_prefix = [str(item) for item in fixture["expected_order_prefix"]]
            top1_pass = [
                result["id"] for result in results[: len(expected_prefix)]
            ] == expected_prefix
        else:
            top1_pass = True
        if not top1_pass:
            failure_reasons.append("top1 expectation failed")

        expected_top3 = fixture.get("expected_top3")
        if expected_top3 is not None:
            top3_pass = _ids_in_top(results, expected_top3, 3)
        elif fixture.get("expected_order_prefix"):
            expected_prefix = [str(item) for item in fixture["expected_order_prefix"]]
            top3_pass = [
                result["id"] for result in results[: len(expected_prefix)]
            ] == expected_prefix
        else:
            top3_pass = top1_pass
        if not top3_pass:
            failure_reasons.append("top3 expectation failed")

    for expected_annotation in fixture.get("expected_annotations") or []:
        if not isinstance(expected_annotation, dict):
            continue
        item_id = str(expected_annotation.get("id") or "")
        match = next((result for result in results if result.get("id") == item_id), None)
        if match is None:
            failure_reasons.append(f"missing annotated result {item_id}")
            continue
        for field in ("freshness_status", "conflict_status"):
            expected_value = expected_annotation.get(field)
            if expected_value is not None and match.get(field) != expected_value:
                failure_reasons.append(f"{item_id} {field} expected {expected_value!r}")

    pass_fail = top1_pass and top3_pass and not failure_reasons
    return {
        "fixture_id": fixture_id,
        "query": packet["query"],
        "query_tags": packet["query_tags"],
        "actual_top_ids": [result["id"] for result in results],
        "actual_top_sources": [result["source_type"] for result in results],
        "no_match": packet["no_match"],
        "top1_pass": top1_pass,
        "top3_pass": top3_pass,
        "pass_fail": pass_fail,
        "failure_reasons": failure_reasons,
    }


def evaluate_fixture_file(path: Path) -> dict[str, Any]:
    """Evaluate the deterministic fixture set and return a JSON packet."""
    fixture_doc = _load_fixture_doc(path)
    fixture_set_id = str(fixture_doc.get("fixture_set_id") or path.stem)
    as_of = str(fixture_doc.get("as_of") or "")
    top_k = int(fixture_doc.get("top_k") or 3)
    fixtures = fixture_doc.get("fixtures")
    if not isinstance(fixtures, list):
        raise RecallQualityError("fixture file must include fixtures list")

    with TemporaryDirectory(prefix="context-recall-quality-") as tmp:
        episodes_path, patterns_path, episodes_ref, patterns_ref = _write_fixture_corpus(
            fixture_doc, Path(tmp)
        )
        fixture_results: list[dict[str, Any]] = []
        warnings: list[str] = []
        corpus: dict[str, Any] | None = None
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                raise RecallQualityError("each fixture must be a mapping")
            packet = build_recall_packet(
                query=str(fixture.get("query") or ""),
                query_tags=_as_string_list(fixture.get("query_tags")),
                top_k=int(fixture.get("top_k") or top_k),
                as_of=as_of,
                episodes_path=episodes_path,
                patterns_path=patterns_path,
                episodes_source_ref=episodes_ref,
                patterns_source_ref=patterns_ref,
            )
            corpus = packet["corpus"]
            warnings.extend(packet["warnings"])
            fixture_results.append(_evaluate_one_fixture(packet, fixture))

    failed_fixture_ids = [
        result["fixture_id"] for result in fixture_results if not result["pass_fail"]
    ]
    top1_pass_count = sum(1 for result in fixture_results if result["top1_pass"])
    top3_pass_count = sum(1 for result in fixture_results if result["top3_pass"])
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_type": FIXTURE_PACKET_TYPE,
        "query": "",
        "query_tags": [],
        "as_of": as_of,
        "top_k": top_k,
        "corpus": corpus or {},
        "results": [],
        "warnings": warnings,
        "no_match": False,
        "advisory_authority": ADVISORY_AUTHORITY,
        "fixture_set_id": fixture_set_id,
        "fixture_results": fixture_results,
        "top1_pass_count": top1_pass_count,
        "top3_pass_count": top3_pass_count,
        "failed_fixture_ids": failed_fixture_ids,
        "pass_fail": not failed_fixture_ids,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic M3/M2 context recall quality."
    )
    parser.add_argument("--json", action="store_true", help="Emit the stable JSON packet.")
    parser.add_argument("--query", default="", help="Query text for query mode.")
    parser.add_argument("--tags", nargs="*", default=[], help="Query tags for query mode.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to return.")
    parser.add_argument("--as-of", default=None, help="Freeze scoring as of this date/datetime.")
    parser.add_argument("--episodes-path", type=Path, default=DEFAULT_EPISODES_PATH)
    parser.add_argument("--patterns-path", type=Path, default=DEFAULT_PATTERNS_PATH)
    parser.add_argument("--fixtures", type=Path, default=None, help="Run fixture eval mode.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("--json is required")

    try:
        if args.fixtures is not None:
            packet = evaluate_fixture_file(args.fixtures)
        else:
            packet = build_recall_packet(
                query=args.query,
                query_tags=args.tags,
                top_k=args.top_k,
                as_of=args.as_of,
                episodes_path=args.episodes_path,
                patterns_path=args.patterns_path,
            )
    except EpisodeStoreError as exc:
        sys.stderr.write(f"EpisodeStoreError: {exc}\n")
        return 1
    except RecallQualityError as exc:
        sys.stderr.write(f"RecallQualityError: {exc}\n")
        return 1

    sys.stdout.write(json.dumps(packet, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
