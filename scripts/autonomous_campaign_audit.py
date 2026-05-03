#!/usr/bin/env python3
"""Read-only autonomous-auto campaign audit builder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha1
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
ACCEPTED_STAGE_SUMMARY_DISPOSITIONS = {
    "accepted",
    "approve",
    "approved",
    "complete",
    "no-changes",
    "pass",
    "passed",
}
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
AUDIT_ITEM_CLASSES = {
    "insight-only",
    "proposal",
    "code-salvage",
    "cleanup-only",
    "no-action",
}
AUDIT_DISPOSITIONS = {"approve", "skip", "defer", "cleanup", "blocked"}
AUDIT_PROTECTED_BOUNDARIES = [
    "no apply routing",
    "no inbox writes",
    "no producer worktrees",
    "no worktree-sync",
    "no trusted-source registry change",
    "no land-now integration",
    "no kernel/governance/M1 mutation",
    "no credential or network expansion",
]
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
AUDIT_BOUNDARY_MARKERS = {
    "apply_routing": {"apply routing", "apply step", "apply-stage", "apply_stage"},
    "inbox_write": {"write inbox", "inbox write", "direct m3", "direct memory"},
    "producer_worktree": {"producer worktree", "producer branch", "producer handoff"},
    "worktree_sync": {"worktree-sync", "/worktree-sync"},
    "land_now_integration": {"land-now", "direct integration", "auto-integrate"},
    "protected_mutation": {"kernel", "governance", "m1", "credential", "network"},
}
STALE_AUDIT_MARKERS = {"stale", "detached", "outdated", "old main", "old base", "historical"}
CODE_SALVAGE_MARKERS = {
    "code",
    "salvage",
    "worktree",
    "producer",
    "handoff",
    "branch",
    "merge",
    "integration",
    "worktree-sync",
}
PROPOSAL_MARKERS = {"proposal", "hydrate"}
CLEANUP_MARKERS = {"cleanup", "clean up", "prune", "remove stale", "close them"}
INSIGHT_MARKERS = {"insight", "capture", "inbox", "intake", "learning", "memory"}
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
    target_band = (
        str(
            _first_present(vision.get("target_band"), latest.get("target_band"))
            or DEFAULT_VISION_TARGET_BAND
        )
        .strip()
        .lower()
    )
    band = (
        str(
            _first_present(
                vision.get("current_band"),
                vision.get("band"),
                latest.get("current_band"),
                latest.get("band"),
            )
            or "unevaluated"
        )
        .strip()
        .lower()
    )
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
        "target_band": target_band if target_band in VISION_BANDS else DEFAULT_VISION_TARGET_BAND,
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
            _safe_mapping(delegation_plan.get("run_ledger_evidence")).get("run_id") or session_id
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


def _campaign_detail_from_children(child_scopes: list[dict[str, Any]], field: str) -> Any:
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


def _residual_risks(summary: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    for field in ("residual_risks", "residual_risk", "risks"):
        for risk in _safe_scalar_list(summary.get(field)):
            text = str(risk).strip()
            if text:
                risks.append(text)
    return list(dict.fromkeys(risks))


def _stage_summary_is_complete(summary: dict[str, Any]) -> bool:
    status = str(summary.get("summary_status") or "").strip().lower()
    disposition = str(summary.get("summary_disposition") or "").strip().lower()
    return status == "complete" and disposition in ACCEPTED_STAGE_SUMMARY_DISPOSITIONS


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
        summary_accepted = bool(summary and _stage_summary_is_complete(summary))
        spawn_provenance = PROVENANCE_REPO_NATIVE if spawn else PROVENANCE_MISSING
        summary_provenance = PROVENANCE_REPO_NATIVE if summary else PROVENANCE_MISSING
        provenance = (
            PROVENANCE_REPO_NATIVE
            if spawn and summary_accepted
            else PROVENANCE_CONFLICT
            if spawn or summary
            else PROVENANCE_MISSING
        )
        if spawn and not summary:
            residuals.append(f"missing stage summary for {stage_id}")
        elif summary and not spawn:
            residuals.append(f"missing stage spawn for {stage_id}")
        elif spawn and summary and not summary_accepted:
            residuals.append(
                "blocking stage summary for "
                f"{stage_id}: status={str(summary.get('summary_status') or '')}, "
                f"disposition={str(summary.get('summary_disposition') or '')}"
            )
        stages[stage_id] = {
            "provenance": provenance,
            "run_id": str(run.get("run_id") or ""),
            "session_id": str(run.get("session_id") or run.get("run_id") or ""),
            "spawn_provenance": spawn_provenance,
            "summary_provenance": summary_provenance,
            "spawned_at": str((spawn or {}).get("spawned_at") or ""),
            "summary_recorded_at": str((summary or {}).get("summary_recorded_at") or ""),
            "subagent_type": str((summary or spawn or {}).get("subagent_type") or ""),
            "summary_status": str((summary or {}).get("summary_status") or ""),
            "summary_disposition": str((summary or {}).get("summary_disposition") or ""),
            "evaluator_disposition": str(
                (summary or {}).get("evaluator_disposition")
                or (summary or {}).get("summary_disposition")
                or ""
            ),
            "structured_scores": _structured_scores(summary or {}),
            "ux_scorecards": _ux_scorecards(summary or {}),
            "verification_commands": _verification_commands(summary or {}),
            "residual_risks": _residual_risks(summary or {}),
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
            risk.replace("for campaign", f"for child scope {run_id}") for risk in run_residuals
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
    residual_risks: list[str] = []
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
        residual_risks.extend(
            str(risk) for risk in _safe_list(scope.get("residual_risks")) if str(risk or "").strip()
        )
    return {
        "structured_scores": structured_scores,
        "ux_scorecards": ux_scorecards,
        "verification_commands": list(dict.fromkeys(verification_commands)),
        "residual_risks": list(dict.fromkeys(residual_risks)),
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
        provenance = PROVENANCE_REPO_NATIVE if any(child_quality.values()) else PROVENANCE_MISSING
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
    residual_risks: list[str] = []
    dispositions: list[str] = []
    for stage_id in evaluator_stage_ids:
        evidence = stages[stage_id]
        disposition = str(evidence.get("evaluator_disposition") or "").strip()
        if disposition:
            dispositions.append(disposition)
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
        residual_risks.extend(
            str(risk)
            for risk in _safe_list(evidence.get("residual_risks"))
            if str(risk or "").strip()
        )
    return {
        "provenance": provenance,
        "stages": evaluator_stage_ids,
        "dispositions": list(dict.fromkeys(dispositions)),
        "structured_scores": structured_scores + child_quality["structured_scores"],
        "ux_scorecards": ux_scorecards + child_quality["ux_scorecards"],
        "verification_commands": list(
            dict.fromkeys(verification_commands + child_quality["verification_commands"])
        ),
        "residual_risks": list(dict.fromkeys(residual_risks + child_quality["residual_risks"])),
    }


def _retrospective_evaluator_evidence(learning_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[Any] = []
    ux_scorecards: list[dict[str, Any]] = []
    verification_commands: list[str] = []
    residual_risks: list[str] = []
    dispositions: list[str] = []
    evidence_count = 0
    for row in learning_rows:
        if not row.get("strict_campaign_match"):
            continue
        has_evidence = False
        row_scores = _safe_scalar_list(row.get("structured_scores"))
        if row_scores:
            scores.extend(row_scores)
            has_evidence = True
        row_scorecards = [
            item for item in _safe_list(row.get("ux_scorecards")) if isinstance(item, dict)
        ]
        if row_scorecards:
            ux_scorecards.extend(row_scorecards)
            has_evidence = True
        for command in _safe_list(row.get("verification_commands")):
            text = str(command or "").strip()
            if text:
                verification_commands.append(text)
                has_evidence = True
        for risk in _safe_list(row.get("residual_risks")):
            text = str(risk or "").strip()
            if text:
                residual_risks.append(text)
                has_evidence = True
        disposition = str(row.get("evaluator_disposition") or "").strip()
        if disposition:
            dispositions.append(disposition)
            has_evidence = True
        if has_evidence:
            evidence_count += 1
    return {
        "provenance": PROVENANCE_REPO_NATIVE if evidence_count else PROVENANCE_MISSING,
        "retrospective_evidence_count": evidence_count,
        "dispositions": list(dict.fromkeys(dispositions)),
        "structured_scores": scores,
        "ux_scorecards": ux_scorecards,
        "verification_commands": list(dict.fromkeys(verification_commands)),
        "residual_risks": list(dict.fromkeys(residual_risks)),
    }


def _merge_retrospective_evaluator_evidence(
    evaluator_evidence: dict[str, Any], retrospective: dict[str, Any]
) -> dict[str, Any]:
    if not retrospective.get("retrospective_evidence_count"):
        return evaluator_evidence
    merged = dict(evaluator_evidence)
    merged["structured_scores"] = _safe_scalar_list(
        merged.get("structured_scores")
    ) + _safe_scalar_list(retrospective.get("structured_scores"))
    merged["ux_scorecards"] = [
        item for item in _safe_list(merged.get("ux_scorecards")) if isinstance(item, dict)
    ] + [item for item in _safe_list(retrospective.get("ux_scorecards")) if isinstance(item, dict)]
    merged["verification_commands"] = list(
        dict.fromkeys(
            [
                str(command)
                for command in (
                    _safe_list(merged.get("verification_commands"))
                    + _safe_list(retrospective.get("verification_commands"))
                )
                if str(command or "").strip()
            ]
        )
    )
    merged["residual_risks"] = list(
        dict.fromkeys(
            [
                str(risk)
                for risk in (
                    _safe_list(merged.get("residual_risks"))
                    + _safe_list(retrospective.get("residual_risks"))
                )
                if str(risk or "").strip()
            ]
        )
    )
    merged["dispositions"] = list(
        dict.fromkeys(
            [
                str(disposition)
                for disposition in (
                    _safe_list(merged.get("dispositions"))
                    + _safe_list(retrospective.get("dispositions"))
                )
                if str(disposition or "").strip()
            ]
        )
    )
    merged["retrospective_evidence_count"] = retrospective["retrospective_evidence_count"]
    if merged["structured_scores"] or merged["ux_scorecards"] or merged["verification_commands"]:
        merged["provenance"] = (
            PROVENANCE_CONFLICT
            if evaluator_evidence.get("provenance") == PROVENANCE_CONFLICT
            else PROVENANCE_REPO_NATIVE
        )
    return merged


def _record_matches_campaign(record: dict[str, Any], loop_id: str) -> bool:
    if str(record.get("session_id") or record.get("loop_id") or "") == loop_id:
        return True
    tags = record.get("tags")
    if isinstance(tags, list) and "autonomous-auto" in tags and "learning-closure" in tags:
        return True
    return False


def _mapping_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(
            [str(key) for key in value.keys()] + [_mapping_text(item) for item in value.values()]
        )
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


def _learning_row_from_record(
    root: Path,
    source: Path,
    record: dict[str, Any],
    *,
    loop_id: str,
) -> dict[str, Any]:
    row = {
        "learning_state": _learning_state(record),
        "provenance": PROVENANCE_REPO_NATIVE,
        "source": _rel(root, source),
        "summary": _learning_summary(record),
        "strict_campaign_match": str(record.get("session_id") or record.get("loop_id") or "")
        == loop_id,
    }
    scores = _structured_scores(record)
    if scores:
        row["structured_scores"] = scores
    scorecards = _ux_scorecards(record)
    if scorecards:
        row["ux_scorecards"] = scorecards
    commands = _verification_commands(record)
    if commands:
        row["verification_commands"] = commands
    risks = _residual_risks(record)
    if risks:
        row["residual_risks"] = risks
    disposition = str(record.get("evaluator_disposition") or record.get("disposition") or "")
    if disposition.strip():
        row["evaluator_disposition"] = disposition.strip()
    return row


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
            rows.append(_learning_row_from_record(root, episodes_path, record, loop_id=loop_id))
    if inbox_dir.is_dir():
        for path in sorted(inbox_dir.glob("*.jsonl")):
            inbox_rows, inbox_errors = _load_jsonl(path)
            errors.extend(inbox_errors)
            for record in inbox_rows:
                if _record_matches_campaign(record, loop_id):
                    rows.append(_learning_row_from_record(root, path, record, loop_id=loop_id))
    rows.sort(key=lambda row: (row["source"], row["learning_state"], row["summary"]))
    return rows, errors


def _proposal_learning_rows(
    root: Path, loop_id: str, proposals_dir: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not proposals_dir.is_dir():
        return rows, errors
    completed_refs = _completed_task_refs(root)
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
        proposal_refs = _proposal_task_refs(data)
        stale_refs = sorted(proposal_refs & completed_refs)
        if stale_refs:
            state = "stale_or_rejected"
        rows.append(
            {
                "learning_state": state,
                "provenance": PROVENANCE_REPO_NATIVE,
                "source": _rel(root, path),
                "summary": str(data.get("title") or data.get("summary") or path.stem),
                "reason": (
                    "proposal task refs already complete: " + ", ".join(stale_refs)
                    if stale_refs
                    else ""
                ),
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


def _collect_completed_task_refs(value: Any) -> set[str]:
    completed: set[str] = set()
    if isinstance(value, dict):
        raw_refs = value.get("completed_task_refs")
        if isinstance(raw_refs, list):
            completed.update(str(item).strip() for item in raw_refs if str(item or "").strip())
        task_ref = str(value.get("task_ref") or value.get("id") or "").strip()
        status = str(value.get("status") or "").strip().lower()
        if task_ref and (status == "complete" or value.get("completed_date")):
            completed.add(task_ref)
        hydrated_ref = str(value.get("hydrated_task_ref") or "").strip()
        if hydrated_ref and value.get("hydrated_at"):
            completed.add(hydrated_ref)
        for item in value.values():
            completed.update(_collect_completed_task_refs(item))
    elif isinstance(value, list):
        for item in value:
            completed.update(_collect_completed_task_refs(item))
    return completed


def _completed_task_refs(root: Path) -> set[str]:
    completed: set[str] = set()
    initiative_bank_paths = sorted((root / ".azoth/initiative-banks").glob("*.yaml"))
    for path in [root / ".azoth/roadmap.yaml", *initiative_bank_paths]:
        data, _errors = _load_yaml_mapping(path)
        if data:
            completed.update(_collect_completed_task_refs(data))
    return completed


def _proposal_task_refs(data: dict[str, Any]) -> set[str]:
    refs: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {
                    "proposed_task_ref",
                    "proposed_task_id",
                    "task_ref",
                    "hydrated_task_ref",
                    "expected_task_ref_at_review_time",
                }:
                    text = str(item or "").strip()
                    if text:
                        refs.add(text)
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    return refs


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
            {str(row.get("source") or "") for row in accepted_rows if str(row.get("source") or "")}
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
    signal_id = str(
        signal.get("id") or signal.get("signal_id") or signal.get("summary") or "learning-signal"
    )
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
    shared_or_medium = (
        severity in {"medium", "high", "critical"} or "shared surface" in text.casefold()
    )

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
        "blast_radius": "protected"
        if protected
        else "cross_system"
        if cross_system
        else "internal",
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
            source_refs = list(
                dict.fromkeys(current.get("source_refs", []) + decision.get("source_refs", []))
            )
            current["source_refs"] = source_refs
        if (
            current is None
            or HARVESTER_ROUTE_PRIORITY[decision["route"]]
            > HARVESTER_ROUTE_PRIORITY[current["route"]]
        ):
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


def _audit_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_audit_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_audit_text(item) for item in value)
    return str(value or "")


def _decision_core_text(decision: dict[str, Any]) -> str:
    return _audit_text(
        {
            "signal_id": decision.get("signal_id"),
            "dedupe_key": decision.get("dedupe_key"),
            "source_refs": decision.get("source_refs"),
            "route": decision.get("route"),
            "selected_action": decision.get("selected_action"),
            "verification_requirement": decision.get("verification_requirement"),
            "residual_risk": decision.get("residual_risk"),
        }
    )


def _audit_slug(value: str, *, fallback: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or fallback


def _audit_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, default=str)
    return sha1(text.encode("utf-8")).hexdigest()[:8]


def _decision_item_class(decision: dict[str, Any]) -> str:
    text = _decision_core_text(decision).casefold()
    selected_action = str(decision.get("selected_action") or "").casefold()
    route = str(decision.get("route") or "").casefold()
    if _contains_marker(text, CLEANUP_MARKERS):
        return "cleanup-only"
    if _contains_marker(text, CODE_SALVAGE_MARKERS):
        return "code-salvage"
    if (
        route == "proposal_needed"
        or selected_action == "refine_proposal"
        or _contains_marker(text, PROPOSAL_MARKERS)
    ):
        return "proposal"
    if (
        route in {"capture_only", "defer_to_intake", "auto_self_heal_now"}
        or selected_action in {"capture_only", "defer_to_inbox_intake", "open_normal_child_scope"}
        or _contains_marker(text, INSIGHT_MARKERS)
    ):
        return "insight-only"
    return "no-action"


def _decision_freshness(decision: dict[str, Any]) -> str:
    text = _decision_core_text(decision).casefold()
    route = str(decision.get("route") or "").casefold()
    if route == "stale_or_rejected":
        return "stale_or_rejected"
    if _contains_marker(text, STALE_AUDIT_MARKERS):
        return "stale_or_historical"
    if "2026-04-21" in text:
        return "historical_replay"
    return "current"


def _boundary_hits(decision: dict[str, Any]) -> list[str]:
    text = _decision_core_text(decision).casefold()
    hits: list[str] = []
    for boundary, markers in AUDIT_BOUNDARY_MARKERS.items():
        if _contains_marker(text, markers):
            hits.append(boundary)
    if decision.get("protected_gate_required") and "protected_gate" not in hits:
        hits.append("protected_gate")
    return sorted(dict.fromkeys(hits))


def _blocked_alternatives(decision: dict[str, Any], boundary_hits: list[str]) -> list[str]:
    alternatives = [str(item) for item in _safe_list(decision.get("rejected_alternatives")) if item]
    text = _decision_core_text(decision).casefold()
    if "direct integration" in text and "direct_integration" not in alternatives:
        alternatives.append("direct_integration")
    if "worktree-sync" in text and "worktree_sync_during_audit" not in alternatives:
        alternatives.append("worktree_sync_during_audit")
    if "apply" in text and "audit_stage_apply" not in alternatives:
        alternatives.append("audit_stage_apply")
    alternatives.extend(f"protected_boundary:{hit}" for hit in boundary_hits)
    return sorted(dict.fromkeys(alternatives))


def _recommended_disposition(
    *,
    decision: dict[str, Any],
    item_class: str,
    freshness_status: str,
    boundary_hits: list[str],
) -> str:
    route = str(decision.get("route") or "").casefold()
    if decision.get("protected_gate_required") or route == "human_gate_required":
        return "blocked"
    if item_class == "cleanup-only":
        return "cleanup"
    if route == "stale_or_rejected" or item_class == "no-action":
        return "skip"
    if item_class == "code-salvage" and freshness_status != "current":
        return "defer"
    if "land_now_integration" in boundary_hits and item_class == "code-salvage":
        return "defer"
    return "approve"


def _least_powerful_action(item_class: str, freshness_status: str) -> str:
    if item_class == "insight-only":
        return "operator-reviewed inbox/intake candidate in a later apply slice"
    if item_class == "proposal":
        return "proposal or task candidate for a later scoped refinement/hydration slice"
    if item_class == "code-salvage":
        if freshness_status == "current":
            return "fresh producer handoff request after explicit item approval"
        return "fresh producer replay from the current target branch before any handoff"
    if item_class == "cleanup-only":
        return "named cleanup request after explicit item approval"
    return "no action"


def _apply_target(item_class: str) -> str:
    return {
        "insight-only": "future_inbox_intake_candidate",
        "proposal": "future_proposal_or_task_candidate",
        "code-salvage": "future_fresh_producer_handoff_request",
        "cleanup-only": "future_named_cleanup_request",
        "no-action": "none",
    }[item_class]


def _blocked_until(
    *,
    item_class: str,
    disposition: str,
    freshness_status: str,
    boundary_hits: list[str],
) -> str:
    if disposition == "blocked":
        return "fresh explicit approval for the protected boundary"
    if item_class == "code-salvage" and freshness_status != "current":
        return "fresh producer replay approval plus current-target-branch verification"
    if item_class in {"insight-only", "proposal", "cleanup-only"}:
        return "explicit item-disposition approval and a separate apply-capable slice"
    if boundary_hits:
        return "protected-boundary review"
    return "not applicable"


def _verification_hint(decision: dict[str, Any], item_class: str) -> str:
    explicit = str(decision.get("verification_requirement") or "").strip()
    if explicit:
        return explicit
    if item_class == "code-salvage":
        return "verify replay from the current target branch before producer handoff"
    if item_class == "insight-only":
        return "verify source refs before governed intake capture"
    return "verify source refs and protected boundaries before apply"


def _audit_item_from_decision(decision: dict[str, Any]) -> dict[str, Any]:
    item_class = _decision_item_class(decision)
    freshness_status = _decision_freshness(decision)
    boundary_hits = _boundary_hits(decision)
    disposition = _recommended_disposition(
        decision=decision,
        item_class=item_class,
        freshness_status=freshness_status,
        boundary_hits=boundary_hits,
    )
    source_refs = [str(ref) for ref in _safe_list(decision.get("source_refs")) if str(ref or "")]
    item_key = {
        "signal_id": decision.get("signal_id"),
        "source_refs": source_refs,
        "dedupe_key": decision.get("dedupe_key"),
    }
    return {
        "item_id": f"A-{_audit_hash(item_key)}",
        "item_class": item_class,
        "source_refs": source_refs,
        "source_summary": str(decision.get("signal_id") or decision.get("dedupe_key") or ""),
        "freshness_status": freshness_status,
        "recommended_disposition": disposition,
        "least_powerful_action": _least_powerful_action(item_class, freshness_status),
        "risk_level": str(decision.get("severity") or "low"),
        "protected_boundary": boundary_hits,
        "apply_target": _apply_target(item_class),
        "verification_hint": _verification_hint(decision, item_class),
        "blocked_until": _blocked_until(
            item_class=item_class,
            disposition=disposition,
            freshness_status=freshness_status,
            boundary_hits=boundary_hits,
        ),
        "blocked_alternatives": _blocked_alternatives(decision, boundary_hits),
        "residual_risk": str(decision.get("residual_risk") or ""),
    }


def _approval_reply(items: list[dict[str, Any]]) -> str:
    approved = [
        item for item in items if item["recommended_disposition"] in {"approve", "cleanup", "defer"}
    ]
    if not approved:
        return (
            "No applyable audit items are recommended. Reply with item ids and dispositions "
            "if you want a later apply-capable slice; broad replies such as 'approve the audit' "
            "remain invalid."
        )
    clauses = [
        f"{item['recommended_disposition']} {item['item_id']} as {item['item_class']}"
        for item in approved[:6]
    ]
    return (
        "Reply with item ids and dispositions, for example: "
        + "; ".join(clauses)
        + ". This records approval intent only; it does not run apply, write inbox, "
        "open producer worktrees, run worktree-sync, or integrate."
    )


def _source_summary(items: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    by_class = {item_class: 0 for item_class in sorted(AUDIT_ITEM_CLASSES)}
    for item in items:
        by_class[item["item_class"]] += 1
    source_refs = sorted(
        {ref for item in items for ref in _safe_list(item.get("source_refs")) if str(ref or "")}
    )
    scorecard = _safe_mapping(report.get("traceability_scorecard"))
    return {
        "item_count": len(items),
        "by_class": by_class,
        "source_refs": source_refs,
        "overall_provenance": str(scorecard.get("overall_provenance") or "unknown"),
        "source_report": "autonomous-auto campaign audit",
    }


def _approval_contract(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "allowed_dispositions": sorted(AUDIT_DISPOSITIONS),
        "requires_item_ids": True,
        "requires_dispositions": True,
        "valid_reply_template": _approval_reply(items),
        "invalid_reply_examples": [
            "approve the audit",
            "do all recommended actions",
            "land now",
        ],
        "ambiguous_approval_rule": (
            "Broad approval does not authorize apply; approval must bind item ids to "
            "explicit dispositions."
        ),
        "apply_authority": False,
        "side_effects_authorized": [],
        "protected_boundaries": AUDIT_PROTECTED_BOUNDARIES,
        "fail_closed_rules": [
            "No item id means no apply.",
            "No disposition means no apply.",
            "Producer worktrees, worktree-sync, inbox writes, apply routing, and integration "
            "belong to later explicitly approved slices.",
        ],
    }


def build_nightly_automation_audit_bundle(
    report: dict[str, Any],
    *,
    audit_window: dict[str, Any] | None = None,
    target_branch: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Project a campaign audit into a read-only nightly approval bundle."""
    campaign = _safe_mapping(report.get("campaign"))
    harvester = _safe_mapping(report.get("learning_harvester"))
    decisions = [
        decision
        for decision in _safe_list(harvester.get("decisions"))
        if isinstance(decision, dict)
    ]
    items = sorted(
        (_audit_item_from_decision(decision) for decision in decisions),
        key=lambda item: item["item_id"],
    )
    blocked_items = [
        item
        for item in items
        if item["recommended_disposition"] in {"blocked", "defer"} or item.get("protected_boundary")
    ]
    branch = str(
        target_branch or campaign.get("target_branch") or campaign.get("branch") or "unknown"
    )
    window = audit_window or {
        "basis": "campaign_audit_report",
        "loop_id": str(campaign.get("loop_id") or ""),
        "generated_at": str(report.get("generated_at") or ""),
    }
    bundle_id_basis = {
        "loop_id": campaign.get("loop_id"),
        "target_branch": branch,
        "item_ids": [item["item_id"] for item in items],
    }
    protected_boundary_hits = sorted(
        {hit for item in items for hit in _safe_list(item.get("protected_boundary"))}
    )
    return {
        "schema_version": 1,
        "bundle_id": (
            f"nightly-automation-audit-"
            f"{_audit_slug(str(campaign.get('loop_id') or ''), fallback=_audit_hash(bundle_id_basis))}"
        ),
        "audit_window": window,
        "generated_at": generated_at or _utc_now_iso(),
        "target_branch": branch,
        "branch_freshness": {
            "status": "current_local_state" if branch != "unknown" else "unknown",
            "materiality": "material",
            "note": "Audit bundle is advisory until source refs and target branch are verified.",
        },
        "source_summary": _source_summary(items, report),
        "items": items,
        "blocked_items": blocked_items,
        "recommended_operator_reply": _approval_reply(items),
        "approval_contract": _approval_contract(items),
        "protected_boundary_hits": protected_boundary_hits,
        "verification_notes": [
            "Audit bundle generation is read-only and grants no apply authority.",
            "Code-salvage items from stale or detached worktrees must be replayed from the current target branch.",
            "Insight-only items stay as future inbox/intake candidates until a later apply-capable slice is explicitly approved.",
            "Direct integration and land-now remain separate protected approvals.",
        ],
        "validation": {
            "read_only": True,
            "applies_actions": False,
            "forbidden_side_effects": [
                "producer_worktree_creation",
                "inbox_write",
                "worktree_sync",
                "apply_routing",
                "handoff_integration",
                "trusted_source_registry_change",
                "roadmap_or_backlog_mutation",
            ],
        },
    }


