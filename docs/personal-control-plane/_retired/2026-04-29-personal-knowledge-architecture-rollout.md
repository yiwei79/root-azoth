# Personal Knowledge Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the personal-root knowledge architecture as a supervised, federated knowledge base with a central index and no bulk memory migration.

**Architecture:** `root-azoth` owns the architecture, schemas, validator, and extraction tooling. The personal root owns curated cards, indexes, source registry, project inventory, and import ledgers. Raw evidence stays in its origin repo or external system; imports are small, reviewed batches with provenance.

**Tech Stack:** Markdown architecture docs, YAML knowledge cards, Python standard-library validators, `pytest`, existing Azoth memory and context-recall concepts.

---

## Required UX Anchor

Before executing any implementation task, read:

```text
docs/personal-control-plane/MULTI-CONTROL-PANEL-UX-ANCHOR.md
```

The implementation must preserve the multi-control-panel target experience:
developer work happens in `root-azoth`, generic runtime changes flow through
the product pipeline, private operator state deploys only to the personal root,
and project writes require project-scoped approval.

## File Structure

Root source files:

- `docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md`: canonical architecture.
- `docs/superpowers/plans/2026-04-29-personal-knowledge-architecture-rollout.md`: this rollout plan.
- `schemas/personal-knowledge-card.schema.yaml`: card contract.
- `schemas/personal-knowledge-import-batch.schema.yaml`: import-batch contract.
- `scripts/personal_knowledge_validate.py`: validator for cards, indexes, policy, and import batches.
- `scripts/personal_knowledge_inventory.py`: read-only candidate inventory from approved sources.
- `tests/test_personal_knowledge_validate.py`: validator tests.
- `tests/test_personal_knowledge_inventory.py`: inventory tests.

Personal-root target files:

- `docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md`: deployed architecture copy.
- `.azoth/knowledge/README.md`: operator-facing knowledge base guide.
- `.azoth/knowledge/policy.yaml`: local policy and gates.
- `.azoth/knowledge/preferences.yaml`: approved operator preferences.
- `.azoth/knowledge/principles.yaml`: approved operator principles.
- `.azoth/knowledge/glossary.yaml`: shared terms.
- `.azoth/knowledge/indexes/topic-index.yaml`: card lookup by topic.
- `.azoth/knowledge/indexes/authority-index.yaml`: card lookup by authority home.
- `.azoth/knowledge/imports/ledger.yaml`: approved/rejected import decisions.
- `.azoth/knowledge/imports/batches/`: reviewed import batches.
- `.azoth/knowledge/cards/root-azoth/`: curated cards distilled from root evidence.
- `.azoth/knowledge/cards/projects/`: project summary cards.
- `.azoth/knowledge/cards/personal/`: personal cards and principles when one-file-per-card is useful.

## Context Map

Targets:

- Documentation: low risk, establishes source truth.
- Schemas and validators: medium risk, can block imports if too strict or too loose.
- Personal-root skeleton: medium privacy risk because it creates the homes future sessions will trust.
- Inventory tooling: medium risk because it reads private root evidence; must stay read-only.
- Batch 0 import: high judgment risk; must require operator approval.

Downstream dependencies:

- `skills/context-recall/SKILL.md` may later read cards.
- `$azoth-start` or personal-root session-start flows may later surface cards.
- `.azoth/projects/index.yaml` and `.azoth/sources/registry.yaml` constrain retrieval.
- Existing Azoth M3/M2 memory remains separate from `.azoth/knowledge/`.

Decision:

- Implement in narrow phases.
- Do not combine validator creation, extraction, and Batch 0 import in one session.
- Keep every import path fail-closed and reviewed.

### Task 1: Freeze Architecture Source And Deployment Copy

**Files:**
- Create: `docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md`
- Create: `docs/superpowers/plans/2026-04-29-personal-knowledge-architecture-rollout.md`
- Create or update: `/Users/yiwei/GithubRepos/personal-azoth-root/docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md`

- [ ] **Step 1: Read the existing personal-root model**

Run:

```bash
sed -n '1,220p' .azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md
```

Expected: the output says personal root is separate from `root-azoth`, forbids bulk personal/global knowledge inside `root-azoth`, and blocks silent inbox draining.

- [ ] **Step 2: Verify root and personal-root status**

Run:

```bash
git status --short --branch
git -C /Users/yiwei/GithubRepos/personal-azoth-root status --short --branch
```

Expected: root is clean or only has this planning work; personal root has no unrelated tracked modifications.

- [ ] **Step 3: Add or refresh the architecture document**

Use the content from `docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md`. The document must include:

- federated knowledge with central personal index,
- plane authority boundaries,
- knowledge classes K0 through K7,
- target `.azoth/knowledge/` shape,
- card contract,
- import flow,
- root extraction policy,
- rollout phases,
- stop conditions.

- [ ] **Step 4: Deploy the architecture copy**

Copy the same architecture into:

```text
/Users/yiwei/GithubRepos/personal-azoth-root/docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md
```

Expected: the personal root now carries the same planning contract but no cards or extracted memories.

- [ ] **Step 5: Validate**

Run:

