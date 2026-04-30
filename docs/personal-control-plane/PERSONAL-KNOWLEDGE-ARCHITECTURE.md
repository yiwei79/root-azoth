# Personal Knowledge Architecture

Status: draft architecture source
Date: 2026-04-29
Source plane: `root-azoth`
Deployment target: personal Azoth root
UX anchor: `docs/personal-control-plane/MULTI-CONTROL-PANEL-UX-ANCHOR.md`

This document defines the scalable knowledge architecture for the operator
personal control plane. It extends the T-038 personal-root model without
changing the v0.2.0 public product contract.

The governing choice is: use a federated knowledge system with a central
personal index. Do not bulk-copy `root-azoth` developer memory into the
personal root.

## Decision

The personal root is the routing and synthesis layer for the operator. It is
not the warehouse for all raw evidence.

Centralize:

- source registry pointers,
- project inventory and project summaries,
- operator preferences and personal principles,
- curated knowledge cards,
- import ledgers and review decisions,
- retrieval indexes.

Distribute:

- raw project memory,
- detailed project roadmaps and backlogs,
- `root-azoth` development memory,
- public product release authority,
- raw external sources,
- credentials and secrets.

This keeps the personal root useful at session start while avoiding stale
duplicates, privacy leakage, and accidental cross-project governance.

## Planes And Authority

| Plane | Authority Home | Personal Root May Store | Personal Root Must Not Store |
| --- | --- | --- | --- |
| `root-azoth` | Toolkit development, release evidence, generated surfaces, governed roadmap truth | Curated cards distilled from approved root evidence, with source refs | Raw `.azoth/memory`, roadmap as mutable personal truth, private release scratch state |
| Public `azoth` | Installable product surface | Release version pointer and install ledger | Private root state, local gates, credentials |
| Personal root | Operator routing, project inventory, personal knowledge | Indexes, summaries, preferences, cards, handoffs, source registry | Toolkit source history, public publishing authority, silent intake decisions |
| Project repos | Project-local truth | Pointer plus summary approved by operator | Project secrets, project backlog mutation without project-scoped approval |
| External sources | Origin system truth | Pointer, privacy class, refresh policy, credential location outside repo | Raw mailbox exports, tokens, unreviewed bulk dumps |

Authority rule: when a card or summary conflicts with the originating system,
the originating system wins until a fresh review updates the personal root.

## Knowledge Classes

| Class | Home | Format | Review Gate | Retrieval Role |
| --- | --- | --- | --- | --- |
| K0 Raw evidence | Origin repo or external system | Native source format | Source-specific approval | Referenced, not loaded by default |
| K1 Source metadata | Personal root `.azoth/sources/registry.yaml` | YAML registry rows | Operator approval per source | Defines what can be read and written |
| K2 Project inventory | Personal root `.azoth/projects/index.yaml` and handoffs | YAML plus Markdown handoff notes | Operator approval per project | Routes work to the right repo |
| K3 Personal preferences | Personal root `.azoth/knowledge/preferences.yaml` | YAML | Explicit operator approval | Shapes defaults and style |
| K4 Personal principles | Personal root `.azoth/knowledge/principles.yaml` | YAML | Explicit operator approval | Shapes recurring decisions |
| K5 Curated cards | Personal root `.azoth/knowledge/cards/` | One YAML file per card | Import-batch approval | Topical retrieval and synthesis |
| K6 Operational memory | Each Azoth deployment `.azoth/memory/` | M3/M2 Azoth memory | Existing Azoth promotion rules | Local session continuity |
| K7 Procedural knowledge | Kernel, skills, agents | Product or repo files | Governed M2 to M1 promotion | Changes behavior mechanically |

The personal root can contain both K5 curated knowledge and K6 local Azoth
operational memory. These are different things. K6 records what happened in
the personal root itself. K5 is a reviewed knowledge base for cross-session and
cross-project recall.

## Target Personal Root Shape

