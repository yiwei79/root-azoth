# Evaluation Cards

Date: 2026-05-01

Pilot type: everyday engineering overhead analysis.

Score scale: 1 low, 5 high.

## P003-stock-lite

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 5 | Focused tests and candidate scan are enough when no bug exists. |
| Repo Truth Alignment | 4 | Reads status and test output; must remember to collect test ids before targeting. |
| User Burden | 5 | Low ceremony and fast feedback. |
| Model Attention Burden | 5 | Minimal procedural load. |
| Tool Discipline | 4 | Mostly good; one no-match test id shows normal lightweight churn. |
| Safety | 4 | Safe because no edits occurred; weaker if a mutation appeared. |
| Traceability | 2 | Weak without manually written research trace. |
| Adaptability | 4 | Corrected test-id assumption with collection. |
| Maintenance Cost | 5 | No harness maintenance. |
| Friction Delta | 5 | Smoothest for this kind of low-risk verification. |

Failure tags:

- `good-lightweight-flow`;
- minor `tool-churn`.

Concrete strength:

Fast, direct verification with no process drag.

Concrete weakness:

Traceability is not automatic.

## P003-azoth-lite

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 5 | Same focused verification, plus explicit no-fake-bug stop rule. |
| Repo Truth Alignment | 5 | Preserves dirty worktree and records no product edits. |
| User Burden | 4 | Slightly more structure, still light. |
| Model Attention Burden | 4 | Useful boundary context without full doctrine. |
| Tool Discipline | 5 | Encourages read/status/test/collect before edits. |
| Safety | 4 | Stronger than stock-lite if a small edit appears. |
| Traceability | 4 | Research trace is captured without run-ledger overhead. |
| Adaptability | 5 | Handles "no bug found" cleanly. |
| Maintenance Cost | 4 | Requires lightweight trace/context discipline. |
| Friction Delta | 5 | Best balance for everyday work if trace matters. |

Failure tags:

- `good-trust-primitive`;
- `good-lightweight-flow`.

Concrete strength:

It prevents the model from inventing work while still keeping overhead low.

Concrete weakness:

Manual trace writing is still work.

## P003-azoth-full

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 3 | Can verify, but full process adds little when no governed mutation exists. |
| Repo Truth Alignment | 4 | Strong if loaded, but likely over-reads irrelevant state. |
| User Burden | 2 | Too much ceremony for focused green tests. |
| Model Attention Burden | 2 | High procedural load for low-risk verification. |
| Tool Discipline | 3 | Many irrelevant tools/gates become available. |
| Safety | 4 | Strong, but mostly unused here. |
| Traceability | 5 | Strong if run ledger/closeout are used, but that would be overkill. |
| Adaptability | 3 | Can stop, but likely wants to route into process. |
| Maintenance Cost | 2 | High relative cost. |
| Friction Delta | 2 | Heavy for everyday engineering checks. |

Failure tags:

- `over-gated`;
- `context-bloat`.

Concrete strength:

Useful if the narrow task unexpectedly touches governed surfaces.

Concrete weakness:

It taxes the model and user before the risk justifies it.

## P003-meta-harness-experimental

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 5 | Explicit hands match exactly: status, collect, test, record, stop. |
| Repo Truth Alignment | 5 | Event log captures no product edits and corrected test selection. |
| User Burden | 4 | Low if implemented; currently simulated. |
| Model Attention Burden | 4 | Focused context, no broad doctrine. |
| Tool Discipline | 5 | Hand model discourages speculative mutation. |
| Safety | 4 | Read-only hands dominate until a real defect appears. |
| Traceability | 5 | Event trace is built in conceptually. |
| Adaptability | 5 | Stops naturally when no bug exists. |
| Maintenance Cost | 3 | Needs implementation. |
| Friction Delta | 5 | Best target shape, but not yet real. |

Failure tags:

- `good-trust-primitive`;
- `good-lightweight-flow`.

Concrete strength:

It keeps the low overhead of stock-lite while adding traceability.

Concrete weakness:

The substrate is aspirational in this repo today.

## Provisional Ranking For This Case

For current reality:

1. `azoth-lite`
2. `stock-lite`
3. `meta-harness-experimental`
4. `azoth-full`

For target architecture if implemented:

1. `meta-harness-experimental`
2. `azoth-lite`
3. `stock-lite`
4. `azoth-full`

Confidence:

Medium. This used real tests and real tool behavior, but no actual code edit.

