# MLIP Elastic Benchmark Master Plan — 10× Cost Reduction for MLIP Elastic-Constant Validation

> **Parent task:** `t_0266945a` (synthesizer)
> **Date:** 2026-06-27
> **Status:** Design frozen; this document is the binding spec for the 6 child tasks.
> **Owner of all numbers in this doc:** synthesizer. Every figure is traced to a source file; downstream workers must NOT invent substitutes.

---

## 0. The claim under test (one sentence)

> *On a 16-element cubic-metal benchmark, a Lupine-corrected single-model
> 1×1×1 elastic-constant calculation matches the accuracy of a 3×3×3 reference
> run while costing ~10× fewer CPU-seconds, and it outperforms a 3- to 5-model
> ensemble while costing ~5× fewer CPU-seconds.*

This is a **cost-accuracy** claim, not a new-physics claim. The physics
(supercell-size independence of uMLIPs) is already demonstrated in the existing
16-element grid; the mlip elastic benchmark *operationalizes* it by attaching a correction
operator and an honest cost ledger, then compares against the two baselines a
supercomputer lab actually runs (big supercell, model ensemble).

---

## 1. What already exists (do NOT re-run)

The following artifacts are in hand and **already published in the library**.
Any child task that re-derives these is wasting compute. The mlip elastic benchmark *layers
on top of* them.

| Asset | Path | What it gives us | Headline number |
|-------|------|------------------|-----------------|
| 16-element 3×3×3 grid | `lupine/data/layer2_outputs_3x3x3_16elem/` | 112 raw per-case JSONs (14 elements × 8 model×functional) + Cu/Ni 16 | mean MAE **17.90 GPa**, total **1736.9 s** |
| Cu/Ni 1×1×1 grid | `lupine/data/layer2_outputs/` | 16 per-case JSONs | mean MAE **13.26 GPa**, total **1217.8 s** (cache-cold) |
| Cu/Ni 3×3×3 grid | `lupine/data/layer2_outputs_3x3x3/` | 16 per-case JSONs | mean MAE **13.29 GPa**, total **519.5 s** (cache-warm) |
| Supercell comparison | `lupine/data/supercell_scaling_16elem_comparison.json` | 144 rows, schema `lupine.supercell_scaling.comparison.v1` | ΔMAE(1→3) Cu/Ni = **+0.03 GPa** |
| Targets | `lupine/data/targets_0K.json` | 16 elements, schema `lupine.targets_0K.v3`, PBE + r2SCAN-shifted | full provenance |
| Correction operator | `lupine/python/lupine/operator.py` | `correct(raw, bias, shift)`, conformal, `compare_operator_to_ensemble` | tested, unit-covered |
| Benchmark driver | `lupine/data/layer2_benchmark_task.py` | single-case CLI: `--element --model --functional --supercell --output` | produces `lupine.layer2.raw.v1` |
| Layer-1 H4 result | `docs/projection-law-round2-results.md` §3 | operator vs ensemble on **classical** potentials | operator wins 4/8; **untested on MLIPs** |
| Layer-2 paper draft | `docs/layer2_research_paper.md` | supercell-independence (Cu+Ni) | retire 4×4×4 |
| Pre-registration | `docs/projection-law-round2-preregistration.md` | H1–H4 + kill conditions | H4 MLIP re-run pending |

**The single missing piece is H4 re-run on MLIPs.** Layer-1 used classical
EAM potentials where the operator won 4/8 elements. Layer 2 has the MLIP
predictions but nobody has yet computed the operator correction, the ensemble
baseline, and the head-to-head on the 16-element MLIP grid. That gap *is* the
mlip elastic benchmark.

---

## 2. Benchmark protocol (binding)

### 2.1 The four arms of the comparison

For each of the 16 elements × the chosen model(s), compute three independent
cubic constants (C₁₁, C₁₂, C₄₄) and record (MAE vs `Tr2SCAN_0K`, CPU-seconds).
The arms are:

