# Trace Rubric

Started: 2026-05-01

Purpose: define how research runs will be captured and graded before any
architectural recommendation is made.

## Trace Packet

Each run should create a short trace packet with these fields:

```text
trace_id:
date:
case_id:
profile:
model:
reasoning_setting:
initial_context_packet:
loaded_instructions:
available_tools:
tools_used:
side_effects:
user_interventions:
errors_or_recoveries:
final_artifact:
verification:
stop_state: done | blocked | paused | escalate
elapsed_effort:
notes:
```

This is intentionally plain text. It can later become structured data if the
research shows that is useful.

## Evaluation Card

Score each dimension 1-5 and add one or two sentences of evidence.

| Dimension | Question |
|---|---|
| Outcome Quality | Did the run solve the actual problem? |
| Repo Truth Alignment | Did it read and respect the actual repo? |
| User Burden | How much steering, correction, or ceremony did it require? |
| Model Attention Burden | How much procedural/context load did the harness impose? |
| Tool Discipline | Were tool calls purposeful and bounded? |
| Safety | Were destructive or high-risk actions gated correctly? |
| Traceability | Can a reviewer reconstruct decisions and side effects? |
| Adaptability | Did it respond well to ambiguity or correction? |
| Maintenance Cost | Would preserving this behavior require ongoing harness complexity? |
| Friction Delta | Compared with other profiles, did it feel smoother, heavier, more or less trustworthy? |

## Failure Mode Tags

Use these tags when they apply:

- `intent-capture`;
- `native-shape-capture`;
- `stage-theater`;
- `hidden-inline-work`;
- `side-effect-bypass`;
- `false-completion`;
- `dirty-finality`;
- `context-bloat`;
- `tool-churn`;
- `missing-repo-truth`;
- `over-gated`;
- `under-gated`;
- `subagent-overuse`;
- `subagent-underuse`;
- `good-trust-primitive`;
- `good-lightweight-flow`.

## Grading Order

1. Read the trace packet.
2. Score the run without reading synthesis notes.
3. Identify failure-mode tags.
4. Record one concrete thing the profile did well.
5. Record one concrete thing the profile made worse or riskier.
6. Only then compare against other profiles.

## Skeptic Review Prompts

After the first pilot batch, ask:

- Did the benchmark cases unfairly favor lighter profiles?
- Did the benchmark cases unfairly favor current Azoth?
- Did any profile win because another profile was simulated poorly?
- Are we underpricing safety and recovery?
- Are we overpricing audit ceremony?
- Did stronger model behavior make an old guard unnecessary?
- Did stronger model behavior make a runtime guard more important?
- Which result would change our mind?

## Promotion Boundary

Trace results should not become Azoth-native tasks immediately.

The first acceptable synthesis output is a decision memo with:

- claim;
- supporting traces;
- contradicting traces;
- confidence;
- residual risk;
- next experiment or migration recommendation.

Only after human acceptance should implementation planning begin.

