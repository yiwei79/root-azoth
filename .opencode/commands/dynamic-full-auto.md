---
description: 'DYNAMIC-FULL-AUTO+ session: high-autonomy auto-family execution with
  an autonomy budget, adaptive discovery/evidence insertion, Checkpoint Γ, optional
  eval-swarm, bounded replay, and closeout'
agent: orchestrator
---

# /dynamic-full-auto $ARGUMENTS

**Primary specification:** `Read` **`.agents/skills/dynamic-full-auto/SKILL.md`** and execute it end-to-end for the goal in `$ARGUMENTS`. This command is the slash entry for that session mode; do not improvise a parallel workflow.

## Role

Orchestrator-only in main chat: this is the **high-autonomy posture** of the shared
auto-family engine. Start by declaring an **autonomy budget**, then continue through
latest-context intake, adaptive discovery / evidence insertion when needed, queen merge
into **`SWARM_RESEARCH_DIGEST.yaml`** when a digest is warranted, **Checkpoint Γ**
(re-classify + `auto-router`), optional **`/eval-swarm`**, bounded replay, and closeout.

Discovery is a shared capability across auto-family pipelines; it is **not** the defining
identity of this mode. The defining property here is that, once the autonomy budget is
approved, the orchestrator may continue end-to-end until a required human gate,
threshold stop, or explicit abort condition is reached.

## Autonomy Budget

Before execution, declare:

- goal
- selected mode = `dynamic-full-auto`
- replay threshold
- whether discovery / evidence insertion may be automatic
- recomposition stop conditions
- required human-gate boundaries

After approval, continue under that budget rather than treating this mode as a temporary
discovery wrapper that must hand off by definition.

## Iron laws (non-negotiable)

Follow the coordination rules in **`.agents/skills/dynamic-full-auto/SKILL.md`**: single-message fan-out, queen aggregation, no worker-to-worker chatter. Subagent work uses **`.agents/skills/subagent-router/SKILL.md`** **BL-011** spawn contract and **BL-012** typed handoffs.

## Gates

- **Scope / pipeline:** `Read` `docs/GATE_PROTOCOL.md` and apply it before the first
	**Write/Edit** in governed or M1 work, including digest mutation and the delivery tail. When you write `pipeline-gate.json`, set
	**`"pipeline"`** to the delivery command you actually run next — exactly one of
	**`"auto"`**, **`"deliver"`**, or **`"deliver-full"`**. Do **not** default to **`auto`** when
	the handoff is **`/deliver`** or **`/deliver-full`**.
- **`azoth_effect: write`:** Discovery waves are **read/analysis** unless scope already permits writes; **writes** (digest append, implementation) require the same gates as **`/auto`** for governed/M1 work.
- **Review failure:** If any review / audit stage returns request-changes, CRITICAL blockers, **`entropy: RED`**, or **`status: needs-input`**, **STOP** and wait for explicit human approval before continuing — same as **`/auto`**.
- **Replay threshold:** Apply the bounded replay contract from the skill and `/auto`:
  route findings to the lowest legitimate upstream corrective stage, stop at the
  approved threshold, and recompose or escalate instead of looping indefinitely.

## Evaluator routing

When deciding whether to insert PRE_DELIVERY_EVAL Wave C, or when the active run includes
an evaluator boundary, read **`.claude/commands/eval.md`** and apply **E1–E6** plus the
skill’s PRE_DELIVERY_EVAL section (including **`/eval-swarm`** when triggers fire).

## Cursor / other IDEs

This command is defined for **Claude Code** (`.claude/commands/`). Other tools receive the equivalent workflow surface via deploy (`python3 scripts/azoth-deploy.py`, D46): prompt/command mirrors for Copilot/OpenCode and a generated `azoth-dynamic-full-auto` wrapper skill for Codex.

**Normative behavior** lives in **`.agents/skills/dynamic-full-auto/SKILL.md`** — in particular:

- **Happy path (Cursor)** — Simulated scope-gate / pipeline-gate before writes (no PreToolUse); **`Task`** per delivery stage when the tool exists; Rich welcome via integrated terminal; digest mutations are writes and require an approved scope.
- **Happy path (Claude Code)** — Same flow; hooks may enforce gates mechanically where configured.
- **Gates** — When writing **`.azoth/pipeline-gate.json`**, set **`"pipeline"`** to the delivery command you will actually run next: **`"auto"`**, **`"deliver"`**, or **`"deliver-full"`** — do not default to `auto` when handing off to `/deliver` or `/deliver-full`.
- **Purpose** — `dynamic-full-auto` is the same orchestration engine in a stronger autonomy posture; it is no longer defined as discovery-first plus downstream handoff.

**Parity references:** `.cursor/rules/claude-code-parity.mdc`, `CLAUDE.md` (Cursor SessionStart gap, welcome paths).

## Arguments

Goal / session intent: **$ARGUMENTS**
