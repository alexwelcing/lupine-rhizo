# Round-1 candidate campaign - raw vs Lupine-corrected

Generated: 2026-07-13T17:07:26.591724+00:00 | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium

Bias arm: biases from C:/Users/alexw/Downloads/lupine-rhizo/data/candidates/model_biases.v1.json (schema lupine.model_biases.v1); cij available: False

Note: B0 concordance is DESCRIPTIVE only, program-wide: fcc B0 dispersion is anti-correlated with |error| (rho = -0.63, n=9), so a B0 concordance level carries no dispersion-error license. Only Born stability (exact physics) and bcc a0 dispersion (rho = 0.89, n=7) currently carry a dispersion-error license (2026-07-13 errata finding 4; Round-3 prereg registered fix 6).

## Concordance thresholds

| property | flag | refuse | baseline n |
|---|---|---|---|
| a0 | 0.0060 | 0.0086 | 21 |
| b0 | 0.2490 | 0.3848 | 21 |
| c11 | 0.4885 | 1.2107 | 21 |
| c12 | 0.5704 | 1.0590 | 21 |
| c44 | 1.2221 | 3.7892 | 21 |

## rs-kcl - **FLAGGED**

group: ionics-rocksalt-oos | structure: rocksalt | formula: KCl | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 6.2931 | 6.3790 | 6.3924 | 6.3553 | 6.3962 | 6.3790 (uncorr) | 6.3924 (uncorr) | 6.3553 (uncorr) | 6.3962 (uncorr) | FLAG |
| b0 | 17.8400 | 17.1481 | 14.2165 | 16.3922 | 16.6178 | 17.1481 (uncorr) | 14.2165 (uncorr) | 16.3922 (uncorr) | 16.6178 (uncorr) | PASS |
| c11 | 40.3200 | 32.6805 | 34.5110 | 39.1616 | 32.0760 | 32.6805 (uncorr) | 34.5110 (uncorr) | 39.1616 (uncorr) | 32.0760 (uncorr) | PASS |
| c12 | 6.6000 | 9.7989 | 3.9867 | 4.9969 | 8.5689 | 9.7989 (uncorr) | 3.9867 (uncorr) | 4.9969 (uncorr) | 8.5689 (uncorr) | FLAG |
| c44 | 6.2900 | 4.9529 | 4.3923 | 4.3756 | 7.8507 | 4.9529 (uncorr) | 4.3923 (uncorr) | 4.3756 (uncorr) | 7.8507 (uncorr) | PASS |

dynamic_return: PASS (dE=2.21e-04 eV/atom, max disp=0.063 A, 8 atoms)

## rs-kbr - **REFUSED**

group: ionics-rocksalt-oos | structure: rocksalt | formula: KBr | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 6.6000 | 6.7172 | 6.7072 | 6.7257 | 6.6950 | 6.7172 (uncorr) | 6.7072 (uncorr) | 6.7257 (uncorr) | 6.6950 (uncorr) | PASS |
| b0 | 15.4000 | 15.1326 | 13.5891 | 12.8918 | 13.6319 | 15.1326 (uncorr) | 13.5891 (uncorr) | 12.8918 (uncorr) | 13.6319 (uncorr) | PASS |
| c11 | 34.6000 | 33.1166 | 31.9124 | 29.2678 | 29.5334 | 33.1166 (uncorr) | 31.9124 (uncorr) | 29.2678 (uncorr) | 29.5334 (uncorr) | PASS |
| c12 | 5.8000 | 16.2945 | 4.3272 | 4.6168 | 5.9313 | 16.2945 (uncorr) | 4.3272 (uncorr) | 4.6168 (uncorr) | 5.9313 (uncorr) | REFUSE |
| c44 | 5.0500 | 3.7989 | 4.7566 | 4.7250 | 3.6437 | 3.7989 (uncorr) | 4.7566 (uncorr) | 4.7250 (uncorr) | 3.6437 (uncorr) | PASS |

dynamic_return: PASS (dE=2.10e-04 eV/atom, max disp=0.058 A, 8 atoms)

## rs-rbcl - **REFUSED**

