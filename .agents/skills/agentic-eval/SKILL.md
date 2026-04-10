---
name: agentic-eval
description: |
  Evaluate and refine agent outputs using rubrics, reflection loops, and evaluator-optimizer
  pipelines (code, reports, analysis). Not for one-off formatting or trivial copy edits.
---

# Agentic Evaluation Patterns

Patterns for self-improvement through iterative evaluation and refinement.

## Overview

Evaluation patterns enable agents to assess and improve their own outputs,
moving beyond single-shot generation to iterative refinement loops.

```
Generate → Evaluate → Critique → Refine → Output
    ↑                              │
    └──────────────────────────────┘
```

## When to Use

- **Quality-critical generation**: Code, reports, analysis requiring high accuracy
- **Tasks with clear evaluation criteria**: Defined success metrics exist
- **Content requiring specific standards**: Style guides, compliance, formatting
- **Pipeline gate enforcement**: Validating stage outputs before proceeding

---

## L2 evidence records (P6-002)

When a governed session should feed **prompt-engineer** later, normalize evaluator/reviewer output into one JSON object per `pipelines/l2-evidence-record.schema.yaml` and append via `scripts/l2_evidence_append.py` (never raw Write to the JSONL path).

| Source | `evidence_kind` | `payload` hints |
|--------|-----------------|-----------------|
| Evaluator rubric / numeric score | `eval_summary` | `overall_score`, `threshold`, per-dimension scores, `rubric_refs` |
| Reviewer disposition + findings | `reviewer_gate` | `disposition`, `findings` (list), `severity` |
| M3 episode pointer | `episode_ref` | `episode_id`, `tags` |
| Human `/eval` structured output | `manual_eval` | criteria scores, `recommended_action` |

Set `source_pipeline` and `source_stage_id` to the active pipeline and stage; set `source_agent` to the archetype that produced the evidence; set `target_surfaces` to the `skills/` / `agents/` / command paths the refinement should consider.

## Operational Use

- **Pipeline gates:** score stage outputs against the design brief, tests, governance rules,
  and entropy before the next stage proceeds.
- **Session closeout:** review artifacts against session goals and capture durable gaps,
  risks, or evidence for follow-up.

---

## Pattern 1: Basic Reflection

Agent evaluates and improves its own output through self-critique.

```text
FUNCTION reflect_and_refine(task, criteria, max_iterations = 3):
    output = GENERATE(task)

    REPEAT up to max_iterations:
        critique = EVALUATE(output against criteria, return structured JSON)
        IF every criterion passes:
            RETURN output

        failed_feedback = COLLECT feedback for failing criteria
        output = REVISE(output to address failed_feedback)

    RETURN output
```

**Key insight**: Use structured JSON output for reliable parsing of critique results.

---

## Pattern 2: Evaluator-Optimizer

Separate generation and evaluation into distinct components.

```text
COMPONENT EvaluatorOptimizer:
    threshold = 0.85

    GENERATE(task):
        RETURN candidate output

    EVALUATE(output, task):
        RETURN structured scores:
            overall_score
            dimensions:
                accuracy
                clarity
                completeness

    OPTIMIZE(output, feedback):
        RETURN revised output

    RUN(task, max_iterations = 3):
        output = GENERATE(task)
        REPEAT up to max_iterations:
            evaluation = EVALUATE(output, task)
            IF evaluation.overall_score >= threshold:
                STOP
            output = OPTIMIZE(output, evaluation)
        RETURN output
```

---

## Pattern 3: Code-Specific Reflection

Test-driven refinement loop for code generation.

```text
COMPONENT CodeReflector:
    REFLECT_AND_FIX(spec, max_iterations = 3):
        code = GENERATE code for spec
        tests = GENERATE tests for spec and current code

        REPEAT up to max_iterations:
            result = RUN tests
            IF result.success:
                RETURN code
            code = REVISE(code using failing test output)

        RETURN code
```

---

## Evaluation Strategies

### Outcome-Based

Evaluate whether output achieves the expected result.

```text
FUNCTION evaluate_outcome(task, output, expected):
    ASK judge whether output satisfies the expected result for the task
    RETURN outcome assessment
```

### LLM-as-Judge

Use LLM to compare and rank outputs.

```text
FUNCTION llm_judge(output_a, output_b, criteria):
    ASK judge to compare both outputs against criteria
    RETURN winner plus reasoning
```

### Rubric-Based

Score outputs against weighted dimensions.

```text
RUBRIC:
    accuracy: weight 0.4
    clarity: weight 0.3
    completeness: weight 0.3

FUNCTION evaluate_with_rubric(output, rubric):
    scores = ASK judge for a 1-5 score on each rubric dimension
    weighted_total = SUM(scores[dimension] * rubric[dimension].weight for each dimension)
    RETURN weighted_total / 5
```

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Clear criteria** | Define specific, measurable evaluation criteria upfront |
| **Iteration limits** | Set max iterations (3-5) to prevent infinite loops |
| **Convergence check** | Stop if output score isn't improving between iterations |
| **Log history** | Keep full trajectory for debugging and analysis |
| **Structured output** | Use JSON for reliable parsing of evaluation results |

---

## Quick Start Checklist

```markdown
### Setup
- [ ] Define evaluation criteria/rubric
- [ ] Set score threshold for "good enough" (default **0.85**, aligned with evaluator agent)
- [ ] Configure max iterations (default: 3)

### Implementation
- [ ] Implement generate() function
- [ ] Implement evaluate() function with structured output
- [ ] Implement optimize() function
- [ ] Wire up the refinement loop

### Safety
- [ ] Add convergence detection
- [ ] Log all iterations for debugging
- [ ] Handle evaluation parse failures gracefully
```
