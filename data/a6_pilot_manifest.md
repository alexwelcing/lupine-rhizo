# A6 Bridge Pilot Manifest

`data/a6_pilot_manifest.json`

## What this is

The smallest usable dataset manifest for the A6 bridge protocol. It uses the existing **5-structure MPtrj pilot set** already present in the repo:

- `docs/glim-m3-upgrade/runs/live/forces/chgnet__baseline.json`
- `docs/glim-m3-upgrade/runs/live/forces/mace-mp-0__baseline.json`
- `docs/glim-m3-upgrade/runs/live/forces/sevennet__baseline.json`

These files share the same 5 configurations (107 atoms total) with reference MPtrj DFT energies and forces.

## How to run

```bash
cd /home/alex/Dev/lupine/lupine-rhizo
python tools/a6_bridge_pilot.py \
  --manifest data/a6_pilot_manifest.json \
  --permutations 5000 \
  --bootstrap 2000 \
  --output docs/glim-m3-upgrade/runs/a6-bridge-pilot-results.json \
  --report docs/glim-m3-upgrade/runs/a6-bridge-pilot-results.md
```

## Schema

```json
{
  "schema": "lupine.a6_bridge.manifest.v1",
  "field": "forces",
  "models": {
    "model-name": ["path/to/cell_result.json"],
    ...
  }
}
```

Each `cell_result.json` must match the `mlip-cell-runner` output format with a `predictions` array containing:

- `material_id` (block identifier)
- `energy_ev_per_atom`
- `forces_ev_per_angstrom`
- `reference.energy_ev_per_atom`
- `reference.forces_ev_per_angstrom`

## Path to full scale

To scale from 5 configs to the MatPES / MPtrj / OMat24 regime, replace the single file per model with lists of `cell_result.json` files produced by `mlip-cell-runner` on those datasets. The protocol expects:

| stage | dataset | target size |
|---|---|---|
| fit | MatPES or MPtrj train | ≥ 10⁴ configs, ≥ 10² materials |
| scale | OMat24 or MPtrj test | ≥ 10⁵ configs |

## Known gaps

- **Coupling-aware null** (geometry-preserving random rotations) is not yet implemented.
- **Core-dimension diagnostic** (local PCA on high-error configurations) is not yet implemented.
- Full-scale manifests for MatPES/MPtrj/OMat24 need to be generated from actual dataset runs.
