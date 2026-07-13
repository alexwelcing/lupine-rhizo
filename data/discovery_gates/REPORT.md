# Discovery gates - reference-free verdicts (li-s panel)

Generated: 2026-07-13T13:12:10.415273+00:00 | device: cuda | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium | thresholds: v2 | gate order: early-stop

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

## Li2S_antifluorite - **FLAGGED**

known-good reference subject (cubic antifluorite, mp-1153-like)

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 5.7015 | 29.4 | 39.0 | 15.4 | 16.8 | 20.8% | PASS | 5.0 |
| mace-mp-small | 5.7219 | 34.1 | 64.9 | 18.9 | 29.8 | 0.3% | PASS | 7.5 |
| mace-mpa-0-medium | 5.7303 | 38.2 | 78.1 | 18.5 | 34.8 | 0.3% | PASS | 4.3 |
| mace-mp-medium | 5.7228 | 34.6 | 68.0 | 17.7 | 23.9 | 0.4% | PASS | 4.0 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | PASS | C11-C12=23.6, C11+2C12=69.7, C44=16.8 GPa | 0.3 |
| born (mace-mp-small) | PASS | C11-C12=46.0, C11+2C12=102.7, C44=29.8 GPa | 0.4 |
| born (mace-mpa-0-medium) | PASS | C11-C12=59.6, C11+2C12=115.0, C44=34.8 GPa | 0.2 |
| born (mace-mp-medium) | PASS | C11-C12=50.3, C11+2C12=103.4, C44=23.9 GPa | 0.2 |
| concordance (a0) | PASS | dispersion=0.005 | 0.000 |
| concordance (b0) | FLAG | dispersion=0.258 | 0.000 |
| concordance (c11) | FLAG | dispersion=0.589 | 0.000 |
| concordance (c12) | PASS | dispersion=0.194 | 0.000 |
| concordance (c44) | PASS | dispersion=0.669 | 0.000 |
| dynamic_return | PASS | dE=1.32e-05 eV/atom, max disp=0.022 A, 39 steps, 96 atoms (mace-mp-medium) | 9.1 |

Subject wall time: **29.9 s**

## LiS_rocksalt - **REFUSED**

speculative subject: unproven 1:1 Li-S composition

| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | B0 Cij vs EOS | Born | wall (s) |
|---|---|---|---|---|---|---|---|---|
| chgnet | 4.9588 | 53.0 | 119.9 | 64.6 | -7.1 | 56.7% | FAIL | 4.9 |
| mace-mp-small | 5.0582 | 49.2 | 59.9 | 44.2 | -18.2 | 0.5% | FAIL | 3.4 |
| mace-mpa-0-medium | 4.9590 | 40.1 | 89.4 | 15.8 | -38.4 | 0.6% | FAIL | 3.8 |
| mace-mp-medium | 5.0230 | 53.2 | 91.5 | 34.5 | -14.3 | 0.5% | FAIL | 3.6 |

| gate | verdict | key numbers | wall (s) |
|---|---|---|---|
| born (chgnet) | FAIL | C11-C12=55.3, C11+2C12=249.1, C44=-7.1 GPa | 0.3 |
| born (mace-mp-small) | FAIL | C11-C12=15.7, C11+2C12=148.3, C44=-18.2 GPa | 0.2 |
| born (mace-mpa-0-medium) | FAIL | C11-C12=73.6, C11+2C12=121.1, C44=-38.4 GPa | 0.2 |
| born (mace-mp-medium) | FAIL | C11-C12=57.1, C11+2C12=160.5, C44=-14.3 GPa | 0.2 |
| concordance (a0) | REFUSE | dispersion=0.020 | 0.000 |
| concordance (b0) | FLAG | dispersion=0.257 | 0.000 |
| concordance (c11) | FLAG | dispersion=0.663 | 0.000 |
| concordance (c12) | REFUSE | dispersion=1.240 | 0.000 |
| concordance (c44) | FLAG | dispersion=1.925 | 0.000 |
| dynamic_return | SKIPPED | early-stop: subject already REFUSED by Born failure (chgnet, mace-mp-small, mace-mpa-0-medium, mace-mp-medium); concordance refusal (a0, c12) | 0.0 |

Subject wall time: **15.7 s**

## Scope and honesty notes

- Born stability is exact physics (necessary conditions only); concordance thresholds are percentiles of our own measured baseline; no threshold in this report was invented.
- Per-property thresholds (v2): each of a0/B0/C11/C12/C44 is gated by p75/p95 of its OWN measured cross-model dispersion baseline (the elastic-baseline sweep), replacing the v1 B0-proxy transfer. Within-family coupling (Cauchy relation, stability) remains; per-property calibration fixes the transfer error, it does not decouple the elastic family.
- Gate order (early-stop): the dynamic-return probe (the most expensive gate) ran only for subjects not already REFUSED by measurement/Born/concordance; a refusal is final (no later gate can overturn it), so skipped probes change no verdict. Skips are recorded per subject.
- The dynamic-return gate is a finite-rattle basin-return probe, NOT a phonon calculation; instabilities incommensurate with the 2x2x2 supercell are invisible to it.
- Thermodynamic (hull-level) gates are OUT OF SCOPE in this run: a mechanically stable subject (e.g. rocksalt LiS) may remain thermodynamically unstable against decomposition; deciding that requires the formation-energy lane.
- Cubic symmetry of each relaxed subject is assumed by construction (all panel prototypes are cubic); the elastic probe measures the cubic C11/C12/C44 only.
