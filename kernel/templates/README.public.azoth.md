# Azoth

**A portable operating system for governed AI-assisted software delivery.**

Azoth gives an AI coding project a durable way to start work, reason about
scope, use agents and tools, preserve useful learning, and stop safely. It is
for people who want more than a prompt collection: a lightweight architecture
that makes autonomy useful without making it unbounded.

The public repository contains the toolkit, documentation, platform adapters,
commands, skills, and installation surfaces needed to use it in a project.

## Why Azoth

AI-assisted development often fails in predictable ways: each session starts
without context, useful lessons remain trapped in chat history, agents expand
scope silently, platform-specific instructions drift apart, and review happens
too late. Azoth addresses those failure modes through a small set of durable
design decisions:

- **One governed operating model:** define the rules once, then project them to
  supported AI-development hosts.
- **Bounded autonomy:** agents can move quickly inside explicit trust,
  scope, approval, checkpoint, and recovery boundaries.
- **Memory with promotion:** retain episodes, promote only reinforced patterns,
  and keep durable instructions under human control.
- **Goal-aware execution:** use lightweight work for simple tasks and staged
  delivery pipelines when the work warrants more review.
- **Honest portability:** preserve shared semantics where a host can enforce
  them, and document degradation where it cannot.

## Personal Harness OS preview

This preview profile keeps ordinary work lightweight while making
authority, context, stopping, and recovery explicit when the work becomes
consequential.

Personal Harness OS is built around three portable contracts:

| Contract | Purpose |
|---|---|
| `HarnessRequest` → `HarnessDecision` | `classify_harness_request` selects a `profile` of `guide`, `assisted`, `managed`, or `governed_autonomy` from intended effects and risk |
| `RouteCapsule` | Exposes route state, required authority, inputs, next safe action, and stop reason |
| Context-view packet | `build_context_view` pulls compact approved summaries and source pointers without dumping raw memory |

The profile treats agents as programmable probabilistic components within an
engineered workflow. It favours the smallest architecture that preserves the
context, deterministic tools, evidence, human authority, and recovery the task
actually needs. Retrieval, durable memory, or multi-agent coordination are
added when a demonstrated failure mode justifies their cost.

In the `v0.3.0-rc.1` candidate, the selected portable contracts, generic
rehearsal surface, and focused tests are implemented and included, while private
operator state and environment-specific cockpit adapters are not. A generic
no-write runner rehearses the public contracts against
`examples/personal-harness/rehearsal-cases.yaml`; a CLI may wrap it later, but
the command name is intentionally not fixed here.

- [Personal Harness OS architecture](docs/PERSONAL_HARNESS_OS.md)
- [Case study: *Narrow Success, Broad Failure*](docs/case-studies/narrow-success-broad-failure.md)

## Architecture at a glance

Azoth uses a four-layer model. The lower layers are deliberately stable; the
upper layers are allowed to adapt to the project and goal.

```text
CURRENT  - Orchestration and delivery
           Commands, pipeline presets, coordination, final delivery
                 ↑
WAVE     - Agents and capabilities
           Role-specific agents, skills, evaluators, domain additions
                 ↑
MINERAL  - Portable knowledge and tools
           Reusable skills, memory, prompts, evaluation rubrics
                 ↑
MOLECULE - Invariant kernel
           Bootloader, trust contract, governance, promotion rules
```

The model prevents two opposite failures: an immutable framework that cannot
adapt, and a fully emergent agent system that slowly loses its standards.

| Layer | What it owns | Change posture |
|---|---|---|
| Molecule | Core identity, trust boundaries, governance and promotion rules | Human-approved only |
| Mineral | Portable knowledge, reusable skills and memory mechanisms | Stable and refinable |
| Wave | Agents and specialised capabilities | Emerges when useful; retained when proven |
| Current | Goal-specific commands and delivery flows | Created and adjusted per goal |

Read the full design rationale in [the architecture guide](docs/AZOTH_ARCHITECTURE.md).

## How a governed session works

Azoth turns a session into a small, inspectable delivery loop:

```text
Activate -> Survey -> Operate -> Harden
   |           |          |         |
   |           |          |         +-- verify, checkpoint, retain lessons
   |           |          +------------ work within scoped trust boundaries
   |           +----------------------- inspect project state and relevant memory
   +----------------------------------- load the kernel and project contract
```

