# Decision Readiness Audit

Date: 2026-05-01

Profile: `azoth-lite`

## Question

Is the research pack ready to support a final comprehensive analysis and
conclusion about Azoth's future harness shape?

## Short Answer

Yes, for a research conclusion.

No, for implementation planning.

The evidence is now strong enough to conclude the desired operating shape at a
strategic level. It is not yet strong enough to create Azoth-native migration
tasks, validators, command changes, or implementation branches.

## Evidence Base Reviewed

External evidence:

- model/harness guidance from OpenAI, Anthropic, Browser Use, and HumanLayer;
- trace-first eval and context-engineering guidance;
- agent skills and managed-agent architecture guidance.

Internal evidence:

- Azoth cartography;
- friction diary;
- Decision Memo 001;
- Skeptic Review 001;
- `azoth-lite` runtime-surface v0;
- fresh Case 5 grading;
- fresh Case 7 grading.

Pilot evidence:

- Case 1: meta-artifact intent correction;
- Case 3: hydration side-effect boundary;
- Case 5: green loop versus packaged delivery;
- Case 6: everyday engineering overhead;
- Case 7: governed packaging.

## What Is Supported

### 1. A Single Full-Harness Default Is Not Justified

Case 1 and Case 6 both show that full Azoth is too much for ordinary meta work,
low-risk verification, and tasks where the main risk is process capture or
overhead.

Supported conclusion:

Full Azoth should not be the universal default.

### 2. No-Harness Or Stock-Lite Alone Is Not Enough

Case 3, Case 5, and Case 7 show that finality, packaging, and governed-state
mutation need explicit boundaries. Stock-lite can reason well from explicit
fixtures, but it lacks durable gate mechanics and reusable escalation rules.

Supported conclusion:

The future should not be near-stock only.

### 3. `azoth-lite` Is The Best Current Default Candidate

`azoth-lite` repeatedly preserved the valuable parts:

- side-effect classification;
- dirty-worktree awareness;
- no fake finality;
- explicit stop states;
- lightweight traceability;
- escalation when governed state appears.

Supported conclusion:

`azoth-lite` is the right default posture to design toward.

### 4. `azoth-full` Is Still Necessary

Case 7 gives `azoth-full` a fair high-audit packaging case, and it wins or ties.
Its extra vocabulary around governed gates, final delivery, run evidence, and
artifact disposition is useful when the task is actually high-audit.

Supported conclusion:

`azoth-full` should remain available as governed mode.

### 5. `meta-harness-experimental` Is The Long-Term Shape, Not The Current Default

The brain/hands/session/event/permissioned-effects model repeatedly scores well,
but it is not implemented. It should inform design, not be treated as an
available runtime.

Supported conclusion:

Use `meta-harness-experimental` as the architectural target.

## What Remains Unproven

1. A real narrow code edit with a failing test has not been compared.
2. Tool-enabled isolated-worktree packaging has not been run.
3. `azoth-lite` is still a manual runbook, not a reusable implementation.
4. User burden has been estimated more than measured.
5. The transition cost from current Azoth to a profile split is unknown.

## Decision Readiness

Ready:

- final comprehensive research conclusion;
- recommendation of target operating model;
- clear statement of what to preserve, shrink, defer, and test next.

Not ready:

- Azoth-native migration planning;
- validators;
- command changes;
- roadmap tasks;
- implementation.

## Audit Verdict

Proceed to final comprehensive analysis and conclusion.

The conclusion should be explicit that the strategic answer is ready, while
implementation remains gated by future approval and validation.

