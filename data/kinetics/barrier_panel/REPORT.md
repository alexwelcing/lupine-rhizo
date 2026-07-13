# Halide cation-vacancy migration-barrier panel (CI-NEB)

Generated: 2026-07-13T16:08:29.682684+00:00  
Schema: `lupine.kinetics_barrier_panel.v1`  
Device: cuda | Supercell: 2^3 rocksalt (one cation vacancy) | 5 interior images, climb=True, improvedtangent tangent, fmax = 0.05 eV/A

Barrier = E_saddle - E_endpoint(relaxed) from the climbing-image NEB band; the <110> nearest-neighbour cation hop is symmetric, so forward ~ backward and the asymmetry is a convergence check.

## Forward barrier (eV) per compound x model

| Compound | chgnet | mace-mp-small | mace-mp-medium | mace-mpa-0-medium | Rel. dispersion | Spread (eV) | Max asym (eV) |
|---|---|---|---|---|---|---|---|
| LiF | 0.481 | 0.631 | 0.589 | 0.677 | 0.321 | 0.196 | 0.0000 |
| LiCl | 0.484 | 0.582 | 0.534 | 0.439 | 0.282 | 0.143 | 0.0000 |
| LiBr | 0.367 | 0.498 | 0.402 | 0.441 | 0.311 | 0.131 | 0.0000 |
| LiI | 0.276 | 0.448 | 0.272 | 0.332 | 0.582 | 0.177 | 0.0000 |
| NaCl | 0.526 | 0.564 | 0.656 | 0.655 | 0.213 | 0.130 | 0.0000 |

_No kinetics references file was found; dispersions are reported without literature comparison._

## Provenance

- Relaxed a0 per (compound, model) reused from C:/Users/alexw/Downloads/lupine-rhizo/data/climate_targets/halide_panel/report.json (subjects[*].per_model[*].properties.a0, generated_at 2026-07-13T13:17:10.087939+00:00); per-cell provenance recorded.
- No kinetics references file at C:/Users/alexw/Downloads/lupine-rhizo/data/candidates/kinetics_targets.json; panel ran without reference comparison.
- Dispersion metric: (max - min) / |median| across models on the FORWARD barrier (lupine_distill.statics.gates.relative_dispersion).
- Endpoints from lupine_distill.statics.build_cation_vacancy_hop (deterministic first-cation vacancy, nearest <110> cation hopper); band from compute_migration_barrier (both endpoints relaxed, IDPP interpolation, two-stage climbing-image NEB, improved tangent).

## Honesty notes

- Neutral vacancy hop only: no charged defects, no electrostatic alignment or image-charge corrections; the physical migrating defect in these halides is usually charged (V_Li'), so values are the NEUTRAL-cell CI-NEB barrier.
- Finite-size: single 2x2x2 (64-atom) rocksalt supercell, one vacancy, fixed-cell CI-NEB; defect-defect and elastic image interactions under PBC are NOT converged out and no supercell extrapolation is done.
- Athermal: T=0 minimum-energy-path barrier; no attempt frequencies, no harmonic prefactors, no finite-temperature or quantum corrections — this is E_m, not a diffusivity.
- Single mechanism: only the nearest-neighbour <110> cation-vacancy hop is probed; other mechanisms (anion hops, curved <110> paths, interstitialcy) are out of scope.
- Symmetric hop: forward and backward barriers should coincide; the recorded asymmetry is a numerical convergence check, not physics.
- No thresholds exist for barrier dispersion: values are descriptive. Deriving kinetics flag/refuse percentiles is future calibration work.
- Model non-independence: mace-mp-small and mace-mp-medium share architecture and training data; dispersion is ensemble spread, not independent-error spread.
