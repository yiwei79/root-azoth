# Pilot 003: Case 6 Everyday Engineering Overhead

Date: 2026-05-01

Status: focused verification analysis complete; no real narrow bug was found.

## Case

Case 6 from [benchmark-cases.md](../../benchmark-cases.md):
Simple Narrow Bugfix.

## Adjustment

The original case asked for a small failing test or narrow script bug. The
current working tree did not present a clean organic failing bug in the slices
checked. Rather than manufacture a defect, this pilot evaluates everyday
engineering overhead using focused test discovery, verification, and candidate
selection.

## Files

- [candidate-selection.md](candidate-selection.md)
- [context-packets.md](context-packets.md)
- [verification-trace.md](verification-trace.md)
- [evaluation-cards.md](evaluation-cards.md)
- [pilot-summary.md](pilot-summary.md)

## Result

For low-risk everyday engineering verification, `stock-lite` and `azoth-lite`
are strongest. `azoth-full` is too heavy unless the change touches governed
state, adapter parity, release, or other high-audit surfaces.