```bash
git diff -- docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md docs/superpowers/plans/2026-04-29-personal-knowledge-architecture-rollout.md
git -C /Users/yiwei/GithubRepos/personal-azoth-root diff -- docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md
```

Expected: diffs are docs-only and contain no secrets or raw memory dumps.

### Task 2: Add Personal Knowledge Skeleton To The Personal Root

**Files:**
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/README.md`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/policy.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/preferences.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/principles.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/glossary.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/indexes/topic-index.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/indexes/authority-index.yaml`
- Create: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/imports/ledger.yaml`

- [ ] **Step 1: Create directories**

Run:

```bash
mkdir -p /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/cards/root-azoth /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/cards/projects /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/cards/personal /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/indexes /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/imports/batches
```

Expected: directories exist and contain no imported cards yet.

- [ ] **Step 2: Add policy**

Create `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/policy.yaml`:

```yaml
schema_version: 1
policy:
  architecture: federated_with_central_index
  bulk_imports_allowed: false
  silent_inbox_draining_allowed: false
  automatic_source_refresh_allowed: false
  project_writes_require_project_scope: true
  credentials_in_repo_allowed: false
  cards_require_source_refs: true
  cards_require_freshness: true
  import_batches_require_operator_approval: true
retrieval:
  max_cards_default: 5
  include_source_refs: true
  include_freshness_status: true
```

- [ ] **Step 3: Add empty preference, principle, glossary, and index files**

Create these exact initial files:

```yaml
# preferences.yaml
schema_version: 1
preferences: []
```

```yaml
# principles.yaml
schema_version: 1
principles: []
```

```yaml
# glossary.yaml
schema_version: 1
terms: []
```

```yaml
# topic-index.yaml
schema_version: 1
topics: []
```

```yaml
# authority-index.yaml
schema_version: 1
authorities: []
```

```yaml
# ledger.yaml
schema_version: 1
imports: []
```

- [ ] **Step 4: Validate no knowledge was migrated**

Run:

```bash
find /Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/cards -type f | sort
```

Expected: no files are listed.

### Task 3: Add Card And Import-Batch Schemas In Root

**Files:**
- Create: `schemas/personal-knowledge-card.schema.yaml`
- Create: `schemas/personal-knowledge-import-batch.schema.yaml`

- [ ] **Step 1: Add the card schema**

Create `schemas/personal-knowledge-card.schema.yaml`:

```yaml
schema_version: 1
name: personal_knowledge_card
required:
  - schema_version
  - id
  - title
  - type
  - scope
  - authority_home
  - privacy
  - status
  - confidence
  - freshness
  - source_refs
  - allowed_use
  - forbidden_use
  - body
enums:
  type:
    - operating_principle
    - operator_preference
    - project_summary
    - source_note
    - toolkit_lesson
    - decision_context
    - glossary_term
  status:
    - active
    - stale
    - superseded
    - archived
  privacy:
    - public
    - internal
    - private
    - secret_pointer_only
  confidence:
    - low
    - medium
    - high
constraints:
  source_refs_min: 1
  body_min_chars: 40
  body_max_chars: 1200
  review_after_required_for_active: true
```

- [ ] **Step 2: Add the import-batch schema**

Create `schemas/personal-knowledge-import-batch.schema.yaml`:

```yaml
schema_version: 1
name: personal_knowledge_import_batch
required:
  - schema_version
  - id
  - created_at
  - source_plane
  - source_refs
  - candidates
  - operator_review
enums:
  source_plane:
    - root-azoth
    - public-azoth
    - personal-root
    - project-repo
    - external-source
  candidate_decision:
    - approved
    - rejected
    - revise
    - defer
constraints:
  candidates_min: 1
  approved_candidates_require_card_path: true
  rejected_candidates_require_reason: true
  operator_review_required_before_deploy: true
```

- [ ] **Step 3: Commit schemas separately**

Run:

```bash
git add schemas/personal-knowledge-card.schema.yaml schemas/personal-knowledge-import-batch.schema.yaml
git commit -m "docs: add personal knowledge schemas"
```

Expected: one focused schema commit.

### Task 4: Add Validator With Focused Tests

**Files:**
- Create: `scripts/personal_knowledge_validate.py`
- Create: `tests/test_personal_knowledge_validate.py`

- [ ] **Step 1: Write failing tests**

Create tests that cover:

- valid card passes,
- missing required field fails,
- active card without `freshness.review_after` fails,
- card with no `source_refs` fails,
- approved import candidate without `card_path` fails,
- rejected import candidate without reason fails,
- card path outside `.azoth/knowledge/cards/` fails.

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_personal_knowledge_validate.py -q
```

Expected: tests fail because the validator does not exist yet.

- [ ] **Step 2: Implement validator**

Implement `scripts/personal_knowledge_validate.py` with only the Python standard library plus the repo's existing YAML loader helper if available. The CLI must support:

```bash
python3 scripts/personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/personal-azoth-root
python3 scripts/personal_knowledge_validate.py --card /path/to/card.yaml
python3 scripts/personal_knowledge_validate.py --batch /path/to/batch.yaml
```

Exit codes:

