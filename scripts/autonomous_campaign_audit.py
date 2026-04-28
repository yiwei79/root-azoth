#!/usr/bin/env python3
"""Read-only autonomous-auto campaign audit builder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yaml_helpers import safe_load_yaml_path

STATE_REL = ".azoth/autonomous-loop-state.local.yaml"
LEDGER_REL = ".azoth/run-ledger.local.yaml"
EPISODES_REL = ".azoth/memory/episodes.jsonl"
INBOX_DIR_REL = ".azoth/inbox"
PROPOSALS_DIR_REL = ".azoth/proposals"
PROVENANCE_REPO_NATIVE = "repo_native"
PROVENANCE_CHAT_ONLY = "chat_only"
PROVENANCE_MISSING = "missing"
PROVENANCE_CONFLICT = "conflict"
LEARNING_STATES = {
    "observed",
    "captured",
    "triaged",
    "planned",
    "implemented",
    "verified",
    "reinforced",
    "stale_or_rejected",
    "missing_evidence",
}
LEARNING_STATE_RANK = {
    "observed": 0,
    "captured": 1,
    "triaged": 2,
    "planned": 3,
    "implemented": 4,
    "verified": 5,
    "reinforced": 6,
    "stale_or_rejected": -1,
    "missing_evidence": -1,
}
VISION_BANDS = {"unevaluated": -1, "red": 0, "yellow": 1, "green": 2}
DEFAULT_VISION_TARGET_BAND = "green"
HARVESTER_ROUTES = {
    "auto_self_heal_now",
    "capture_only",
    "proposal_needed",
    "human_gate_required",
    "defer_to_intake",
    "stale_or_rejected",
}
HARVESTER_ROUTE_PRIORITY = {
    "human_gate_required": 60,
    "defer_to_intake": 50,
    "auto_self_heal_now": 40,
    "proposal_needed": 30,
    "capture_only": 20,
    "stale_or_rejected": 10,
}
PROTECTED_SIGNAL_MARKERS = {
    "kernel",
    "governance",
    "m1",
    "destructive",
    "credential",
    "credentials",
    "network",
    "cross-branch",
    "protected",
    "human gate",
    "human-gate",
}
CROSS_SYSTEM_SIGNAL_MARKERS = {
    "cross-system",
    "user-governed",
    "inbox/intake",
    "intake",
    "promote",
}
INTERNAL_SELF_HEAL_MARKERS = {
    "autonomous-auto",
    "campaign audit",
    "campaign-audit",
    "lifecycle-route",
    "strategy-preflight",
    "scope-gate",
    "run-ledger",
    "write claim",
    "stage evidence",
    "readiness",
    "retrospective",
    "self-capture",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(root: Path, path: Path | str | None, default_rel: str) -> Path:
    if path is None:
        return root / default_rel
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_yaml_mapping(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, []
    try:
        data = safe_load_yaml_path(path)
    except Exception as exc:  # pragma: no cover - exact parser errors vary by PyYAML.
        return {}, [f"could not parse YAML at {path}: {exc}"]
    if not isinstance(data, dict):
        return {}, [f"YAML root at {path} is not a mapping"]
    return data, []


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{index}: invalid JSONL row: {exc}")
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            errors.append(f"{path}:{index}: JSONL row is not an object")
    return rows, errors


def _artifact(path: Path, *, errors: list[str] | None = None) -> dict[str, Any]:
    provenance = PROVENANCE_REPO_NATIVE if path.exists() else PROVENANCE_MISSING
    if errors:
        provenance = PROVENANCE_CONFLICT
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "provenance": provenance,
        "errors": list(errors or []),
    }


def _ledger_runs(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        return []
    return [run for run in runs if isinstance(run, dict)]


def _matching_run(ledger: dict[str, Any], loop_id: str) -> dict[str, Any]:
    for run in _ledger_runs(ledger):
        if str(run.get("run_id") or "") == loop_id:
            return run
    return {}


def _matching_runs(ledger: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    wanted = {str(value).strip() for value in ids if str(value or "").strip()}
    if not wanted:
        return []
    matches: list[dict[str, Any]] = []
    seen: set[int] = set()
    for run in _ledger_runs(ledger):
        run_ids = {
            str(run.get("run_id") or "").strip(),
            str(run.get("session_id") or "").strip(),
        }
        if wanted & run_ids and id(run) not in seen:
            matches.append(run)
            seen.add(id(run))
    return matches


def _safe_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_scalar_list(value: Any) -> list[Any]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    return [value]


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _sort_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1_000_000_000


def _child_scope_sort_key(scope: dict[str, Any]) -> tuple[int, str, str, str]:
    return (
        _sort_int(scope.get("loop_iteration")),
        str(scope.get("timestamp") or ""),
        str(scope.get("session_id") or ""),
        str(scope.get("run_id") or ""),
    )


def _sorted_child_scopes(scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(scopes, key=_child_scope_sort_key)


def _vision_from_mapping(value: Any, provenance: str) -> dict[str, Any]:
    vision = _safe_mapping(value)
    latest = _safe_mapping(vision.get("latest"))
    scorecard = _first_present(vision.get("scorecard"), latest.get("scorecard"))
    score = _first_present(
        vision.get("score"),
        latest.get("score"),
        _safe_mapping(scorecard).get("score") if isinstance(scorecard, dict) else None,
        _safe_mapping(scorecard).get("total") if isinstance(scorecard, dict) else None,
    )
    target_band = str(
        _first_present(vision.get("target_band"), latest.get("target_band"))
        or DEFAULT_VISION_TARGET_BAND
    ).strip().lower()
    band = str(
        _first_present(
            vision.get("current_band"),
            vision.get("band"),
            latest.get("current_band"),
            latest.get("band"),
        )
        or "unevaluated"
    ).strip().lower()
    target_rank = VISION_BANDS.get(target_band, VISION_BANDS[DEFAULT_VISION_TARGET_BAND])
    current_rank = VISION_BANDS.get(band)
    realized = vision.get("realized")
    if not isinstance(realized, bool):
        realized = bool(current_rank is not None and current_rank >= target_rank)
    has_evidence = bool(
        vision
        and any(
            item not in (None, "", [], {})
            for item in (
                band,
                score,
                scorecard,
                vision.get("updated_at"),
                latest.get("updated_at"),
                vision.get("note"),
                latest.get("note"),
            )
        )
    )
    return {
        "band": band,
        "target_band": target_band
        if target_band in VISION_BANDS
        else DEFAULT_VISION_TARGET_BAND,
        "score": score,
        "scorecard": scorecard if isinstance(scorecard, dict) else {},
        "realized": realized,
        "updated_at": str(_first_present(vision.get("updated_at"), latest.get("updated_at")) or ""),
        "note": str(_first_present(vision.get("note"), latest.get("note")) or ""),
        "provenance": provenance if has_evidence else PROVENANCE_MISSING,
    }


def _completion_reason_from_state(state: dict[str, Any]) -> str:
    explicit = str(state.get("completion_reason") or "").strip()
    if explicit:
        return explicit
    vision = _vision_from_mapping(state.get("vision"), PROVENANCE_REPO_NATIVE)
    if vision.get("realized"):
        return "vision_realized"
    return ""


def _closeout_episode_child_scopes(
    episodes: list[dict[str, Any]], loop_id: str
) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    for record in episodes:
        context = _safe_mapping(record.get("context"))
        payload = _safe_mapping(context.get("verbatim_payload"))
        if str(payload.get("loop_id") or "").strip() != loop_id:
            continue
        loop_decision = _safe_mapping(payload.get("loop_decision"))
        delegation_plan = _safe_mapping(payload.get("delegation_plan"))
        budget = _safe_mapping(payload.get("autonomy_budget"))
        handoff_campaign = _safe_mapping(payload.get("handoff_campaign"))
        architect_judgment = _safe_mapping(loop_decision.get("architect_judgment"))
        selected = _safe_mapping(architect_judgment.get("selected"))
        session_id = str(payload.get("session_id") or record.get("session_id") or "").strip()
        run_id = str(
            _safe_mapping(delegation_plan.get("run_ledger_evidence")).get("run_id")
            or session_id
        ).strip()
        candidate_id = str(
            loop_decision.get("candidate_id")
            or selected.get("candidate_id")
            or payload.get("backlog_id")
            or ""
        )
        stage_plan = _safe_list(delegation_plan.get("stages"))
        scopes.append(
            {
                "session_id": session_id or run_id or loop_id,
                "run_id": run_id or session_id or loop_id,
                "goal": str(payload.get("goal") or ""),
                "action": str(loop_decision.get("action") or ""),
                "candidate_id": candidate_id,
                "status": "closed",
                "loop_iteration": _first_present(
                    payload.get("loop_iteration"),
                    payload.get("iteration"),
                    loop_decision.get("loop_iteration"),
                    loop_decision.get("iteration"),
                ),
                "timestamp": str(record.get("timestamp") or payload.get("timestamp") or ""),
                "provenance": PROVENANCE_REPO_NATIVE,
                "approval_basis": str(
                    payload.get("approval_basis") or budget.get("approval_basis") or ""
                ),
                "budget": budget,
                "autonomy_budget": budget,
                "stop_conditions": _safe_list(budget.get("stop_conditions")),
                "changed_files": _safe_list(context.get("files_changed")),
                "closeout_episode_id": str(record.get("id") or ""),
                "loop_decision": loop_decision,
                "delegation_plan": delegation_plan,
                "stage_plan": stage_plan,
                "selected_seed": payload.get("selected_seed"),
                "selected_candidate": selected or None,
                "completion_reason": str(
                    _first_present(
                        payload.get("completion_reason"),
                        loop_decision.get("completion_reason"),
                        handoff_campaign.get("completion_reason"),
                    )
                    or ""
                ),
                "vision": _first_present(
                    payload.get("vision"),
                    loop_decision.get("vision"),
                    handoff_campaign.get("vision"),
                ),
                "structured_scores": _structured_scores(payload)
                + _structured_scores(loop_decision)
                + _structured_scores(handoff_campaign),
                "ux_scorecards": _ux_scorecards(payload)
                + _ux_scorecards(loop_decision)
                + _ux_scorecards(handoff_campaign),
                "verification_commands": list(
                    dict.fromkeys(
                        _verification_commands(payload)
                        + _verification_commands(loop_decision)
                        + _verification_commands(handoff_campaign)
                    )
                ),
                "route_rationale": str(
                    loop_decision.get("reason") or architect_judgment.get("rationale") or ""
                ),
            }
        )
    return _sorted_child_scopes(scopes)


def _child_run_ids(child_scopes: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for scope in child_scopes:
        ids.extend([str(scope.get("run_id") or ""), str(scope.get("session_id") or "")])
    return list(dict.fromkeys(value for value in ids if value))


def _campaign_detail_from_children(
    child_scopes: list[dict[str, Any]], field: str
) -> Any:
    for scope in reversed(child_scopes):
        value = scope.get(field)
        if value not in (None, "", [], {}):
            return value
    return None


def _state_history_child_scopes(state: dict[str, Any], loop_id: str) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    state_loop_id = str(state.get("loop_id") or "").strip()
    history = state.get("history")
    if not isinstance(history, list):
        return scopes
    for item in history:
        if not isinstance(item, dict):
            continue
        session_id = str(item.get("session_id") or item.get("run_id") or "").strip()
        if loop_id and state_loop_id != loop_id and session_id and session_id != loop_id:
            continue
        scopes.append(
            {
                "session_id": session_id or loop_id,
                "action": str(item.get("action") or ""),
                "candidate_id": str(item.get("candidate_id") or ""),
                "status": str(item.get("result") or item.get("status") or ""),
                "loop_iteration": item.get("loop_iteration") or item.get("iteration"),
                "timestamp": str(item.get("timestamp") or item.get("recorded_at") or ""),
                "provenance": PROVENANCE_REPO_NATIVE,
            }
        )
    return scopes


def _ledger_child_scope(run: dict[str, Any], loop_id: str) -> dict[str, Any]:
    if not run:
        return {}
    return {
        "session_id": str(run.get("session_id") or run.get("run_id") or loop_id),
        "action": "",
        "candidate_id": str(run.get("backlog_id") or ""),
        "status": str(run.get("status") or ""),
        "loop_iteration": run.get("loop_iteration") or run.get("iteration"),
        "timestamp": str(run.get("created_at") or ""),
        "provenance": PROVENANCE_REPO_NATIVE,
    }


def _child_scopes(
    state: dict[str, Any],
    run: dict[str, Any],
    loop_id: str,
    closeout_scopes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_session: dict[str, dict[str, Any]] = {}
    for scope in closeout_scopes:
        by_session[str(scope["session_id"])] = scope
    for scope in _state_history_child_scopes(state, loop_id):
        session_id = str(scope["session_id"])
        existing = by_session.get(session_id, {})
        by_session[session_id] = {**scope, **{k: v for k, v in existing.items() if v}}
    ledger_scope = _ledger_child_scope(run, loop_id)
    if ledger_scope:
        session_id = str(ledger_scope["session_id"])
        existing = by_session.get(session_id, {})
        merged = {**ledger_scope, **{k: v for k, v in existing.items() if v}}
        by_session[session_id] = merged
    if not by_session and state:
        by_session[loop_id] = {
            "session_id": loop_id,
            "action": "",
            "candidate_id": "",
            "status": str(state.get("status") or ""),
            "provenance": PROVENANCE_REPO_NATIVE,
        }
    return _sorted_child_scopes(list(by_session.values()))


def _latest_by_stage(entries: Any) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not isinstance(entries, list):
        return latest
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        stage_id = str(entry.get("stage_id") or "").strip()
        if stage_id:
            latest[stage_id] = entry
    return latest


def _expected_stage_ids(run: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for field in ("stages_completed", "pending_stage_ids"):
        values = run.get(field)
        if isinstance(values, list):
            ids.extend(str(value) for value in values if str(value or "").strip())
    ids.extend(_latest_by_stage(run.get("stage_spawns")).keys())
    ids.extend(_latest_by_stage(run.get("stage_summaries")).keys())
    return sorted(dict.fromkeys(ids))


def _structured_scores(summary: dict[str, Any]) -> list[Any]:
    scores: list[Any] = []
    for field in ("scores", "evaluator_scores"):
        scores.extend(_safe_scalar_list(summary.get(field)))
    if summary.get("score") is not None:
        scores.append(summary.get("score"))
    scorecard = _safe_mapping(summary.get("scorecard"))
    for field in ("score", "total", "overall", "consensus"):
        if scorecard.get(field) is not None:
            scores.append(scorecard[field])
            break
    return scores


def _ux_scorecards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    scorecards: list[dict[str, Any]] = []
    for field in ("ux_anchor_scorecard", "ux_scorecard", "UX Anchor Scorecard"):
        scorecard = _safe_mapping(summary.get(field))
        if scorecard:
            scorecards.append(scorecard)
    scorecard = _safe_mapping(summary.get("scorecard"))
    if scorecard and any("ux" in str(key).lower() for key in scorecard):
        scorecards.append(scorecard)
    return scorecards


def _verification_commands(summary: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for field in ("verification_commands", "validation_commands", "tests_run"):
        for command in _safe_scalar_list(summary.get(field)):
            text = str(command).strip()
            if text:
                commands.append(text)
    verification = _safe_mapping(summary.get("verification"))
    for command in _safe_scalar_list(
        _first_present(verification.get("commands"), verification.get("command"))
    ):
        text = str(command).strip()
        if text:
            commands.append(text)
    return list(dict.fromkeys(commands))


def _stage_evidence(run: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if not run:
        return {"provenance": PROVENANCE_MISSING, "stages": {}}, [
            "missing run ledger entry for campaign"
        ]
    spawns = _latest_by_stage(run.get("stage_spawns"))
    summaries = _latest_by_stage(run.get("stage_summaries"))
    stages: dict[str, dict[str, Any]] = {}
    residuals: list[str] = []
    for stage_id in _expected_stage_ids(run):
        spawn = spawns.get(stage_id)
        summary = summaries.get(stage_id)
        spawn_provenance = PROVENANCE_REPO_NATIVE if spawn else PROVENANCE_MISSING
        summary_provenance = PROVENANCE_REPO_NATIVE if summary else PROVENANCE_MISSING
        provenance = (
            PROVENANCE_REPO_NATIVE
            if spawn and summary
            else PROVENANCE_CONFLICT
            if spawn or summary
            else PROVENANCE_MISSING
        )
        if spawn and not summary:
            residuals.append(f"missing stage summary for {stage_id}")
        elif summary and not spawn:
            residuals.append(f"missing stage spawn for {stage_id}")
        stages[stage_id] = {
            "provenance": provenance,
            "run_id": str(run.get("run_id") or ""),
            "session_id": str(run.get("session_id") or run.get("run_id") or ""),
            "spawn_provenance": spawn_provenance,
            "summary_provenance": summary_provenance,
            "spawned_at": str((spawn or {}).get("spawned_at") or ""),
            "summary_recorded_at": str((summary or {}).get("summary_recorded_at") or ""),
            "subagent_type": str(
                (summary or spawn or {}).get("subagent_type") or ""
            ),
            "summary_status": str((summary or {}).get("summary_status") or ""),
            "summary_disposition": str((summary or {}).get("summary_disposition") or ""),
            "structured_scores": _structured_scores(summary or {}),
            "ux_scorecards": _ux_scorecards(summary or {}),
            "verification_commands": _verification_commands(summary or {}),
        }
    if not stages:
        residuals.append("missing stage evidence for campaign")
    aggregate = _aggregate_provenance(stage["provenance"] for stage in stages.values())
    return {"provenance": aggregate, "stages": stages}, residuals


def _stage_evidence_for_runs(
    runs: list[dict[str, Any]],
    *,
    expected_child_run_ids: list[str],
) -> tuple[dict[str, Any], list[str]]:
    if not runs:
        if expected_child_run_ids:
            return {"provenance": PROVENANCE_MISSING, "stages": {}}, [
                f"missing run ledger entry for child scope {run_id}"
                for run_id in expected_child_run_ids
            ]
        return {"provenance": PROVENANCE_MISSING, "stages": {}}, [
            "missing run ledger entry for campaign"
        ]

    combined: dict[str, dict[str, Any]] = {}
    residuals: list[str] = []
    prefix_keys = len(runs) > 1
    for run in runs:
        evidence, run_residuals = _stage_evidence(run)
        run_id = str(run.get("run_id") or run.get("session_id") or "")
        residuals.extend(
            risk.replace("for campaign", f"for child scope {run_id}")
            for risk in run_residuals
        )
        stages = evidence.get("stages")
        if not isinstance(stages, dict):
            continue
        for stage_id, stage in stages.items():
            key = f"{run_id}:{stage_id}" if prefix_keys else stage_id
            combined[key] = stage

    aggregate = _aggregate_provenance(stage["provenance"] for stage in combined.values())
    return {"provenance": aggregate, "stages": combined}, residuals


def _child_quality_evidence(child_scopes: list[dict[str, Any]]) -> dict[str, Any]:
    structured_scores: list[Any] = []
    ux_scorecards: list[dict[str, Any]] = []
    verification_commands: list[str] = []
    for scope in child_scopes:
        structured_scores.extend(_safe_scalar_list(scope.get("structured_scores")))
        ux_scorecards.extend(
            scorecard
            for scorecard in _safe_list(scope.get("ux_scorecards"))
            if isinstance(scorecard, dict)
        )
        verification_commands.extend(
            str(command)
            for command in _safe_list(scope.get("verification_commands"))
            if str(command or "").strip()
        )
    return {
        "structured_scores": structured_scores,
        "ux_scorecards": ux_scorecards,
        "verification_commands": list(dict.fromkeys(verification_commands)),
    }


def _evaluator_evidence(
    stage_evidence: dict[str, Any], child_scopes: list[dict[str, Any]]
) -> dict[str, Any]:
    stages = stage_evidence.get("stages")
    child_quality = _child_quality_evidence(child_scopes)
    if not isinstance(stages, dict):
        return {
            "provenance": PROVENANCE_MISSING,
            "stages": [],
            **child_quality,
        }
    evaluator_stage_ids = [
        stage_id
        for stage_id, evidence in stages.items()
        if isinstance(evidence, dict)
        and (
            evidence.get("subagent_type") == "evaluator"
            or "evaluator" in str(stage_id)
            or str(stage_id).endswith("_s4")
        )
    ]
    if not evaluator_stage_ids:
        provenance = (
            PROVENANCE_REPO_NATIVE
            if any(child_quality.values())
            else PROVENANCE_MISSING
        )
        return {
            "provenance": provenance,
            "stages": [],
            **child_quality,
        }
    provenance = _aggregate_provenance(
        str(stages[stage_id].get("provenance") or PROVENANCE_MISSING)
        for stage_id in evaluator_stage_ids
    )
    structured_scores: list[Any] = []
    ux_scorecards: list[dict[str, Any]] = []
    verification_commands: list[str] = []
    for stage_id in evaluator_stage_ids:
        evidence = stages[stage_id]
        structured_scores.extend(_safe_scalar_list(evidence.get("structured_scores")))
        ux_scorecards.extend(
            scorecard
            for scorecard in _safe_list(evidence.get("ux_scorecards"))
            if isinstance(scorecard, dict)
        )
        verification_commands.extend(
            str(command)
            for command in _safe_list(evidence.get("verification_commands"))
            if str(command or "").strip()
        )
    return {
        "provenance": provenance,
        "stages": evaluator_stage_ids,
        "structured_scores": structured_scores + child_quality["structured_scores"],
        "ux_scorecards": ux_scorecards + child_quality["ux_scorecards"],
        "verification_commands": list(
            dict.fromkeys(
                verification_commands + child_quality["verification_commands"]
            )
        ),
    }


def _record_matches_campaign(record: dict[str, Any], loop_id: str) -> bool:
    if str(record.get("session_id") or record.get("loop_id") or "") == loop_id:
        return True
    tags = record.get("tags")
    if isinstance(tags, list) and "autonomous-auto" in tags and "learning-closure" in tags:
        return True
    return False


def _mapping_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join([str(key) for key in value.keys()] + [_mapping_text(item) for item in value.values()])
    if isinstance(value, list):
        return " ".join(_mapping_text(item) for item in value)
    return str(value or "")


def _learning_state(record: dict[str, Any]) -> str:
    state = str(record.get("learning_state") or record.get("state") or "").strip()
    return state if state in LEARNING_STATES else "missing_evidence"


def _learning_summary(record: dict[str, Any]) -> str:
    return str(
        record.get("summary")
        or record.get("lesson")
        or record.get("title")
        or record.get("id")
        or ""
    )


def _learning_rows(
    root: Path,
    loop_id: str,
    episodes_path: Path,
    inbox_dir: Path,
    *,
    episodes: list[dict[str, Any]] | None = None,
    episode_errors: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    loaded_episodes = episodes
    loaded_episode_errors = list(episode_errors or [])
    if loaded_episodes is None:
        loaded_episodes, loaded_episode_errors = _load_jsonl(episodes_path)
    errors.extend(loaded_episode_errors)
    for record in loaded_episodes:
        if _record_matches_campaign(record, loop_id):
            rows.append(
                {
                    "learning_state": _learning_state(record),
                    "provenance": PROVENANCE_REPO_NATIVE,
                    "source": _rel(root, episodes_path),
                    "summary": _learning_summary(record),
                }
            )
    if inbox_dir.is_dir():
        for path in sorted(inbox_dir.glob("*.jsonl")):
            inbox_rows, inbox_errors = _load_jsonl(path)
            errors.extend(inbox_errors)
            for record in inbox_rows:
                if _record_matches_campaign(record, loop_id):
                    rows.append(
                        {
                            "learning_state": _learning_state(record),
                            "provenance": PROVENANCE_REPO_NATIVE,
                            "source": _rel(root, path),
                            "summary": _learning_summary(record),
                        }
                    )
    rows.sort(key=lambda row: (row["source"], row["learning_state"], row["summary"]))
    return rows, errors


def _proposal_learning_rows(root: Path, loop_id: str, proposals_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not proposals_dir.is_dir():
        return rows, errors
    for path in sorted(proposals_dir.glob("*.yaml")):
        data, yaml_errors = _load_yaml_mapping(path)
        errors.extend(yaml_errors)
        if not data:
            continue
        text = _mapping_text(data).casefold()
        if loop_id.casefold() not in text and not (
            "autonomous-auto" in text and "learning" in text
        ):
            continue
        status = str(data.get("status") or data.get("proposal_status") or "captured")
        state = "planned" if status in {"accepted", "approved", "ready", "hydrated"} else "captured"
        rows.append(
            {
                "learning_state": state,
                "provenance": PROVENANCE_REPO_NATIVE,
                "source": _rel(root, path),
                "summary": str(data.get("title") or data.get("summary") or path.stem),
            }
        )
    return rows, errors


def _route_failure_rows(state: dict[str, Any], loop_id: str) -> list[dict[str, Any]]:
    if str(state.get("loop_id") or "") != loop_id:
        return []
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(state.get("history")), start=1):
        if not isinstance(item, dict):
            continue
        preflight = _safe_mapping(item.get("strategy_preflight"))
        if not preflight:
            continue
        route = str(preflight.get("verdict") or "")
        blocked = _safe_list(preflight.get("blocked_alternatives"))
        if route == "allow_open" and not blocked:
            continue
        rows.append(
            {
                "learning_state": "observed",
                "provenance": PROVENANCE_REPO_NATIVE,
                "source": f"{STATE_REL}#history[{index}].strategy_preflight",
                "summary": str(
                    preflight.get("mismatch_reason")
                    or preflight.get("next_safe_action")
                    or route
                    or "strategy-preflight route failure"
                ),
            }
        )
    return rows


def _aggregate_provenance(values: Any) -> str:
    provenances = [str(value) for value in values if str(value or "")]
    if not provenances:
        return PROVENANCE_MISSING
    if PROVENANCE_CONFLICT in provenances:
        return PROVENANCE_CONFLICT
    if PROVENANCE_MISSING in provenances:
        return PROVENANCE_MISSING
    if PROVENANCE_CHAT_ONLY in provenances:
        return PROVENANCE_CHAT_ONLY
    return PROVENANCE_REPO_NATIVE


def _truthful_inline_absence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_rows: list[dict[str, Any]] = []
    for row in rows:
        rank = LEARNING_STATE_RANK.get(str(row.get("learning_state")), -1)
        if rank < LEARNING_STATE_RANK["implemented"]:
            continue
        summary = str(row.get("summary") or "").lower()
        if (
            ("inline" in summary or "no fake" in summary or "without fake" in summary)
            and "stage" in summary
            and ("evidence" in summary or "subagent" in summary)
        ):
            accepted_rows.append(row)
    return {
        "accepted": bool(accepted_rows),
        "provenance": PROVENANCE_REPO_NATIVE if accepted_rows else PROVENANCE_MISSING,
        "row_count": len(accepted_rows),
        "sources": sorted(
            {
                str(row.get("source") or "")
                for row in accepted_rows
                if str(row.get("source") or "")
            }
        ),
        "basis": (
            "Implemented or verified learning closure records that absent delegated stage "
            "rows were an explicit inline-execution exception, not evidence to backfill."
            if accepted_rows
            else ""
        ),
    }


def _learning_score(
    rows: list[dict[str, Any]],
    *,
    truthful_absence: dict[str, Any] | None = None,
) -> str:
    if not rows:
        return PROVENANCE_MISSING
    if any(row["learning_state"] == "missing_evidence" for row in rows) and not (
        truthful_absence or {}
    ).get("accepted"):
        return PROVENANCE_CONFLICT
    return _aggregate_provenance(row["provenance"] for row in rows)


def _best_learning_rank(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return -1
    return max(LEARNING_STATE_RANK.get(str(row.get("learning_state")), -1) for row in rows)


def _contains_marker(text: str, markers: set[str]) -> bool:
    folded = text.casefold()
    return any(marker in folded for marker in markers)


def _signal_text(signal: dict[str, Any]) -> str:
    values = [
        signal.get("summary"),
        signal.get("recommended_action"),
        signal.get("reason"),
        signal.get("title"),
        signal.get("source"),
        signal.get("learning_state"),
    ]
    tags = signal.get("tags")
    if isinstance(tags, list):
        values.extend(str(tag) for tag in tags)
    return " ".join(str(value or "") for value in values)


def _signal_severity(signal: dict[str, Any], text: str) -> str:
    severity = str(signal.get("severity") or "").strip().lower()
    if severity in {"critical", "high", "medium", "low"}:
        return severity
    folded = text.casefold()
    if "critical" in folded:
        return "critical"
    if "high" in folded:
        return "high"
    if "medium" in folded or "repeated" in folded or "shared surface" in folded:
        return "medium"
    return "low"


def learning_harvester_decision(
    signal: dict[str, Any],
    *,
    approval_basis: str = "",
    selected_action: str = "",
) -> dict[str, Any]:
    """Classify one learning signal without granting write authority."""
    text = _signal_text(signal)
    learning_state = str(signal.get("learning_state") or signal.get("state") or "").strip()
    signal_id = str(signal.get("id") or signal.get("signal_id") or signal.get("summary") or "learning-signal")
    source = str(signal.get("source") or signal.get("path") or "").strip()
    protected = bool(signal.get("protected_gate_required") or signal.get("requires_human_gate"))
    protected = protected or _contains_marker(text, PROTECTED_SIGNAL_MARKERS)
    cross_system = bool(signal.get("cross_system") or signal.get("defer_to_intake"))
    cross_system = cross_system or _contains_marker(text, CROSS_SYSTEM_SIGNAL_MARKERS)
    stale = learning_state == "stale_or_rejected" or _contains_marker(
        text, {"stale", "rejected", "superseded", "obsolete", "duplicate"}
    )
    residual_signal = bool(signal.get("residual_signal"))
    internal = _contains_marker(text, INTERNAL_SELF_HEAL_MARKERS)
    severity = _signal_severity(signal, text)
    shared_or_medium = severity in {"medium", "high", "critical"} or "shared surface" in text.casefold()

    if protected:
        route = "human_gate_required"
        action = "stop_for_human_gate"
        residual = "Protected boundary blocks autonomous self-heal."
    elif cross_system:
        route = "defer_to_intake"
        action = "defer_to_inbox_intake"
        residual = "Cross-system or user-governed signal stays in inbox/intake."
    elif stale:
        route = "stale_or_rejected"
        action = "none"
        residual = "Signal is stale, duplicate, superseded, or intentionally rejected."
    elif residual_signal:
        route = "capture_only"
        action = "capture_only"
        residual = "Audit residual remains visible but is not itself a fresh self-heal candidate."
    elif internal and approval_basis and not shared_or_medium:
        route = "auto_self_heal_now"
        action = selected_action or "open_normal_child_scope"
        residual = ""
    elif internal:
        route = "proposal_needed" if shared_or_medium else "capture_only"
        action = "refine_proposal" if route == "proposal_needed" else "capture_only"
        residual = (
            "Evaluator or proposal review is required before auto self-heal."
            if route == "proposal_needed"
            else "Signal remains visible but does not justify immediate repair."
        )
    else:
        route = "capture_only"
        action = "capture_only"
        residual = "Signal remains visible but does not justify immediate repair."

    source_refs = [source] if source else []
    rejected = sorted(HARVESTER_ROUTES - {route})
    return {
        "signal_id": signal_id,
        "source_refs": source_refs,
        "dedupe_key": str(signal.get("summary") or signal_id).casefold(),
        "severity": severity,
        "blast_radius": "protected" if protected else "cross_system" if cross_system else "internal",
        "route": route,
        "protected_gate_required": protected,
        "selected_action": action,
        "rejected_alternatives": rejected,
        "approval_basis": str(approval_basis or ""),
        "verification_requirement": (
            "human approval required"
            if protected
            else "intake triage required"
            if cross_system
            else "evaluator review required"
            if route == "proposal_needed"
            else "normal scope-gate, run-ledger, write-claim, lifecycle-route, and strategy-preflight checks"
            if route == "auto_self_heal_now"
            else "capture visibility in campaign report"
        ),
        "residual_risk": residual,
    }


def build_learning_harvester_report(
    *,
    learning_rows: list[dict[str, Any]],
    residuals: list[str],
    approval_basis: str = "",
) -> dict[str, Any]:
    """Deduplicate and route repo-native autonomous-auto learning signals."""
    raw_signals: list[dict[str, Any]] = [dict(row) for row in learning_rows]
    raw_signals.extend(
        {
            "id": f"residual-{index}",
            "source": "campaign-audit",
            "summary": residual,
            "learning_state": "observed",
            "residual_signal": True,
        }
        for index, residual in enumerate(residuals, start=1)
    )
    decisions_by_key: dict[str, dict[str, Any]] = {}
    for signal in raw_signals:
        decision = learning_harvester_decision(signal, approval_basis=approval_basis)
        key = str(decision.get("dedupe_key") or decision.get("signal_id") or "")
        current = decisions_by_key.get(key)
        if current is not None:
            source_refs = list(dict.fromkeys(current.get("source_refs", []) + decision.get("source_refs", [])))
            current["source_refs"] = source_refs
        if current is None or HARVESTER_ROUTE_PRIORITY[decision["route"]] > HARVESTER_ROUTE_PRIORITY[current["route"]]:
            if current is not None:
                decision["source_refs"] = list(
                    dict.fromkeys(current.get("source_refs", []) + decision.get("source_refs", []))
                )
            decisions_by_key[key] = decision
    decisions = sorted(
        decisions_by_key.values(),
        key=lambda item: (-HARVESTER_ROUTE_PRIORITY[item["route"]], item["dedupe_key"]),
    )
    route_counts = {route: 0 for route in sorted(HARVESTER_ROUTES)}
    for decision in decisions:
        route_counts[decision["route"]] += 1
    selected_route = decisions[0]["route"] if decisions else "capture_only"
    return {
        "schema_version": 1,
        "decisions": decisions,
        "route_counts": route_counts,
        "selected_learning_route": selected_route,
        "rejected_alternatives": sorted(HARVESTER_ROUTES - {selected_route}),
        "summary": (
            "Harvester found no learning signals."
            if not decisions
            else f"Harvester routed {len(decisions)} deduplicated learning signal(s)."
        ),
        "write_authority": "advisory_only_strategy_preflight_still_required",
    }


def _recommend_next_route(
    *,
    residuals: list[str],
    stage_evidence: dict[str, Any],
    evaluator_evidence: dict[str, Any],
    learning_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    stage_absence_accepted = bool(
        _safe_mapping(stage_evidence.get("truthful_absence")).get("accepted")
        and stage_evidence.get("provenance") == PROVENANCE_MISSING
    )
    evaluator_absence_accepted = bool(
        _safe_mapping(evaluator_evidence.get("truthful_absence")).get("accepted")
        and evaluator_evidence.get("provenance") == PROVENANCE_MISSING
    )
    if (
        stage_evidence["provenance"] in {PROVENANCE_CONFLICT, PROVENANCE_MISSING}
        and not stage_absence_accepted
    ):
        return {
            "route": "repair_evidence",
            "reason": "Stage evidence is incomplete or contradictory.",
            "confidence": 0.8,
            "confidence_basis": [
                f"stage_evidence provenance is {stage_evidence['provenance']}"
            ],
        }
    if (
        evaluator_evidence["provenance"] in {PROVENANCE_CONFLICT, PROVENANCE_MISSING}
        and not evaluator_absence_accepted
    ):
        return {
            "route": "repair_evidence",
            "reason": "Evaluator evidence is missing or incomplete.",
            "confidence": 0.8,
            "confidence_basis": [
                f"evaluator_evidence provenance is {evaluator_evidence['provenance']}"
            ],
        }
    if _best_learning_rank(learning_rows) < LEARNING_STATE_RANK["implemented"]:
        return {
            "route": "plan_learning_closure",
            "reason": "Learning evidence is missing or below implemented or verified.",
            "confidence": 0.7,
            "confidence_basis": [
                "best learning state is below implemented",
                f"learning rows observed: {len(learning_rows)}",
            ],
        }
    if residuals:
        return {
            "route": "review_residuals",
            "reason": "Residual risks remain.",
            "confidence": 0.6,
            "confidence_basis": [f"residual risk count: {len(residuals)}"],
        }
    return {
        "route": "stop",
        "reason": (
            "Campaign evidence is complete and learning is closed."
            if not stage_absence_accepted
            else "Campaign evidence is closed; absent delegated stage rows are truthfully recorded as inline execution rather than backfilled."
        ),
        "confidence": 1.0,
        "confidence_basis": [
            (
                "stage, evaluator, and learning evidence are repo-native"
                if not stage_absence_accepted
                else "inline-execution absence is repo-native and non-repairable"
            ),
            "no residual risks remain",
        ],
    }


def _effective_evidence_provenance(evidence: dict[str, Any]) -> str:
    if (
        _safe_mapping(evidence.get("truthful_absence")).get("accepted")
        and evidence.get("provenance") == PROVENANCE_MISSING
    ):
        return PROVENANCE_REPO_NATIVE
    return str(evidence.get("provenance") or PROVENANCE_MISSING)


def _nonblocking_absence_residuals(
    residuals: list[str],
    *,
    truthful_absence: dict[str, Any],
) -> tuple[list[str], list[str]]:
    if not truthful_absence.get("accepted"):
        return residuals, []
    blocking: list[str] = []
    accepted: list[str] = []
    for residual in residuals:
        text = residual.lower()
        if (
            "missing stage evidence" in text
            or "missing evaluator" in text
            or "missing structured evaluator" in text
            or "missing ux anchor scorecard" in text
        ):
            accepted.append(residual)
        else:
            blocking.append(residual)
    return blocking, accepted


def build_campaign_audit(
    root: Path,
    loop_id: str,
    *,
    state_path: Path | str | None,
    ledger_path: Path | str | None,
    episodes_path: Path | str | None,
    inbox_dir: Path | str | None,
) -> dict[str, Any]:
    """Build a deterministic local-file audit report without writing artifacts."""
    root = Path(root)
    resolved_state = _resolve(root, state_path, STATE_REL)
    resolved_ledger = _resolve(root, ledger_path, LEDGER_REL)
    resolved_episodes = _resolve(root, episodes_path, EPISODES_REL)
    resolved_inbox = _resolve(root, inbox_dir, INBOX_DIR_REL)
    resolved_proposals = root / PROPOSALS_DIR_REL

    state, state_errors = _load_yaml_mapping(resolved_state)
    ledger, ledger_errors = _load_yaml_mapping(resolved_ledger)
    episodes, episode_errors = _load_jsonl(resolved_episodes)
    closeout_scopes = _closeout_episode_child_scopes(episodes, loop_id)
    state_history_scopes = _state_history_child_scopes(state, loop_id)
    primary_run = _matching_run(ledger, loop_id)
    child_run_ids = _child_run_ids(closeout_scopes + state_history_scopes)
    runs = _matching_runs(ledger, [loop_id, *child_run_ids])
    if primary_run and all(run is not primary_run for run in runs):
        runs.insert(0, primary_run)
    run = primary_run or (runs[-1] if runs else {})
    learning_rows, learning_errors = _learning_rows(
        root,
        loop_id,
        resolved_episodes,
        resolved_inbox,
        episodes=episodes,
        episode_errors=episode_errors,
    )
    episode_artifact_errors = list(learning_errors)
    proposal_rows, proposal_errors = _proposal_learning_rows(root, loop_id, resolved_proposals)
    learning_rows.extend(proposal_rows)
    learning_rows.extend(_route_failure_rows(state, loop_id))
    learning_rows.sort(key=lambda row: (row["source"], row["learning_state"], row["summary"]))
    learning_errors.extend(proposal_errors)

    source_artifacts = {
        "state": _artifact(resolved_state, errors=state_errors),
        "ledger": _artifact(resolved_ledger, errors=ledger_errors),
        "episodes": _artifact(resolved_episodes, errors=episode_artifact_errors),
        "inbox": _artifact(resolved_inbox),
        "proposals": _artifact(resolved_proposals, errors=proposal_errors),
    }
    child_scopes = _child_scopes(state, run, loop_id, closeout_scopes)
    stage_evidence, stage_residuals = _stage_evidence_for_runs(
        runs,
        expected_child_run_ids=child_run_ids,
    )
    evaluator_evidence = _evaluator_evidence(stage_evidence, child_scopes)
    truthful_absence = _truthful_inline_absence(learning_rows)
    if truthful_absence.get("accepted"):
        stage_evidence["truthful_absence"] = truthful_absence
        evaluator_evidence["truthful_absence"] = truthful_absence
    residuals = list(stage_residuals)
    if state_errors:
        residuals.extend(state_errors)
    if ledger_errors:
        residuals.extend(ledger_errors)
    if learning_errors:
        residuals.extend(learning_errors)
    if not learning_rows:
        residuals.append("missing learning closure evidence")
    if evaluator_evidence["provenance"] != PROVENANCE_MISSING:
        if not evaluator_evidence.get("structured_scores"):
            residuals.append("missing structured evaluator score fields")
        if not evaluator_evidence.get("ux_scorecards"):
            residuals.append("missing UX Anchor Scorecard fields")
        if not evaluator_evidence.get("verification_commands"):
            residuals.append("missing evaluator verification command fields")
    residuals, accepted_absence_residuals = _nonblocking_absence_residuals(
        residuals,
        truthful_absence=truthful_absence,
    )

    scorecard = {
        "source_artifacts": _aggregate_provenance(
            artifact["provenance"]
            for key, artifact in source_artifacts.items()
            if key != "proposals" or artifact["exists"] or artifact["errors"]
        ),
        "child_scopes": _aggregate_provenance(
            scope["provenance"] for scope in child_scopes
        ),
        "stage_evidence": _effective_evidence_provenance(stage_evidence),
        "evaluator_evidence": _effective_evidence_provenance(evaluator_evidence),
        "learning_closure": _learning_score(
            learning_rows,
            truthful_absence=truthful_absence,
        ),
    }
    scorecard["overall_provenance"] = _aggregate_provenance(scorecard.values())
    route = _recommend_next_route(
        residuals=residuals,
        stage_evidence=stage_evidence,
        evaluator_evidence=evaluator_evidence,
        learning_rows=learning_rows,
    )
    campaign_provenance = (
        PROVENANCE_REPO_NATIVE
        if (state and str(state.get("loop_id") or "") == loop_id) or closeout_scopes
        else PROVENANCE_MISSING
        if not state
        else PROVENANCE_CONFLICT
    )
    state_matches_loop = bool(state and str(state.get("loop_id") or "") == loop_id)
    approval_basis = str(
        (_safe_mapping(state.get("autonomy_budget")).get("approval_basis") if state_matches_loop else "")
        or _campaign_detail_from_children(child_scopes, "approval_basis")
        or ""
    )
    learning_harvester = build_learning_harvester_report(
        learning_rows=learning_rows,
        residuals=residuals,
        approval_basis=approval_basis,
    )
    budget = (
        state.get("autonomy_budget")
        if state_matches_loop and isinstance(state.get("autonomy_budget"), dict)
        else _campaign_detail_from_children(child_scopes, "autonomy_budget") or {}
    )
    loop_decision = _campaign_detail_from_children(child_scopes, "loop_decision") or {}
    selected_candidate = _campaign_detail_from_children(child_scopes, "selected_candidate")
    stop_conditions = (
        budget.get("stop_conditions")
        if isinstance(budget, dict) and isinstance(budget.get("stop_conditions"), list)
        else _campaign_detail_from_children(child_scopes, "stop_conditions") or []
    )
    child_vision = _campaign_detail_from_children(child_scopes, "vision")
    vision = (
        _vision_from_mapping(state.get("vision"), PROVENANCE_REPO_NATIVE)
        if state_matches_loop
        else _vision_from_mapping(child_vision, PROVENANCE_REPO_NATIVE)
        if child_vision
        else _vision_from_mapping({}, PROVENANCE_MISSING)
    )
    completion_reason = (
        _completion_reason_from_state(state)
        if state_matches_loop
        else str(_campaign_detail_from_children(child_scopes, "completion_reason") or "")
    )
    return {
        "schema_version": 1,
        "generated_at": _utc_now_iso(),
        "campaign": {
            "loop_id": loop_id,
            "objective": str(
                (state.get("objective") if state_matches_loop else "")
                or _campaign_detail_from_children(child_scopes, "goal")
                or run.get("goal")
                or ""
            ),
            "status": str(
                (state.get("status") if state_matches_loop else "")
                or ("observed_from_closeout" if child_scopes else "")
                or run.get("status")
                or ""
            ),
            "completion_reason": completion_reason,
            "iteration": state.get("iteration") if state_matches_loop else len(child_scopes) or None,
            "max_iterations": budget.get("max_iterations")
            if isinstance(budget, dict)
            else None,
            "vision": vision,
            "vision_band": vision["band"],
            "vision_score": vision["score"],
            "vision_provenance": vision["provenance"],
            "approval_basis": approval_basis,
            "budget": budget,
            "stop_conditions": stop_conditions,
            "selected_seed": (
                state.get("selected_seed") if state_matches_loop else None
            )
            or _campaign_detail_from_children(child_scopes, "selected_seed"),
            "selected_candidate": selected_candidate,
            "route_rationale": str(
                _campaign_detail_from_children(child_scopes, "route_rationale") or ""
            ),
            "stage_plan": _campaign_detail_from_children(child_scopes, "stage_plan")
            or [],
            "loop_decision": loop_decision,
            "closeout_episode_ids": [
                scope["closeout_episode_id"]
                for scope in child_scopes
                if scope.get("closeout_episode_id")
            ],
            "provenance": campaign_provenance,
        },
        "source_artifacts": source_artifacts,
        "child_scopes": child_scopes,
        "stage_evidence": stage_evidence,
        "evaluator_evidence": evaluator_evidence,
        "verification_commands": evaluator_evidence["verification_commands"],
        "learning_closure_rows": learning_rows,
        "learning_harvester": learning_harvester,
        "accepted_absence_residuals": accepted_absence_residuals,
        "traceability_scorecard": scorecard,
        "next_route_recommendation": route,
        "residual_risks": residuals,
        "validation": {
            "read_only": True,
            "local_file_only": True,
            "jsonl_errors": learning_errors,
            "allowed_learning_states": sorted(LEARNING_STATES),
        },
    }
