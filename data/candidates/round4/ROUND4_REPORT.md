# Round-4 theorem-capped correction campaign

Run: `correction-round4-20260719` · 32/32 model/material cells completed on the isolated Round-4 Cloud Run jobs.

Analysis amended 2026-07-19 (`docs/plans/2026-07-19-round4-preregistration-amendment.md`): B0 is descriptive-only (preregistration §5) and perovskite elastic constants are exploratory-only; neither enters the confirmatory denominator.

## Registered group/property results

| Group | Property | Scope | Applied | Improved | Worsened | Median raw | Median corrected | p (two-sided) | Win |
|---|---:|---|---:|---:|---:|---:|---:|---:|:---:|
| ionics-rocksalt | a0 | confirmatory | 7 | 5 | 2 | 0.0151705 | 0.0142436 | 0.453125 | NO |
| ionics-rocksalt | b0 | descriptive | 0 | 0 | 0 | 0.0902228 | 0.0902228 | — | NO |
| ionics-rocksalt | c11 | confirmatory | 1 | 0 | 1 | 0.27159 | 0.27159 | 1 | NO |
| ionics-rocksalt | c12 | confirmatory | 0 | 0 | 0 | 0.193731 | 0.193731 | — | NO |
| ionics-rocksalt | c44 | confirmatory | 0 | 0 | 0 | 0.190187 | 0.190187 | — | NO |
| perovskites | a0 | confirmatory | 4 | 4 | 0 | 0.0127536 | 0.0127536 | 0.125 | NO |
| perovskites | b0 | descriptive | 6 | 5 | 1 | 0.098626 | 0.0504845 | 0.21875 | NO |
| perovskites | c11 | exploratory | 2 | 0 | 2 | 0.115033 | 0.274425 | 0.5 | NO |
| perovskites | c12 | exploratory | 3 | 1 | 2 | 0.118836 | 0.11007 | 1 | NO |
| perovskites | c44 | exploratory | 5 | 3 | 2 | 0.0985136 | 0.0799044 | 1 | NO |

## Disposition

- Ionics-rocksalt: **FAIL** (0/4 confirmatory property wins: a0, c11, c12, c44).
- Perovskites: **FAIL** (0/1 confirmatory property wins: a0).
- Theorem consistency: 0 licensed, oracle-in-hull worsened cells (required: zero).
- Registered conclusion: both groups fail the >=2/3 property-win criterion; the public correction scope remains same-class lattice constants only and further cap tuning is frozen absent a new theorem.
- Excluded from the confirmatory denominator: b0 everywhere (descriptive-only, preregistration §5); perovskite c11/c12/c44 (exploratory-only, 2026-07-19 amendment — clamped-ion finite differences at the nearest sealed 2.5%-spaced volume vs relaxed/experimental references).

The complete machine-readable decisions, the repaired measurement binding (isolated jobs + immutable image digests), artifact paths, and SHA-256 hashes are in `report.json`.
