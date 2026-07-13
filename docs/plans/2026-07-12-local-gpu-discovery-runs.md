# Local GPU Run Plan — Discovery-Gates Calibration (2026-07-12)

> **Lane:** local GPU discovery (RTX A4500 20 GB, no cloud spend)
> **Status:** planned, not started
> **Framing:** exploratory-descriptive per the 2026-07-02 process note in
> [`y-matrix-confirmatory-results-2026-07-01.md`](./y-matrix-confirmatory-results-2026-07-01.md)
> — threshold calibration is an engineering fix with documented provenance,
> not a pass/kill registration. A registration follows only if a
> publication-bound claim comes out of Run 3.

## Why these runs

The first discovery-gates run
([`data/discovery_gates/REPORT.md`](../../data/discovery_gates/REPORT.md),
2026-07-02) produced a **false refusal on the known-good subject**: Li2S
antifluorite was REFUSED because the concordance thresholds (flag ≥ 0.2490,
refuse ≥ 0.3848) were derived from **B0** cross-model dispersion and applied
unchanged to C11/C44, which physically disperse more across models
(C11 dispersion 0.589, C44 0.669 → REFUSE). The report itself flags this
transfer as "a documented proxy, not a per-property calibration." A
reference-free gate that refuses its known-good calibration subject cannot
gate anything. Fixing the calibration is the highest-leverage next local
experiment, and it needs only local GPU.

## Environment (verified 2026-07-12)

- GPU: NVIDIA RTX A4500, 20 GB, driver 595.71.
- Venv: `.venv-mlip312\Scripts\python` — torch 2.11.0+cu128, CUDA available;
  local backends: **chgnet, mace** (mace-mp-small, mace-mp-medium,
  mace-mpa-0-medium). GPU lane pins: `python/requirements-gpu-lane.lock`.
- **Not local:** SevenNet, Orb, UMA — those run as `mlip-cell-*` Cloud Run
  jobs only; any panel needing them goes through a promotion packet, never
  hand-launched.
- Runner pattern: `TORCHDYNAMO_DISABLE=1` set CLI-side only (no Triton on
  Windows), `PYTHONUTF8=1`, `--device cuda`.
- Baseline data present: `data/y_matrix_runs/bound/` — 85 evidence files,
  21 materials × 4 models, schema `lupine.mlip.calc_evidence.v1`.
- Statics suite green on this branch: 111 tests
  (structures/elastic/gates/calculations/eos/surfaces).

## Run 0 — preflight (no GPU)

1. Query the live ledger for prior claims touching discovery gates, Li-S, or
   per-property dispersion (`wrangler d1 execute glim-ledger --remote`), so we
   build on `manifold_runs` / existing Y-matrix claims instead of re-deriving.
2. Restore `python/scripts/run_y_matrix_statics.py` from
   `archive/2026-07-01/python/scripts/` (same restore pattern as the statics
   tests — the 2026-07-01 cleanup archived the script that produces the
   calibration baseline while the lane is still active).
3. Smoke: one Ni/fcc cell per local model on cuda; confirm wall times match
   the ~4–7 s/cell envelope from the 2026-07-02 report.

## Run 1 — per-property dispersion baseline (main GPU run)

**Goal:** replace the B0-only threshold proxy with measured per-property
thresholds.

- Compute relaxed a0, B0 (BM3 EOS), and cubic C11/C12/C44 for the **21
  Y-matrix bound materials × 4 local models** (extend `run_y_matrix_statics`
  or a thin new CLI on `lupine_distill.statics`; elastic lane already exists
  in `statics/elastic.py`).
- Per material and property, record cross-model relative dispersion
  `(max − min)/|median|`; derive **per-property p75/p95** (a0, B0, C11, C12,
  C44 each get their own flag/refuse thresholds).
- Output: `data/discovery_gates/thresholds.v2.json` with full provenance
  (inputs, seed, per-material dispersions) + a short REPORT section.
- Cost envelope: 21 materials × 4 models ≈ 84 cells; at ~5–30 s/cell
  (elastic constants are the slow part) ≈ **10–45 min wall**, well inside the
  A4500. No cloud.
- Coupling caveat to carry in the report: elastic constants are internally
  coupled (Cauchy relation, stability), so per-property thresholds are still
  *within-family* calibration — they fix the transfer error, they do not
  decouple the family.

## Run 2 — recalibrated Li-S verdicts (small GPU run)

- Point `statics/gates.py` concordance at the v2 per-property thresholds
  (keep v1 reachable for comparison; extend `test_statics_gates.py` for the
  per-property path).
- Re-run `python/scripts/run_discovery_gates.py --device cuda` (both
  subjects, ~1 min).
- Expected: Li2S antifluorite clears the mis-transferred refusals (its C11
  dispersion should sit inside the *measured* C11 baseline); LiS rocksalt
  verdict recorded either way. If Li2S still refuses on a per-property
  threshold, that is a real finding about the gate design, not noise — report
  it descriptively, do not tune until it passes.

## Run 3 — stretch: widen the subject panel

Only after Run 2 lands: a small known-good/speculative panel (e.g. Na2S/NaS,
Mg2Si/MgSi — one known antifluorite/L1₂-adjacent pair per chemistry),
per-element matched-n, descriptive reporting. This is where a
registration-worthy claim ("reference-free gates separate known-good from
speculative at rate X") could emerge; if so, register before the confirmatory
sweep per house rules.

## Write-back and promotion discipline

- Evidence artifacts land in `data/discovery_gates/` (versioned JSON +
  REPORT.md regeneration) and results are written back to the ledger as
  claims/evidence — a local file nobody downstream reads doesn't count.
- If Run 3 motivates the full 6-model concordance panel (adds SevenNet, Orb,
  UMA), emit a **promotion packet** with exact `gcloud run jobs execute`
  canaries; cloud starts from the packet.

## Exit criteria

1. `thresholds.v2.json` exists with per-property p75/p95 + provenance.
2. Discovery-gates report regenerated under v2; known-good subject no longer
   refused by threshold transfer (or the residual refusal is documented as a
   gate-design finding).
3. Statics test suite still green; ledger claim(s) recorded.
