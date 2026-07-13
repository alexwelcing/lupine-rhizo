# Discovery gates - reference-free verdicts on a real Li-S case

Generated: 2026-07-02T18:17:27.899011+00:00 | device: cuda | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium

Two subjects: **Li2S antifluorite** (known-good) and **LiS rocksalt** (speculative 1:1 composition). All gates are reference-free: no experimental or DFT value for either subject is consulted.

## Concordance thresholds (data-derived, not invented)

- metric: `(max - min) / |median|` across models, per property
- flag at >= **0.2490** (p75), refuse at >= **0.3848** (p95)
- derivation: p75/p95 of the per-material cross-model relative dispersion (max-min)/|median| of B0 over 21 Y-matrix materials x 4 models in C:/Users/alexw/Downloads/lupine-rhizo/data/y_matrix_runs/bound (schema lupine.mlip.calc_evidence.v1)
- baseline samples: 21 materials; per-material dispersions recorded in report.json

Threshold transfer: the p75/p95 baseline is measured on B0 dispersions and applied to a0/B0/C11/C12/C44 alike. a0 disperses less than B0 (lenient there); shear constants typically disperse more (strict there). This is a documented proxy, not a per-property calibration.

## Li2S_antifluorite - **REFUSED**

known-good reference subject (cubic antifluorite, mp-1153-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.7015 | 29.4 | 39.0 | 15.4 | 16.8 | 20.8% | PASS | 5.5 |
| mace-mp-small | 5.7219 | 34.1 | 64.9 | 18.9 | 29.8 | 0.3% | PASS | 7.4 |
| mace-mp-medium | 5.7228 | 34.6 | 68.0 | 17.7 | 23.9 | 0.4% | PASS | 4.3 |
| mace-mpa-0-medium | 5.7303 | 38.2 | 78.1 | 18.5 | 34.8 | 0.3% | PASS | 4.7 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=23.6, C11+2C12=69.7, C44=16.8 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=46.0, C11+2C12=102.7, C44=29.8 GPa | 0.5 |
| born (mace-mp-medium) | PASS | C11-C12=50.3, C11+2C12=103.4, C44=23.9 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=59.6, C11+2C12=115.0, C44=34.8 GPa | 0.3 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | FLAG | dispersion=0.258 | 0.000 |
| concordance (c11) | REFUSE | dispersion=0.589 | 0.000 |
| concordance (c12) | PASS | dispersion=0.194 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.669 | 0.000 |
| dynamic_return | PASS | dE=1.32e-05 eV/atom, max disp=0.022 A, 39 steps, 96 atoms (mace-mp-medium) | 9.4 |

Subject wall time: **31.3 s**

## LiS_rocksalt - **REFUSED**

speculative subject: unproven 1:1 Li-S composition

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.9588 | 53.0 | 120.0 | 64.7 | -7.1 | 56.8% | FAIL | 5.3 |
| mace-mp-small | 5.0582 | 49.2 | 59.9 | 44.2 | -18.2 | 0.5% | FAIL | 3.5 |
| mace-mp-medium | 5.0230 | 53.2 | 91.5 | 34.5 | -14.3 | 0.5% | FAIL | 3.6 |
| mace-mpa-0-medium | 4.9590 | 40.1 | 89.4 | 15.8 | -38.4 | 0.6% | FAIL | 4.4 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | FAIL | C11-C12=55.3, C11+2C12=249.3, C44=-7.1 GPa | 0.3 |
| born (mace-mp-small) | FAIL | C11-C12=15.7, C11+2C12=148.3, C44=-18.2 GPa | 0.2 |
| born (mace-mp-medium) | FAIL | C11-C12=57.1, C11+2C12=160.5, C44=-14.3 GPa | 0.2 |
| born (mace-mpa-0-medium) | FAIL | C11-C12=73.6, C11+2C12=121.1, C44=-38.4 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.020 | 0.000 |
| concordance (b0) | FLAG | dispersion=0.257 | 0.000 |
| concordance (c11) | REFUSE | dispersion=0.664 | 0.000 |
| concordance (c12) | REFUSE | dispersion=1.242 | 0.000 |
| concordance (c44) | REFUSE | dispersion=1.925 | 0.000 |
| dynamic_return | FAIL | dE=-3.41e-01 eV/atom, max disp=2.289 A, 271 steps, 64 atoms (mace-mp-medium) | 46.1 |

Subject wall time: **62.8 s**

## Scope and honesty notes

- Born stability is exact physics (necessary conditions only); concordance thresholds are percentiles of our own measured baseline; no threshold in this report was invented.
- Threshold transfer: the p75/p95 baseline is measured on B0 dispersions and applied to a0/B0/C11/C12/C44 alike. a0 disperses less than B0 (lenient there); shear constants typically disperse more (strict there). This is a documented proxy, not a per-property calibration.
- The dynamic-return gate is a finite-rattle basin-return probe, NOT a phonon calculation; instabilities incommensurate with the 2x2x2 supercell are invisible to it.
- Thermodynamic (hull-level) gates are OUT OF SCOPE in this run: rocksalt LiS may be mechanically stable while remaining thermodynamically unstable against decomposition (e.g. to Li2S + S); deciding that requires the formation-energy lane.
- Cubic symmetry of each relaxed subject is assumed by construction (both prototypes are cubic); the elastic probe measures the cubic C11/C12/C44 only.
