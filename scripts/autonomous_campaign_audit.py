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
                "route_rationale": str(
                    loop_decision.get("reason") or architect_judgment.get("rationale") or ""
                ),
            }
        )
    scopes.sort(key=lambda scope: str(scope.get("session_id") or ""))
    return scopes


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
    history = state.get("history")
    if not isinstance(history, list):
        return scopes
    for item in history:
        if not isinstance(item, dict):
            continue
        session_id = str(item.get("session_id") or item.get("run_id") or "").strip()
        if loop_id and session_id and session_id != loop_id:
            continue
        scopes.append(
            {
                "session_id": session_id or loop_id,
                "action": str(item.get("action") or ""),
                "candidate_id": str(item.get("candidate_id") or ""),
                "status": str(item.get("result") or item.get("status") or ""),
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
    return [by_session[key] for key in sorted(by_session)]


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
            "subagent_type": str(
                (summary or spawn or {}).get("subagent_type") or ""
            ),
            "summary_status": str((summary or {}).get("summary_status") or ""),
            "summary_disposition": str((summary or {}).get("summary_disposition") or ""),
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


def _evaluator_evidence(stage_evidence: dict[str, Any]) -> dict[str, Any]:
    stages = stage_evidence.get("stages")
    if not isinstance(stages, dict):
        return {"provenance": PROVENANCE_MISSING, "stages": []}
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
        return {"provenance": PROVENANCE_MISSING, "stages": []}
    provenance = _aggregate_provenance(
        str(stages[stage_id].get("provenance") or PROVENANCE_MISSING)
        for stage_id in evaluator_stage_ids
    )
    return {"provenance": provenance, "stages": evaluator_stage_ids}


def _record_matches_campaign(record: dict[str, Any], loop_id: str) -> bool:
    if str(record.get("session_id") or record.get("loop_id") or "") == loop_id:
        return True
    tags = record.get("tags")
    if isinstance(tags, list) and "autonomous-auto" in tags and "learning-closure" in tags:
        return True
    return False


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


def _learning_score(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return PROVENANCE_MISSING
    if any(row["learning_state"] == "missing_evidence" for row in rows):
        return PROVENANCE_CONFLICT
    return _aggregate_provenance(row["provenance"] for row in rows)


def _best_learning_rank(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return -1
    return max(LEARNING_STATE_RANK.get(str(row.get("learning_state")), -1) for row in rows)


def _recommend_next_route(
    *,
    residuals: list[str],
    stage_evidence: dict[str, Any],
    evaluator_evidence: dict[str, Any],
    learning_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if stage_evidence["provenance"] in {PROVENANCE_CONFLICT, PROVENANCE_MISSING}:
        return {
            "route": "repair_evidence",
            "reason": "Stage evidence is incomplete or contradictory.",
        }
    if evaluator_evidence["provenance"] in {PROVENANCE_CONFLICT, PROVENANCE_MISSING}:
        return {
            "route": "repair_evidence",
            "reason": "Evaluator evidence is missing or incomplete.",
        }
    if _best_learning_rank(learning_rows) < LEARNING_STATE_RANK["implemented"]:
        return {
            "route": "plan_learning_closure",
            "reason": "Learning evidence is captured but not implemented or verified.",
        }
    if residuals:
        return {"route": "review_residuals", "reason": "Residual risks remain."}
    return {"route": "stop", "reason": "Campaign evidence is complete and learning is closed."}


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

    state, state_errors = _load_yaml_mapping(resolved_state)
    ledger, ledger_errors = _load_yaml_mapping(resolved_ledger)
    episodes, episode_errors = _load_jsonl(resolved_episodes)
    closeout_scopes = _closeout_episode_child_scopes(episodes, loop_id)
    primary_run = _matching_run(ledger, loop_id)
    child_run_ids = _child_run_ids(closeout_scopes)
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

    source_artifacts = {
        "state": _artifact(resolved_state, errors=state_errors),
        "ledger": _artifact(resolved_ledger, errors=ledger_errors),
        "episodes": _artifact(resolved_episodes, errors=learning_errors),
        "inbox": _artifact(resolved_inbox),
    }
    child_scopes = _child_scopes(state, run, loop_id, closeout_scopes)
    stage_evidence, stage_residuals = _stage_evidence_for_runs(
        runs,
        expected_child_run_ids=child_run_ids,
    )
    evaluator_evidence = _evaluator_evidence(stage_evidence)
    residuals = list(stage_residuals)
    if state_errors:
        residuals.extend(state_errors)
    if ledger_errors:
        residuals.extend(ledger_errors)
    if learning_errors:
        residuals.extend(learning_errors)
    if not learning_rows:
        residuals.append("missing learning closure evidence")

    scorecard = {
        "source_artifacts": _aggregate_provenance(
            artifact["provenance"] for artifact in source_artifacts.values()
        ),
        "child_scopes": _aggregate_provenance(
            scope["provenance"] for scope in child_scopes
        ),
        "stage_evidence": stage_evidence["provenance"],
        "evaluator_evidence": evaluator_evidence["provenance"],
        "learning_closure": _learning_score(learning_rows),
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
            "completion_reason": str(
                state.get("completion_reason") if state_matches_loop else ""
            ),
            "iteration": state.get("iteration") if state_matches_loop else len(child_scopes) or None,
            "max_iterations": budget.get("max_iterations")
            if isinstance(budget, dict)
            else None,
            "approval_basis": str(
                (budget.get("approval_basis") if isinstance(budget, dict) else "")
                or _campaign_detail_from_children(child_scopes, "approval_basis")
                or ""
            ),
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
        "learning_closure_rows": learning_rows,
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
