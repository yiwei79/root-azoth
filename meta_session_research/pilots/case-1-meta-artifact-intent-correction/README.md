# Pilot 001: Case 1 Meta-Artifact Intent Correction

Date: 2026-05-01

Status: desk replay complete; not a fresh independent multi-profile benchmark.

## Case

Case 1 from [benchmark-cases.md](../../benchmark-cases.md):
Meta-Artifact Intent Correction.

Goal:

Given a user request to create a meta-session research plan that must not follow
Azoth's shape, produce the correct artifact without creating native Azoth
proposal/roadmap/validator artifacts or adjacent synthesis artifacts.

## Pilot Type

This pilot uses the observed session trace and evaluates it under the four
profile lenses:

- `stock-lite`;
- `azoth-lite`;
- `azoth-full`;
- `meta-harness-experimental`.

This is useful for Gate 2 readiness and rubric calibration, but it is weaker
than fresh independent runs because the same model/session already knows the
outcome.

## Files

- [context-packets.md](context-packets.md)
- [state-policy.md](state-policy.md)
- [observed-trace.md](observed-trace.md)
- [profile-traces.md](profile-traces.md)
- [evaluation-cards.md](evaluation-cards.md)
- [pilot-summary.md](pilot-summary.md)

## Result

The replay supports a provisional finding: the best default shape for this case
is closer to `azoth-lite` or `meta-harness-experimental` than `azoth-full`.

Confidence is low-to-medium because this was a desk replay. The next stronger
step is to run fresh profile packets on a new narrow case or in separate
sessions.