group: ionics-rocksalt-oos | structure: rocksalt | formula: RbCl | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 6.5810 | 6.6910 | 6.7318 | 6.6976 | 6.6654 | 6.6910 (uncorr) | 6.7318 (uncorr) | 6.6976 (uncorr) | 6.6654 (uncorr) | REFUSE |
| b0 | 16.4700 | 13.2689 | 13.0654 | 13.1783 | 16.2257 | 13.2689 (uncorr) | 13.0654 (uncorr) | 13.1783 (uncorr) | 16.2257 (uncorr) | PASS |
| c11 | 36.4600 | 29.0143 | 28.0493 | 29.4224 | 34.7991 | 29.0143 (uncorr) | 28.0493 (uncorr) | 29.4224 (uncorr) | 34.7991 (uncorr) | PASS |
| c12 | 6.4700 | 8.7097 | 5.4903 | 4.9394 | 7.6848 | 8.7097 (uncorr) | 5.4903 (uncorr) | 4.9394 (uncorr) | 7.6848 (uncorr) | FLAG |
| c44 | 4.6800 | 2.5172 | 5.4752 | 4.3590 | 6.9057 | 2.5172 (uncorr) | 5.4752 (uncorr) | 4.3590 (uncorr) | 6.9057 (uncorr) | PASS |

dynamic_return: PASS (dE=2.06e-04 eV/atom, max disp=0.058 A, 8 atoms)

## rs-naf - **REFUSED**

group: ionics-rocksalt-oos | structure: rocksalt | formula: NaF | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 4.6342 | 4.7024 | 4.6873 | 4.6987 | 4.7409 | 4.7024 (uncorr) | 4.6873 (uncorr) | 4.6987 (uncorr) | 4.7409 (uncorr) | REFUSE |
| b0 | 48.4900 | 43.0991 | 50.5273 | 47.7564 | 38.1473 | 43.0991 (uncorr) | 50.5273 (uncorr) | 47.7564 (uncorr) | 38.1473 (uncorr) | FLAG |
| c11 | 96.3000 | 102.4705 | 100.8960 | 89.4012 | 76.0922 | 102.4705 (uncorr) | 100.8960 (uncorr) | 89.4012 (uncorr) | 76.0922 (uncorr) | PASS |
| c12 | 24.5900 | 16.6722 | 25.6958 | 27.4568 | 19.6765 | 16.6722 (uncorr) | 25.6958 (uncorr) | 27.4568 (uncorr) | 19.6765 (uncorr) | PASS |
| c44 | 27.9400 | 22.0810 | 27.5345 | 26.2903 | 27.7732 | 22.0810 (uncorr) | 27.5345 (uncorr) | 26.2903 (uncorr) | 27.7732 (uncorr) | PASS |

dynamic_return: PASS (dE=2.41e-05 eV/atom, max disp=0.027 A, 8 atoms)

## pv-cspbbr3 - **REFUSED**

group: perovskite-oos | structure: perovskite | formula: CsPbBr3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 5.8740 | 6.0290 | 6.0163 | 5.9977 | 6.0128 | 6.0223 | 6.0142 | 5.9916 | 6.0031 | PASS |
| b0 | 22.5700 | 18.0772 | 18.4858 | 16.5874 | 20.8054 | 19.5768 | 18.4698 | 16.3969 | 20.9291 | PASS |
| c11 | 55.2750 | 27.6489 | 45.9329 | 40.7366 | 44.8768 | 27.6489 (uncorr) | 45.9329 (uncorr) | 40.7366 (uncorr) | 44.8768 (uncorr) | PASS |
| c12 | 6.2170 | 13.2016 | 4.5841 | 4.3366 | 8.9643 | 13.2016 (uncorr) | 4.5841 (uncorr) | 4.3366 (uncorr) | 8.9643 (uncorr) | REFUSE |
| c44 | 3.2220 | 1.6597 | 3.7792 | 3.5575 | 4.2939 | 1.6597 (uncorr) | 3.7792 (uncorr) | 3.5575 (uncorr) | 4.2939 (uncorr) | PASS |

dynamic_return: PASS (dE=7.80e-05 eV/atom, max disp=0.116 A, 5 atoms)

## pv-cspbcl3 - **FLAGGED**

group: perovskite-oos | structure: perovskite | formula: CsPbCl3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 5.6050 | 5.7431 | 5.7249 | 5.7034 | 5.7521 | 5.7367 | 5.7228 | 5.6975 | 5.7429 | FLAG |
| b0 | 20.5000 | 20.2167 | 23.8271 | 21.8856 | 21.5334 | 21.8939 | 23.8065 | 21.6341 | 21.6615 | PASS |
| c11 | 29.5000 | 45.3486 | 61.2002 | 51.7734 | 45.5196 | 45.3486 (uncorr) | 61.2002 (uncorr) | 51.7734 (uncorr) | 45.5196 (uncorr) | PASS |
| c12 | 16.0000 | 8.6270 | 5.0476 | 6.8612 | 9.3395 | 8.6270 (uncorr) | 5.0476 (uncorr) | 6.8612 (uncorr) | 9.3395 (uncorr) | PASS |
| c44 | 5.0400 | 0.9179 | 4.8683 | 4.6218 | 6.4023 | 0.9179 (uncorr) | 4.8683 (uncorr) | 4.6218 (uncorr) | 6.4023 (uncorr) | PASS |

