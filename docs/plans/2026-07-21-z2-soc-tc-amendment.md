# Z2 spin/SOC and Curie-temperature preregistration amendment

Date: 2026-07-21
Campaign: `discovery.round-4.z2-magnetic-anisotropy.v1`

## Timing and reason

This amendment was made before any spin-capable Z2 measurement was executed. The earlier scalar-only Z2 abstention audit established that the declared MLIP images could not measure magnetic anisotropy. It did not produce or inspect SOC/Tc outcomes. This amendment restores the intended confirmatory measurement with an isolated multi-fidelity runner rather than treating scalar energies as magnetic evidence.

## Frozen scope

- Primary endpoint: exact signed magnetocrystalline-anisotropy ordering on the locked panel, Spearman rho = 1, with zero easy-axis errors.
- Secondary endpoints: per-material nearest-neighbour exchange `J`, exchange anisotropy `B/J`, Green/MC/RNSW Curie-temperature estimates, RNSW MAE, and published-method-envelope coverage.
- Failures and non-convergence are recorded without imputation; any failed material makes the aggregate measurement incomplete.
- At least five materials must complete. The locked panel contains seven materials and is excluded from Z2-specific fitting, threshold tuning, and model selection.
- Long-range exchange, itinerant corrections, finite-size scaling, substrates, and experimental Tc claims remain excluded.

## Reference lock

The reference is Tiwari et al., “Computing Curie temperature of two-dimensional ferromagnets in the presence of exchange anisotropy,” Phys. Rev. Research 3, 043024 (2021), DOI `10.1103/PhysRevResearch.3.043024`, Supplemental Table 1. Exact C2DB structure bytes and the derived panel are SHA-256 locked in `data/candidates/z2_soc_tc_panel.lock.json`; source limitations and the absence of statistical error bars are retained in that artifact.

## Execution boundary

The dedicated `soc_tc` row performs MLIP/FIRE geometry relaxation followed by separate GPAW PBE scalar FM and AFM calculations and non-selfconsistent force-theorem SOC band energies along x, y, and z. Tc is computed only inside the published fit domain. The image may be built, deployed, and smoke-tested with `--help`, but the heavy seven-material SOC campaign must not start while the Z1 sparse-DFT pilot owns the local compute queue unless the owner approves.
