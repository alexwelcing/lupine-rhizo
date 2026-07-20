# Boundary Theorems for Runtime Correction — Lean Design (2026-07-20)

**Status:** exploratory / ideation space (owner direction: the gate effort locked too early; this layer maps the correction boundary, it does not freeze new gates)
**Motivation (measured):** along-path profile wobble of foundation MLIPs on the Z1 panel is ~100–130 meV RMS; every low-dimensional correction gate abstains correctly; even a perfect model-routing oracle only reaches 70 meV. The correction boundary needs machine-checked theorems, not folklore.

## Vocabulary (new module `OpenDistillationFactory/HonestErrors/CorrectionBoundary.lean`)

- `Profile n := Fin n → ℝ` — energy profile along a reaction path (model or reference).
- `barrier p := max' p − min' p` — path barrier (max-min, matching the frozen campaign convention).
- `deviation m r := m − r` pointwise; `wobble d := max' d − min' d`.

## Theorems

1. **`barrier_shift_invariant`** — `barrier (p + const) = barrier p`.
   Global additive shifts cannot change any barrier. (Why the shift family was dead on arrival — now a theorem, not a mood.)

2. **`barrier_error_le_wobble`** — `|barrier m − barrier r| ≤ wobble (deviation m r)`.
   The measurable upper bound: a model's barrier error never exceeds its profile wobble. Equality is achievable (witness constructed), so the bound is tight — no information-free correction can beat it.

3. **T-slope-stability family** —
   - `slope_correction_error_le`: if the per-point slope ratios `s_i = (m i − r i) / r i` all share one sign and the correction scales by the median ratio, the corrected barrier error is bounded by the spread of the slope residuals.
   - `slope_instability_witness`: if the slope signs differ, no single-ratio correction can dominate the raw profile's error — the abstention certificate (the computable form of our direction gate for slopes).

4. **`anchor_impossibility_bound`** — for a correction that sets one anchor point `k` to its reference value and leaves the rest of the profile untouched, the residual barrier error is bounded below by `wobble d − (max' d − d k ∪ d k − min' d)`-style remainder; precisely: anchoring point `k` removes at most the deviation at `k`, so the residual error `≥ wobble d − |d k|` in the worst case. The 2-point anchor (saddle + endpoint) reconstructs the reference barrier exactly (trivial) — proving that sparse anchors pay for accuracy with model irrelevance, and nothing cheaper buys it.

## Conventions

- Follow `HonestErrors/{Acceptance,StageGates}` and the Empirical Registry idiom: small computational types, `norm_num`-provable statements, zero sorry, zero new axioms, `deriving Repr` on structures.
- Concrete computational witnesses for tightness cases (like the existing gate-refutation theorems) — equality-achieving profiles for (2), sign-flip examples for (3), single-anchor residuals for (4).
- Wire the module into `OpenDistillationFactory.lean` root; doc-comment header states the exploratory status explicitly (no consumer may treat these as frozen gates).
- `lake build` must pass; the empirical registry count guards (`#guard theoremInventory.length`) must be updated if inventory changes, with the ATLAS sync evidence regenerated per the documented flow.

## Non-goals

No new preregistered gates, no changes to the frozen Z1/Z3/Round-4 records, no claims-registry changes. This is the ideation layer that tells us what the next campaign CAN be.
