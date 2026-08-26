# Round-5 preregistration v3 — regime-optimal bias estimator

> **Status:** FROZEN FOR REGISTRATION. Re-locked at `2026-08-17T14:59:30Z`
> after independent pre-execution review rejected the first v3 lock.
> This is a new prospective campaign identity. It preserves the rejected v1 and
> independently accepted v2 records byte-for-byte. No Round-5 execution,
> materialized panel, model output, reference outcome, or correction outcome was
> inspected in making this amendment. Any later scientific-contract change
> requires a new campaign version.

## 1. Why v3 exists

The v2 preregistration estimated multiplicative bias with the fixed-point median
of the leave-one-out calibration ratios. The machine-checked development
`theory-artifacts/OptimalBias.lean` proves that this choice creates the apparent
selectivity of the sharp gate:

- for inflation (`U < lo`), `b = lo` improves every true in-hull target and is
  the unique maximizer of the guaranteed absolute improvement margin;
- for deflation (`hi < U`), the real minimax estimator is
  `b* = U*(lo+hi)/(2*U+lo-hi)`; and
- the fixed-point integer optimum is one of `floor(b*)` or `ceil(b*)`, both
  in-hull when admissible, selected by exact comparison of the guaranteed
  margin.

The exact sharp gate is therefore vacuous for a suitable estimator on every
strictly one-sided hull. The only remaining runtime abstentions are the unchanged
direction/calibration gates, the rounding-soundness belt-and-braces gate, and
fail-closed input/provenance checks. This changes the prospective Round-5
scientific intervention; it does not reinterpret or replay frozen Round 1–4.

## 2. Frozen calibration step

For held-out structure X, registered model m, property p, and the exact grouping
tuple `(class, chemistry, structure_prototype,
composition_space_neighbourhood)`:

1. Select every other panel structure in the same tuple with a non-null,
   provenance-accepted reference for p. X is excluded. Require at least four;
   otherwise ABSTAIN `insufficient_calibration`.
2. Compute each ratio `pred_i/ref_i` and convert it to fixed-point integer units
   `U = 10000` by decimal round-half-even. Emit the full ordered ratio list,
   count, `lo`, `hi`, and the legacy median as an audit-only comparator.
3. Apply the unchanged direction gate. `U < lo` is inflation; `hi < U` is
   deflation. Any mixed-side hull or ratio equal to U ABSTAINS `direction_gate`.
4. Inflation estimator: set `b = lo`.
5. Deflation estimator: set `N = U*(lo+hi)`, `D = 2*U+lo-hi`,
   `q = floor(N/D)`, and `c = ceil(N/D)`. Keep only in-hull candidates from
   `{q,c}`. For candidate x define
   `Wdefl(x) = min(lo*(U-x), 2*U*x-hi*(U+x))`. Choose the x that maximizes
   `Wdefl(x)/(U*x)` by exact integer cross-multiplication. Emit, for every
   candidate, x, `Wdefl(x)`, and the exact objective numerator and denominator;
   also emit the two cross-products, their relation, and the selected x. If the
   objective ties, choose the larger x for the larger robustness region.
   Floating-point comparison is forbidden.
6. Evaluate the rounding-robust gate in §3. If it passes,
   `corrected = pred/(b/U)`; otherwise leave the prediction unchanged and
   ABSTAIN `rounding_robust_sharp_license`.
7. Require the corrected prediction to be finite. If finite input would produce
   a non-finite correction, leave the finite prediction unchanged and ABSTAIN
   `non_finite_correction`.

The implementation is
`python/lupine_distill/statics/optimal_bias.py`, SHA-256
`1bbfb5c3c19aebb21af14ee32dfbadc6158096eddb7a34a9beeeaf472d0e2c4f`.
Its structured output contract is frozen in
`data/candidates/round5_elastic_panel-selection.v3.lock.json`. Missing,
malformed, nonpositive, out-of-domain, or implementation-digest-mismatched
inputs refuse; they are never imputed.

## 3. Rounding-robust belt-and-braces gate

The gate is evaluated only on fixed-point values obtained by round-half-even,
with error bound `eps = 1/2` scaled unit. It uses the exact dynamic THEORY-4
bounds, not the unsound bare strict inequality and not floating-point arithmetic.

Inflation:

- gate margin `G = lo*(U+b)-2*U*b`;
- require `G > (1/2)*(3*U+1/2+b-lo)`; and
- require theorem domain `U < lo <= b <= 2*U`.

Deflation:

- gate margin `G = 2*U*b-hi*(U+b)`;
- require `G > (1/2)*(3*U-hi+b+1/2)`; and
- require theorem domain `0 < b <= hi < U`.

