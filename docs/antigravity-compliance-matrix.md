# Antigravity Compliance Matrix (P1-016)

Gap matrix documenting Claude Code hook → Antigravity workflow parity for each
Azoth behavioral contract. Updated as part of P1-016 delivery.

## Parity Levels

| Symbol | Meaning |
|--------|---------|
| ✅ | **Mechanical** — same enforcement mechanism available on both platforms |
| ⚠️ | **Instruction-only** — Antigravity relies on workflow text and agent compliance; not mechanically blocked |
| 🔶 | **Manual** — requires explicit human action to trigger; no automation |
| ❌ | **Not enforceable** — fundamental platform limitation; accepted degradation |

## Matrix

| Behavior | Claude Code Mechanism | Antigravity Mechanism | Parity | Notes |
|----------|----------------------|----------------------|--------|-------|
| **Scope-gate enforcement** | `PreToolUse` hook reads `scope-gate.json`; blocks Write/Edit if missing/expired | `azoth-core.md` Compliance Checklist §1 + workflow `Preconditions` sections + `scripts/scope_gate_check.py` | ⚠️ | Agent can bypass instruction check; script provides optional mechanical validation but is not auto-triggered |
| **Pipeline-gate enforcement** | `PreToolUse` hook reads `pipeline-gate.json`; blocks governed writes without gate | Workflow `Preconditions` step + `docs/GATE_PROTOCOL.md` reference | ⚠️ | Same instruction-only limitation as scope-gate |
| **Pipeline stage discipline** | Workflow text + subagent isolation | Workflow `Preconditions` + `azoth-core.md` Compliance Checklist §3-4 + visible Declaration block requirement | ⚠️ | Stages run inline — no context isolation between review and implementation |
| **Subagent isolation** | `Agent(subagent_type=...)` / `Task()` spawn fresh-context subagents | Not available — all stages execute inline in the same conversation context | ❌ | Fundamental Antigravity limitation. Review stages cannot be guaranteed context-independent from implementation stages. Honest documentation in alignment summaries required. |
| **Entropy tracking** | `PreToolUse` telemetry hook (`session_telemetry.py`) logs every tool use; `entropy-guard` skill for zone classification | `entropy-guard` skill self-check at stage boundaries (instruction-triggered) | ⚠️ | No per-tool-use mechanical counting; relies on agent performing periodic self-checks |
| **Session orientation** | `SessionStart` hook runs `welcome.py --plain`; output injected into context and mirrored to `session-orientation.txt` | `/start` workflow invoked manually; `welcome.py` run via terminal command | 🔶 | Not automatic — requires human or agent to invoke `/start` at session open |
| **Context recall** | `/start` → `context-recall` skill invocation; `SessionStart` provides orientation | `/start` workflow must explicitly invoke `context-recall` skill | ⚠️ | Equivalent when `/start` is followed; no guarantee of invocation without hooks |
| **M3 episode capture** | `/session-closeout` W1 → `remember` skill | `/session-closeout` W1 → `remember` skill | ✅ | Same workflow-level mechanism; same skill |
| **M2 promotion** | `/promote` + human approval | `/promote` + human approval | ✅ | Same workflow |
| **Write-claim safety** | `PreToolUse` hook checks `run-ledger.local.yaml` for competing claims; blocks if conflict | `scripts/run_ledger.py` check in workflow preconditions; `azoth-core.md` STOP condition | ⚠️ | No mechanical blocking; documented as Antigravity limitation |
| **Co-Authored-By rejection** | `commit-msg` git hook (`scripts/git_commit_policy.py`) | Same git hook (git-level enforcement) | ✅ | Git hooks are platform-independent |
| **Pip install guard** | `PreToolUse` hook on Bash (`pip-install-guard.py`) | Not available — no Bash hook equivalent | ❌ | Antigravity does not intercept terminal commands |
| **Kernel file protection** | `settings.json` deny list: `Edit(kernel/**)` | `azoth-core.md` bootstrap boundary + STOP condition | ⚠️ | Instruction-only; no mechanical deny |

## Summary

- **✅ Mechanical parity:** 3 behaviors (M3 capture, M2 promotion, Co-Authored-By)
- **⚠️ Instruction-only:** 8 behaviors (scope-gate, pipeline-gate, stage discipline, entropy, context-recall, write-claims, kernel protection, pip guard)
- **🔶 Manual:** 1 behavior (session orientation)
- **❌ Not enforceable:** 2 behaviors (subagent isolation, pip install guard)

## Mitigation Strategy

For ⚠️ instruction-only behaviors, the Antigravity adapter uses three reinforcement layers:

1. **`azoth-core.md` Compliance Checklist** — always-on rule with explicit pre-write verification items
2. **Workflow `Preconditions` sections** — each workflow starts with visible verification steps that emit pass/fail output
3. **Optional validation scripts** — `scripts/scope_gate_check.py` and `scripts/run_ledger.py` provide command-line verification callable from workflows

For ❌ not-enforceable behaviors, the gap is documented honestly in `azoth-core.md` §Antigravity Limitations and workflow alignment summaries.
