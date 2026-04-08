---
name: prompt-engineer
description: |
  Refine SKILL.md, agent definitions, and slash commands for clarity and reliability;
  apply L2 optimization loops from evaluation evidence. Use when editing instruction
  surfaces or system prompts.
---

# Prompt Engineer

Shape prompts and instructions for maximum clarity, reliability, and
effectiveness across Azoth's agent ecosystem.

## Overview

Prompt engineering in Azoth goes beyond ad-hoc prompt writing. It's the
discipline of crafting instructions that produce reliable, high-quality
agent behavior — and improving them systematically over time.

```
Draft → Structure → Test → Evaluate → Refine → Promote
```

## When to Use

- **Creating new skills** — SKILL.md frontmatter + content structure
- **Writing agent instructions** — .agent.md posture and behavior definitions
- **Designing commands** — slash command prompts that compose pipelines
- **L2 auto-refinement** — improving instructions based on evaluation data
- **Cross-platform adaptation** — ensuring instructions work across Claude Code, OpenCode, Copilot

---

## Prompt Structure Patterns

### Pattern 1: Role-Context-Task-Format (RCTF)

The foundation for any agent instruction.

```markdown
## Role
You are a {role} responsible for {scope}.

## Context
{what the agent needs to know before acting}

## Task
{specific, actionable instructions}

## Format
{expected output structure}
```

### Pattern 2: Structured Skill (SKILL.md)

Azoth skills follow a consistent structure:

```yaml
---
name: skill-name
description: |
  Clear description with "Use this skill when:" list.
  Each trigger condition on its own line.
---

# Skill Title

{overview — what this skill does and why}

## When to Use
{concrete trigger conditions}

## Process / Patterns
{step-by-step or pattern catalog}

## Template
{copy-paste template for quick use}

## Integration
{how this connects to pipeline, bootloader, other skills}

## Best Practices
{table of practices with rationales}
```

### Pattern 3: Chain-of-Thought Gate

For decisions that need explicit reasoning:

```markdown
Before deciding, work through these steps:

1. State the decision clearly
2. List the options (minimum 2)
3. For each option, state: pro, con, risk
4. Choose and state the reasoning
5. State what would change your mind
```

### Pattern 5: Azoth effect label (build transparency)

Any instruction surface that can trigger **Write/Edit** (builder path) must declare it.

**Slash commands** (`.claude/commands/*.md`): set in YAML frontmatter (see `kernel/GOVERNANCE.md` — Instruction effect labels):

```yaml
---
description: "..."
azoth_effect: read | write | mixed
---
```

**Skills, AGENTS.md, or ad-hoc prompts** where frontmatter is not used: put a single visible line near the top:

```markdown
**Azoth effect:** `write`
```

Use `read` for analysis-only, `write` when implementation or file mutation is in the default path, `mixed` when the human must approve before any write.

### Pattern 4: Few-Shot with Rubric

For tasks requiring consistent quality:

```markdown
## Examples

### Good (score: 5/5)
{example with annotation of why it scores well}

### Adequate (score: 3/5)
{example with annotation of what's missing}

### Poor (score: 1/5)
{example with annotation of what's wrong}

## Rubric
| Dimension | 5 | 3 | 1 |
|-----------|---|---|---|
| Accuracy | ... | ... | ... |
```

---

## Instruction Quality Checklist

Before finalizing any prompt or instruction:

```markdown
### Clarity
- [ ] No ambiguous pronouns (what does "it" refer to?)
- [ ] No implicit assumptions (what does the agent need to know?)
- [ ] Action verbs are specific (not "handle" — "validate", "transform", "reject")

### Reliability
- [ ] Works on first read (no re-reading needed)
- [ ] Edge cases addressed (what if input is empty? malformed?)
- [ ] Output format is explicit (JSON? markdown? table?)

### Boundaries
- [ ] What the agent SHOULD do is clear
- [ ] What the agent should NOT do is explicit
- [ ] Escalation path defined (when to ask human)

### Testability
- [ ] Success criteria defined
- [ ] Can be evaluated by agentic-eval
- [ ] Failure modes documented
```

---

## L2 Auto-Refinement

The prompt-engineer skill supports automatic instruction improvement
based on evidence (L2 self-improvement).

### Refinement Loop

```
1. Collect evaluation data from agentic-eval
2. Identify patterns in failures/low-scores
3. Hypothesize instruction improvement
4. Generate A/B variants
5. Evaluate variants against same criteria
6. Propose winning variant for human approval
```

### Refinement Rules

- Never auto-apply refinements — always propose to human
- Track all variants with version history
- Minimum 3 evaluations before proposing a change
- Refinements that touch governance require full pipeline

---

## Anti-Slop Guidelines

When writing prompts, apply the Trust Contract's anti-slop commitment:

| Slop Pattern | Fix |
|-------------|-----|
| "Be thorough and comprehensive" | Specify exactly what to check |
| "Consider all aspects" | List the specific aspects |
| "Ensure high quality" | Define the quality criteria |
| "Handle edge cases" | Name the specific edge cases |
| "Follow best practices" | State which practices and why |

---

## L2 evidence consumption (P6-002)

Delivery runs can leave **machine-readable evidence** for L2 refinement without merging that text into evaluator/reviewer threads (D21 isolation).

**Store:** append-only `.azoth/memory/l2-refinement-evidence.jsonl` (one JSON object per line).

**Schema:** `pipelines/l2-evidence-record.schema.yaml` — validated by `scripts/l2_evidence_validate.py`.

**Write path:** only `scripts/l2_evidence_append.py` may append. It requires an **approved**, unexpired `.azoth/scope-gate.json` whose `session_id` matches `--session-id` and the record’s `session_id`. If `delivery_pipeline` is `governed` **or** `target_layer` is `M1`, it also requires an approved, unexpired `.azoth/pipeline-gate.json` with the same `session_id`. Do **not** use the Edit/Write tool directly on the JSONL file.

**Orchestrator flow:** after evaluator/reviewer (or human `/eval`), optionally build one record (see `skills/agentic-eval/SKILL.md` — L2 mapping), run `python3 scripts/l2_evidence_append.py --session-id <scope session_id>` with the JSON on stdin, then spawn **prompt-engineer** in a **fresh** context with `Read` targets: last *K* lines of the JSONL filtered by `session_id`, plus the instruction surfaces in `target_surfaces`.

**Human gate:** refinements to `skills/` or `agents/` remain **ask_first** / propose-only — never auto-apply.

---

## Integration

### With Skills
- Every SKILL.md follows prompt-engineer structure patterns
- New skills should pass the instruction quality checklist

### With Agents
- Agent `.agent.md` files use RCTF pattern
- Posture tier definitions follow structured format

### With Pipeline
- Stage prompts follow chain-of-thought gate pattern
- Gate evaluation criteria use rubric-based format

### With Self-Improve
- L2 auto-refinement is the active partnership between
  prompt-engineer and self-improve skills
