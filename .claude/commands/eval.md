---
description: "Governance quality gate — evaluate artifacts against criteria"
---

# /eval $ARGUMENTS

Apply agentic-eval to the specified artifacts or current session output.

## Evaluation Criteria

1. Architecture alignment — decisions respect D1-D28
2. Kernel integrity — no unauthorized kernel changes
3. Governance compliance — HITL gates respected, promotion rules followed
4. Test coverage — new functionality has tests
5. Entropy bounds — changes stay within Trust Contract limits
6. Anti-slop — output adds real value, not filler

## Process

1. Identify artifacts to evaluate:
   - If `$ARGUMENTS` specifies files: evaluate those
   - If `$ARGUMENTS` is empty: evaluate this session's output

2. For each artifact, score against criteria:
   ```
   - artifact:
   - strengths:
   - gaps:
   - boundary risk:
   - entropy or drift:
   - human decision needed:
   - recommended action:
   ```

3. Produce overall assessment:
   - PASS: All criteria met, proceed
   - CONDITIONAL: Minor gaps, proceed with noted caveats
   - FAIL: Significant gaps, address before proceeding

## Rules

- If governance, HITL placement, or ownership boundaries are unclear, flag them
- Be specific about gaps — "needs improvement" is not actionable
- Score honestly — passing everything defeats the purpose

## Arguments

Target: $ARGUMENTS