Because G is integral, the implementation derives the exact smallest admissible
integer margin by rational arithmetic. The severe inflation and deflation
rounding witnesses from `SharpCorrectionLicense.lean` must refuse. A bare sharp
gate pass with insufficient rounding margin is an abstention, not a license.
The inflation theorem currently covers `b <= 2U`; a larger rounded inflation
bias fails closed pending a reviewed theorem extension.

The theorem bindings are Lupine meta commit
`d1de22a7cdca971aa8f81c73df6b3e36555b3d99`:

- `theory-artifacts/OptimalBias.lean`, SHA-256
  `34c1b40b3f3ce0ae5b564b2119c67de37da059ea90406ee3f6fb09c4855114c7`;
- `theory-artifacts/SharpCorrectionLicense.lean`, SHA-256
  `872860108877682eb182467f6a718c31d507d84c841b3adcbe94c7faee5fa968`.

Reviewed equivalent theorems for both bindings must land in `lean-spec` before
execution. A formula, strictness, theorem, or digest mismatch REFUSES dispatch.

## 4. What calibration must output

Every non-refused calibration record emits:

- schema and scale;
- calibration count and all fixed-point ratios;
- side, lo, hi, and audit-only median;
- estimator identity and selected fixed-point bias;
- for deflation: N, D, floor, ceil, admissible candidates, each candidate's
  exact objective numerator/denominator, the exact comparison cross-products
  and relation, selected bias, and deterministic tie rule;
- rounding epsilon, sharp margin, exact required margin, bare-sharp result,
  theorem-domain result, and robust-gate result; and
- applied flag plus explicit abstention reason.

The model×structure×property result must additionally bind the CampaignManifest
content hash, selection-contract hash, materialized-panel hash, implementation
hash, model artifact hash, runner image digest, attempt number, and immutable
artifact URI. The held-out oracle ratio and in-hull status are computed only
later for theorem-consistency analysis; they are never represented as
runtime-knowable.

## 5. Design and endpoints retained from v2

All independently accepted v2 repairs remain unchanged:

- exactly 125 elastic structures (63 ionics-rocksalt, 62 perovskites) and four
  registered models, exactly 500 model×structure cells;
- complete selected calibration groups with occupancy zero or at least five;
- at least 16 pre-outcome calibration-eligible distinct structures per
  class×property before dispatch;
- a0, C11, C12, and C44 confirmatory; B0 descriptive only;
- one distinct structure as the primary and hull-width secondary sampling unit;
- the two-sided exact sign test with strict alpha 0.1 and at least 16 distinct
  non-tied applied structures per scorable class×property;
- the six structure-level hull-width contrasts with Holm family-wise alpha 0.1;
- dedicated digest-pinned Cloud Run jobs with `maxRetries: 0`; and
- no adaptive extension, replacement, outcome-dependent pooling, retry,
  imputation, or legacy Round-4 job reuse.

A class succeeds only if at least three of four confirmatory properties win under
the v2 endpoint. Underpowered properties remain `UNDERPOWERED_NOT_SCORABLE`.
Fewer than three scorable properties yields `INCONCLUSIVE_UNDERPOWERED`.

## 6. Theorem-consistency and interpretation

Among applied model×structure×property cells whose held-out ratio is later
observed inside its calibration hull, the worsened count must be zero. Any
positive count kills promotion as an implementation, rounding, provenance, or
reference defect.

The new estimator does not make hull membership observable, prove transfer to
out-of-hull targets, license mixed-side hulls, or license derived elastic
aggregates. It changes only the registered scalar correction for each primitive
property. Round-4 remains a negative frozen campaign. No replay of its outcomes
is confirmatory Round-5 evidence.

## 7. Immutable execution boundary

The v3 CampaignManifest, this preregistration, and the v3 panel-selection
contract must be content-addressed in `registry/campaigns.v1.json` before any
Round-5 execution or outcome inspection. The materialized source pool and panel
may be produced only from the frozen selector, then hash-locked before dispatch.

Round 5 may not execute until:

1. both theory bindings have reviewed equivalents in `lean-spec`;
2. the v3 implementation and tests pass independent review;
3. a deterministic source pool and 125-structure panel satisfy every v3 lock;
4. dedicated jobs bind immutable images and `maxRetries: 0`; and
5. all manifest, contract, implementation, source, panel, model, and runner
   digests reconcile exactly.

Any missing, stale, contradictory, unverified, out-of-schema, or digest-mismatched
evidence is a refusal. No frozen earlier campaign is modified, replayed, or
retroactively reclassified.
