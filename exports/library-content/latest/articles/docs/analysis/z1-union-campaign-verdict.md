# Z1 Union Campaign — Verdict of Record (2026-07-24)

**Campaign:** Z1 sparse-DFT union-anchor pilot, 23 active paths (7 deferred ≥159-atom paths pending investment-grade compute), 4 uMLIPs, GPAW fd/PBE at amendment-02 adopted settings (h=0.20, kpts=(1,1,1)).
**Basis:** amendment 01 — same-engine gate primary (sparse-vs-dense GPAW), VASP-referenced secondary; T1 wander reported per path.
**Receipts:** `/tmp/z1-union-local/` anchors (129/129 checkpoints, 0 failed, 0 memory-skipped); campaign record `data/candidates/z1-union-campaign.json` (sha256 sidecar).

## Per-model verdicts

| Model | Guided paths | Same-engine MAE | Same-engine check | VASP-referenced MAE | Verdict |
|---|---|---|---|---|---|
| chgnet | 22/22 | 0.0 meV | ≤15 | 693.0 meV | **SELF_CONSISTENCY_CHECK** |
| mace-mp-small | 21/21 | 6.8 meV | ≤15 | 705.7 meV | **SELF_CONSISTENCY_CHECK** |
| mace-mp-medium | 22/22 | 0.0 meV | ≤15 | 693.0 meV | **SELF_CONSISTENCY_CHECK** |
| mace-mpa-0-medium | 21/21 | 6.8 meV | ≤15 | 705.7 meV | **SELF_CONSISTENCY_CHECK** |

**Interpretation:** `SELF_CONSISTENCY_CHECK` records sparse-vs-dense agreement within the same GPAW engine. It is not an external-reference accuracy win; the VASP-referenced MAE is shown separately and does not satisfy the former claim.

**Guidance-quality split:** chgnet and mace-mp-medium located the true extrema on every guided path (0.0 meV — their anchor sets always covered the dense profile's argmax/argmin, so by the union law (`barrier_eq_barrier_of_extrema_mem`) their sparse barriers are exactly the dense barriers). mace-mp-small and mace-mpa-0-medium missed extrema on some paths; their deficits (6.8 meV mean) are pure undercoverage error per `barrier_mono_subset`. The protocol ranks model guidance at zero extra cost.

**Gate-power caveat (standing):** on ≤7-image paths the dense extension makes sparse ≡ nearly dense by construction; the same-engine verdict is partly structural. Non-trivial signals here: the 0.0-vs-6.8 guidance split, the union economics, and the cost ledger. The sparsity stress test belongs to longer paths.

## T1 wander map (all 23 paths)

mean 952.3 meV, max 4542.4 meV; clean paths: path-27 only (33.5 meV). Largest: path-14 (4542.4, no guiding models), path-0 (4212.3, Ag-F-Li, metallic saddle — mechanism in `docs/analysis/t1-wander-mechanism.md`), path-25 (1229.1), path-3 (1177.4), path-4 (1126.4), path-6 (1055.8). Smallest after path-27: path-27 33.5, path-16 117.3, path-7 135.0, path-29 189.1, path-17 268.7, path-1 269.9.

**T1 law check:** machine-checked `abs_barrier_sub_le_wander` says barrier error ≤ offset wander. Measured VASP-referenced MAE 693.0–705.7 meV vs mean wander 952.3 meV — inside the bound, as required.

## Frozen economics (provenance separated)

- Projected campaign design: **72.4% fewer DFT evaluations**.
- Measured execution ledger: **$14.65 per 129 anchors**.
- Neither result establishes prospective accuracy.

The unresolved `$14.65` versus `$4.65` conflict remains preserved in its provenance record and is not resolved here.
