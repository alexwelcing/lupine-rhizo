# The Formalization Ladder — making proof part of the loop

> Status: design note, 2026-07-02. Owner: research loop. Companion to
> `docs/plans/y-matrix-confirmatory-results-2026-07-01.md` (process note) and
> the lean-spec Theory layer.

## The gap this closes

Today's generated theorems are **receipts**: decidable comparisons of two
constants computed in Python (`theorem ... : 170 ≤ 250 := by decide`). The
kernel certifies the final inequality; the meaning (what was measured, how the
median was taken, which null was used) lives in docstrings and in unverified
Python. The modules are generated after the science and sit outside the lake
build. Formalization is a stamp at the end of the loop, not a load-bearing
part of it.

## The ladder

**L0 — receipt theorems (current).** Scalar facts, post-hoc, outside CI.
Value: tamper-evidence for endpoints. Limit: nothing composes; analysis
untrusted.

**L1 — the corpus builds.** Generated evidence modules are part of the
lean-spec lake build and CI. Every commit re-verifies every standing claim;
a broken or stale module fails the build instead of rotting silently.
(Closes audit finding "evidence-derived modules outside build graph".)

**L2 — evidence as data, analysis in the kernel.** A typed
`Lupine.Evidence.Cell` structure (material, model, family, property,
predicted, reference — integer-scaled); the bound dataset embedded as Lean
terms by the generator; and the summary statistics *recomputed inside Lean*:
medians, ratios, per-family counts proven about the embedded dataset via
`decide`/`native_decide`. Python becomes a proposer; the kernel checks the
computation, not just the endpoint. The Python and Lean numbers must agree or
the module fails to build — a machine-checked replication of the analysis.

**L3 — theory consumes evidence.** The Theory layer's objects take L2 data as
witnesses: softening as a typed bias/variance decomposition (Round 2's
finding becomes a term, not a paragraph); non-transfer facts as `Prop`s;
the correction routing table ("gearbox") as a structure whose well-formedness
requires an improvement witness for every routed gear and a non-transfer
witness for every interlock. Routing decisions become type-checkable.

## Typed claim-shapes as registration

Thresholded pass/kill registration is retired for exploratory work (process
note, 2026-07-02). Its replacement at L2/L3: before an experiment runs, define
the **claim-shape** — the Lean type of the fact the experiment could
establish. The experiment then either produces a witness or does not. This
keeps registration's honesty (the shape is fixed before the data) without its
theater (no invented numeric thresholds); and reserved threshold registration
remains only for interested-party claims (operator uplift) and
publication-bound claims.

## Non-goals (for now)

- Proving physics (DFT correctness, BM3 fitting theory) — out of scope; the
  kernel checks data-analysis arithmetic, not quantum mechanics.
- Replacing the ledger — D1 remains the operational corpus; Lean is the
  verification layer. The two must reference each other (atlas_theorems
  revision fix, audit finding).

## Ratchet rule

Each new evidence family enters at the highest rung the tooling supports at
the time, and never below L1 once L1 lands. The ladder only ratchets upward.
