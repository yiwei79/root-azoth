# Personal Harness OS

> Status: proposed public preview for `v0.3.0-rc.1`. The routing and context
> contracts described here are implemented and tested in the selected June 2026
> snapshot. The portable rehearsal surface described below is the approved
> release-candidate projection and must be verified in the extracted public
> tree; the wider operating surface remains under development.

Personal Harness OS is Azoth's lightweight default path for agent-assisted work.
It keeps ordinary work small while preserving explicit authority, evidence,
stopping, and recovery boundaries for consequential work.

The design emerged after using a more comprehensive agentic framework across
real delivery. Some orchestration layers improved control; others duplicated
live repository state or imposed the full framework's context and ceremony on
tasks that did not need it. Personal Harness OS makes the minimum useful
contract executable instead of treating one universal workflow as the default.

For the longer engineering argument, see
[*Narrow Success, Broad Failure*](case-studies/narrow-success-broad-failure.md).

## Design goals

- Route by intended effect and risk, not by a personified agent role.
- Load compact, relevant context rather than dump every available source.
- Keep advisory context separate from governing instructions and authority.
- Make the next safe action and stop reason visible before execution.
- Allow project-local practices to emerge behind a thin shared contract.
- Escalate to richer memory, orchestration, or governed autonomy only when the
  task earns their cost.
- Preserve evidence and recovery without making every task enter the heaviest
  path.

## Stable interfaces

### `HarnessRequest` and `classify_harness_request`

`HarnessRequest` captures a goal, intended actions, planned paths, trace
requirements, success criteria, constraints, and relevant repository
conditions. `classify_harness_request` maps that request into one operating
mode. It builds on the lower-level side-effect classifier rather than
duplicating its risk logic.

The classifier is advisory and deterministic. It does not execute tools, grant
authority, or mutate project state.

### `HarnessDecision`

The classifier returns a `HarnessDecision`. The decision's `profile` field
contains `guide`, `assisted`, `managed`, or
`governed_autonomy`; the remaining fields retain the operator promise,
exclusions, source references, escalation reasons, and route capsule needed to
understand that selection.

### `RouteCapsule`

Every decision produces a compact typed packet containing:

- selected profile;
- side-effect class;
- route state;
- whether fresh authority is required;
- the authority plane;
- required inputs;
- next safe action; and
- stop reason, when applicable.

The packet prevents friendly UX from hiding a missing approval or turning an
advisory recommendation into write authority.

### `build_context_view` and the context-view packet

`build_context_view` joins only the summaries needed for the selected route:

- the route capsule;
- compact memory results;
- optional approved personal context;
- a project receipt or readback; and
- explicit forbidden actions.

Raw memory entries are filtered. Missing optional sources remain missing or
produce warnings; they are not invented. Context entries retain a source
pointer so a caller can inspect the authority when needed.

### `build_personal_harness_context`

`build_personal_harness_context` provides the integration path. It classifies
the request, asks existing recall components for bounded results, adds optional
project state, and returns one JSON-serialisable packet. It is read-only by
default.

## Mode ladder

| Mode | What it provides | What it must not imply |
|---|---|---|
| `guide` | Orientation, explanation, and decision support | Project mutation, installed autonomy, or planning-state ownership |
| `assisted` | Skills, selected tools, agents, and focused checks | Hidden roadmap/backlog ownership or no-human-gate continuation |
| `managed` | Project-local operating and planning state | Authority inherited from another repository or invisible hydration |
| `governed_autonomy` | Campaign-bounded continuation | Open-ended loops, stale approval, or action without budget and stop conditions |

`managed` and `governed_autonomy` deliberately stop when fresh authority is
missing. The mode ladder is a usability feature, not a way to bypass control.

## Example route

With the repository's `scripts/` directory on the Python import path:

```python
from harness_profile import HarnessRequest, classify_harness_request

decision = classify_harness_request(
    HarnessRequest(
        goal="Verify the project before changing its release workflow.",
        requested_actions=("focused_verification",),
        planned_paths=("release/",),
        trace_required=True,
    )
)

print(decision.to_route_capsule())
```

