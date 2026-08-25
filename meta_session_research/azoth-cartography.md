# Azoth Cartography

Started: 2026-05-01

Purpose: map the current Azoth system as it exists. This is intentionally
descriptive. Future status is not decided here.

## Repo Surface Snapshot

Observed from `find` and `rg --files` on 2026-05-01:

| Area | Observed Count | Apparent Role |
|---|---:|---|
| `.azoth/` | 267 files | Runtime state, roadmap, memory, inbox, governed approvals, proposals, run ledger, handoffs, research, campaign state. |
| `kernel/` | 29 files | Layer 0 trust/governance/bootloader and platform templates. |
| `skills/` | 19 files | Procedural capabilities and progressive/reusable agent knowledge. |
| `agents/` | 12 files | Agent archetypes across core, research, meta, and utility roles. |
| `commands/` | 22 files | Neutral command contracts and selected command bodies. |
| `pipelines/` | 21 files | Pipeline presets, schemas, examples, run-ledger/stage-summary schemas. |
| `scripts/` | 54 files | Tooling for deploy, gates, roadmap, run ledger, autonomous loop, extraction, memory, tests, and UX surfaces. |
| `tests/` | 104 files | Regression suite for adapters, gates, schemas, roadmap, autonomous behavior, parity, and scripts. |
| `docs/` | 22 files | Architecture, platform guides, playbooks, gate protocol, control-plane docs. |

## Core Identity

Source: [README.md](../README.md), [azoth.yaml](../azoth.yaml),
[docs/AZOTH_ARCHITECTURE.md](../docs/AZOTH_ARCHITECTURE.md).

Azoth identifies as a portable agentic toolkit with:

- a small invariant kernel;
- refinable skills and memory;
- agent archetypes;
- per-goal pipelines;
- governed delivery and trust boundaries;
- adapters across Claude Code, Codex, OpenCode, Copilot, Cursor, and Gemini.

The root repo is the private workshop and source of truth for extracting the
public package.

Research pressure:

The philosophy says minimal invariant kernel and emergent structure. The current
surface shows a much larger operational layer. Research must determine whether
that larger layer is necessary earned structure or accumulated ceremony.

## Layer 0: Kernel

Sources:

- [kernel/TRUST_CONTRACT.md](../kernel/TRUST_CONTRACT.md)
- [kernel/GOVERNANCE.md](../kernel/GOVERNANCE.md)
- [kernel/BOOTLOADER.md](../kernel/BOOTLOADER.md)
- [kernel/PROMOTION_RUBRIC.md](../kernel/PROMOTION_RUBRIC.md)

Apparent jobs:

- define entropy ceilings and blast-radius bounds;
- require human approval for kernel, governance, dependencies, promotion, and
  final delivery;
- define append-only memory and promotion rules;
- run deterministic boot phases: ACTIVATE, SURVEY, OPERATE, HARDEN;
- enforce drift detection against kernel checksums;
- require phone-friendly alignment summaries.

Likely trust primitives to test:

- bounded side effects;
- human gates for irreversible or high-trust actions;
- drift detection;
- durable memory;
- explicit closeout state.

Open question:

Can these primitives survive in a much smaller default profile without forcing
all work through current pipeline ceremony?

## Memory And State

Sources:

- `.azoth/memory/episodes.jsonl`
- `.azoth/memory/patterns.yaml`
- `.azoth/telemetry/session-log.jsonl`
- `.azoth/run-ledger.local.yaml`
- `.azoth/session-state.md`
- `.azoth/bootloader-state.md`

Apparent jobs:

- preserve episodes and patterns across sessions;
- track run stages, spawns, summaries, inline exceptions, and write claims;
- provide session continuity and closeout state;
- support append-only learning and audit.

Research pressure:

External evidence supports durable session/event state. The research question is
whether Azoth's current memory and ledger surfaces are the right size and shape,
or whether a smaller session log plus generated context views would do the job
with less model and user burden.

## Commands

Source: [docs/CANONICAL_COMMAND_CONTRACT.md](../docs/CANONICAL_COMMAND_CONTRACT.md)
and `commands/*/command.yaml`.

Observed commands:

| Command | Effect | Apparent Role |
|---|---|---|
| `start` | read | Session orientation. |
| `next` | mixed | Roadmap priority and scope card. |
| `plan` | read | Structured planning without execution. |
| `auto` | write | Compose and execute pipeline from goal classification. |
| `deliver` | write | Lean additive delivery. |
| `deliver-full` | write | Governed delivery for high-risk work. |
| `autonomous-auto` | write | Branch-local autonomous Azoth self-development. |
| `dynamic-full-auto` | inferred from skill surface | Adaptive multi-wave orchestration. |
| `eval` | read | Governance quality gate. |
| `eval-swarm` | mixed | Strict multi-evaluator assessment. |
| `remember` | write | Capture structured learning. |
| `session-closeout` | write | Evaluation, closeout, sync. |
| `resume` | write | Resume active scope or parked session. |
| `roadmap` | read | Roadmap dashboard. |
| `sync` | write | Extract/sync patterns. |
| `test` | write | Generate tests. |
| `hookmode` | write | Inspect or switch Codex operating mode. |

