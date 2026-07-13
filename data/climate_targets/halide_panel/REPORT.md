# Discovery gates - reference-free verdicts on a real Li-S case

Generated: 2026-07-13T02:33:05.607441+00:00 | device: cuda | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium

Two subjects: **Li2S antifluorite** (known-good) and **LiS rocksalt** (speculative 1:1 composition). All gates are reference-free: no experimental or DFT value for either subject is consulted.

## Concordance thresholds (data-derived, not invented)

- metric: `(max - min) / |median|` across models, per property
- flag at >= **0.2490** (p75), refuse at >= **0.3848** (p95)
- derivation: p75/p95 of the per-material cross-model relative dispersion (max-min)/|median| of B0 over 21 Y-matrix materials x 4 models in C:/Users/alexw/Downloads/lupine-rhizo/data/y_matrix_runs/bound (schema lupine.mlip.calc_evidence.v1)
- baseline samples: 21 materials; per-material dispersions recorded in report.json

Threshold transfer: the p75/p95 baseline is measured on B0 dispersions and applied to a0/B0/C11/C12/C44 alike. a0 disperses less than B0 (lenient there); shear constants typically disperse more (strict there). This is a documented proxy, not a per-property calibration.

## LiF_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-1138-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.0908 | 53.6 | 98.6 | 43.6 | 32.2 | 15.5% | PASS | 8.5 |
| mace-mp-small | 4.0793 | 62.6 | 110.6 | 38.9 | 49.3 | 0.3% | PASS | 8.0 |
| mace-mp-medium | 4.0933 | 59.0 | 92.1 | 42.0 | 50.0 | 0.6% | PASS | 4.9 |
| mace-mpa-0-medium | 4.1000 | 65.8 | 114.3 | 41.2 | 60.2 | 0.3% | PASS | 5.5 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=55.0, C11+2C12=185.7, C44=32.2 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=71.7, C11+2C12=188.4, C44=49.3 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=50.1, C11+2C12=176.0, C44=50.0 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=73.1, C11+2C12=196.7, C44=60.2 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | PASS | dispersion=0.200 | 0.000 |
| concordance (c11) | PASS | dispersion=0.212 | 0.000 |
| concordance (c12) | PASS | dispersion=0.111 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.565 | 0.000 |
| dynamic_return | PASS | dE=2.13e-05 eV/atom, max disp=0.012 A, 31 steps, 64 atoms (mace-mp-medium) | 6.2 |

Subject wall time: **33.0 s**

## LiCl_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-22905-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.1484 | 33.7 | 69.4 | 37.5 | 18.8 | 42.9% | PASS | 7.7 |
| mace-mp-small | 5.1407 | 36.7 | 60.8 | 24.6 | 28.2 | 0.2% | PASS | 3.6 |
| mace-mp-medium | 5.1297 | 33.1 | 53.0 | 23.4 | 24.6 | 0.5% | PASS | 4.6 |
| mace-mpa-0-medium | 5.1836 | 39.0 | 61.9 | 29.1 | 26.4 | 2.6% | PASS | 5.7 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=31.9, C11+2C12=144.4, C44=18.8 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=36.2, C11+2C12=109.9, C44=28.2 GPa | 0.1 |
| born (mace-mp-medium) | PASS | C11-C12=29.7, C11+2C12=99.8, C44=24.6 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=32.8, C11+2C12=120.1, C44=26.4 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.010 | 0.000 |
| concordance (b0) | PASS | dispersion=0.168 | 0.000 |
| concordance (c11) | FLAG | dispersion=0.267 | 0.000 |
| concordance (c12) | REFUSE | dispersion=0.526 | 0.000 |
| concordance (c44) | FLAG | dispersion=0.373 | 0.000 |
| dynamic_return | PASS | dE=2.69e-05 eV/atom, max disp=0.015 A, 32 steps, 64 atoms (mace-mp-medium) | 5.4 |

Subject wall time: **27.0 s**

## LiBr_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-23259-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.5077 | 25.1 | 25.9 | 20.8 | 10.1 | 10.2% | PASS | 7.0 |
| mace-mp-small | 5.4985 | 24.3 | 38.0 | 17.5 | 19.9 | 0.2% | PASS | 3.8 |
| mace-mp-medium | 5.5067 | 25.8 | 40.6 | 18.5 | 17.6 | 0.2% | PASS | 4.7 |
| mace-mpa-0-medium | 5.5273 | 26.0 | 42.2 | 18.0 | 19.3 | 0.5% | PASS | 5.0 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=5.0, C11+2C12=67.5, C44=10.1 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=20.5, C11+2C12=72.9, C44=19.9 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=22.1, C11+2C12=77.5, C44=17.6 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=24.1, C11+2C12=78.3, C44=19.3 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | PASS | dispersion=0.064 | 0.000 |
| concordance (c11) | REFUSE | dispersion=0.416 | 0.000 |
| concordance (c12) | PASS | dispersion=0.184 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.534 | 0.000 |
| dynamic_return | PASS | dE=2.82e-05 eV/atom, max disp=0.016 A, 33 steps, 64 atoms (mace-mp-medium) | 4.9 |