The result is a decision packet, not an execution request. A caller can display
it, use it to select bounded tooling, or stop for the authority it names.

## Context selection contract

Personal Harness OS uses pointer-style progressive disclosure:

1. Begin with the goal, intended effects, and route.
2. Add a small number of relevant summaries with source references.
3. Inspect the underlying source only when the current decision needs it.
4. Keep raw evidence at its origin rather than copying it into every context
   surface.
5. Append session evidence separately from durable policy.
6. Let a separate review or architecture pass decide whether repeated evidence
   deserves promotion.

This is intentionally different from injecting a large instruction manual or a
complete memory dump at startup. It also does not prohibit retrieval: indexed
retrieval is appropriate when the information landscape and measured failure
mode justify it.

## Authority and recovery

The harness distinguishes four concerns:

- **advice** — may be generated without write authority;
- **project-local effects** — require authority owned by the target project;
- **governed continuation** — requires an explicit budget, evidence ledger,
  write claim, and stop conditions; and
- **protected or external effects** — stop for direct human authority.

Crossing from one concern to another is an explicit transition. Authority in a
toolkit or operator surface never silently grants authority inside a project.
Git checkpoints, manifests, deterministic validation, and rollback paths remain
the preferred recovery mechanisms for file-backed work.

## Public preview boundary

The proposed public preview contains the portable routing and context contracts,
neutral examples, focused tests, and this design document.

It intentionally excludes:

- private operator or project data;
- machine-specific paths and repository names;
- private cockpit and daily-flow adapters;
- workshop campaigns, memories, receipts, and release evidence;
- credentials, tokens, and external-system configuration; and
- any claim that the preview is a finished universal harness or has external
  adoption.

The excluded integrations remain useful implementation evidence, but they are
not part of a consumer-safe product surface.

## Portable rehearsal surface

The release candidate should make the contracts inspectable through three
portable pieces:

1. A generic rehearsal runner that accepts a case file and returns a
   JSON-serialisable report.
2. Consumer-facing representative cases at
   `examples/personal-harness/rehearsal-cases.yaml`.
3. A focused no-write rehearsal test wired into public CI.

Each case should declare its goal, intended actions, relevant paths or context,
and expected profile, route state, authority requirement, authority plane, and
warnings. The runner should execute the same public request, classifier,
decision, route, and context builders described above; compare repository state
before and after; and fail if a case violates its expected contract or mutates
the target repository.

This is a behavioural rehearsal surface, not a second orchestration layer. A
CLI wrapper may call the runner, but this preview intentionally does not lock a
final command name before the public implementation settles it.

## Validation contract

The release candidate should run the portable tests in public CI:

```bash
python3 -m pytest \
  tests/test_harness_profile.py \
  tests/test_context_view.py \
  tests/test_personal_harness_context.py \
  -q
```

The tests cover:

- lightweight routing for read-only work;
- escalation for governed, external, or destructive effects;
- explicit authority and stop reasons;
- deterministic JSON-ready route capsules;
- raw-memory filtering and bounded context selection;
- optional-source and freshness warnings; and
- preservation of project receipts without granting them authority they do not
  own.

Public CI must also run the focused rehearsal test against
`examples/personal-harness/rehearsal-cases.yaml` and verify both the declared
route expectations and the no-write contract.

The wider Azoth product extraction, installer smoke, link/reference checks, and
private-artifact preflight must also pass before publication.

## What this preview does not settle

- The final public package boundary for every Azoth operating profile.
- Whether the mode names remain the best long-term user-facing language.
- Which applications need indexed retrieval beyond file and tool discovery.
- How project-specific harness improvements should be evaluated and promoted
  across environments.
- Whether a learned higher-level harness can safely emerge from accumulated
  agent traces. That remains a research hypothesis, not an implemented product
  claim.

Personal Harness OS is therefore best understood as a tested architectural
direction: a small route-aware surface that keeps daily work light and makes
consequential work visibly governed.
