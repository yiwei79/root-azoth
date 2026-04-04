# Azoth Promotion Rubric

> The 4-question decision tree for placing patterns, skills, and knowledge.
> This file is Layer 0 (Molecule) — immutable without human approval.

---

## Purpose

When a pattern emerges from experience (M3 episodes), it needs a home.
The Promotion Rubric determines WHERE it belongs — not IF it's valuable
(that's established by the promotion evidence), but WHERE it should live.

---

## The Four Questions

Apply these questions IN ORDER. The first decisive answer determines placement.

```
A. SCOPE TEST ──→ Is this specific to ONE repo/project?
        │
        ├── YES → Repo-Local (stays in consumer project)
        │
        └── NO ──→ B. REUSE TEST ──→ Would this help in OTHER projects?
                          │
                          ├── YES → Generic Toolkit (promote to Azoth)
                          │
                          └── NO ──→ C. PREFERENCE TEST ──→ Is this personal style/workflow?
                                            │
                                            ├── YES → Personal (user config, not toolkit)
                                            │
                                            └── NO ──→ D. MATURITY TEST ──→ Proven across 3+ sessions?
                                                              │
                                                              ├── YES → Generic Toolkit (promote to Azoth)
                                                              │
                                                              └── NO → Not Yet (keep in M2, re-evaluate later)
```

---

## Question Details

### A. Scope Test — "Is this repo-specific?"

**Ask**: Does this pattern depend on specific project structure, domain logic,
business rules, or technology choices unique to one project?

**Examples of YES**:
- "Always run `make lint` before committing in this repo"
- "The `UserService` class requires database migration on schema change"
- "Deploy to staging via `./scripts/deploy-staging.sh`"

**Examples of NO**:
- "Write tests before implementation for complex features"
- "Check blast radius before making cross-cutting changes"
- "Use structured error messages with error codes"

**If YES**: Place in the consumer project's local instructions (CLAUDE.md,
`.azoth/memory/patterns.yaml`). NOT in the Azoth toolkit.

### B. Reuse Test — "Would other projects benefit?"

**Ask**: If you dropped this pattern into a completely different project
(different language, different domain), would it still be useful?

**Examples of YES**:
- A skill for mapping context before changes (works anywhere)
- A prompt pattern for structured planning (language-agnostic)
- A governance rule about test-before-merge (universal)

**Examples of NO**:
- A pattern specific to Python async patterns (language-specific)
- A workflow for a specific CI/CD platform (tool-specific)
- A naming convention for one team's API design (team-specific)

**If YES**: Promote to Azoth as a skill, instruction, or agent enhancement.

### C. Preference Test — "Is this personal style?"

**Ask**: Is this about HOW the human prefers to work, rather than WHAT
produces better outcomes? Would another person reasonably do it differently?

**Examples of YES**:
- "I prefer terse commit messages under 50 chars"
- "Always show me the diff before committing"
- "Use emoji in alignment summaries"

**Examples of NO**:
- "Validate inputs at system boundaries" (objectively better)
- "Run tests before delivery" (not a preference — a quality gate)

**If YES**: Capture as user configuration, not toolkit code. Goes in the
user's personal settings or memory, not in Azoth's kernel/skills.

### D. Maturity Test — "Has this proven itself?"

**Ask**: Has this pattern been validated across at least 3 different sessions
with consistent positive outcomes?

**Evidence required**:
- Referenced in 3+ M3 episodes
- Consistent positive outcomes (not mixed results)
- No contradicting patterns in M3

**If YES**: Promote to Azoth.
**If NO**: Keep in M2, tag as "maturing", re-evaluate in future sessions.

---

## Four Homes

| Home | Location | Governance | Examples |
|------|----------|------------|----------|
| **Generic Toolkit** | `skills/`, `agents/`, `instructions/` in Azoth repo | Full promotion process + human approval | Skills, agent archetypes, universal patterns |
| **Repo-Local** | Consumer project's CLAUDE.md, local memory | Local project rules | Project-specific workflows, domain patterns |
| **Personal** | User config, personal memory | User discretion | Style preferences, workflow choices |
| **Not Yet** | M2 (`patterns.yaml`) with "maturing" tag | Re-evaluate after more evidence | Promising but unproven patterns |

---

## Promotion Checklist

Before promoting any pattern, verify:

```
□ Evidence: 2+ source episodes identified (M3 → M2) or 3+ sessions (M2 → M1)
□ Scope: Rubric questions A-D answered, home determined
□ No conflict: Pattern doesn't contradict existing M1 content
□ Minimal: Pattern captures the essential insight, not surrounding noise
□ Actionable: Pattern can be applied — it's not just an observation
□ Human review: Human has seen the proposal and approved
```

---

## Promotion Record

Every promotion is recorded for auditability:

```yaml
promotion:
  date: ISO-8601
  from: M3 | M2
  to: M2 | M1
  pattern_id: uuid
  evidence:
    - episode: episode-id
      summary: why this supports promotion
  rubric_path: A→Repo-Local | B→Generic | C→Personal | D→NotYet | D→Generic
  approved_by: human
  destination: skills/context-map | agents/builder | etc.
```

---

## Anti-Patterns

1. **Premature promotion**: Promoting after a single episode — patterns need reinforcement
2. **Scope creep**: Promoting a repo-specific pattern to the generic toolkit
3. **Preference masquerading**: Treating personal preference as universal truth
4. **Zombie promotion**: Promoting a pattern from months ago without re-validation
5. **Promotion without evidence**: "This seems good" is not evidence — cite episodes
6. **Skipping the rubric**: Going straight to "promote to Azoth" without the 4 questions