- `0` when all validated artifacts pass,
- `1` when any validation error exists.

Output format:

```text
personal knowledge validation OK
```

or:

```text
personal knowledge validation failed:
- <path>: <message>
```

- [ ] **Step 3: Run tests**

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_personal_knowledge_validate.py -q
```

Expected: all focused validator tests pass.

### Task 5: Add Read-Only Root Inventory

**Files:**
- Create: `scripts/personal_knowledge_inventory.py`
- Create: `tests/test_personal_knowledge_inventory.py`

- [ ] **Step 1: Write failing tests**

Tests should build a temp root with:

- `.azoth/memory/patterns.yaml`,
- `.azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md`,
- `.azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md`.

Expected inventory JSON must include candidate ids, source paths, source plane,
recommended card type, and risk reason. It must not write any card files.

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_personal_knowledge_inventory.py -q
```

Expected: tests fail because the inventory helper does not exist yet.

- [ ] **Step 2: Implement read-only inventory**

CLI:

```bash
python3 scripts/personal_knowledge_inventory.py --source-root /Users/yiwei/GithubRepos/root-azoth --source-plane root-azoth --json
```

Rules:

- read only,
- write nothing,
- list candidate records only,
- include source provenance,
- mark raw `.azoth/memory/episodes.jsonl` as `risk: raw_memory_bulk_import_forbidden`,
- mark `.azoth/inbox/**` as `risk: inbox_requires_intake_or_manual_excerpt`,
- mark root release evidence and approved M2 patterns as candidate sources.

- [ ] **Step 3: Run tests**

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_personal_knowledge_inventory.py -q
```

Expected: all focused inventory tests pass.

### Task 6: Generate Batch 0 As A Review Artifact Only

**Files:**
- Create: `.azoth/knowledge-import-candidates/batch-000-root-azoth.yaml` in `root-azoth`

- [ ] **Step 1: Run read-only inventory**

Run:

```bash
python3 scripts/personal_knowledge_inventory.py --source-root /Users/yiwei/GithubRepos/root-azoth --source-plane root-azoth --json
```

Expected: JSON candidates print to stdout; no personal-root files change.

- [ ] **Step 2: Draft batch 0**

Create exactly 5 to 10 candidates. Each candidate must include:

- proposed card id,
- proposed title,
- type,
- source refs,
- privacy,
- confidence,
- allowed use,
- forbidden use,
- draft body,
- decision: `defer` until operator review.

- [ ] **Step 3: Validate batch**

Run:

```bash
python3 scripts/personal_knowledge_validate.py --batch .azoth/knowledge-import-candidates/batch-000-root-azoth.yaml
```

Expected: validation passes with all candidates undeployed.

- [ ] **Step 4: Stop for operator review**

Expected final message: "Batch 0 is drafted for review. No cards were deployed."

### Task 7: Deploy Approved Batch 0

**Files:**
- Create approved card files under `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/cards/root-azoth/`
- Modify: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/imports/ledger.yaml`
- Modify: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/indexes/topic-index.yaml`
- Modify: `/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/knowledge/indexes/authority-index.yaml`

- [ ] **Step 1: Confirm operator approval**

Required approval text must name:

- batch id,
- approved candidate ids,
- rejected or deferred candidate ids,
- target personal-root path.

Stop if approval does not name these.

- [ ] **Step 2: Write approved cards**

Write only approved candidates. Do not write rejected or deferred candidates.

- [ ] **Step 3: Update ledger**

Append one import record per candidate decision.

- [ ] **Step 4: Update indexes**

Index cards by topic and authority home.

- [ ] **Step 5: Validate personal root**

Run:

```bash
python3 /Users/yiwei/GithubRepos/root-azoth/scripts/personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/personal-azoth-root
git -C /Users/yiwei/GithubRepos/personal-azoth-root status --short --branch
```

Expected: validation passes and only approved personal-root knowledge files changed.

### Task 8: Add Recall Surface After Batch 0 Proves Useful

**Files:**
- Modify: personal-root session-start instructions or add a personal-root skill after operator approval.
- Test: focused tests for whichever recall helper is introduced.

- [ ] **Step 1: Review Batch 0 usefulness**

Ask whether the approved cards helped at least one real session-start or planning decision.

Expected: explicit operator yes/no before changing recall behavior.

- [ ] **Step 2: Add a narrow recall helper**

The helper must:

- load at most 5 cards by default,
- require source refs,
- display freshness,
- label cards advisory unless policy says otherwise,
- never write source or project repos.

- [ ] **Step 3: Validate**

Run focused tests for the helper and then:

```bash
python3 scripts/roadmap_dashboard.py
python3 scripts/azoth-deploy.py --check
```

Expected: root remains healthy and generated surfaces stay in sync.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-29-personal-knowledge-architecture-rollout.md`.

Recommended execution path:

1. Execute Task 2 and Task 3 in the next session.
2. Execute Task 4 and Task 5 in a separate implementation session.
3. Execute Task 6 as a review-only session.
4. Execute Task 7 only after explicit operator approval of Batch 0.
5. Delay Task 8 until Batch 0 has proven useful in real operation.
