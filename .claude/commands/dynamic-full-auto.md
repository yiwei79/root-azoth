---
description: "DYNAMIC-FULL-AUTO+ session: adaptive research/explore swarms, digest, Checkpoint Γ, optional eval-swarm, then /auto-style delivery"
azoth_effect: write
agent: orchestrator
---

# /dynamic-full-auto $ARGUMENTS

**Primary specification:** `Read` **`skills/dynamic-full-auto/SKILL.md`** and execute it end-to-end for the goal in `$ARGUMENTS`. This command is the slash entry for that session mode; do not improvise a parallel workflow.

## Role

Orchestrator-only in main chat: run **adaptive** discovery waves (research + explore), queen merge into **`SWARM_RESEARCH_DIGEST.yaml`**, **`scripts/swarm_research_digest.py validate`**, **Checkpoint Γ** (re-classify + `auto-router`), optional **`/eval-swarm`**, then hand off to **`/auto`**, **`/deliver`**, or **`/deliver-full`** for gated implementation — per the skill.

## Iron laws (non-negotiable)

Follow **`.agents/skills/swarm-coordination/SKILL.md`**: single-message fan-out, queen aggregation, no worker-to-worker chatter. Subagent work uses **`skills/subagent-router/SKILL.md`** **BL-011** spawn contract and **BL-012** typed handoffs.

## Gates

- **Scope / pipeline:** `Read` `docs/GATE_PROTOCOL.md` and apply it before the first
	**Write/Edit** in governed or M1 work, including digest mutation and the delivery tail. When you write `pipeline-gate.json`, set
	**`"pipeline"`** to the delivery command you actually run next — exactly one of
	**`"auto"`**, **`"deliver"`**, or **`"deliver-full"`**. Do **not** default to **`auto`** when
	the handoff is **`/deliver`** or **`/deliver-full`**.
- **`azoth_effect: write`:** Discovery waves are **read/analysis** unless scope already permits writes; **writes** (digest append, implementation) require the same gates as **`/auto`** for governed/M1 work.
- **Review failure:** If any review / audit stage returns request-changes, CRITICAL blockers, **`entropy: RED`**, or **`status: needs-input`**, **STOP** and wait for explicit human approval before continuing — same as **`/auto`**.

## Evaluator routing

When deciding whether to insert PRE_DELIVERY_EVAL Wave C, or when the delivery tail includes
an evaluator boundary, read **`.claude/commands/eval.md`** and apply **E1–E6** plus the skill’s
PRE_DELIVERY_EVAL section (including **`/eval-swarm`** when triggers fire).

## Cursor / other IDEs

This command is defined for **Claude Code** (`.claude/commands/`). Other tools receive the equivalent workflow surface via deploy (`python3 scripts/azoth-deploy.py`, D46): prompt/command mirrors for Copilot/OpenCode and a generated `azoth-dynamic-full-auto` wrapper skill for Codex.

**Normative behavior** lives in **`skills/dynamic-full-auto/SKILL.md`** — in particular:

- **Happy path (Cursor)** — Simulated scope-gate / pipeline-gate before writes (no PreToolUse); **`Task`** per delivery stage when the tool exists; Rich welcome via integrated terminal; digest mutations are writes and require an approved scope.
- **Happy path (Claude Code)** — Same flow; hooks may enforce gates mechanically where configured.
- **Gates** — When writing **`.azoth/pipeline-gate.json`**, set **`"pipeline"`** to the delivery command you will actually run next: **`"auto"`**, **`"deliver"`**, or **`"deliver-full"`** — do not default to `auto` when handing off to `/deliver` or `/deliver-full`.

**Parity references:** `.cursor/rules/claude-code-parity.mdc`, `CLAUDE.md` (Cursor SessionStart gap, welcome paths).

## Arguments

Goal / session intent: **$ARGUMENTS**