Subject wall time: **25.4 s**

## LiI_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-22899-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 6.0145 | 20.0 | 24.9 | 20.8 | 9.4 | 10.8% | PASS | 7.2 |
| mace-mp-small | 6.0639 | 19.9 | 34.1 | 12.8 | 12.4 | 0.1% | PASS | 4.2 |
| mace-mp-medium | 6.0800 | 16.0 | 21.1 | 13.6 | 11.8 | 0.3% | PASS | 4.8 |
| mace-mpa-0-medium | 6.0512 | 19.4 | 30.6 | 13.8 | 15.5 | 0.0% | PASS | 5.4 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=4.1, C11+2C12=66.6, C44=9.4 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=21.3, C11+2C12=59.6, C44=12.4 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=7.5, C11+2C12=48.2, C44=11.8 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=16.9, C11+2C12=58.2, C44=15.5 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.011 | 0.000 |
| concordance (b0) | PASS | dispersion=0.206 | 0.000 |
| concordance (c11) | REFUSE | dispersion=0.469 | 0.000 |
| concordance (c12) | REFUSE | dispersion=0.590 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.507 | 0.000 |
| dynamic_return | PASS | dE=6.81e-05 eV/atom, max disp=0.083 A, 29 steps, 64 atoms (mace-mp-medium) | 4.2 |

Subject wall time: **25.8 s**

## NaCl_rocksalt - **REFUSED**

rocksalt control with existing a0/B0 Y-matrix cells

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.6955 | 25.0 | 41.7 | 21.5 | 6.0 | 12.7% | PASS | 5.3 |
| mace-mp-small | 5.6900 | 27.2 | 45.0 | 18.3 | 11.6 | 0.1% | PASS | 2.9 |
| mace-mp-medium | 5.6832 | 25.4 | 52.0 | 12.2 | 10.9 | 0.0% | PASS | 3.4 |
| mace-mpa-0-medium | 5.7135 | 20.9 | 42.8 | 9.7 | 12.4 | 0.9% | PASS | 3.8 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=20.2, C11+2C12=84.6, C44=6.0 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=26.7, C11+2C12=81.6, C44=11.6 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=39.8, C11+2C12=76.3, C44=10.9 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=33.1, C11+2C12=62.1, C44=12.4 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | FLAG | dispersion=0.249 | 0.000 |
| concordance (c11) | PASS | dispersion=0.234 | 0.000 |
| concordance (c12) | REFUSE | dispersion=0.774 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.571 | 0.000 |
| dynamic_return | PASS | dE=5.60e-05 eV/atom, max disp=0.030 A, 32 steps, 64 atoms (mace-mp-medium) | 4.8 |

Subject wall time: **20.2 s**

## MgO_rocksalt - **REFUSED**

oxide rocksalt control with existing a0/B0 Y-matrix cells

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.2536 | 133.5 | 208.2 | 78.3 | 86.4 | 8.9% | PASS | 3.7 |
| mace-mp-small | 4.2533 | 149.4 | 256.9 | 93.1 | 138.0 | 1.1% | PASS | 2.0 |
| mace-mp-medium | 4.2545 | 147.3 | 248.6 | 94.7 | 117.4 | 0.9% | PASS | 2.5 |
| mace-mpa-0-medium | 4.2565 | 148.1 | 265.3 | 88.9 | 135.9 | 0.3% | PASS | 2.7 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=129.9, C11+2C12=364.8, C44=86.4 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=163.7, C11+2C12=443.1, C44=138.0 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=153.9, C11+2C12=438.0, C44=117.4 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=176.5, C11+2C12=443.1, C44=135.9 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.001 | 0.000 |
| concordance (b0) | PASS | dispersion=0.107 | 0.000 |
| concordance (c11) | PASS | dispersion=0.226 | 0.000 |
| concordance (c12) | PASS | dispersion=0.180 | 0.000 |
| concordance (c44) | REFUSE | dispersion=0.408 | 0.000 |
| dynamic_return | PASS | dE=1.95e-06 eV/atom, max disp=0.007 A, 45 steps, 64 atoms (mace-mp-medium) | 8.3 |

Subject wall time: **19.2 s**

## Scope and honesty notes

- Born stability is exact physics (necessary conditions only); concordance thresholds are percentiles of our own measured baseline; no threshold in this report was invented.
- Threshold transfer: the p75/p95 baseline is measured on B0 dispersions and applied to a0/B0/C11/C12/C44 alike. a0 disperses less than B0 (lenient there); shear constants typically disperse more (strict there). This is a documented proxy, not a per-property calibration.
- The dynamic-return gate is a finite-rattle basin-return probe, NOT a phonon calculation; instabilities incommensurate with the 2x2x2 supercell are invisible to it.
- Thermodynamic (hull-level) gates are OUT OF SCOPE in this run: a mechanically stable subject (e.g. rocksalt LiS) may remain thermodynamically unstable against decomposition; deciding that requires the formation-energy lane.
- Cubic symmetry of each relaxed subject is assumed by construction (all panel prototypes are cubic); the elastic probe measures the cubic C11/C12/C44 only.