| Arm | Label | What it is | N models | Cell |
|-----|-------|------------|----------|------|
| A | `raw-1x1x1` | single model, conventional cell, **no correction** | 1 (best PBE) | 1×1×1 |
| B | `corrected-1x1x1` | single model, conventional cell, **+ Lupine operator** | 1 (best PBE) | 1×1×1 |
| C | `ref-3x3x3` | single model, 3×3×3 supercell, no correction | 1 (best PBE) | 3×3×3 |
| D | `ensemble-1x1x1` | mean of 3 distinct architectures, conventional cell | 3 | 1×1×1 |

The **mlip elastic benchmark headline** is built from four pairwise comparisons:

- **B vs C** — *does the corrected small cell match the big-cell reference?*
  Win = `MAE(B) ≤ MAE(C) + ε` with ε = 1.0 GPa (target uncertainty), at
  `cost(B) ≪ cost(C)`.
- **B vs D** — *does the corrected single model beat the ensemble?*
  Win = `MAE(B) < MAE(D)` at `cost(B) < cost(D)`.
- **A vs B** — *does the operator actually help?* Sanity check:
  `MAE(B) < MAE(A)`.
- **cost(C)/cost(B)** and **cost(D)/cost(B)** — the 10× / 5× multipliers.

### 2.2 Model selection (resolve the alias FIRST)

**The QET≡TensorNet alias is a data-integrity blocker.** In MatPES 2025.2 the
`QET` and `TensorNet` labels both resolve to a `TensorNet-MatPES-*` checkpoint
and return byte-identical Cᵢⱼ in every matched case (`layer2_supercell_evaluation.md`
§3.3). The "4-model ensemble" framing double-weights TensorNet. **Before any
mlip elastic benchmark number is published:**

1. Treat the model roster as **3 distinct architectures**: M3GNet, CHGNet,
   TensorNet. Drop the `QET` label from headline tables, or document it as an
   alias footnote only.
2. The "best single model" for arms A/B/C is the lowest-MAE **PBE** model on
   the 16-element grid. From `supercell_scaling_16elem_comparison.json` that is
   **QET/PBE = TensorNet/PBE at 13.25 GPa mean** (Table 7 of the round-2
   results). Because QET≡TensorNet, the honest statement is "TensorNet/PBE,
   13.25 GPa" — and we use `model_name = TensorNet-PES-MatPES-PBE-2025.2`.
3. The ensemble (arm D) is the mean of **M3GNet, CHGNet, TensorNet** (3
   architectures, PBE). Do NOT average in the r2SCAN variants for the headline;
   report a PBE/r2SCAN-functional-mix sensitivity in the supplement.

### 2.3 The correction operator inputs (arm B)

`correct(raw, bias, shift)` needs three vectors per element. These are
**derived from the 16-element grid**, not re-fitted on the test elements:

- `raw` = the TensorNet/PBE 1×1×1 prediction `(C11, C12, C44)` for that element.
- `shift` = functional shift = `Tr2SCAN_0K − TPBE_0K` from `targets_0K.json`.
  This is an element-specific scalar-vector (each Cᵢⱼ shifted by the same
  bulk-modulus ratio for now; see §6 caveat).
- `bias` = the 1D binding-constraint bias vector. **This is the new compute.**
  Layer 1 used per-family classical bias vectors (Ackland-1987 etc.). For Layer
  2 we extract the bias as the **first principal component of the centered
  TensorNet/PBE error matrix across the 16 elements** (leave-one-out: fit on
  15, predict the 16th). This mirrors the Layer-1 analysis plan
  (preregistration §Analysis plan items 1–2) applied to MLIPs.

**Leave-one-out is mandatory.** In-sample bias fitting would leak the target.
The protocol: for element *e*, fit `b` on the other 15 elements' error vectors,
then `corrected_e = raw_e − b + shift_e`. Report `MAE(B)` as the mean over the
16 LOO-corrected predictions. The operator module already supports this via
`leave_one_out_calibration`.

### 2.4 Cost model (core-hours, the currency of HPC labs)

Wall-clock seconds are recorded in every `lupine.layer2.raw.v1` JSON under
`runtime_seconds`. Convert to **core-seconds** using the documented concurrency
of the run, then to **core-hours**:

```
core_hours = runtime_seconds × n_cores / 3600
```

