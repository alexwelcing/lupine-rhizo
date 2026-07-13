# Discovery gates - reference-free verdicts (climate-halides panel)

Generated: 2026-07-13T13:17:10.087939+00:00 | device: cuda | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium | thresholds: v2 | gate order: early-stop

All gates are reference-free: no experimental or DFT value for any subject is consulted.

## Concordance thresholds (data-derived, not invented)

- metric: `(max - min) / |median|` across models, per property

| property | flag (p75) | refuse (p95) | baseline n |
|---|---|---|---|
| a0 | 0.0060 | 0.0086 | 21 |
| b0 | 0.2490 | 0.3848 | 21 |
| c11 | 0.4885 | 1.2107 | 21 |
| c12 | 0.5704 | 1.0590 | 21 |
| c44 | 1.2221 | 3.7892 | 21 |

- derivation: p75/p95 of the per-material cross-model relative dispersion (max-min)/|median| of a0 over 21 materials in C:/Users/alexw/Downloads/lupine-rhizo/data/y_matrix_runs/elastic_baseline (schema lupine.mlip.calc_evidence.v1)
- per-material dispersions recorded in report.json

Per-property thresholds (v2): each of a0/B0/C11/C12/C44 is gated by p75/p95 of its OWN measured cross-model dispersion baseline (the elastic-baseline sweep), replacing the v1 B0-proxy transfer. Within-family coupling (Cauchy relation, stability) remains; per-property calibration fixes the transfer error, it does not decouple the elastic family.

## LiF_rocksalt - **CERTIFIED**

