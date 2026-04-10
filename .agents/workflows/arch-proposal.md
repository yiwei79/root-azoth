# /arch-proposal $ARGUMENTS

Structured **proposal** for changes that touch D1–D53, layer boundaries, or normative
architecture narrative. Use this instead of drafting “approved architecture” inline in chat.

## Cursor parity (hooks)

**PreToolUse** hooks from `.claude/settings.json` **do not run in Cursor**. Before any
**Write/Edit**, simulate the same gates as other mixed/write commands: **`Read`**
`.azoth/scope-gate.json` (and `.azoth/pipeline-gate.json` when the scope is **governed**
or **M1** per `claude-code-parity.mdc`). Do not treat chat text as scope approval.

If this command **orchestrates** a multi-stage delivery in Cursor, use the **`Task`** tool
per isolated stage and forward **`prior_stage_summaries`** (typed YAML handoffs) per
`skills/subagent-router/SKILL.md` — do not collapse review/eval/build stages into one thread.

## Authority boundary

- The proposal file is **not** authority for **`kernel/**`** or **normative docs**.
- Agents **must not** auto-write **`docs/AZOTH_ARCHITECTURE.md`**, **`docs/adrs/**`**, or
  **`docs/DECISIONS_INDEX.md`** from this command. Those paths are **human promotion**
  targets only.

## Artifact

1. **`Read`** `pipelines/architecture-proposal.schema.yaml` and the example
   `pipelines/examples/architecture-proposal.minimal.yaml`.
2. Draft a YAML document under **`.azoth/proposals/`** (e.g. `.azoth/proposals/<slug>.yaml`).
3. Validate before treating the file as well-formed:

   ```bash
   python3 scripts/architecture_proposal_validate.py .azoth/proposals/<slug>.yaml
   ```

4. Present the proposal to the human and obtain explicit status transitions (e.g. draft →
   submitted → **`approved_for_docs`**).

## After `approved_for_docs` (human workflow)

When the human marks the proposal **`approved_for_docs`**, **the human** (not the agent)
promotes content into canonical documentation:

1. Edit **`docs/AZOTH_ARCHITECTURE.md`** as needed for architecture narrative and tables.
2. Optionally add or update an ADR under **`docs/adrs/`** when the change warrants a
   dedicated decision record.
3. When introducing or updating decision rows, edit **`docs/DECISIONS_INDEX.md`** so the
   index stays consistent with D1–D53 references in the proposal’s `decision_refs`.

Agents may assist with **draft text in chat** or in the proposal `details` object, but
**commits** to those three doc locations remain **human-gated** promotion steps.

## Rules

- Keep **`decision_refs`** aligned with real IDs in `docs/DECISIONS_INDEX.md`.
- If the work is **M1 / governed**, run the appropriate delivery pipeline (`/deliver-full`,
  `/auto`, `/deliver`) so **`pipeline-gate.json`** matches scope before implementation
  writes elsewhere in the repo.
- After changing this command file, run **`python3 scripts/azoth-deploy.py`** from the
  repo root (D46).

## Arguments

Optional topic or backlog id: `$ARGUMENTS`