Research pressure:

Command contracts make side effects visible and support adapter projection, but
may also pull ordinary tasks into Azoth ceremony. Profile tests should measure
whether command-first operation improves safety enough to justify its cognitive
and context cost.

## Skills

Source: [skills/index.yaml](../skills/index.yaml).

Observed skills:

- `context-recall`;
- `stage6-rubric`;
- `alignment-sync`;
- `agentic-eval`;
- `auto-router`;
- `autonomous-auto`;
- `context-map`;
- `cursor-review-insights`;
- `prompt-engineer`;
- `remember`;
- `self-improve`;
- `structured-autonomy-plan`;
- `subagent-router`;
- `dynamic-full-auto`;
- `karpathy-principles`;
- `orientation`;
- `entropy-guard`.

Apparent jobs:

- context retrieval and blast-radius mapping;
- route selection and subagent routing;
- autonomous continuation;
- alignment summaries;
- evaluation and self-improvement;
- memory capture;
- operator orientation.

Research pressure:

Skills are the subsystem most aligned with external guidance on progressive
disclosure. The research should test whether many current command/pipeline
behaviors can become skills loaded on demand.

## Agents

Source: [AGENTS.md](../AGENTS.md), `agents/**`.

Observed archetypes:

- core: architect, builder, orchestrator, planner, reviewer;
- research: research-orchestrator, researcher;
- meta: prompt-engineer, evaluator, agent-crafter;
- utility: context-architect.

Apparent jobs:

- separate planning, implementation, review, research, evaluation, and meta-work;
- support multi-agent orchestration and platform portability;
- provide named trust postures.

Research pressure:

External evidence supports subagents for breadth, isolation, and review, but
warns that multi-agent coding can be costly and coordination-heavy. Azoth should
measure where named stage ownership prevents mistakes and where it creates
bookkeeping without independent value.

## Pipelines And Gates

Sources:

- `pipelines/*.pipeline.yaml`
- [docs/GATE_PROTOCOL.md](../docs/GATE_PROTOCOL.md)
- [scripts/check_gates.py](../scripts/check_gates.py)
- [scripts/scope_gate_check.py](../scripts/scope_gate_check.py)
- [scripts/pipeline_lint.py](../scripts/pipeline_lint.py)

Observed pipeline presets:

- `auto`;
- `deliver`;
- `full`;
- `hotfix`;
- `docs`;
- `research`;
- `review`;
- `refactor`.

Apparent jobs:

- make route structure and gate requirements explicit;
- provide schema validation;
- distinguish human and agent gates;
- bind scope approval to pipeline execution.

Research pressure:

This is a likely fork point: either pipelines are essential governed-mode
infrastructure, or they are too heavy as default flow. Benchmarks should compare
pipeline-driven and route-capsule-driven work.

## Autonomous Mode

Sources:

- [scripts/autonomous_loop.py](../scripts/autonomous_loop.py)
- [skills/autonomous-auto/SKILL.md](../skills/autonomous-auto/SKILL.md)
- `.azoth/autonomous-loop-state.local.yaml`
- `.azoth/inbox/session-reflection-2026-04-25-autonomous-auto-*.jsonl`

Apparent jobs:

- manage branch-local autonomous continuation;
- choose next work from queues, backlog, initiatives, and proposals;
- record alignment packets, loop state, lifecycle route decisions, and campaign
  reports;
- support self-capture of mistakes.

Research pressure:

Autonomous mode is the richest evidence source and the highest risk of harness
capture. It contains valuable durability concepts, but also many reflections
about route-before-open, false completion, stale planning surfaces, packaging
gaps, and report-quality issues.

## Adapter And Product Surfaces

Sources:

- [scripts/azoth-deploy.py](../scripts/azoth-deploy.py)
- [sync-config.yaml](../sync-config.yaml)
- [docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md](../docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md)
- `kernel/templates/platform-adapters/**`

Apparent jobs:

- project commands, agents, skills, hooks, and rules into multiple host tools;
- preserve protocol-first semantics across platform-specific UX surfaces;
- extract public product artifacts from this workshop repo.

Research pressure:

Adapter parity is probably real operational value. The question is whether the
projection layer should carry a lighter protocol instead of full Azoth ceremony.

## Initial Cartography Takeaway

Azoth already contains many pieces that external research says matter:
durability, gates, traceability, skills, pause/resume, evals, and side-effect
awareness. The open question is size and default posture. Batch 0 should not ask
"Azoth or no Azoth"; it should ask which pieces belong in `stock-lite`,
`azoth-lite`, `azoth-full`, and `meta-harness-experimental`.