For the MatPES `matcalc` runs the models run single-process on GPU or CPU; we
report **CPU-equivalent core-hours** assuming `n_cores = 1` for the per-case
number (the matcalc ElasticityCalc is single-threaded relax + stress-strain),
and separately record the host's total core count for the node-hours figure.

**Cost arms (per element, then ×16):**

| Arm | Runtime source | Notes |
|-----|----------------|-------|
| A raw-1x1x1 | existing `layer2_outputs/` + a cache-warm re-run | the 1217.8 s total is cache-cold; report cache-warm |
| B corrected-1x1x1 | = A + bias-PCA compute (negligible, <1 s) | correction is post-hoc algebra |
| C ref-3x3x3 | existing `layer2_outputs_3x3x3_16elem/` | 1736.9 s total over 128 cases → per-element mean |
| D ensemble-1x1x1 | = A × 3 architectures (M3GNet, CHGNet, TensorNet) | need M3GNet + CHGNet 1×1×1 runs; TensorNet already in A |

**The cache confound must be killed.** The existing 1×1×1 total (1217.8 s) is
slower than 3×3×3 (519.5 s) purely because of one-time HuggingFace model
downloads (`layer2_supercell_evaluation.md` §2.2). For the mlip elastic benchmark, **all
cost numbers come from cache-warm runs** (models pre-downloaded). The protocol
task (t_f26f577b) must specify a warm-cache pre-step and discard cold-cache
timings from the headline.

### 2.5 What the headline table looks like

| Arm | MAE Cᵢⱼ (GPa) | Core-hours (16 elem) | vs corrected-1x1x1 |
|-----|---------------|----------------------|--------------------|
| A raw-1x1x1 | (compute) | (compute) | accuracy baseline |
| **B corrected-1x1x1** | **(compute)** | **(compute)** | **= 1.0×** |
| C ref-3x3x3 | (compute) | (compute) | cost ratio = 10× target |
| D ensemble-1x1x1 | (compute) | (compute) | cost ratio = 5× target |

The "(compute)" cells are filled by the execute task (t_90f20a91). The
synthesizer does not pre-fill them — that would be fabrication.

---

## 3. Figure plan (4 figures, all data-driven)

1. **Fig. 1 — Cost-accuracy frontier (the money figure).** X = core-hours
   (log), Y = MAE Cᵢⱼ (GPa). Four points: A, B, C, D, each with a 95% CI bar on
   MAE (bootstrap over 16 elements). Annotate the B→C and B→D cost ratios.
   This is the figure that goes in the funder brief.
2. **Fig. 2 — Supercell-size independence.** Per-element MAE at 1×1×1 vs 3×3×3
   for the matched Cu/Ni subset (scatter, y=x line). Caption: "ΔMAE = +0.03 GPa;
   finite-size effects are not the binding error source." Reuse
   `supercell_scaling_16elem_comparison.json`.
3. **Fig. 3 — Operator vs ensemble, per element.** Grouped bar: for each of 16
   elements, three bars (raw single, corrected single, ensemble mean). Color
   the winner. Shows *where* the operator wins (hypothesis: BCC transition
   metals) and where it loses (noble metals, per Layer-1 pattern).
4. **Fig. 4 — Error stratification by bonding class.** Box plot of per-element
   MAE grouped: alkaline-earth FCC (Ca, Sr), noble FCC (Cu, Ag, Au),
   post-transition (Al), transition BCC+FCC. Reuse the §6.3 stratification
   from `projection-law-round2-results.md`. Establishes the error floor is
   physics-driven, not protocol-driven.

All four figures are generated from `mlip_elastic_benchmark_results.json` by a single script
the execute task produces. Static PNG + the dashboard (t_2f7fc928) reads the
same JSON.

---

## 4. Risk register (what can kill the claim, and the pre-planned response)