```text
personal-azoth-root/
  docs/
    personal-control-plane/
      PERSONAL-KNOWLEDGE-ARCHITECTURE.md
  .azoth/
    knowledge/
      README.md
      policy.yaml
      preferences.yaml
      principles.yaml
      glossary.yaml
      cards/
        root-azoth/
        projects/
        personal/
      indexes/
        topic-index.yaml
        authority-index.yaml
      imports/
        ledger.yaml
        batches/
    memory/
      episodes.jsonl
      patterns.yaml
      personal/
      project-summaries/
    projects/
      index.yaml
      handoffs/
    sources/
      registry.yaml
    releases/
      applied.yaml
    inbox/
      pending/
      archived/
```

The `.azoth/knowledge/` subtree is the curated personal knowledge base. The
existing `.azoth/memory/` subtree remains the local Azoth memory system for the
personal root itself.

## Knowledge Card Contract

Each curated card should be small enough to load into session context and
precise enough to cite back to its source.

```yaml
schema_version: 1
id: kb-root-azoth-001
title: Green campaign is not release readiness
type: operating_principle
scope:
  - azoth
  - release
authority_home: root-azoth
privacy: private
status: active
confidence: high
freshness:
  reviewed_at: "2026-04-29"
  review_after: "2026-05-29"
source_refs:
  - repo: root-azoth
    path: .azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md
    commit: b0763a8
allowed_use:
  - session_start_recall
  - release_planning
forbidden_use:
  - automatic_project_mutation
  - public_release_claim
body: >
  A completed autonomous campaign proves that campaign budget ended. Release
  readiness still requires packaging, deploy parity, validation, and clean
  state.
```

Required fields:

- `schema_version`
- `id`
- `title`
- `type`
- `scope`
- `authority_home`
- `privacy`
- `status`
- `confidence`
- `freshness.reviewed_at`
- `source_refs`
- `allowed_use`
- `forbidden_use`
- `body`

Allowed `type` values:

- `operating_principle`
- `operator_preference`
- `project_summary`
- `source_note`
- `toolkit_lesson`
- `decision_context`
- `glossary_term`

Allowed `status` values:

- `active`
- `stale`
- `superseded`
- `archived`

## Import Flow

Every import from `root-azoth`, a project repo, or an external source follows
the same supervised flow.

```text
Inventory -> Candidate batch -> Classify -> Human review -> Deploy -> Validate -> Recall
```

1. Inventory source material in read-only mode.
2. Produce an import batch with candidate cards and provenance.
3. Classify each candidate by authority home, privacy, risk, and expected use.
4. Ask the operator to approve, reject, or revise the batch.
5. Deploy approved cards into `.azoth/knowledge/cards/`.
6. Append the import decision to `.azoth/knowledge/imports/ledger.yaml`.
7. Update indexes and run validation.
8. Use only the top relevant cards during session start or planning.

No step may silently drain inbox evidence, auto-promote memory, mutate
governance, or write into a project repo.

## Root-Azoth Extraction Policy

`root-azoth` contains useful developer knowledge, but it is not the personal
knowledge base. Extraction from it must be selective.

Allowed extraction:

- durable operator principles,
- workflow lessons that apply beyond one release incident,
- source pointers to public or private root evidence,
- sanitized summaries of release and governance lessons,
- personal preferences explicitly expressed by the operator.

Forbidden extraction:

- raw `.azoth/memory/episodes.jsonl` bulk import,
- raw inbox rows,
- local gates and run-ledger state,
- roadmap state as personal project truth,
- generated scratch artifacts,
- secrets, credentials, or private downstream project facts,
- release authority claims.

Candidate batch 0 should be tiny: 5 to 10 cards. It should prove retrieval
quality before any larger import.

Suggested first candidates:

- Green campaign completion is not release readiness.
- Memory needs read-back into action selection.
- No silent inbox draining or automatic intake decisions.
- Route-first workflows beat stale chat-memory continuation.
- Docs-first architecture slices should precede implementation when the gap is new.

