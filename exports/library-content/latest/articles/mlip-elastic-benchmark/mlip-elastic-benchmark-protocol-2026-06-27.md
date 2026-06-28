# MLIP Elastic Benchmark Protocol — 10× Cost Reduction for MLIP Elastic-Constant Validation

> **Date:** 2026-06-27  
> **Parent task:** `t_0266945a` (synthesizer)  
> **Design source:** `lupine-rhizo/docs/plans/mlip-elastic-benchmark-master-2026-06-27.md` (binding; this protocol is the runnable translation)

## Claim under test

On a 16-element cubic-metal benchmark, a Lupine-corrected single-model 1×1×1 elastic-constant calculation matches the accuracy of a 3×3×3 reference run while costing ~10× fewer CPU-seconds, and outperforms a 3-architecture ensemble while costing ~5× fewer CPU-seconds.

## Element roster (16)

`Ag Al Au Ca Cr Cu Fe Mo Nb Ni Pd Pt Sr Ta V W`

## Four benchmark arms

| Arm | Label | Model | Cell | Correction |
|-----|-------|-------|------|------------|
| A | `raw-1x1x1` | TensorNet/PBE | 1×1×1 | None |
| B | `corrected-1x1x1` | TensorNet/PBE | 1×1×1 | LOO-PCA bias + functional shift |
| C | `ref-3x3x3` | TensorNet/PBE | 3×3×3 | None |
| D | `ensemble-1x1x1` | M3GNet/PBE + CHGNet/PBE + TensorNet/PBE | 1×1×1 | None (mean) |

- QET is deduplicated to TensorNet (byte-identical checkpoint).
- Headline targets are `TPBE_0K` from `targets_0K.json`.

## Bias operator (arm B)

1. For each element, compute the TensorNet/PBE 1×1×1 error vector: `raw − TPBE_0K`.
2. Leave-one-out: fit the first principal component of the centered error matrix on the other 15 elements; apply that bias to the held-out element.
3. Add functional shift `Tr2SCAN_0K − TPBE_0K`.
4. Report mean and median MAE over the 16 LOO-corrected predictions.

Implementation: `lupine/python/lupine/operator.py:correct()` and `leave_one_out_calibration()`.

## Cost model

`core_hours = runtime_seconds × n_cores / 3600`, with `n_cores = 1` for per-case CPU-equivalent core-hours. All headline costs are cache-warm. The 1×1×1 matrix is re-run after model download so HuggingFace cache misses do not inflate costs.

## Execution steps

1. Warm model cache: run a 2-element smoke test (Ca, Cu) for all three architectures.
2. Run the 16-element 1×1×1 matrix for M3GNet, CHGNet, TensorNet, PBE + r2SCAN (96 cases) using `lupine/data/run_mlip_elastic_benchmark_1x1x1_matrix.py`.
3. Aggregate with `lupine-mlip-benchmark/scripts/aggregate.py`, which combines the new 1×1×1 results, the existing 3×3×3 16-element grid, and `targets_0K.json`.
4. Verify schema and plausibility with `lupine-mlip-benchmark/scripts/verify.py`.
5. Fill placeholders in the preprint, dashboard, and funder brief using the resulting `mlip_elastic_benchmark_results.json`.

## Config

The machine-readable case matrix lives in `lupine-mlip-benchmark/config/mlip_elastic_benchmark.yaml` (192 cases: 16 elements × 3 architectures × 2 functionals × 2 supercells).

## Kill conditions / caveats

- If `MAE(B) > MAE(C) + 1.0 GPa`, the corrected small cell does not match the supercell reference.
- If `MAE(B) ≥ MAE(D)`, the corrected single model does not beat the ensemble; pivot headline to the supercell-independence saving only.
- Report median MAE alongside mean because Cr is a pathological outlier.
- r2SCAN targets are scalar bulk-modulus shifted; Au uses a PW91-GGA fallback; QET≡TensorNet; costs are cache-warm and single-seed.