| Risk | Likelihood | Impact | Pre-planned response |
|------|-----------|--------|----------------------|
| **Operator does NOT beat ensemble on MLIPs** (H4 fails at Layer 2 as it was inconclusive at Layer 1) | Medium | Fatal to headline | Report it honestly. Pivot headline to the *supercell-independence* cost saving (B vs C), which is already demonstrated. The 10× claim survives even if the 5× ensemble claim does not. Pre-register this fallback in the protocol. |
| **QET≡TensorNet alias inflates "4-model ensemble"** | Certain (already observed) | Misleading headline | Drop QET from roster; 3 architectures only. Document in §2.2. |
| **1×1×1 cost is cache-cold, not comparable** | Certain (already observed) | Understates cost saving | All headline costs from cache-warm runs. §2.4. |
| **r2SCAN targets are synthesized (bulk-modulus shift), not measured** | Certain | Weakens "DFT reference" framing | Report PBE-only headline against `TPBE_0K`; r2SCAN as supplement. State the approximation in methods. |
| **TensorNet/PBE "best model" is chosen post-hoc** | Medium | Selection bias | Report the operator result for *all three* architectures in the supplement; headline uses the pre-specified best (lowest grid MAE) with selection acknowledged. |
| **Single random seed / single relax per case** | Medium | No variance estimate | Run 3 seeds on a 4-element subset (Ca, Cu, Fe, Cr — one per bonding class) for a variance bar; headline stays single-seed with the subset variance reported. |
| **Cr is a pathological outlier (43.5 GPa MAE)** | Certain | Skews means | Report both mean and median MAE; the median (14.12 GPa) is the more defensible headline. Pre-specify a robust metric. |

---

## 5. Child task dependency chain (binding)

The 6 children were created as flat siblings of this parent. That is wrong for
execution order. The real chain is:

```
t_f26f577b (protocol)  ──┬──> t_90f20a91 (execute + curate results)
                         │         │
                         │         ├──> t_4596db0d (HPC artifact)
                         │         │
                         │         └──> t_fc2f8d24 (preprint)  ──┐
                         │                                        ├──> t_715ce4cf (funder brief)
                         │                                        │
                         └────────────────────────────────────────> t_2f7fc928 (dashboard)
```

- **t_f26f577b (researcher, protocol)** is the critical path head. Nothing
  executes until its `mlip-elastic-benchmark-protocol-2026-06-27.md` + config JSON exist. It
  should base its protocol on THIS document (the design is already frozen
  here); its job is to translate §2 into a runnable config + the exact SLURM/GCP
  invocation matrix.
- **t_90f20a91 (devops, execute)** depends on the protocol. Produces
  `mlip_elastic_benchmark_results.json`. This is the gating artifact for the preprint,
  dashboard, and funder brief.
- **t_4596db0d (software-engineer, HPC artifact)** depends on the protocol
  (needs the config) but can proceed in parallel with execute once the config
  exists. Its smoke test validates the protocol's reproducibility.
- **t_fc2f8d24 (synthesizer, preprint)** depends on execute (needs the numbers).
- **t_2f7fc928 (software-engineer, dashboard)** depends on execute (needs the
  JSON). Can proceed in parallel with the preprint.
- **t_715ce4cf (synthesizer, funder brief)** depends on the preprint (needs the
  distilled headline). It is the terminal task.

I will wire these dependencies via `kanban_link` so the dispatcher fans out in
the correct order, not all at once.

---

## 6. Scientific caveats that MUST appear in every downstream artifact

These are non-negotiable. Any child task that omits them is producing a
misleading document.

1. **r2SCAN targets are approximated.** The `Tr2SCAN_0K` tensors are PBE
   tensors scaled by a scalar bulk-modulus ratio (Liu 2024). This assumes shear
   constants scale with the bulk modulus, which is not generally true. Al, Ca,
   Sr have no r2SCAN shift at all (`shift_factor = 1.0`). **Headline numbers
   should be reported against `TPBE_0K`; r2SCAN is a sensitivity check.**
2. **Au uses a PW91-GGA fallback**, not PBE (no stable PBE Au tensor was found
   in de Jong 2015, AFLOW, OQMD, JARVIS, or Alexandria). Document as a
   provenance caveat.
3. **QET≡TensorNet** (§2.2). The roster is 3 architectures, not 4.
4. **The operator is untested on MLIPs at scale.** Layer-1 (classical
   potentials) won 4/8. The mlip elastic benchmark is the first Layer-2 MLIP test of H4. If
   it fails, we pivot to the supercell-independence cost story (§4 risk 1).