The workflow is backed by four safeguards:

1. **Scope before change.** Map the task and its blast radius before editing.
2. **Trust-aware action.** Separate actions that may proceed, need approval,
   or must never run automatically.
3. **Meaningful human gates.** Require a human decision when risk, governance,
   or scope expansion makes it valuable.
4. **Recovery by design.** Use checkpoints and Git-based recovery rather than
   treating a failed autonomous run as irreversible.

For the precise contract, see the [Trust Contract](kernel/TRUST_CONTRACT.md)
and [gate protocol](docs/GATE_PROTOCOL.md).

## Memory that improves without silently rewriting policy

Azoth separates transient experience from durable operating rules:

```text
Episodes -> candidate patterns -> human-approved durable knowledge -> skills and instructions
   M3              M2                         promotion                         M1
```

- **Episodes** capture what happened during work.
- **Patterns** preserve lessons that recur and remain useful.
- **Skills and instructions** hold durable procedures only after promotion.

This design keeps the system capable of learning while preventing one-off
outputs, stale preferences, or model mistakes from becoming permanent policy.
See [governance](kernel/GOVERNANCE.md), the [promotion rubric](kernel/PROMOTION_RUBRIC.md),
and [architecture details](docs/AZOTH_ARCHITECTURE.md#5-layer-1-minerals-portable-knowledge).

## Platforms and portability

Azoth is protocol-first. Its core governance and workflow semantics live in
portable source files; adapters translate them into the conventions of each
host. Claude Code and Codex are co-primary interactive design surfaces, while
other supported hosts use thin adapters where their capabilities differ.

This is intentionally not a promise that every host enforces every rule in the
same way. Azoth records those differences instead of reducing the entire system
to the weakest platform.

- [Co-primary platform blueprint](docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md)
- [Platform adapters](kernel/templates/platform-adapters/)
- [Deployment script](scripts/azoth-deploy.py)

## What is included

| Surface | Purpose |
|---|---|
| [`kernel/`](kernel/) | Bootloader, trust contract, governance, promotion rules |
| [`skills/`](skills/) | Reusable procedures for planning, memory, evaluation, routing and delivery |
| [`agents/`](agents/) | Role-based agent definitions and capability boundaries |
| [`commands/`](commands/) | Human-facing entry points for sessions, planning, delivery and review |
| [`pipelines/`](pipelines/) | Declarative delivery presets and staged orchestration |
| [`docs/`](docs/) | Architecture, decisions, platform strategy and protocols |
| [`scripts/`](scripts/) | Installation, deployment, validation, checkpoint and support utilities |

## Install

Clone this repository into the project where you want to use Azoth, then run:

```bash
pip install -r requirements-dev.txt
bash install.sh
```

The Bash installer projects the appropriate Azoth surfaces into the target
project. Then open `CLAUDE.md` or the generated host-specific entrypoint and
follow the bootloader. `install.ps1` is provided for Windows, but PowerShell was
unavailable in the `v0.3.0-rc.1` validation environment, so this candidate makes
no PowerShell parity claim.

For a fresh GitHub Copilot project, explicitly select the Copilot surface:

```bash
AZOTH_PLATFORMS=copilot bash /path/to/azoth/install.sh
```

## Start exploring

- Want the conceptual model? Start with the [architecture guide](docs/AZOTH_ARCHITECTURE.md).
- Want the design record? Browse the [architecture decisions index](docs/DECISIONS_INDEX.md).
- Want safety and autonomy rules? Read the [Trust Contract](kernel/TRUST_CONTRACT.md).
- Want to understand host differences? Read the [co-primary platform blueprint](docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md).
- Want to use or extend it? Start with [`commands/`](commands/) and [`skills/`](skills/).

## Boundaries and status

Azoth is an evolving toolkit. Some pipeline and memory-promotion capabilities
are intentionally staged or partial; the [decisions index](docs/DECISIONS_INDEX.md)
tracks implementation status. It is designed for governed AI-assisted delivery,
not as a claim of universal autonomy, identical enforcement across every host,
or a substitute for human engineering judgment.

## License

Licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).
Commercial use outside the licence's permitted noncommercial purposes requires
a separate written agreement. Contact [Yiwei Ye on GitHub](https://github.com/yiwei79).
