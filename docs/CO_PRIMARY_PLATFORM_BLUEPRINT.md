# Co-Primary Platform Blueprint

> Strategic platform blueprint for Azoth after the shift from parity-first thinking
> to goal-first design.

## 1. Purpose

This blueprint defines how Azoth should treat **Claude Code** and **Codex** as
**co-primary interactive platforms** while preserving the **adapter pattern** for
other target platforms such as GitHub Copilot, Cursor, OpenCode, and Gemini /
Antigravity.

The goal is not mechanical sameness across all harnesses.

The goal is:

- low-stress operation
- anti-slop defaults
- high-quality output
- bounded risk
- portable command semantics
- reasonable compatibility across platforms

This document intentionally uses the term **commands** for user-facing entrypoints.
Azoth may still use **pipelines** internally for multi-stage execution, but
user-facing `/auto`, `/next`, `/deliver`, and related entrypoints remain
**commands**, not "workflows."

Implementation follow-up: see `docs/CANONICAL_COMMAND_CONTRACT.md` for the
neutral command-contract design and `commands/` for the prototype canonical path.

## 2. Decision Summary

Azoth should evolve from:

- **Claude-first with adapters**

to:

- **protocol-first with two co-primary command surfaces and a stable adapter layer**

The two co-primary platforms are:

- **Claude Code**
- **Codex**

The adapter platforms remain:

- **GitHub Copilot**
- **Cursor**
- **OpenCode**
- **Gemini / Antigravity**

Co-primary does **not** mean equal mechanics.
It means both platforms are allowed to shape canonical Azoth design, and the
core Azoth experience must feel first-class on both.

## 3. Design Principles

### 3.1 Goal-first over parity-first

Azoth should optimize for the human outcome:

- calm, low-babysitting operation
- bounded entropy
- strong review and quality culture
- useful autonomy without "AI slop"

Full mechanical parity is not required if the goal is still achieved.

### 3.2 Protocol-first over harness-first

Azoth governance should be defined once in a harness-agnostic protocol, then
projected into harness-native surfaces.

Harness-specific mechanics are **accelerants**, not the definition of correctness.

### 3.3 Thin adapters

Platform-specific layers should stay thin.
They should express:

- platform capabilities
- platform UX affordances
- enforcement opportunities
- file format transformations

They should not redefine Azoth semantics.

### 3.4 Commands stay commands

User-facing entrypoints stay under the command model.

Examples:

- `/start`
- `/next`
- `/auto`
- `/deliver`
- `/deliver-full`
- `/session-closeout`

Internally, a command may invoke a multi-stage pipeline, but the product
language stays command-oriented.

## 4. Platform Taxonomy

### 4.1 Level A — Co-Primary Platforms

These platforms shape canonical Azoth design and must support the main Azoth
experience as a first-class experience.

- **Claude Code**
- **Codex**

Requirements:

- first-class session entry
- first-class command execution
- first-class agent / subagent usage
- first-class review / evaluation loops
- first-class memory and closeout continuity
- strong enough governance to achieve low-stress, anti-slop operation

### 4.2 Level B — Strong Adapters

These platforms should preserve most Azoth semantics and remain useful for
serious work, but they do not define the core.

- **GitHub Copilot**
- **Cursor**
- **OpenCode**

Requirements:

- reasonable command compatibility
- shared state compatibility
- shared memory / closeout compatibility
- documented degradations where the platform is weaker

### 4.3 Level C — Compatibility Adapters

These platforms should consume the protocol where possible, but accepted
degradations are broader.

- **Gemini / Antigravity**

Requirements:

- consume core governance documents
- expose core commands where possible
- keep failure modes honest and documented

## 5. Unified Governance Model

Azoth governance should be described in four universal layers.

### 5.1 Intent Layer

Canonical policy and meaning:

- trust contract
- risk classes
- posture tiers
- entropy ceiling
- human-gate rules
- memory promotion rules
- kernel immutability rules

Primary sources:

- `kernel/TRUST_CONTRACT.md`
- `kernel/GOVERNANCE.md`
- `kernel/PROMOTION_RUBRIC.md`
- `AGENTS.md`

### 5.2 State Layer

Shared state artifacts that every platform must read and write consistently:

- `.azoth/scope-gate.json`
- `.azoth/pipeline-gate.json`
- `.azoth/run-ledger.local.yaml`
- `.azoth/bootloader-state.md`
- `.azoth/session-state.md`
- `.azoth/memory/episodes.jsonl`
- `.azoth/memory/patterns.yaml`
- `.azoth/final-delivery-approvals.jsonl`

### 5.3 Evidence Layer

Artifacts that justify progression through the system:

- test results
- lint / format results
- reviewer findings
- evaluator summaries
- integrity checks
- approval records
- alignment summaries

Azoth should define progression by evidence, not by harness-specific magic.

### 5.4 Enforcement Layer

Harness-specific means of nudging, checking, or blocking:

- Claude hooks
- Codex hooks, rules, sandbox, approvals
- Cursor rules
- Copilot prompts and PR review surfaces
- OpenCode permissions
- Gemini / Antigravity instruction surfaces

Only this layer is harness-specific.

## 6. Command Model

### 6.1 Canonical command semantics

Azoth commands should be defined once in a neutral command contract.

Each canonical command should specify:

- command name
- purpose
- entry conditions
- required state artifacts
- allowed risk envelope
- expected evidence before completion
- output / handoff artifacts
- optional internal pipeline mapping

This neutral command contract should be the long-term source of truth.

### 6.2 Harness-native command surfaces