def _evaluator_quality_text(evaluator_evidence: dict[str, Any]) -> str:
    scores = _safe_scalar_list(evaluator_evidence.get("structured_scores"))
    score_text = ", ".join(str(score) for score in scores) if scores else "not recorded"
    dispositions = _safe_scalar_list(evaluator_evidence.get("dispositions"))
    disposition_text = (
        ", ".join(str(disposition) for disposition in dispositions)
        if dispositions
        else "not recorded"
    )
    ux_present = bool(evaluator_evidence.get("ux_scorecards"))
    return (
        f"Evaluator disposition: {disposition_text}; "
        f"scores: {score_text}; "
        f"UX Anchor Scorecard {'present' if ux_present else 'not recorded'}."
    )


def _campaign_audit_executive_read(
    *,
    campaign: dict[str, Any],
    evaluator_evidence: dict[str, Any],
    residuals: list[str],
    route: dict[str, Any],
) -> dict[str, Any]:
    completion_reason = str(campaign.get("completion_reason") or "unknown")
    vision_band = str(campaign.get("vision_band") or "unknown")
    residual = "; ".join(residuals) if residuals else "none"
    next_route = str(route.get("route") or "unknown")
    implication = (
        "Campaign evidence is complete enough to stop without repair."
        if not residuals and next_route == "stop"
        else "Campaign evidence needs follow-up before the operator can treat it as complete."
    )
    return {
        "change_summary": f"Campaign {completion_reason} with {vision_band} UX vision evidence.",
        "quality_assessment": _evaluator_quality_text(evaluator_evidence),
        "residual_risk": residual,
        "next_route": next_route,
        "operator_implication": implication,
        "evidence_contract": [
            "campaign declaration and budget",
            "delegated stage evidence",
            "evaluator scores and UX Anchor Scorecard",
            "verification commands",
            "learning closure",
        ],
    }