5. **Bias is leave-one-out.** Any in-sample bias fit invalidates the claim.
6. **Costs are cache-warm, single-seed, single-relax.** Variance is estimated
   on a 4-element subset only.

---

## 7. Reproducibility contract (the single-command promise)

The HPC artifact (t_4596db0d) must satisfy: a fresh clone + one command produces
`mlip_elastic_benchmark_results.json` that byte-matches (within model nondeterminism) the
execute task's output. Concretely:

- `Apptainer.def` pins Python + matgl + matcalc + pymatgen + numpy versions.
- `config/mlip_elastic_benchmark.yaml` lists the 16 elements × 3 architectures × 2 functionals
  × 2 supercells (1×1×1, 3×3×3) = 192 cases, plus the LOO bias-PCA step.
- `run.sh` executes the matrix, writes per-case JSON to `results/`, then
  `aggregate.py` rolls them into `mlip_elastic_benchmark_results.json`.
- `verify.py` runs a 2-element smoke test (Ca + Cu, one per bonding class) in
  <5 min and checks the schema.

The execute task (t_90f20a91) produces the canonical `mlip_elastic_benchmark_results.json`;
the artifact task packages the *recipe* to reproduce it. They must agree on the
schema. The schema is:

```json
{
  "schema_version": "lupine.mlip_elastic_benchmark.v1",
  "provenance": {"git_sha": "...", "matpes_release": "2025.2", "host": "...", "run_at": "..."},
  "arms": {
    "raw-1x1x1":       {"mae_cij": ..., "core_hours": ..., "n_cases": 16},
    "corrected-1x1x1": {"mae_cij": ..., "core_hours": ..., "n_cases": 16, "bias_method": "LOO-PCA"},
    "ref-3x3x3":       {"mae_cij": ..., "core_hours": ..., "n_cases": 16},
    "ensemble-1x1x1":  {"mae_cij": ..., "core_hours": ..., "n_cases": 16, "n_models": 3}
  },
  "cost_ratios": {"corrected_vs_ref": ..., "corrected_vs_ensemble": ...},
  "per_element": [ {"element": "Cu", "arm": "corrected-1x1x1", "c11": ..., "c12": ..., "c44": ..., "mae": ..., "runtime_s": ...}, ... ],
  "caveats": ["r2SCAN targets approximated", "QET=TensorNet alias deduplicated", "cache-warm costs", "Au PW91 fallback"]
}
```

---

## Appendix A — Element roster and bonding classes

| Class | Elements | N | Expected MAE tier |
|-------|----------|---|-------------------|
| Alkaline-earth FCC | Ca, Sr | 2 | low (~3 GPa) |
| Noble / coinage FCC | Cu, Ag, Au | 3 | medium (~12 GPa) |
| Post-transition | Al | 1 | medium (~15 GPa) |
| 3d/4d transition FCC | Ni, Pd, Pt | 3 | high (~22 GPa) |
| 3d/4d/5d transition BCC | Cr, Fe, Mo, Nb, Ta, V, W | 7 | high (~22 GPa), Cr pathological |

## Appendix B — Source-file line references for every headline number

- 16-element 3×3×3 mean MAE 17.90 GPa: `supercell_scaling_16elem_comparison.json` summary `3x3x3_16elem` (112 cases) + Cu/Ni 3×3×3 (16 cases) merged.
- Cu/Ni 1×1×1 vs 3×3×3 ΔMAE +0.03 GPa: same file, `1x1x1` vs `3x3x3` summaries.
- QET/PBE best model 13.25 GPa: `projection-law-round2-results.md` Table 7 (line ~290).
- QET≡TensorNet alias: `layer2_supercell_evaluation.md` §3.3 (lines 159–174).
- Cache-cold confound: `layer2_supercell_evaluation.md` §2.2 (lines 94–100).
- Operator Layer-1 result 4/8: `projection-law-round2-results.md` §3.2 Table 3.
- Operator API: `lupine/python/lupine/operator.py:72` (`correct`), `:122` (`leave_one_out_calibration`), `:139` (`compare_operator_to_ensemble`).
