# Halide cation-vacancy migration-barrier panel (CI-NEB)

Generated: 2026-07-13T17:04:36.589281+00:00  
Schema: `lupine.kinetics_barrier_panel.v1`  
Device: cuda | Supercell: 3^3 rocksalt (one cation vacancy) | 5 interior images, climb=True, improvedtangent tangent, fmax = 0.05 eV/A

Barrier = E_saddle - E_endpoint(relaxed) from the climbing-image NEB band; the <110> nearest-neighbour cation hop is symmetric, so forward ~ backward and the asymmetry is a convergence check.

## Forward barrier (eV) per compound x model

| Compound | mace-mp-medium | Rel. dispersion | Spread (eV) | Max asym (eV) |
|---|---|---|---|---|
| LiF | 0.570 | n/a | n/a | 0.0000 |
| LiCl | 0.492 | n/a | n/a | 0.0000 |
| LiBr | 0.381 | n/a | n/a | 0.0000 |
| LiI | 0.259 | n/a | n/a | 0.0000 |
| NaCl | 0.606 | n/a | n/a | 0.0000 |

## Reference comparison (model - reference, eV)

| Compound | Reference (eV) | mace-mp-medium | Median delta |
|---|---|---|---|
| LiF | 0.660 | -0.090 | -0.090 |
| LiCl | 0.410 | 0.082 | 0.082 |
| LiBr | 0.390 | -0.009 | -0.009 |
| LiI | 0.380 | -0.121 | -0.121 |
| NaCl | 0.690 | -0.084 | -0.084 |

## Provenance

- Relaxed a0 per (compound, model) reused from C:/Users/alexw/Downloads/lupine-rhizo/data/climate_targets/halide_panel/report.json (subjects[*].per_model[*].properties.a0, generated_at 2026-07-13T13:17:10.087939+00:00); per-cell provenance recorded.
- Kinetics references loaded from C:/Users/alexw/Downloads/lupine-rhizo/data/candidates/kinetics_targets.json.
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
