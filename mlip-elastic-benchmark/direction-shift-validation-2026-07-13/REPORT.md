# Direction-Shift Accuracy Validation — 2026-07-13

**Question:** did the correction operator's shifted direction actually improve accuracy, under honest out-of-sample (leave-one-material-out) evaluation?

**Verdict: YES on the prespecified primary target (Tr2SCAN_0K), with statistically significant directional agreement; NO on the secondary TPBE_0K target (consistent with the 2026-06-27 diagnosis's target-dependence finding). The v0.1 global-LOO-PCA failure mode (63.40 GPa) is also reproduced, confirming the falsification.**

Runner: `validation_script.py` (deterministic, seeded, venv `.venv-mlip312`, CPU only — no model loads).
Full numbers: `results.json`.

**Certification boundary:** every corrected Cij MAE and every scalar-bulk/directional aggregate below is an empirical held-out diagnostic and is **uncertified** as a correction license. Componentwise evidence certifies an MAE only if every included target component has a valid scalar license; bulk projections and all other derived maps require a separate vector-valued license for the exact transformation.

## Protocol (prespecified before running)

- Primary target Tr2SCAN_0K; secondary (report-only) TPBE_0K.
- Leave-one-material-out over the 16 cubic metals (Ag Al Au Ca Cr Cu Fe Mo Nb Ni Pd Pt Sr Ta V W); per-property errors on C11/C12/C44.
- Arms: (1) raw TensorNet/PBE 1x1x1; (2) shift-only; (3) v0.2 scalar-bulk (LOO alpha, `ScalarBulkOperator.lean` normal-equation fit on the bulk projection B=(C11+2C12)/3); (4) v0.3 directional (`DirectionalCorrectionScheme.lean`: pred = raw + shift + alpha*d, d = bulk direction (1,2,0), alpha = global LOO least squares); (5) 3-model PBE ensemble mean (recorded, reference arm). Plus the recorded v0.1 global-LOO-PCA arm for falsification.
- Metrics: mean/median of per-element MAE (diagnosis convention); directional agreement at property level (16x3 = 48 cases): sign(correction) == sign(target - raw) AND |err_after| < |err_before|, with a two-sided exact sign test on improved-vs-worsened (ties excluded); per-bonding-class breakdown (5 classes from the diagnosis).
- Success criterion: corrected < shift-only < raw on mean MAE vs Tr2SCAN, reproducing 14.13 (scalar-bulk) and the 63.40 v0.1 failure within ~1 GPa.

## Data provenance (what was reconstructed and why)

The WSL repo holding `lupine/data/targets_0K.json` (16-element version) and `python/lupine/feedback.py` is absent on this machine. `shed/lupine/targets_0K.json` is a *different* 15-element curation (Pb instead of Ca/Sr; e.g. its PBE Ag C11 = 123 vs the benchmark's 107) and was NOT used. Inputs actually used:

- **Raw, ensemble, and v0.1-corrected per-element predictions:** recorded in `lupine-rhizo/data/mlip-elastic-benchmark/mlip_elastic_benchmark_results.json` (run 2026-06-27, git 3716feec).
- **TPBE_0K targets:** reconstructed exactly as raw − raw-error using the diagnosis per-element error table (quoted to 0.01 GPa).
- **Tr2SCAN_0K targets:** per the preprint caveat, Tr2SCAN = TPBE scaled componentwise by a per-element scalar bulk-modulus factor (factor 1.0 for Al/Ca/Sr). Factors recovered from the diagnosis scalar-bulk table via shift = (corrected − raw)/alpha + least-squares scalar fit; recovered factors range 0.9956 (Nb) to 1.1952 (Cu). The scalar-factor model fits the extracted shifts to < 0.35 GPa on every component.
- **Reference v0.2 alphas and FeedbackLoop scorecard:** `lupine-rhizo/mlip-elastic-benchmark/feedback_loop_benchmark.json`.

The reconstruction is validated by 13/13 reproduction gates (below), all matching the diagnosis to <= 0.01 GPa.

## Reproduction gates — all PASS

| Gate | Got (mean, median) | Diagnosis | Pass |
|---|---|---|---|
| raw vs TPBE | 14.55, 13.48 | 14.55, 13.48 | PASS |
| raw vs Tr2SCAN | 22.55, 22.50 | 22.55, 22.50 | PASS |
| shift-only vs TPBE | 16.28, 15.74 | 16.28, 15.74 | PASS |
| shift-only vs Tr2SCAN | 14.55, 13.49 | 14.55, 13.48 | PASS |
| scalar-bulk vs TPBE | 19.17, 19.01 | 19.17, 19.01 | PASS |
| scalar-bulk vs Tr2SCAN | 14.13, 11.16 | 14.13, 11.16 | PASS |
| v0.1-unshifted (recorded) vs TPBE | 54.28, 55.09 | 54.28, 55.09 | PASS |
| v0.1-unshifted (recorded) vs Tr2SCAN | 45.83, 46.04 | 45.83, 46.05 | PASS |
| v0.1 (recorded+shift) vs TPBE | 63.39, 65.33 | 63.40, 65.33 | PASS |
| v0.1 (recorded+shift) vs Tr2SCAN | 54.28, 55.09 | 54.28, 55.09 | PASS |
| ensemble vs TPBE | 11.60, 11.62 | 11.60, 11.62 | PASS |
| ensemble vs Tr2SCAN | 19.89, 19.66 | 19.89, 19.65 | PASS |
| scalar-bulk LOO alphas vs recorded v0.2 alphas | max dev 8e-5 | — | PASS |

Additionally, the reimplemented v0.3 directional operator (bulk direction, global LOO alpha) matches the recorded `feedback-projection-offset-none` per-element MAE to <= 0.003 GPa — the absent WSL `feedback.py` projection policy is therefore independently reproduced from the Lean spec formulas alone.

## Per-arm accuracy (mean / median of per-element MAE, GPa)

| Arm | vs Tr2SCAN_0K (primary) | vs TPBE_0K (secondary) |
|---|---|---|
| raw | 22.55 / 22.50 | 14.55 / 13.48 |
| shift-only | **14.55 / 13.49** | 16.28 / 15.74 |
| scalar-bulk v0.2 (LOO) | **14.13 / 11.16** | 19.17 / 19.01 |
| directional v0.3 (LOO) | **13.26 / 9.03** | 18.44 / 17.10 |
| v0.1 global-LOO-PCA (+shift) | 54.28 / 55.09 | 63.39 / 65.33 |
| ensemble 3-model 1x1x1 | 19.89 / 19.66 | 11.60 / 11.62 |

Success-criterion ordering on the primary target holds: **v0.3 (13.26) < v0.2 (14.13) < shift-only (14.55) < ensemble (19.89) < raw (22.55) << v0.1 (54.28)**.

## Directional agreement (primary target Tr2SCAN_0K)

Property-level, 48 cases; ties (zero applied correction: Al/Ca/Sr have zero functional shift) excluded. "Success" = correction moved prediction toward target AND shrank |error|.

| Arm | active cases | toward target | toward AND improved | improved / worsened | sign-test p (two-sided) |
|---|---|---|---|---|---|
| shift-only | 39 | 79.5% | 71.8% | 28 / 11 | **0.0095** |
| scalar-bulk v0.2 | 39 | 79.5% | 71.8% | 28 / 11 | **0.0095** |
| directional v0.3 | 45 | 84.4% | 73.3% | 33 / 12 | **0.0025** |
| v0.1 (+shift) | 48 | 77.1% | 20.8% | 10 / 38 | **6.2e-5 (harmful)** |
| ensemble (ref) | 48 | 70.8% | 60.4% | 29 / 19 | 0.19 (n.s.) |

Material level (per-element MAE improved vs raw): v0.3 improves 12/16 (p = 0.077), v0.2 and shift-only 10/13 non-tied (p = 0.092), v0.1 worsens **16/16** (p = 3.1e-5), ensemble improves 12/16 (p = 0.077).

Note the v0.1 pathology: 77% of its corrections point *toward* the target but only 21% land closer — the global PC direction systematically **overshoots** (magnitude failure, not sign failure).

### Per-class (fraction toward-and-improved, v0.3 vs Tr2SCAN)

post_transition 3/3, transition_bcc 81.0%, transition_fcc 77.8%, noble_coinage_fcc 66.7%, alkaline_earth_fcc 25% (Ca/Sr have near-zero raw error, ~2.4 GPa MAE, so any correction tends to hurt). Class-mean MAE vs raw: transition_bcc 27.6 -> 19.3, transition_fcc 31.7 -> 8.9, noble 19.0 -> 11.0, post_transition 10.6 -> 5.9, alkaline_earth 2.4 -> 5.7 (worsened).

## Secondary target TPBE_0K (report only)

No corrected arm beats raw (14.55): shift-only 16.28, v0.2 19.17, v0.3 18.44. Directional agreement is not significant or trends harmful (v0.2: 13 improved / 26 worsened, p = 0.053). This reproduces the diagnosis's finding that the operator is **target-dependent** and only recommended for the Tr2SCAN-corrected target.

## Reproduced vs diverged from the 2026-06-27 diagnosis

Reproduced (<= 0.01 GPa): all six operator-table rows (raw, shift-only, global-loo-pca, global-loo-pca-unshifted, scalar-bulk, ensemble) on both targets; the 16 v0.2 LOO alphas (max dev 8e-5); the v0.3 feedback-projection-offset-none aggregates 13.26 / 9.03 and per-element MAE (<= 0.003 GPa).

Clarified: the recorded `corrected-1x1x1` arm in `mlip_elastic_benchmark_results.json` corresponds to the diagnosis's *unshifted* row (raw + bias, 54.28 vs TPBE); the headline 63.40 failure = recorded + functional shift. Both identities verified.

Diverged / not reproduced:
1. **v0.1 internals from scratch:** a 4-variant LOO-PCA scan (centered/uncentered x sign) did not match the recorded v0.1 predictions (best max-abs-dev 92.5 GPa). The exact v0.1 bias-coefficient scheme lives only in the WSL repo; the failure mode is validated from the *recorded* v0.1 predictions instead, which is sufficient for the falsification claim.
2. **v0.3 offset modes (median/oracle) not re-run** — outlier-threshold bookkeeping is secondary to the direction question; recorded values are quoted in `results.json` for reference.

## Honesty caveats

1. Targets are **reconstructed**, not read from the original `targets_0K.json` (WSL-only). The reconstruction is over-determined and passes 13/13 gates, but it is derived from the same diagnosis document it validates; an independent target re-derivation from MatPES would strengthen this.
2. The Tr2SCAN_0K target is itself an approximation (PBE tensors scaled by a scalar bulk-modulus ratio — preprint caveat #1), so "more accurate vs Tr2SCAN" inherits that approximation, and the functional-shift direction is partially aligned with the target by construction. The honest LOO content of the result is the *learned* parts: the scalar alpha (v0.2) and the direction-projected alpha (v0.3) were always fit on the other 15 elements, and they improve over blind shift-only (13.26 / 14.13 vs 14.55).
3. Shift-only/scalar-bulk sign tests exclude Al/Ca/Sr (zero shift -> zero correction, 9 tied cases).
4. Single model (TensorNet/PBE), single seed, 16 materials; the diagnosis's seed-variance subset says seed noise is ~0, but n = 16 keeps all sign-test power modest at the material level.

## Bottom line

Under honest leave-one-material-out evaluation, **the direction the operator shifted did get more accurate on the prespecified Tr2SCAN target**: 73% of applied corrections moved predictions toward the target and landed closer (v0.3: 33 improved vs 12 worsened, p = 0.0025; v0.2: 28 vs 11, p = 0.0095), mean MAE improved 22.55 -> 14.13 (v0.2) -> 13.26 (v0.3) GPa, beating the 3-model ensemble (19.89) at ~2.7x lower cost. The claim does **not** transfer to the TPBE headline target, and the v0.1 global-PCA operator is confirmed harmful (54.28/63.40 GPa; worsens all 16 materials, p = 3.1e-5) — the failure is overshoot along a mis-specified global direction, exactly as diagnosed.
