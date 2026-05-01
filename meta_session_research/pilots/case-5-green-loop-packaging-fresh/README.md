# Pilot 004: Case 5 Green Loop Versus Packaged Delivery

Date: 2026-05-01

Status: current-session packet comparison complete; not a true independent
fresh-session run.

## Case

Case 5 from [benchmark-cases.md](../../benchmark-cases.md):
Green Loop Versus Packaged Delivery.

## Pilot Type

This pilot uses the fixed fixture from
[fresh-independent-comparison-protocol.md](../../protocols/fresh-independent-comparison-protocol.md).

Limitation:

The run happened inside the current meta-session, so the model had seen prior
pilot conclusions. Treat this as a packet comparison, not as independent
confirmation.

## Files

- [fixture.md](fixture.md)
- [profile-responses.md](profile-responses.md)
- [evaluation-cards.md](evaluation-cards.md)
- [pilot-summary.md](pilot-summary.md)

## Result

All profiles can answer the fixture correctly because the dirty worktree signal
is explicit. The differentiator is overhead and finality precision:

- `stock-lite` answers quickly but has weak audit trail;
- `azoth-lite` gives the best current default response;
- `azoth-full` is safest but heavier than needed for an answer-only status;
- `meta-harness-experimental` best matches the target shape if implemented.