## Retrieval Model

The personal root should not load the entire knowledge base into every session.
Retrieval should be narrow, cited, and role-aware.

Session start should consider:

1. active project, if any,
2. operator goal,
3. relevant preferences and principles,
4. project index and handoff summary,
5. top 3 to 5 matching knowledge cards,
6. source registry constraints.

Retrieval output should include:

- card id,
- one-line summary,
- why it matched,
- source refs,
- freshness status,
- whether it is advisory or authoritative.

Cards are advisory unless they describe a personal-root policy or an explicit
operator preference. Project-local truth still belongs to the project repo.

## Governance Rules

1. No bulk imports.
2. No silent inbox draining.
3. No automatic source refresh unless a later governed task defines a supervised schedule.
4. No project writes without project-scoped approval.
5. No credentials or raw mailbox exports in tracked repo state.
6. No public product mutation from personal-root knowledge.
7. No M2 or M1 mutation without existing Azoth governance.
8. Every imported card must retain source provenance.
9. Every card must have a freshness policy.
10. Stale cards remain readable but should not steer action without review.

## Rollout Phases

Phase 0: Architecture source

- Store this architecture in `root-azoth`.
- Deploy a copy to the personal root.
- Do not migrate knowledge yet.

Phase 1: Personal-root skeleton

- Add `.azoth/knowledge/` directories.
- Add `policy.yaml`, empty indexes, empty ledger, and README.
- Validate that the repo remains local-only unless the operator chooses a private remote.

Phase 2: Validator and schemas

- Add schemas for knowledge cards and import batches.
- Add a validator that checks required fields, allowed enum values, provenance, and path safety.
- Add focused tests.

Phase 3: Read-only source inventory

- Add a root-side inventory helper that lists candidate source artifacts without writing cards.
- Start with `root-azoth` memory patterns, release evidence docs, and T-038/T-039 artifacts.

Phase 4: Batch 0 curation

- Generate 5 to 10 candidate cards.
- Review with the operator.
- Deploy only approved cards.
- Update import ledger and indexes.

Phase 5: Recall integration

- Teach the personal-root session-start flow to surface top matching knowledge cards.
- Keep card loading small and cited.
- Do not alter project repos.

Phase 6: Project onboarding pilot

- Add one or two project profiles.
- Record pointer-only source entries.
- Create project summaries by approval, not by automatic scan.

Phase 7: Maintenance

- Add freshness review cadence.
- Add supersession handling.
- Add archive retention policy.
- Consider optional private remote or encrypted backup only after the local model feels right.

## Stop Conditions

Stop before implementation if any of the following are true:

- the operator has not approved the target personal-root path,
- the target repo is dirty for reasons unrelated to the current deployment,
- a source contains secrets or raw private data,
- an import candidate has no source provenance,
- a proposed card would become a hidden instruction,
- a card conflicts with a project repo and no fresh project review exists,
- the proposed task would mutate governance or M1 without the governed pipeline.

## Open Decisions

- Whether the personal root remains local-only or gets a private/encrypted remote.
- Whether cards should be one file per card or batch files by domain after scale is proven.
- Which first two project repos should be registered.
- Which external sources are pointer-only at first.
- How often stale cards should be reviewed.
- Whether personal preferences should be stored only in YAML or mirrored into human-readable Markdown.

## Near-Term Recommendation

The current near-term deployment path is the T-047 procedure in
`docs/personal-control-plane/PERSONAL-CONTROL-PLANE-DEPLOYMENT-PROCEDURE.md`.
Treat the personal root as desired state plus reconciliation before any future
mutation-capable slice.

Future personal-root updates should run through T-048 from an approved
desired-state manifest, then use T-049 for pointer-only project onboarding and
T-050 for stable deployment closeout. Do not resume older skeleton, inventory,
or Batch 0 wording as the next action unless the roadmap route explicitly points
back to it.
