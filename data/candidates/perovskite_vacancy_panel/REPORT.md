# Perovskite B-site vacancy panel (neutral, referenced)

Generated: 2026-07-13T14:33:13.290513+00:00  
Schema: `lupine.perovskite_vacancy_panel.v1`  
Device: cuda | Supercell: 2x2x2 (one B-site vacancy, fixed-cell position relaxation)  
E_vac = E_defect + mu - E_bulk (metal-rich-limit neutral vacancy; fmax = 0.01 eV/A)

Article context: target class #5 failure mode — uMLIPs are expected to misestimate Sn vacancy formation (under-coordinated neighbours), so the H3 signature is E_vac dispersing MORE across models than the same compounds' bulk properties.

## E_vac (eV) per compound x model

| Compound | Vacancy | chgnet | mace-mp-small | mace-mp-medium | mace-mpa-0-medium | Rel. dispersion | Spread (eV) |
|---|---|---|---|---|---|---|---|
| CsSnI3 | V_Sn | FAILED | 1.004 | 0.818 | 1.560 | 0.739 | 0.742 |
| CsSnBr3 | V_Sn | FAILED | 1.008 | 1.068 | 1.523 | 0.482 | 0.515 |
| CsSnCl3 | V_Sn | FAILED | 0.808 | 1.057 | 1.891 | 1.024 | 1.082 |
| CsGeI3 | V_Ge | -0.408 | 0.438 | 0.362 | 1.355 | 4.407 | 1.763 |
| CsPbI3 | V_Pb | 1.068 | 1.782 | 1.259 | 2.814 | 1.148 | 1.745 |

## Defect vs bulk cross-model dispersion (bulk from round-1 report)

| Compound | E_vac disp | a0 disp | b0 disp | c11 disp | E_vac/a0 | E_vac/b0 | E_vac/c11 |
|---|---|---|---|---|---|---|---|
| CsSnI3 | 0.739 | 0.0095 | 0.346 | 0.764 | 77.8 | 2.1 | 1.0 |
| CsSnBr3 | 0.482 | 0.0080 | 0.225 | 0.621 | 60.3 | 2.1 | 0.8 |
| CsSnCl3 | 1.024 | 0.0086 | 0.371 | 0.724 | 119.6 | 2.8 | 1.4 |
| CsGeI3 | 4.407 | 0.0127 | 0.130 | 0.520 | 345.8 | 34.0 | 8.5 |
| CsPbI3 | 1.148 | 0.0048 | 0.153 | 0.464 | 237.1 | 7.5 | 2.5 |

## Elemental chemical potentials mu (eV/atom) per model

| Species | Reference | chgnet | mace-mp-small | mace-mp-medium | mace-mpa-0-medium |
|---|---|---|---|---|---|
| Ge | diamond | -4.4567 | -4.5972 | -4.5258 | -4.6103 |
| Pb | fcc | -3.6641 | -3.6903 | -3.6965 | -3.7051 |
| Sn | diamond | n/a | -3.9658 | -3.9212 | -3.9947 |

## Provenance

- Relaxed a0 per (compound, model) reused from C:/Users/alexw/Downloads/lupine-rhizo/data/candidates/round1/report.json (candidates[*].per_model[*].properties.a0, generated_at 2026-07-13T14:14:06.554750+00:00); no re-relaxation.
- Bulk a0/b0/c11 dispersions quoted from the same round-1 report (gates.concordance blocks, thresholds.v2 baseline).
- Elemental references: Sn -> explicit 'diamond' override (alpha-Sn; ASE's default Sn reference state is beta-Sn bct, unsupported by compute_referenced_vacancy_formation); Ge -> ASE default 'diamond'; Pb -> ASE default 'fcc'. mu relaxed per model by the module's recentring EOS scan.
- Dispersion metric: (max - min) / |median| across models (lupine_distill.statics.gates.relative_dispersion).

## Honesty notes

- Neutral vacancies only: no charged defects, no electrostatic alignment or image-charge corrections; for these halide perovskites the physical vacancy is usually charged (V_Sn'' etc.), so values are the metal-rich-limit NEUTRAL formation energy.
- Finite-size: single 2x2x2 (40-atom) supercell, one vacancy, fixed-cell position relaxation; no supercell-size extrapolation. Defect-defect interaction under PBC is NOT converged out.
- Athermal: T=0 statics, no vibrational or configurational entropy.
- Chemical potential is the metal-rich limit: mu(X) from the relaxed elemental bulk under the SAME calculator (alpha-Sn diamond for Sn — ASE's default beta-Sn bct reference is unsupported by the module and alpha-Sn is the T=0 ground state; diamond-Ge; fcc-Pb). Halide-rich conditions would shift all values by the compound formation energy.
- Cubic perovskite reference phase: a0 per (compound, model) is reused from data/candidates/round1/report.json (per_model properties a0); the room-temperature phases of several of these compounds are distorted (orthorhombic/monoclinic) — this panel probes the cubic prototype.
- No thresholds exist for E_vac dispersion: values are descriptive. Deriving per-property vacancy flag/refuse percentiles (as thresholds.v2 did for a0/B0/C11/C12/C44) is a Round-3 calibration need.
- Model non-independence: mace-mp-small and mace-mp-medium share architecture and training data; dispersion is ensemble spread, not independent-error spread.