The same canonical command should then be projected into native surfaces:

- **Claude Code** → `.claude/commands/*.md`
- **Codex** → `.agents/skills/azoth-*` wrappers + `.codex/*`
- **Copilot** → `.github/prompts/*.prompt.md`
- **OpenCode** → `.opencode/commands/*.md`
- **Cursor** → Claude-compatible commands + `.cursor/rules/*.mdc`

### 6.3 Internal pipeline distinction

Pipelines remain valid as an internal execution concept.
Commands are the human-facing contract; pipelines are the execution machinery.

Rule:

- **User-facing naming uses "command"**
- **Execution-graph naming may use "pipeline"**

## 7. Capability Bands

Azoth should evaluate platform support through capability bands rather than
parity rhetoric.

### Band A — Instruction Fidelity

Can the platform reliably consume:

- `CLAUDE.md`
- `AGENTS.md`
- skills
- agents
- command guidance

### Band B — Soft Governance

Can the platform reliably honor:

- scope checks
- risk posture
- review discipline
- human gates
- anti-slop instructions

### Band C — Bounded Execution

Can the platform provide:

- sandboxing
- approvals
- path restrictions
- network restrictions
- command rules

### Band D — Hard Enforcement

Can the platform mechanically block:

- dangerous command execution
- invalid state transitions
- edits to protected files
- out-of-policy writes

Claude Code is strongest in Band D.
Codex is strong in Bands A-C and partially strong in D.
Adapter platforms should be judged by how well they preserve A-C without
forcing core semantics to splinter.

## 8. Platform Roles

### 8.1 Claude Code

Role:

- governance-enhanced co-primary surface

Primary strengths:

- strong hooks
- strongest preflight enforcement
- best surface for governed kernel or policy work

Architectural meaning:

- Claude-specific hardening should remain available
- Claude-specific hardening must not become the only expression of a core rule

### 8.2 Codex

Role:

- flow-optimized co-primary surface

Primary strengths:

- strong instruction layering
- strong bounded execution model
- strong multi-agent and cloud options
- strong session throughput potential

Architectural meaning:

- Codex should be optimized for low-stress, anti-slop coding quality
- Codex-specific governance should focus on quality, boundedness, and calm flow
- Codex should not be treated as a merely degraded Claude adapter

### 8.3 GitHub Copilot

Role:

- strong adapter and portability reference

Primary strengths:

- PR-native review use cases
- lightweight project compatibility
- useful benchmark for "minimum serious Azoth compatibility"

Architectural meaning:

- Copilot should influence the portable core
- Copilot should not dictate co-primary interaction design

### 8.4 Cursor and OpenCode

Role:

- strong adapters for serious but lower-control usage

Architectural meaning:

- preserve shared semantics
- document softer enforcement honestly
- avoid bespoke semantic forks

### 8.5 Gemini / Antigravity

Role:

- compatibility adapter

Architectural meaning:

- keep the adapter alive
- accept documented degradation
- do not contort the core around its weakest constraints

## 9. Complexity Guardrails

To prevent co-primary support from turning into unbounded complexity, Azoth
should enforce these architectural rules.

### 9.1 One canonical policy model

Risk classes, posture tiers, gates, and entropy rules must be defined only once.

### 9.2 One canonical state model

The `.azoth/*` state artifacts are the shared system of record.

### 9.3 One canonical command model

Commands are authored once and projected outward.
Per-platform command files are generated surfaces, not semantic forks.

### 9.4 Adapters may strengthen, never redefine

A platform adapter may:

- add enforcement
- improve discoverability
- improve ergonomics
- map capabilities into native affordances

It may not:

- change the meaning of a command
- invent different gate semantics
- weaken kernel / governance rules silently

### 9.5 Weakest-platform truth does not define the whole system

Azoth should not collapse to the least capable adapter.
Instead:

- the **core protocol** must be portable
- the **co-primary surfaces** may add richer execution
- adapters declare honest degradations

## 10. Compatibility Promise

Azoth should publish an explicit compatibility promise.

### 10.1 Co-primary promise

Claude Code and Codex both aim to deliver:

- a first-class command-driven Azoth session
- strong continuity across start, command execution, review, and closeout
- sufficient governance for low-stress anti-slop work

### 10.2 Adapter promise

Other platforms aim to deliver:

- shared command semantics where possible
- shared state compatibility
- shared memory / closeout compatibility
- documented enforcement differences

### 10.3 Honesty rule

Azoth must document accepted degradations instead of calling them parity.

## 11. Migration Direction

This blueprint implies a medium-term architecture shift.

### 11.1 Near term

Keep the current deploy pattern:

- canonical agents
- canonical skills
- current command projection surfaces
- `scripts/azoth-deploy.py` as projection compiler

### 11.2 Medium term

Introduce a neutral canonical command specification so `.claude/commands/*.md`
stop being the sole de facto source of truth.

Target shape:

- canonical command spec
- generated Claude command files
- generated Codex command wrappers
- generated Copilot prompts
- generated OpenCode command files

### 11.3 Long term

Treat platform support as:

- **co-primary strategy** for Claude Code + Codex
- **stable adapter strategy** for the rest

This preserves scalability better than either:

- Claude-only canonical design
- or full equal-weight parity across every harness

## 12. Blueprint Outcome

If Azoth follows this blueprint, the intended result is:

- one governance protocol
- one shared state model
- one command model
- two co-primary harnesses
- several stable adapters
- less Claude lock-in
- less per-platform semantic drift
- better alignment with Azoth's real goal:
  low-stress, anti-slop, high-quality coding
