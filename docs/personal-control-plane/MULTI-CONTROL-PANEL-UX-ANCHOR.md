# Multi-Control-Panel UX Anchor

Status: target-experience anchor
Date: 2026-04-29
Source plane: `root-azoth`
Deployment target: personal Azoth root

This document defines the operator experience Azoth is aiming for as it moves
from a developer workshop into a distributed set of control panels. It is not
an implementation spec. It is the shared mental model that future rollout,
schema, validator, installer, and personal-knowledge sessions should preserve.

## UX Thesis

Azoth should feel like one coherent operating system distributed across several
authority planes, not like one repo copied everywhere.

The operator should always know:

- which panel they are in,
- what that panel is allowed to decide,
- where the source of truth lives,
- what will be deployed,
- what requires approval,
- what evidence proves the action happened,
- what did not happen.

The target experience is calm, explicit, and receipt-backed. Azoth may automate
bounded work, but it should never make the operator wonder whether it silently
drained an inbox, modified a project, changed governance, published a release,
or imported private knowledge.

## Panel Mental Model

| Panel | Operator Question | Primary Authority | Typical Actions | Forbidden Feeling |
| --- | --- | --- | --- | --- |
| Developer panel: `root-azoth` | Should Azoth itself change? | Toolkit source, tests, governance, roadmap, release evidence | Design, implement, validate, extract, publish, document rollout | "Maybe my personal state got mixed into the product." |
| Product panel: public `azoth` | What can users install? | Clean extracted release surface | Installers, public docs, tags, release notes, platform adapters | "Maybe private root state leaked into the release." |
| Personal control panel | What should I do across my projects and knowledge? | Operator inventory, curated knowledge, source registry, handoffs | Route priorities, recall personal principles, track project/source pointers, apply approved Azoth updates | "Maybe it is mutating my projects or importing everything silently." |
| Project panel | What should change in this repo? | Project-local code, roadmap, memory, gates | Project-scoped delivery, project memory, project closeout | "Maybe the personal root bypassed this project's own gates." |

The panels cooperate through explicit handoffs. They do not inherit each
other's authority.

## North-Star Experience

The ideal operator flow looks like this:

1. Open a session in any panel.
2. Azoth identifies the panel, repo, version, privacy class, and authority
   boundary.
3. The session-start surface names the safe next actions for that panel.
4. If the work affects another panel, Azoth says which deployment path applies.
5. The operator approves the boundary before writes happen.
6. The work runs through the correct pipeline.
7. The result includes a receipt: changed files, validations, commit, release,
   deployment ledger, and residual risks.
8. The operator can answer "what changed where?" without reconstructing the
   chat.

The experience should be boring in the best way: predictable, scoped, and easy
to audit.

## Distribution Flow

```text
root-azoth developer panel
  -> root validation and CI/CD
  -> product extraction
  -> public azoth release when generic
  -> approved personal-root update
  -> approved project-level update
```

Not every change goes through every step.

- Generic Azoth runtime changes should be developed and validated in
  `root-azoth`, then extracted into public `azoth`, then applied to personal
  root or projects from the approved release.
- Operator-private configuration, personal knowledge cards, project inventory,
  and source registry data should never be published through public `azoth`.
- Personal-root-only content may be deployed directly to the personal root, but
  only as an explicit operator-approved deployment step with a local receipt.
- Project changes remain project-scoped. The personal root coordinates and
  summarizes; it does not silently push into projects.

## Panel Identity Cues

Every panel should eventually make these cues visible at session start:

- Panel: developer, product, personal, or project.
- Repo/path and branch.
- Installed Azoth version and source release.
- Privacy class: public, private, local-only, or secret-pointer-only.
- Authority: what this panel can modify.
- Blocked actions: what this panel must not modify.
- Current route: next safe action, stop reason, or approval needed.
- Evidence ledger: where receipts will be written.

The UX should make authority boundaries impossible to miss. If the operator is
in the personal root, the session should not look like a product-release
session. If the operator is in a project repo, it should not look like the
personal root can mutate global preferences without a separate approval.

## Cockpit Main Menu And Context Firewall

The first cockpit UX surface is a terminal-first, cockpit-local main menu. It
should be available from `yiwei-azoth-cockpit` without requiring the operator
to remember hidden command contracts before they can orient.

The menu mental model is safe-open:

- read cockpit identity, repo status, release ledger, project pointer metadata,
  and handoff receipts,
- show the latest approved public/installable `azoth` release as the sync
  authority,
- show the cockpit manifest version and whether the cockpit appears synced to
  that public release,
- list registered projects such as `ras-or-ray` from pointer-only metadata,
- print safe next actions and copy-paste project-session prompts,
- write no files and start no hidden work.

"Synced with azoth" means synced with the latest approved public/installable
`azoth` release. It does not mean synced with every `root-azoth` workshop patch.
Root workshop drift can be shown as advisory context, but it must not become
the cockpit's release authority unless that change is published through the
approved public release path.

The context firewall is part of the UX, not an implementation detail.

