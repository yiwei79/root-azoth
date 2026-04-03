# Azoth Governance

> Rules governing memory, promotion, drift detection, and human-in-the-loop gates.
> This file is Layer 0 (Molecule) — immutable without human approval.

---

## 1. Memory Governance

### Append-Only Rule (M3: Episodic)

Episodes in `.azoth/memory/episodes.jsonl` are **append-only**.

- Episodes are NEVER edited after creation
- Episodes are NEVER deleted
- Each episode is a single JSON line with a timestamp
- Episodes decay naturally — unreinforced episodes lose relevance over time but are never removed

### Episode Schema

```json
{
  "id": "uuid",
  "timestamp": "ISO-8601",
  "session_id": "uuid",
  "type": "success | failure | decision | pattern | observation",
  "goal": "what the session was trying to achieve",
  "summary": "what happened",
  "lessons": ["what was learned"],
  "tags": ["relevant-tags"],
  "reinforcement_count": 0
}
```

### Pattern Governance (M2: Semantic)

Patterns in `.azoth/memory/patterns.yaml` are **human-approved**.

- Patterns are promoted from M3 via the Promotion Rubric
- Promotion requires: evidence from 2+ episodes, human approval
- Patterns can be updated (with human approval) but not silently modified
- Each pattern tracks its source episodes for auditability

### Pattern Schema

```yaml
- id: uuid
  name: descriptive-name
  description: what this pattern captures
  source_episodes: [episode-id-1, episode-id-2]
  promoted_date: ISO-8601
  promoted_by: human
  status: active | deprecated
  content: |
    The actual pattern content
```

### Procedural Governance (M1: Kernel/Skills/Agents)

M1 content lives in `kernel/`, `skills/`, and `agents/`. Changes follow
the full governance process:

- Proposed via Promotion Rubric (kernel/PROMOTION_RUBRIC.md)
- Reviewed through governance pipeline
- Human-approved before merge
- Validated by drift detection after merge

---

## 2. Human-in-the-Loop Gates

### Gate Types (D24)

Every pipeline gate declares its type. The type determines who approves.

| Type | Approver | When Required |
|------|----------|---------------|
| `human` | Project owner | Kernel changes, governance, design approval, final delivery |
| `agent` | Designated agent (architect, evaluator) | Plan quality, test coverage, auto-test pass |

### Mandatory Human Gates

These actions **always** require explicit human approval, regardless of
pipeline or context:

1. **Kernel modifications** — any change to files in `kernel/`
2. **Governance changes** — any change to governance rules or gate definitions
3. **M2 → M1 promotion** — promoting a pattern to procedural knowledge
4. **Dependency additions** — adding new external dependencies
5. **Pipeline self-modification** — changing pipeline definitions or gate types
6. **Design approval** — architect's design brief before implementation
7. **Final delivery** — completed work before considering it done

### Agent Gates

These can be approved by a designated agent:

1. **Plan quality** — architect reviews planner output
2. **Test coverage** — evaluator scores test completeness
3. **Auto-test pass** — CI/test runner confirms all tests green
4. **Governance disposition** — architect dispositions governance findings

### Gate Violation Response

If an action requiring a human gate is attempted without approval:

1. Block the action
2. Log the violation in session telemetry
3. Present the action to human for explicit approval or rejection
4. Do not retry until human signal is received

---

## 3. Promotion Flow

Knowledge flows upward through the memory layers:

```
M3 (Episodic) → M2 (Semantic) → M1 (Procedural)
  append-only     human-approved    governance-gated
```

### M3 → M2 Promotion

**Trigger**: Pattern detected across 2+ episodes.

**Process**:
1. Agent identifies recurring pattern in M3 episodes
2. Agent proposes promotion with evidence (source episodes)
3. Human reviews proposal
4. Human approves → pattern written to M2
5. Human rejects → episode tagged as "promotion-rejected" (not deleted)

### M2 → M1 Promotion

**Trigger**: Pattern proven durable across 3+ sessions.

**Process**:
1. Agent identifies M2 pattern ready for procedural encoding
2. Agent proposes specific implementation (skill, agent instruction, or kernel change)
3. Promotion Rubric applied (kernel/PROMOTION_RUBRIC.md)
4. Governance review (if scope includes kernel or agents)
5. Human approves → implemented in appropriate location
6. Drift detection validates the change

### Promotion Anti-Patterns

- **Rushing**: Promoting after a single episode — wait for reinforcement
- **Skip-review**: Auto-promoting without human signal — never allowed
- **Over-abstracting**: Promoting a pattern that's too specific to one context
- **Stale promotion**: Promoting a pattern that was relevant months ago but may no longer apply — re-validate first

---

## 4. Drift Detection Contract

### What Is Monitored

| File/Directory | Check Frequency | Drift Response |
|----------------|-----------------|----------------|
| `kernel/*` | Session start + end | HALT on any change |
| `azoth.yaml` | Session start | Warn on unexpected change |
| `.claude/settings.json` | Session start | Warn on deny-rule changes |
| `.azoth/memory/patterns.yaml` | Before promotion | Verify no silent edits |

### Integrity Check Mechanism

```bash
# Generate checksums for kernel files
sha256sum kernel/*.md > .azoth/kernel-checksums.sha256

# Verify at session start
sha256sum -c .azoth/kernel-checksums.sha256
```

### Drift Severity Levels

| Level | Meaning | Response |
|-------|---------|----------|
| **NONE** | All checksums match | Proceed |
| **MINOR** | Non-kernel config changed | Log warning, continue with caution |
| **MAJOR** | Kernel file modified | HALT — human must review and approve |
| **CRITICAL** | Kernel file missing | HALT — do not operate without full kernel |

---

## 5. Proactive Agent Posture (D26)

Agents default to proactive-within-boundaries.

### Always-Do (No Permission Needed)

- Pre-action context mapping (explore before changing)
- Dependency pre-staging (fetch related files autonomously)
- Test discovery (find existing tests before writing new ones)
- Memory pattern surfacing ("This matches episode X")
- Checkpoint suggestions ("Approaching entropy ceiling")
- Adjacent issue identification ("Found 2 related issues nearby")

### Ask-First (Identify But Get Approval)

- Scope expansion ("Evidence suggests new sub-question")
- Agent capability routing ("This needs Context Architect, not just SWE")
- Refactoring opportunities ("This could be cleaner — want me to?")
- Cross-agent escalation ("Governance issue found — invoke reviewer?")

### Never-Auto (Always Require Human Signal)

- Kernel modifications
- Governance changes
- Dependency additions
- Pipeline self-modification
- Memory M2 → M1 promotion
- File deletion

---

## 6. Session Telemetry

Every agent action is logged for auditability.

### Telemetry Record Schema

```json
{
  "session_id": "uuid",
  "turn": 1,
  "agent": "builder",
  "action": "edit",
  "target": "src/main.py",
  "outcome": "success",
  "files_changed": 1,
  "entropy_delta": 0.1,
  "timestamp": "ISO-8601"
}
```

Stored in `.azoth/telemetry/session-log.jsonl` (gitignored).
Used by entropy guard for real-time monitoring and by HARDEN phase for
session summary generation.

---

## Governance Invariants

1. **Memory is append-only at M3** — no episode is ever edited or deleted
2. **Promotion requires human approval** — no auto-promotion at any layer
3. **Kernel is immutable** — changes only via full governance pipeline + human gate
4. **Gates are typed** — every gate declares `human` or `agent`, enforced by pipeline
5. **Drift is detected** — kernel integrity checked at every session boundary
6. **Violations are logged** — no silent failures, all governance events recorded