dynamic_return: PASS (dE=1.24e-04 eV/atom, max disp=0.114 A, 5 atoms)

## pv-cscaf3 - **CERTIFIED**

group: perovskite-oos | structure: perovskite | formula: CsCaF3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 4.5260 | 4.5852 | 4.5844 | 4.5980 | 4.5977 | 4.5801 | 4.5827 | 4.5933 | 4.5903 | PASS |
| b0 | 50.9000 | 46.4436 | 48.1416 | 46.3049 | 45.2397 | 50.2966 | 48.1000 | 45.7729 | 45.5086 | PASS |
| c11 | 102.0000 | 79.7075 | 96.9142 | 86.4686 | 88.4639 | 79.7075 (uncorr) | 96.9142 (uncorr) | 86.4686 (uncorr) | 88.4639 (uncorr) | PASS |
| c12 | 25.3000 | 25.3651 | 23.5964 | 25.9012 | 23.1778 | 25.3651 (uncorr) | 23.5964 (uncorr) | 25.9012 (uncorr) | 23.1778 (uncorr) | PASS |
| c44 | 25.5000 | 19.3555 | 25.0506 | 24.2708 | 25.0541 | 19.3555 (uncorr) | 25.0506 (uncorr) | 24.2708 (uncorr) | 25.0541 (uncorr) | PASS |

dynamic_return: PASS (dE=2.71e-05 eV/atom, max disp=0.039 A, 5 atoms)

## pv-kmgf3 - **CERTIFIED**

group: perovskite-oos | structure: perovskite | formula: KMgF3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 3.9924 | 4.0618 | 4.0493 | 4.0496 | 4.0514 | 4.0573 | 4.0479 | 4.0455 | 4.0449 | PASS |
| b0 | 75.0700 | 59.6783 | 68.7356 | 67.9200 | 60.9053 | 64.6293 | 68.6762 | 67.1397 | 61.2674 | PASS |
| c11 | 138.0000 | 103.0186 | 125.2746 | 122.3938 | 117.3953 | 103.0186 (uncorr) | 125.2746 (uncorr) | 122.3938 (uncorr) | 117.3953 (uncorr) | PASS |
| c12 | 43.6000 | 27.6080 | 40.6132 | 40.1971 | 31.9744 | 27.6080 (uncorr) | 40.6132 (uncorr) | 40.1971 (uncorr) | 31.9744 (uncorr) | PASS |
| c44 | 49.8300 | 31.2497 | 45.4693 | 41.7892 | 44.6245 | 31.2497 (uncorr) | 45.4693 (uncorr) | 41.7892 (uncorr) | 44.6245 (uncorr) | PASS |

dynamic_return: PASS (dE=1.47e-05 eV/atom, max disp=0.038 A, 5 atoms)

## Arm metrics: |relative error| vs references (raw vs corrected)

| group | property | n cells | median raw | median corr | mean raw | mean corr |
|---|---|---|---|---|---|---|
| all | a0 | 32 | 1.63% | 1.63% | 1.75% | 1.70% |
| all | b0 | 32 | 10.32% | 10.58% | 11.67% | 11.22% |
| all | c11 | 32 | 16.16% | 16.16% | 22.64% | 22.64% |
| all | c12 | 32 | 25.83% | 25.83% | 32.93% | 32.93% |
| all | c44 | 32 | 17.14% | 17.14% | 20.41% | 20.41% |
| ionics-rocksalt-oos | a0 | 16 | 1.60% | 1.60% | 1.60% | 1.60% |
| ionics-rocksalt-oos | b0 | 16 | 11.30% | 11.30% | 11.26% | 11.26% |
| ionics-rocksalt-oos | c11 | 16 | 14.53% | 14.53% | 12.84% | 12.84% |
| ionics-rocksalt-oos | c12 | 16 | 23.97% | 23.97% | 33.23% | 33.23% |
| ionics-rocksalt-oos | c44 | 16 | 21.11% | 21.11% | 19.88% | 19.88% |
| perovskite-oos | a0 | 16 | 1.75% | 1.64% | 1.90% | 1.79% |
| perovskite-oos | b0 | 16 | 9.28% | 10.32% | 12.09% | 11.18% |
| perovskite-oos | c11 | 16 | 20.33% | 20.33% | 32.45% | 32.45% |
| perovskite-oos | c12 | 16 | 28.45% | 28.45% | 32.63% | 32.63% |
| perovskite-oos | c44 | 16 | 13.29% | 13.29% | 20.94% | 20.94% |

## Risk-coverage

- candidates: 8
- certified: 2, flagged: 2, refused: 4
- issued (certified+flagged): 4 (50% coverage)