| State Class | Owner | Cockpit Main Menu Behavior |
| --- | --- | --- |
| Project pointers | Cockpit | May read and display pointer metadata. |
| Global preferences and personal memory | Cockpit | May summarize cockpit-owned status only. |
| Release ledger and receipts | Cockpit | May read and validate sync/receipt shape. |
| Project code and dependencies | Project repo | Must not import, summarize, or index. |
| Project memory and instructions | Project repo | Must remain project-local until a project session loads them. |
| Project gates and write approvals | Project repo | Must be opened in the project repo or fresh project-scoped gate. |

Project switching is handoff execution:

1. The cockpit prints the selected project path and current safe status.
2. The cockpit prints a fresh project-session prompt.
3. The operator starts or switches into that project repo/session.
4. Only then does project-local context load.

The cockpit must not import project source files, source summaries, dependency
inventories, secrets, retrieval indexes, or project instructions into its own
context as part of a switch. A project summary may be recorded later only
through an explicit receipt-backed lane that says what is being copied and why.

Future writes remain possible, but only through explicit lanes:

- cockpit-owned write lane: add project pointer, update cockpit memory, record
  receipt, or update release ledger,
- project-owned write lane: switch into the project repo/session or open a
  fresh project-scoped gate,
- source/retrieval lane: onboard or index sources only after separate approval.

## Target Operator Prompts

The system should make these prompts natural and safe:

- "What panel am I in, and what can it do?"
- "What is the next safe action here?"
- "Prepare a personal-root update from the latest approved Azoth release."
- "Inventory root-azoth knowledge candidates, but do not import them."
- "Show me the Batch 0 knowledge cards for review."
- "Apply these approved cards to the personal root."
- "Register this project as pointer-only."
- "Update this specific project from Azoth vX.Y.Z with project-scoped approval."
- "Show what changed where after this rollout."

The system should resist ambiguous prompts with a short boundary clarification
when the requested action could cross panels.

## Approval UX

Approval should be explicit, narrow, and local to the panel boundary.

| Action | Required Approval |
| --- | --- |
| Change toolkit/runtime behavior | Root governed pipeline approval |
| Publish public `azoth` | Release approval naming tag and release |
| Install/update personal root from release | Personal-root deployment approval |
| Import knowledge cards | Batch approval naming candidate ids |
| Register a project source | Source registry approval naming read/write boundaries |
| Write to a project repo | Project-scoped approval in that repo |
| Promote M2 to M1 | Existing governed promotion pipeline |

Approvals should not be sticky across authority changes. A Green campaign,
successful release, or approved knowledge batch does not authorize a different
panel's writes.

## Knowledge UX

The personal root should feel like a curated memory desk, not an attic full of
raw boxes.

Good knowledge experience:

- relevant cards are few and cited,
- source refs are visible,
- freshness is visible,
- advisory vs authoritative status is visible,
- raw evidence stays at the source,
- imports happen in reviewed batches,
- rejected and deferred candidates are recorded,
- stale cards remain readable but do not steer action without review.

Bad knowledge experience:

- every root memory episode is copied into personal root,
- inbox rows become hidden instructions,
- project-specific facts appear without source or freshness,
- the agent cannot explain why a card was loaded,
- old cards silently override current project truth.

## Deployment UX

Every deployment should produce a receipt.

Minimum receipt fields:

- source panel,
- target panel,
- source version or commit,
- target path,
- files changed,
- commands run,
- validation result,
- approval basis,
- residual risks,
- next safe action.

For public release deployments, the receipt belongs in `root-azoth` release
evidence and public release artifacts. For personal-root deployments, the
receipt belongs in the personal root's release or import ledger. For project
deployments, the receipt belongs in that project and may be summarized back to
the personal root by approval.

## What Success Feels Like

Developer panel success:

- "We changed Azoth deliberately, tested it, and know whether it belongs in the
  public product."

Product panel success:

- "A clean user-installable release exists, with no private root or personal
  state mixed in."

Personal control panel success:

- "I can see my projects, sources, approved knowledge, and safe next actions
  without exposing secrets or accidentally changing project repos."

Project panel success:

- "This repo received only the approved Azoth behavior or project work, and its
  own gates remained authoritative."

Cross-panel success:

- "The handoff is obvious. The source of truth is obvious. The receipt is
  obvious. The stop conditions are obvious."

## Anti-Patterns

- Copying `root-azoth` `.azoth/memory/` into personal root.
- Treating public `azoth` as a private deployment ledger.
- Treating personal root as a project-write daemon.
- Treating project summaries as project truth after the project changed.
- Running import, deployment, and recall integration in one oversized session.
- Letting a release approval imply personal-root import approval.
- Letting a personal-root approval imply project-write approval.
- Hiding route decisions inside chat instead of writing receipts.

## Rollout Implications

Future sessions should use this anchor as a quick alignment check:

1. Name the panel being changed.
2. Name the panel being deployed to, if different.
3. Name whether the change is generic product behavior or private operator
   state.
4. Select the correct pipeline.
5. Stop before crossing a panel boundary without approval.
6. Write the receipt in the target panel.
7. Keep imports and migrations small enough to review.

For the personal knowledge architecture rollout, the immediate next experience
target is modest:

- The personal root has a visible `.azoth/knowledge/` home.
- It is empty by default.
- It validates before imports.
- It can receive a reviewed Batch 0.
- It can surface a few cited cards later without pretending they are project
  truth.
