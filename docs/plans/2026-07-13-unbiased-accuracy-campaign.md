# Preregistration: Unbiased Raw-MLIP vs Lupine-Enhanced-MLIP Accuracy Campaign (Round 1)

- **Status:** PRE-REGISTERED, written BEFORE any candidate prediction is run.
- **Date frozen:** 2026-07-13
- **Design authority:** fixed by session lead; this document fleshes out but does not alter the arm/metric design.
- **Targets file (frozen with this doc):** `data/candidates/round1_targets.json` (`lupine.campaign_targets.v1`)
- **Instrument:** local lane only (CPU/GPU per standing rules of the discovery lane); no cloud promotion in Round 1.

## 1. Question

Does the Lupine enhancement layer (per-class median-bias de-bias + v2 gates as selective prediction) improve the accuracy and honesty of foundation MLIP property predictions on materials *outside* the calibration corpus, relative to the same MLIPs used raw?

This is a methodology demonstration on a small, fixed candidate set — not a survey-scale benchmark.

## 2. Candidates (fixed; no additions after freeze)

Two classes only. MOF / cathode / catalyst classes are **deferred to cloud promotion** (off-instrument locally).

### Group A — HEA fcc Cantor-subset (`hea-fcc`)
| id | formula | structure | a0 ref | B0 ref | Cij ref |
|---|---|---|---|---|---|
| hea-cocrni | CoCrNi | fcc random solid solution | 3.56 Å (exp, Laplanche Scripta Mater. 177 (2020) 44–48) | 189 GPa (exp, derived from single-crystal Cij) | C11 249 / C12 159 / C44 138 GPa (exp, RUS single crystal, same source) |
| hea-cocrfeni | CoCrFeNi | fcc RSS | 3.57 Å (exp consensus, ±0.01) | 163 GPa (exp, derived from Wu et al. Acta Mater. 81 (2014) Table II: G=84, ν=0.28) | null — no published experimental single-crystal Cij found |
| hea-coni | CoNi | fcc RSS | 3.535 Å (other: Vegard estimate) | 172 GPa (exp, derived from Wu 2014: G=84, ν=0.29) | null |
| hea-feni | FeNi (50:50) | fcc RSS | 3.582 Å (exp, tetrataenite XRD; disorder caveat) | 176.7 GPa (exp, Singh & Guruswamy AIP Adv. 13 (2023) 115112) | null — measured in AIP Adv. 2023 but numbers not retrieved; fill before freeze or exclude FeNi from Cij leg |

### Group B — Lead-free halide perovskites, cubic 5-atom ABX3 (`halide-perovskite`)
| id | formula | a0 ref (phase/T caveat) | B0 ref | Cij ref | MP id |
|---|---|---|---|---|---|
| hp-cssncl3 | CsSnCl3 | 5.579 Å exp @403 K (cubic only >~379 K) | 22.7 GPa DFT-PBE (Roknuzzaman Sci. Rep. 7 (2017) 14025) | 50.66 / 8.71 / 6.01 GPa DFT-PBE (same) | mp-1070375 |
| hp-cssnbr3 | CsSnBr3 | 5.804 Å exp RT (cubic at RT) | 19.09 GPa DFT-PBE | 43.89 / 6.69 / 5.21 GPa DFT-PBE | mp-27214 |
| hp-cssni3 | CsSnI3 | 6.219 Å exp, B-α cubic ~500 K (RT black phase is orthorhombic) | 17.59 GPa DFT (Hayatullah APPA 124 (2013); WEAK, method spread) | 21.34 / 1.22 / 5.74 GPa DFT-PBE (WEAK — see targets file) | mp-614013 |
| hp-csgei3 | CsGeI3 | null (cubic only >550 K; HT value unpinned; guess 6.05 Å) | 18.89 GPa DFT-PBE | 40.32 / 8.18 / 8.87 GPa DFT-PBE | mp-28377 (R3m RT phase) |
| hp-cspbi3-control | CsPbI3 (known-good control) | 6.2894 Å exp @634 K (Trots & Myagkota JPCS 69 (2008)) | 14.76 GPa DFT-PBE (2025 pressure-DFT study) | 34.84 / 4.73 / 3.66 GPa DFT-PBE | null (cubic id unverified) |

Full citations, kinds (exp / DFT-PBE / other), and per-value caveats live in the targets JSON. **Values marked null are excluded from the corresponding property leg; they must not be filled after any prediction has run.**

## 3. Arms (per candidate × property)

Properties: `a0` (relaxed lattice parameter), `B0` (bulk modulus), `C11/C12/C44` (where reference exists).