def _campaign_implications(executive_read: dict[str, Any]) -> list[str]:
    if executive_read.get("residual_risk") == "none" and executive_read.get("next_route") == "stop":
        return [
            "Campaign can stop cleanly; no repair route is recommended.",
            "Operator-facing evidence is repo-native and complete enough for audit without raw ledger spelunking.",
        ]
    return [
        "Campaign needs a follow-up route before it should be treated as fully complete.",
        "Operator-facing evidence should name the residual risk and recommended repair route.",
    ]


def _ux_anchor_fit(
    *,
    campaign: dict[str, Any],
    evaluator_evidence: dict[str, Any],
    residuals: list[str],
    scorecard: dict[str, Any],
) -> dict[str, Any]:
    ux_present = bool(evaluator_evidence.get("ux_scorecards"))
    vision_band = str(campaign.get("vision_band") or "unknown")
    provenance = str(scorecard.get("overall_provenance") or "unknown")
    if (
        not residuals
        and ux_present
        and vision_band == "green"
        and provenance == PROVENANCE_REPO_NATIVE
    ):
        band = "green"
    elif residuals:
        band = "yellow"
    else:
        band = "red"
    gaps: list[str] = []
    if not ux_present:
        gaps.append("missing UX Anchor Scorecard")
    if residuals:
        gaps.extend(residuals)
    return {
        "band": band,
        "evidence": [
            f"vision_band={vision_band}",
            f"traceability={provenance}",
            "UX Anchor Scorecard present" if ux_present else "UX Anchor Scorecard missing",
        ],
        "gaps": gaps,
    }


