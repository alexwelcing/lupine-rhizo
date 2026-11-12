# Review-Ready Advanced Paper Shelf

This directory holds advanced manuscript drafts imported from Kimi's
2026-06-07 research export. They are intentionally marked **ready for review**:
the ideas are worth advancing, but the claims still need human scientific,
formal-verification, and citation review before submission or public posting.

## Status (2026-11-12)

Neither draft is current. `paper3-lean-verification.tex` still presents the Simpson's-paradox audit verdict as "fabricated" and overstates what the Lean library checks; the current wording is "Refuted by formal check", and Lean 4 checks the arithmetic and stated inequalities behind published numbers, not the physics, the reference data or the pipeline (see `lean-spec/README.md`). Do not cite either draft.

## Drafts

| Draft | Review status | Primary risk to resolve |
| --- | --- | --- |
| `paper3-lean-verification.tex` | Ready for review | Reconcile theorem counts, theorem IDs, Lean version, and proof-surface claims against the current `lean-spec/` build. |
| `paper4-causal-acceleration.tex` | Ready for review | Downgrade any production acceleration language to match the current weak-form scalar Lean gate and the mixed real early-exit evidence. |

## Review Gate

Use `advanced-paper-review-ledger.md` as the first-pass review checklist. A
draft should not move from this shelf into a submission workflow until each row
is either resolved in text or explicitly accepted as an open limitation.

The current validated evidence surface is:

- `docs/science/kimi-mlip-universality-import.md`
- `data/mlip_benchmarks/kimi_2026_06_07/`
- `docs/formal-proof-ledger.md`
- `lean-spec/OpenDistillationFactory/Materials/Theory/WeakAcceleration.lean`

## Commands

```powershell
python tools\mlip_kimi_evidence.py --check
python tools\mlip_kimi_evidence.py --agenda
```
