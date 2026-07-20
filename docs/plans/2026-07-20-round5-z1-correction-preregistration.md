# Round-5 Z1-Correction Pilot — Preregistration (2026-07-20)

**Status:** FROZEN before execution · **Owner:** Alex Welcing (director)
**Campaign id:** `discovery.round-5.z1-correction.v1`

## Question

Can the direction-gated correction layer deliver a specific, preregistered accuracy improvement over the bare foundation-MLIP floor on migration-barrier prediction — in the hard regime where Round-4 proved the floor fails (all models, MAE 135–243 meV vs the 40 meV screening gate)?

## Locked context (no changes after this timestamp)

- **Test panel:** `data/candidates/z1_nebdft2k_barriers.lock.json` (SHA-256 `192fe54a…`) — the Round-4 panel, 30 chemistry-held-out LiTraj nebDFT2k paths. It remains frozen; nothing in this pilot re-fits or re-locks it.
- **Floor measurements:** Round-4 float64 chain (`gs://shed-489901-atlas-outputs/z1/campaign-float64/`): mace-mpa-0-medium 135.0, mace-mp-small 151.9, mace-mp-medium 174.7, chgnet 242.5 meV barrier MAE.
- **Training panel (to be locked):** ≤12 DFT-NEB paths from the LiTraj **training split** — chemical systems DISJOINT from every test-panel chemistry (checked by Materials Project id). Built with the same conventions (BVSE images, DFT-relaxed profiles, frozen CI-NEB protocol), hash-locked before any model sees it.
- **Exploratory basis (indication only, not evidence):** leave-one-out analysis of the Round-4 artifacts — chgnet raw 243→112 meV under a per-model linear error model (a=−11 meV, b=−271 meV/eV); selective coverage 80% → 77 meV. MACE variants show weak/no gain under the same form. These numbers motivated this pilot and do NOT count as its result.

## Frozen protocol

1. **Correction form (per model):** linear error model `ê(ref) = a + b·ref` fitted by least squares on the training panel only. **Gate:** the correction applies only where the direction is one-sided across ALL training paths (signed errors strictly one side of zero — the proven `wrong_direction_*` theorem requirement); otherwise the model abstains for that path set. **Theorem caps** (Round-4 v2): applied only if `|median(ratio) − 1| > 2·spread(ratio)` for inflation-side fits and `1 − median > 3·spread AND median ≥ 0.5` for deflation-side fits.
2. **Execution:** each of the 4 available models runs the ≤12 training paths on the isolated Cloud Run jobs (same images, same frozen CI-NEB protocol as Round-4). Fit on those results only.
3. **Scoring:** apply the frozen fitted correction to the Round-4 float64 test-panel predictions (offline, byte-verified artifacts; no re-measurement of the test panel).
4. **Metrics (primary):** corrected vs raw barrier MAE per model at full coverage. **Secondary:** selective-coverage curve (accepted-subset MAE at 90/80/70% coverage, with refusal driven by |corrected signed error| ranking — declared, not tuned).

## Success criteria

- **WIN (per model):** corrected MAE ≤ 0.5 × raw MAE at full coverage.
- **Strong WIN (campaign):** at least one model also reaches corrected MAE ≤ 100 meV at full coverage.
- **No-harm (required for any claimed win):** no chemistry family in the test panel has corrected MAE worse than 1.1 × its raw MAE.

## Kill conditions

- Any leakage detected (training/test chemistry overlap, test-panel refits) → campaign void, recorded.
- Corrected MAE worse than raw for ≥2 models → the correction form is refuted for this observable; recorded, not tuned.

## Publication

Whatever the outcome: library research report with all numbers and receipts; lupine.science field note only if a WIN holds (or explicitly as a "the correction is refuted" note if not). Claims registry entries stay `unsupported` until ingestion.