def _operator_packet_parity(
    *,
    campaign: dict[str, Any],
    executive_read: dict[str, Any],
    route: dict[str, Any],
) -> dict[str, Any]:
    return {
        "objective": campaign.get("objective") or "",
        "approval_basis": campaign.get("approval_basis") or "",
        "next_likely_move": route.get("route") or "unknown",
        "stop_conditions": campaign.get("stop_conditions") or [],
        "residual_risk": executive_read.get("residual_risk") or "unknown",
    }


def _public_learning_rows(learning_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if key != "strict_campaign_match"}
        for row in learning_rows
    ]


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
            "confidence_basis": [f"stage_evidence provenance is {stage_evidence['provenance']}"],
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
    evaluator_evidence = _merge_retrospective_evaluator_evidence(
        _evaluator_evidence(stage_evidence, child_scopes),
        _retrospective_evaluator_evidence(learning_rows),
    )
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
        residuals.extend(str(risk) for risk in _safe_list(evaluator_evidence.get("residual_risks")))
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
        "child_scopes": _aggregate_provenance(scope["provenance"] for scope in child_scopes),
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
        (
            _safe_mapping(state.get("autonomy_budget")).get("approval_basis")
            if state_matches_loop
            else ""
        )
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
    campaign = {
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
        "max_iterations": budget.get("max_iterations") if isinstance(budget, dict) else None,
        "vision": vision,
        "vision_band": vision["band"],
        "vision_score": vision["score"],
        "vision_provenance": vision["provenance"],
        "approval_basis": approval_basis,
        "budget": budget,
        "stop_conditions": stop_conditions,
        "branch": str((state.get("branch") if state_matches_loop else "") or ""),
        "selected_seed": (state.get("selected_seed") if state_matches_loop else None)
        or _campaign_detail_from_children(child_scopes, "selected_seed"),
        "selected_candidate": selected_candidate,
        "route_rationale": str(
            _campaign_detail_from_children(child_scopes, "route_rationale") or ""
        ),
        "stage_plan": _campaign_detail_from_children(child_scopes, "stage_plan") or [],
        "loop_decision": loop_decision,
        "closeout_episode_ids": [
            scope["closeout_episode_id"]
            for scope in child_scopes
            if scope.get("closeout_episode_id")
        ],
        "provenance": campaign_provenance,
    }
    executive_read = _campaign_audit_executive_read(
        campaign=campaign,
        evaluator_evidence=evaluator_evidence,
        residuals=residuals,
        route=route,
    )
    payload = {
        "schema_version": 1,
        "generated_at": _utc_now_iso(),
        "campaign": campaign,
        "executive_read": executive_read,
        "campaign_implications": _campaign_implications(executive_read),
        "ux_anchor_fit": _ux_anchor_fit(
            campaign=campaign,
            evaluator_evidence=evaluator_evidence,
            residuals=residuals,
            scorecard=scorecard,
        ),
        "operator_packet_parity": _operator_packet_parity(
            campaign=campaign,
            executive_read=executive_read,
            route=route,
        ),
        "source_artifacts": source_artifacts,
        "child_scopes": child_scopes,
        "stage_evidence": stage_evidence,
        "evaluator_evidence": evaluator_evidence,
        "verification_commands": evaluator_evidence["verification_commands"],
        "learning_closure_rows": _public_learning_rows(learning_rows),
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
    bundle = build_nightly_automation_audit_bundle(payload)
    payload["nightly_audit_bundle"] = bundle
    payload["approval_contract"] = bundle["approval_contract"]
    return payload
