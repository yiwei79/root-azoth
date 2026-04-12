---
name: context-map
description: |
  Map blast radius and dependency graphs before multi-file or cross-cutting work; assess
  risk and pre-stage dependencies at the start of a pipeline stage or unfamiliar area.
---

# Context Map

Map blast radius before action. Understand what exists, what connects, and
what could break — before changing anything.

## Overview

Context mapping is the "look before you leap" discipline. Every change has
a blast radius: files that will be modified, files that depend on those files,
tests that cover them, and systems that consume them.

```
Goal → Identify targets → Map dependencies → Assess blast radius → Proceed or scope-down
```

## When to Use

- **Before any implementation stage** in a pipeline
- **Before cross-cutting changes** (rename, move, refactor)
- **When entering unfamiliar code** (new module, inherited project)
- **When entropy ceiling is a concern** (large changes need pre-mapping)

---

## The Context Map Process

### Step 1: Identify Direct Targets

What files will this change directly modify?

```
Target files:
- [ ] src/auth/handler.py (modify login flow)
- [ ] src/auth/middleware.py (update session check)
- [ ] tests/test_auth.py (update test cases)
```

### Step 2: Map Dependencies

What depends on the targets? What do the targets depend on?

```
Upstream (targets depend on):
- src/db/session.py (session store interface)
- src/config.py (auth settings)

Downstream (depends on targets):
- src/api/routes.py (imports auth handler)
- src/api/middleware_chain.py (registers middleware)
- docs/api.md (documents auth flow)
```

### Step 3: Assess Blast Radius

```
Blast Radius Assessment:
  Direct files:    3
  Upstream deps:   2
  Downstream deps: 3
  Total affected:  8
  Entropy zone:    YELLOW (5-10 files)
  
  Risk factors:
  - [ ] Touches public API? → Yes (auth endpoint)
  - [ ] Touches tests? → Yes (needs update)
  - [ ] Touches config? → No
  - [ ] Cross-module? → Yes (auth → api)
  
  Recommendation: Checkpoint before proceeding
```

### Step 4: Scope Decision

Based on the blast radius:


| Blast Radius        | Action                           |
| ------------------- | -------------------------------- |
| GREEN (< 5 files)   | Proceed directly                 |
| YELLOW (5-10 files) | Checkpoint, then proceed         |
| RED (> 10 files)    | Scope down or get human approval |


---

## Context Map Template

Use this template at the start of any implementation stage:

```markdown
## Context Map — {goal}

### Targets
- {file}: {what changes}

### Dependencies
- Upstream: {what targets depend on}
- Downstream: {what depends on targets}

### Blast Radius
- Files affected: {N}
- Entropy zone: {GREEN | YELLOW | RED}
- Risk factors: {list}

### Existing Tests
- {test file}: covers {what}

### Decision
- {proceed | checkpoint-first | scope-down | human-approval}
```

---

## Proactive Posture

This skill operates at **always-do** tier (D26): agents should map context
before making changes without needing permission. It's information gathering,
not action taking.

---

## Best Practices


| Practice                | Rationale                                                         |
| ----------------------- | ----------------------------------------------------------------- |
| **Map before changing** | Prevents surprise cascading failures                              |
| **Include tests**       | Tests are dependencies — if they break, the change isn't done     |
| **Check git blame**     | Recent changes to targets suggest active development — coordinate |
| **Update the map**      | If scope changes during implementation, re-map                    |
| **Share the map**       | Include in alignment summary so human sees the blast radius       |


