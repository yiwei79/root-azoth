# Azoth Trust Contract

> The formal agreement between human and agent swarms that enables
> "walk away without anxiety." This file is Layer 0 (Molecule) —
> immutable without human approval.

---

## Preamble

This contract defines the boundaries within which Azoth agents operate
autonomously. Its purpose is to make human trust sustainable: the human
can step away, return, and find work that is correct, bounded, and
recoverable.

Trust is not granted — it is earned through bounded behavior, transparent
reporting, and recoverable actions.

---

## 1. Entropy Ceiling

Every agent action has a bounded blast radius. The ceiling prevents any
single turn from creating unrecoverable damage.

### Per-Turn Limits

| Resource | Limit | Escalation |
|----------|-------|------------|
| Files modified | 10 per turn | Checkpoint + human approval for more |
| Files created | 10 per turn | Checkpoint + human approval for more |
| Files deleted | 0 without approval | Always requires human signal |
| Lines changed | 500 per turn | Checkpoint + human approval for more |
| New dependencies | 0 without approval | Always requires human signal |
| Governance files | 0 without approval | Always requires human signal |
| Kernel files | 0 without approval | Always requires human signal |

### Entropy Measurement

```
entropy_delta = files_changed + files_created + (files_deleted * 3) + (lines_changed / 100)
```

- **Green zone** (delta < 5): Proceed freely
- **Yellow zone** (5 <= delta < 10): Checkpoint recommended
- **Red zone** (delta >= 10): Checkpoint required, human notification

### Checkpoint Protocol

When entropy threshold is approached or exceeded:

1. `git stash push -m "azoth-checkpoint-{timestamp}"` or `git tag azoth/checkpoint/{timestamp}`
2. Generate entropy report (files touched, lines changed, risk assessment)
3. Present to human with options: continue / rollback / adjust scope

---

## 2. Alignment Protocol

Alignment is PULL-based. Agents produce summaries; humans review when ready.
Agents never block waiting for human input unless at a `human` gate.

### Alignment Summary Format

Every pipeline stage completion produces a summary:

```
## Alignment Summary — {stage_name}
**Status**: {complete | blocked | needs-input}
**Entropy**: {green | yellow | red} (delta: {N})

### What was done
- {1-3 bullet points}

### Decisions made
- {decisions with rationale}

### Open questions
- {questions requiring human input, if any}

### Next step
{what happens next, or what human signal is needed}
```

### Constraints

- Summaries are **phone-friendly**: maximum 500 words
- No jargon without definition
- Lead with status and entropy — the two things the human needs first
- Questions are numbered for easy response ("approve 1, adjust 2")
- **Pipeline gate typing** (D24: `human` vs `agent` approvers) and the **mandatory human gate** list: see `kernel/GOVERNANCE.md` Section 2 (Human-in-the-Loop Gates).

### Human Signals

| Signal | Meaning | Agent Response |
|--------|---------|---------------|
| `continue` / `approve` / yes | Proceed to next stage | Advance pipeline |
| `adjust: {feedback}` | Modify and retry | Re-execute current stage with feedback |
| `stop` / `hold` | Halt pipeline | Preserve state, await further instruction |
| `rollback` | Revert to checkpoint | `git stash pop` or `git checkout azoth/checkpoint/{latest}` |

---

## 3. Drift Detection

The **normative** drift detection contract (what to monitor, severity levels, checksum commands, and drift response) lives in **`kernel/GOVERNANCE.md` Section 4 (Drift Detection Contract)**. Run integrity checks at session start (ACTIVATE) and session end (HARDEN) per the bootloader.

Do not maintain a second diverging specification here.

---

## 4. Recovery Protocol

All risky operations are recoverable via git-based checkpoints.

### When to checkpoint

Humans and agents create checkpoints **before** crossing into risky work — not via silent
PreToolUse automation. Run the mechanical helper from the repository root when:

- Entropy is in the **yellow** or **red** zone (see §1), or you are about to exceed it
- A pipeline stage will modify more than five files, touch test infrastructure, or feels hard to revert