1. **Raw single-MLIP** — one prediction per local model:
   `chgnet`, `mace-mp-small`, `mace-mp-medium`, `mace-mpa-0-medium`.
   Standard relax-from-`lattice_guess_angstrom` → EOS → strain-Cij pipeline (protocol as in `docs/plans/mlip-elastic-benchmark-protocol-2026-06-27.md`).
2. **Lupine-enhanced** — per-(model, property, class) **median-bias de-bias**. Calibration sets are DISJOINT from the candidates:
   - HEA `a0`/`B0`: fcc-metal subset (Ag, Al, Au, Ca, Cu, Ni, Pd, Pt, Sr) of the 21-material baseline.
   - Perovskite `a0`/`B0`: full 21-material baseline.
   - HEA `C11/C12/C44`: bias from the 16-metal Cij validation set (`mlip-elastic-benchmark/direction-shift-validation-2026-07-13`) where model coverage allows; otherwise the Cij prediction is issued **uncorrected** (and labeled so).
   - Disjointness note: calibration materials are elemental; candidates are multi-component alloys/compounds. Elemental Ni appearing in the calibration set and as a *constituent* of HEA candidates is recorded, not hidden — material-level disjointness holds.
3. **LAMMPS classical MEAM leg** (Group A only) — `MoCoNiVFeAlCr_2nn.meam`, same property pipeline, as a classical-potential floor.
4. **Gates arm** — v2 gates: per-property concordance + Born stability + dynamic-return, evaluated in the standing early-stop order. Scored as **SELECTIVE PREDICTION**: coverage vs risk, i.e. median |rel err| on issued predictions vs refused predictions.

## 4. Metrics (fixed)

- Per-property **median and mean |relative error|** vs the pre-registered reference, per arm.
- **Directional sign test** for the de-bias corrections (does the correction move the prediction toward the reference more often than away; exact binomial).
- **Risk–coverage table** for the gates arm (coverage %, median |rel err| issued, median |rel err| refused).

### Success criteria (pre-registered)
- **De-bias:** reduces median |rel err| for **≥ 2 of 3 properties per group**, with sign-test **p < 0.1**.
- **Gates:** refused predictions have higher raw error than issued ones — descriptive; **report either way**.
- CsSnI3 Cij and CsGeI3 a0 are excluded from headline criteria (weak/null references, flagged pre-run in the targets file).

### Round-2 trigger
After Round-1 analysis, new/modified theorems are proposed; the **identical protocol re-runs** with the enhanced layer. Round-2 prereg follows the axis-based format per standing memory.

## 5. Fixed run parameters

- HEA RSS supercells: 3×3×3 conventional fcc (108 atoms), random equiatomic site occupation, **fixed RNG seed 20260713**, one configuration per candidate (identical config across all arms/models).
- Perovskites: 5-atom cubic unit cell, full cell+ion relax under Pm-3m symmetry constraint; if a model breaks symmetry (CsGeI3 R3m well), record which minimum was scored.
- B0 via Birch–Murnaghan EOS fit (±4% volume, 9 points); Cij via ±0.5% strains, per the elastic-benchmark protocol.
- No GPU-exclusive steps required; runs stay on the local lane.

## 6. Honesty notes (pre-registered limitations)

1. **RSS supercells are only statistically cubic.** A single 108-atom random configuration has residual anisotropy; cubic Cij extraction is an approximation. The fixed seed is recorded; per-configuration scatter is NOT sampled in Round 1.
2. **Phase/temperature convention mismatches.** Several perovskite "cubic" references are high-temperature phases (CsSnCl3 @403 K, CsSnI3 ~500 K, CsPbI3 @634 K, CsGeI3 >550 K) compared against athermal 0 K relaxations; each mismatch is flagged per-value in the targets JSON. Thermal expansion biases exp a0 high relative to athermal predictions — this affects raw and de-biased arms identically, which is exactly why the per-class de-bias is the treatment under test.
3. **Derived reference values.** HEA B0 references are derived from polycrystal G, ν (Wu et al. 2014) or single-crystal Cij (Laplanche 2020) rather than direct EOS measurements; derivations are stated inline.
4. **Small n.** 4 + 5 candidates demonstrate methodology, not survey-scale claims. No per-group statistical generalization beyond the stated sign tests.
5. **Null discipline.** CoCrFeNi/CoNi/FeNi experimental Cij and CsGeI3 cubic a0 could not be verified by the freeze; they are null and their legs are excluded rather than backfilled from memory.
6. **Deferred classes.** MOF / cathode / catalyst candidates are deferred to cloud promotion; they are off-instrument locally and out of scope for Round 1.

## 7. Freeze declaration

The reference values in `data/candidates/round1_targets.json` and the arms/metrics/success criteria above were fixed on 2026-07-13 **before** any Round-1 prediction was executed. Any post-freeze edit to references or criteria invalidates Round 1 and requires a new preregistration.
