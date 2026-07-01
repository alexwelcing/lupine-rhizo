# A6 bridge pilot results

Schema: `lupine.a6_bridge.results.v1`
Timestamp: 2026-07-01T15:15:12Z
Permutations: 5,000 | Bootstrap: 2,000 | Seed: 42

## Dataset

- Models: chgnet, mace-mp-0, sevennet
- Blocks (materials/trajectories): 5
- Configurations: 5
- Atoms: 107
- Max configs per block: 1

## Force-field alignment

| pair | mag_corr | atom_cos | field_cos | delta_rel |
|---|---|---|---|---|
| chgnet|mace-mp-0 | 0.849, p=0.0002 ✓ | 0.196, p=0.0010 ✓ | 0.107, p=0.0836 ✗ | 1.594, p=0.8366 ✗ |
| chgnet|sevennet | 0.700, p=0.0002 ✓ | 0.289, p=0.0002 ✓ | 0.188, p=0.0120 ✓ | 1.166, p=0.9782 ✗ |
| mace-mp-0|sevennet | 0.859, p=0.0002 ✓ | 0.272, p=0.0002 ✓ | 0.710, p=0.0002 ✓ | 0.521, p=1.0000 ✗ |

### Force-field aggregate (Fisher's method)

- **mag_corr**: χ² = 51.10, df = 6, pair ps = [0.0001999600079984003, 0.0001999600079984003, 0.0001999600079984003]
- **atom_cos**: χ² = 47.89, df = 6, pair ps = [0.0009998000399920016, 0.0001999600079984003, 0.0001999600079984003]
- **field_cos**: χ² = 30.84, df = 6, pair ps = [0.08358328334333133, 0.01199760047990402, 0.0001999600079984003]

## Coupling-aware (geometry-preserving) null

| pair | mag_corr | atom_cos | field_cos | delta_rel |
|---|---|---|---|---|
| chgnet|mace-mp-0 | 0.849, p=0.7033 ✗ | 0.196, p=0.0529 ✗ | 0.107, p=0.2827 ✗ | 1.594, p=0.4466 ✗ |
| chgnet|sevennet | 0.700, p=0.5594 ✗ | 0.289, p=0.0010 ✓ | 0.188, p=0.0529 ✗ | 1.166, p=0.8771 ✗ |
| mace-mp-0|sevennet | 0.859, p=0.9520 ✗ | 0.272, p=0.0010 ✓ | 0.710, p=0.0010 ✓ | 0.521, p=1.0000 ✗ |

If observed alignment survives this null, the shared force-field pattern is not an artifact of mechanical/elastic constraints.


## Energy-field alignment

| pair | energy_corr | energy_cos | energy_mae_ratio |
|---|---|---|---|
| chgnet|mace-mp-0 | 0.631, degenerate | 0.631, degenerate | 0.251, degenerate |
| chgnet|sevennet | 0.598, degenerate | 0.598, degenerate | 0.259, degenerate |
| mace-mp-0|sevennet | 0.999, degenerate | 0.999, degenerate | 1.030, degenerate |

### Energy-field aggregate (Fisher's method)

- **energy_corr**: χ² = nan, df = 0, pair ps = []
- **energy_cos**: χ² = nan, df = 0, pair ps = []

## Energy-field null note

Every block contains only one configuration, so the stratified permutation
null for energy is degenerate (there is nothing to permute within a block).
Energy observed statistics are still valid; energy p-values and Fisher
aggregation are omitted. For a meaningful energy null, group single-config
blocks into coarser strata or use multi-config trajectories.

## Interpretation notes

- A6 is supported for a field/pair when `field_cos` / `mag_corr` is well above
  the stratified null (p ≤ 0.05) and the bootstrap CI excludes the null mean.
- `delta_rel` estimates the relative model-specific perturbation off the shared core.
- Energy and force alignment can disagree; the keystone theorem uses the joint
  scalarized field `q_M = ‖r_M‖²`.
- The permutation null controls per-structure size but not mechanical/elastic
  coupling; a coupling-aware null is required before publication.