halide solid-electrolyte anchor (known-good rocksalt, mp-1138-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.0908 | 53.6 | 98.6 | 43.6 | 32.2 | 15.5% | PASS | 6.2 |
| mace-mp-small | 4.0793 | 62.6 | 110.6 | 38.9 | 49.3 | 0.3% | PASS | 7.0 |
| mace-mpa-0-medium | 4.1000 | 65.8 | 114.3 | 41.2 | 60.2 | 0.3% | PASS | 4.9 |
| mace-mp-medium | 4.0933 | 59.0 | 92.1 | 42.0 | 50.0 | 0.6% | PASS | 4.5 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=55.0, C11+2C12=185.7, C44=32.2 GPa | 0.2 |
| born (mace-mp-small) | PASS | C11-C12=71.7, C11+2C12=188.4, C44=49.3 GPa | 0.1 |
| born (mace-mpa-0-medium) | PASS | C11-C12=73.1, C11+2C12=196.7, C44=60.2 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=50.1, C11+2C12=176.0, C44=50.0 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | PASS | dispersion=0.201 | 0.000 |
| concordance (c11) | PASS | dispersion=0.212 | 0.000 |
| concordance (c12) | PASS | dispersion=0.111 | 0.000 |
| concordance (c44) | PASS | dispersion=0.565 | 0.000 |
| dynamic_return | PASS | dE=2.13e-05 eV/atom, max disp=0.012 A, 31 steps, 64 atoms (mace-mp-medium) | 6.2 |

Subject wall time: **28.8 s**

## LiCl_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-22905-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.1484 | 33.7 | 69.4 | 37.5 | 18.8 | 42.9% | PASS | 5.8 |
| mace-mp-small | 5.1407 | 36.7 | 60.8 | 24.6 | 28.2 | 0.2% | PASS | 3.4 |
| mace-mpa-0-medium | 5.1836 | 39.0 | 61.9 | 29.1 | 26.4 | 2.6% | PASS | 5.3 |
| mace-mp-medium | 5.1297 | 33.1 | 53.0 | 23.4 | 24.6 | 0.5% | PASS | 3.9 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=31.9, C11+2C12=144.4, C44=18.8 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=36.2, C11+2C12=109.9, C44=28.2 GPa | 0.1 |
| born (mace-mpa-0-medium) | PASS | C11-C12=32.8, C11+2C12=120.1, C44=26.4 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=29.7, C11+2C12=99.8, C44=24.6 GPa | 0.2 |
| concordance (a0) | REFUSE | dispersion=0.010 | 0.000 |
| concordance (b0) | PASS | dispersion=0.168 | 0.000 |
| concordance (c11) | PASS | dispersion=0.267 | 0.000 |
| concordance (c12) | PASS | dispersion=0.526 | 0.000 |
| concordance (c44) | PASS | dispersion=0.373 | 0.000 |
| dynamic_return | SKIPPED | early-stop: subject already REFUSED by concordance refusal (a0) | 0.0 |

Subject wall time: **18.3 s**

## LiBr_rocksalt - **CERTIFIED**

halide solid-electrolyte anchor (known-good rocksalt, mp-23259-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.5077 | 25.1 | 25.9 | 20.8 | 10.1 | 10.2% | PASS | 5.7 |
| mace-mp-small | 5.4985 | 24.3 | 38.0 | 17.5 | 19.9 | 0.2% | PASS | 3.2 |
| mace-mpa-0-medium | 5.5273 | 26.0 | 42.2 | 18.0 | 19.3 | 0.5% | PASS | 4.4 |
| mace-mp-medium | 5.5067 | 25.8 | 40.6 | 18.5 | 17.6 | 0.2% | PASS | 4.3 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=5.0, C11+2C12=67.5, C44=10.1 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=20.5, C11+2C12=72.9, C44=19.9 GPa | 0.2 |
| born (mace-mpa-0-medium) | PASS | C11-C12=24.1, C11+2C12=78.3, C44=19.3 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=22.1, C11+2C12=77.5, C44=17.6 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | PASS | dispersion=0.064 | 0.000 |
| concordance (c11) | PASS | dispersion=0.415 | 0.000 |
| concordance (c12) | PASS | dispersion=0.184 | 0.000 |
| concordance (c44) | PASS | dispersion=0.534 | 0.000 |
| dynamic_return | PASS | dE=2.82e-05 eV/atom, max disp=0.016 A, 33 steps, 64 atoms (mace-mp-medium) | 5.0 |

Subject wall time: **22.6 s**

## LiI_rocksalt - **REFUSED**

halide solid-electrolyte anchor (known-good rocksalt, mp-22899-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 6.0145 | 20.0 | 24.9 | 20.8 | 9.4 | 10.8% | PASS | 5.7 |
| mace-mp-small | 6.0639 | 19.9 | 34.1 | 12.8 | 12.4 | 0.1% | PASS | 3.5 |
| mace-mpa-0-medium | 6.0512 | 19.4 | 30.6 | 13.8 | 15.5 | 0.0% | PASS | 4.9 |
| mace-mp-medium | 6.0800 | 16.0 | 21.1 | 13.6 | 11.8 | 0.3% | PASS | 5.3 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=4.1, C11+2C12=66.6, C44=9.4 GPa | 0.1 |
| born (mace-mp-small) | PASS | C11-C12=21.3, C11+2C12=59.6, C44=12.4 GPa | 0.1 |
| born (mace-mpa-0-medium) | PASS | C11-C12=16.9, C11+2C12=58.2, C44=15.5 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=7.5, C11+2C12=48.2, C44=11.8 GPa | 0.2 |
| concordance (a0) | REFUSE | dispersion=0.011 | 0.000 |
| concordance (b0) | PASS | dispersion=0.206 | 0.000 |
| concordance (c11) | PASS | dispersion=0.469 | 0.000 |
| concordance (c12) | FLAG | dispersion=0.590 | 0.000 |
| concordance (c44) | PASS | dispersion=0.507 | 0.000 |
| dynamic_return | SKIPPED | early-stop: subject already REFUSED by concordance refusal (a0) | 0.0 |

Subject wall time: **19.4 s**

## NaCl_rocksalt - **FLAGGED**

rocksalt control with existing a0/B0 Y-matrix cells

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.6955 | 25.0 | 41.7 | 21.5 | 6.0 | 12.7% | PASS | 4.1 |
| mace-mp-small | 5.6900 | 27.2 | 45.0 | 18.3 | 11.6 | 0.1% | PASS | 2.3 |
| mace-mpa-0-medium | 5.7135 | 20.9 | 42.8 | 9.7 | 12.4 | 0.9% | PASS | 3.4 |
| mace-mp-medium | 5.6832 | 25.4 | 52.0 | 12.2 | 10.9 | 0.0% | PASS | 3.3 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=20.2, C11+2C12=84.6, C44=6.0 GPa | 0.2 |
| born (mace-mp-small) | PASS | C11-C12=26.7, C11+2C12=81.6, C44=11.6 GPa | 0.1 |
| born (mace-mpa-0-medium) | PASS | C11-C12=33.1, C11+2C12=62.1, C44=12.4 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=39.8, C11+2C12=76.3, C44=10.9 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | PASS | dispersion=0.249 | 0.000 |
| concordance (c11) | PASS | dispersion=0.235 | 0.000 |
| concordance (c12) | FLAG | dispersion=0.774 | 0.000 |
| concordance (c44) | PASS | dispersion=0.571 | 0.000 |
| dynamic_return | PASS | dE=5.60e-05 eV/atom, max disp=0.030 A, 32 steps, 64 atoms (mace-mp-medium) | 4.8 |

Subject wall time: **17.9 s**

## MgO_rocksalt - **CERTIFIED**

oxide rocksalt control with existing a0/B0 Y-matrix cells

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.2536 | 133.5 | 208.2 | 78.3 | 86.4 | 8.9% | PASS | 3.1 |
| mace-mp-small | 4.2533 | 149.4 | 256.9 | 93.1 | 138.0 | 1.1% | PASS | 1.7 |
| mace-mpa-0-medium | 4.2565 | 148.1 | 265.3 | 88.9 | 135.9 | 0.3% | PASS | 2.5 |
| mace-mp-medium | 4.2545 | 147.3 | 248.6 | 94.7 | 117.4 | 0.9% | PASS | 2.1 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=129.9, C11+2C12=364.8, C44=86.4 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=163.7, C11+2C12=443.1, C44=138.0 GPa | 0.1 |
| born (mace-mpa-0-medium) | PASS | C11-C12=176.5, C11+2C12=443.1, C44=135.9 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=153.9, C11+2C12=438.0, C44=117.4 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.001 | 0.000 |
| concordance (b0) | PASS | dispersion=0.107 | 0.000 |
| concordance (c11) | PASS | dispersion=0.226 | 0.000 |
| concordance (c12) | PASS | dispersion=0.180 | 0.000 |
| concordance (c44) | PASS | dispersion=0.408 | 0.000 |
| dynamic_return | PASS | dE=1.95e-06 eV/atom, max disp=0.007 A, 45 steps, 64 atoms (mace-mp-medium) | 8.3 |

Subject wall time: **17.7 s**

## Scope and honesty notes

- Born stability is exact physics (necessary conditions only); concordance thresholds are percentiles of our own measured baseline; no threshold in this report was invented.
- Per-property thresholds (v2): each of a0/B0/C11/C12/C44 is gated by p75/p95 of its OWN measured cross-model dispersion baseline (the elastic-baseline sweep), replacing the v1 B0-proxy transfer. Within-family coupling (Cauchy relation, stability) remains; per-property calibration fixes the transfer error, it does not decouple the elastic family.
- Gate order (early-stop): the dynamic-return probe (the most expensive gate) ran only for subjects not already REFUSED by measurement/Born/concordance; a refusal is final (no later gate can overturn it), so skipped probes change no verdict. Skips are recorded per subject.
- The dynamic-return gate is a finite-rattle basin-return probe, NOT a phonon calculation; instabilities incommensurate with the 2x2x2 supercell are invisible to it.
- Thermodynamic (hull-level) gates are OUT OF SCOPE in this run: a mechanically stable subject (e.g. rocksalt LiS) may remain thermodynamically unstable against decomposition; deciding that requires the formation-energy lane.
- Cubic symmetry of each relaxed subject is assumed by construction (all panel prototypes are cubic); the elastic probe measures the cubic C11/C12/C44 only.
