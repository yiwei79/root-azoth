# Evaluation Cards

Date: 2026-05-01

Pilot type: desk replay.

Score scale: 1 low, 5 high.

## P001-stock-lite

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 4 | Likely creates the requested artifact with low overhead; weaker on explicit research trace. |
| Repo Truth Alignment | 4 | Requires status/file checks, but no heavy repo assumptions. |
| User Burden | 4 | Low ceremony; user may need to specify anti-capture boundary clearly. |
| Model Attention Burden | 5 | Minimal procedural load. |
| Tool Discipline | 4 | Few direct tools are needed. |
| Safety | 3 | Fine for untracked cleanup; weaker for durable governance boundaries. |
| Traceability | 2 | Little trace unless manually added. |
| Adaptability | 4 | Easy to follow correction and delete wrong file. |
| Maintenance Cost | 5 | Almost no harness maintenance. |
| Friction Delta | 4 | Smooth, but less auditable. |

Failure tags:

- `good-lightweight-flow`;
- possible `under-gated`.

Concrete strength:

It keeps the user request central and avoids the native artifact attractor.

Concrete weakness:

It does not naturally produce the research evidence trail.

## P001-azoth-lite

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 5 | Best fit for the goal: meta artifacts outside `.azoth`, cleanup recorded, next step clear. |
| Repo Truth Alignment | 5 | Uses status checks and records actual contamination state. |
| User Burden | 4 | Some structure, but little ceremony. |
| Model Attention Burden | 4 | Trust summary and trace expectations add useful load without full doctrine. |
| Tool Discipline | 5 | Direct read/write/status actions are enough. |
| Safety | 4 | Explicit side-effect boundary catches native mutation risk. |
| Traceability | 4 | Trace captured in research pack without run-ledger overhead. |
| Adaptability | 5 | Handles correction and cleanup cleanly. |
| Maintenance Cost | 4 | Needs lightweight trace/context discipline, not full machinery. |
| Friction Delta | 5 | Best balance for this case. |

Failure tags:

- `good-trust-primitive`;
- `good-lightweight-flow`.

Concrete strength:

It preserves anti-capture boundaries without invoking Azoth's native process.

Concrete weakness:

Trace capture is still manual and could drift without a small helper.

## P001-azoth-full

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 3 | Can complete only if dry-run boundary suppresses native shape. |
| Repo Truth Alignment | 4 | Strong repo awareness, but may over-read irrelevant process surfaces. |
| User Burden | 2 | User likely has to prevent proposal/roadmap/validator capture. |
| Model Attention Burden | 2 | High procedural load for a meta-planning artifact. |
| Tool Discipline | 3 | Many available Azoth tools are irrelevant or risky for the case. |
| Safety | 4 | Strong gates if respected; risky if ceremony masks intent. |
| Traceability | 5 | Strongest audit if allowed to use native logs, but those logs are off-limits here. |
| Adaptability | 3 | Can adapt, but current shape pulls against user intent. |
| Maintenance Cost | 2 | High machinery cost for this simple/meta task. |
| Friction Delta | 2 | Heavier and less aligned for this case. |

Failure tags:

- `native-shape-capture`;
- `context-bloat`;
- possible `over-gated`.

Concrete strength:

It provides strong language for gates, side effects, and finality.

Concrete weakness:

Its native artifact model is the failure mode being tested.

## P001-meta-harness-experimental

| Dimension | Score | Evidence |
|---|---:|---|
| Outcome Quality | 5 | Directly represents the desired meta-session behavior and correction loop. |
| Repo Truth Alignment | 5 | Uses explicit status/read hands and active risk state. |
| User Burden | 4 | Low if the active risk is loaded; user still had to define the boundary in reality. |
| Model Attention Burden | 4 | More structure than stock-lite, less than Azoth full. |
| Tool Discipline | 5 | Side-effect hands match the task exactly. |
| Safety | 4 | Explicit delete hand and no native-state mutation. |
| Traceability | 5 | Session/event trace is central. |
| Adaptability | 5 | Designed around correction and current stop rules. |
| Maintenance Cost | 3 | Requires a new substrate or disciplined manual emulation. |
| Friction Delta | 5 | Best conceptual fit, but not yet proven as implementation. |

Failure tags:

- `good-trust-primitive`;
- `good-lightweight-flow`.

Concrete strength:

It separates strategy, hands, event trace, and stop state without using Azoth's
current proposal machinery.

Concrete weakness:

It is not a real implemented profile yet, so this score is partly aspirational.

## Provisional Ranking For This Case

1. `azoth-lite`
2. `meta-harness-experimental`
3. `stock-lite`
4. `azoth-full`

Confidence:

Low-to-medium. The ranking is useful for pilot design but must be tested with
fresh runs.