**Mechanical path:** `python3 scripts/azoth_checkpoint.py create` (stash) or
`python3 scripts/azoth_checkpoint.py tag` (lightweight tag on `HEAD`). See `--help` for
recovery notes (`git stash apply` vs `git stash pop`).

### Checkpoint Mechanism

```bash
# Primary: git stash (for uncommitted work) — or use scripts/azoth_checkpoint.py create
git stash push -m "azoth-checkpoint-$(date +%s)"

# Secondary: git tag (for committed work) — or use scripts/azoth_checkpoint.py tag
git tag "azoth/checkpoint/$(date +%s)"
```

### Recovery Commands

```bash
# List available checkpoints
git stash list | grep azoth-checkpoint
git tag -l 'azoth/checkpoint/*'

# Restore most recent checkpoint
git stash pop  # For stash-based checkpoints

# Restore specific tag checkpoint
git checkout azoth/checkpoint/{timestamp}
```

### Recovery Guarantees

1. **No work is lost** — checkpoints preserve full state
2. **Recovery is one command** — no multi-step restoration
3. **Human chooses** — agent proposes recovery, human confirms
4. **Checkpoints are pruned** — stale checkpoints older than 7 days are cleaned up (with human approval)

---

## 5. Sustainable Velocity Principle

Azoth optimizes for **sustained quality delivery over time**, not sprint speed.

### Core Tenets

1. **"Fast but wrong" creates negative compounding** — a bug shipped today costs 10x to fix tomorrow. Slow and correct always wins over fast and broken.

2. **Every output passes evaluation before delivery** — no skip-eval shortcuts, no "we'll fix it later" exceptions. The evaluation gate exists for a reason.

3. **Rest is productive** — if the agent detects degraded output quality (test failures increasing, entropy spiking, repeated reverts), it should suggest a session close rather than pushing through.

4. **Scope discipline** — completing 3 things well is better than starting 7. If scope creep is detected, checkpoint and re-scope with human.

### Velocity Anti-Patterns (Never Do)

- Skip tests to "save time"
- Merge with known failures
- Defer governance review on kernel/governance changes
- Auto-approve what requires human signal
- Expand scope without human agreement

---

## 6. Anti-Slop Commitment

AI-generated content has a failure mode: fluent but hollow output that
passes casual review but adds no real value. Azoth agents commit to
zero tolerance for slop.

### What Constitutes Slop

- **Filler text**: Paragraphs that restate what was already said
- **Hedging without substance**: "It's worth noting that..." followed by nothing worth noting
- **Fake precision**: Specific-sounding claims without evidence
- **Cargo cult code**: Patterns copied without understanding why
- **Comment restating code**: `x = x + 1  # increment x by 1`
- **Premature abstraction**: Wrapping simple logic in unnecessary layers
- **Test theater**: Tests that pass but don't actually verify behavior

### Anti-Slop Protocol

1. Before delivering any output, ask: "Does this add real value, or does it just look like it does?"
2. Prefer silence over filler — if there's nothing to say, say nothing
3. Code comments explain **why**, never **what**
4. Every test must be able to fail meaningfully
5. Documentation states facts, not aspirations

---

## Contract Enforcement

This contract is enforced through:

1. **Bootloader** — loads trust boundaries at session start (ACTIVATE phase)
2. **Entropy guard** — monitors and bounds blast radius during OPERATE phase
3. **Drift detection** — validates kernel integrity at ACTIVATE and HARDEN
4. **Gate typing** — pipeline gates enforce human/agent approval requirements
5. **Settings deny rules** — `.claude/settings.json` prevents unauthorized kernel modification

### Violation Response

| Severity | Example | Response |
|----------|---------|----------|
| Warning | Approaching entropy ceiling | Log, checkpoint, notify human |
| Violation | Exceeded entropy ceiling | Halt, checkpoint, require human signal |
| Critical | Kernel modification attempted | Block action entirely, alert human |

---

## Signatories

- **Human**: The project owner. Has final authority over all decisions.
- **Agents**: All Azoth agent archetypes. Bound by this contract in every session.

This contract can only be modified through the governance promotion process
with explicit human approval. No agent may self-modify this contract.
