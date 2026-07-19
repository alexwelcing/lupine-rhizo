# Z3 adsorption reference panel

The Z3 panel is built from the 32-row `BM_dataset_adsorption.json` artifact in the
CatBench benchmark collection (Zenodo `10.5281/zenodo.17157086`, CC BY 4.0). The
source file is pinned by SHA-256
`72d44b03c53b4262f3bb5b69d960b33f53a2cfb243416b44a9755dfbe0f6d100`.

## Scientific lineage

The structures and energies originate in the GAME-Net study, “Fast evaluation
of the adsorption energy of organic molecules on metals via graph neural
networks” (`10.1038/s43588-023-00437-y`, 2023). That work extended adsorption
benchmarking from small surface fragments to industrially relevant large
molecules from biomass conversion, polyurethane synthesis, and plastics
recycling. CatBench subsequently repackaged the relaxed adsorbate-slab, clean
slab, and gas-reference systems as directly executable reaction records.

The references are VASP 5.4.4 DFT(PBE) calculations with D2 dispersion
reparameterized for metals, a 450 eV plane-wave cutoff, PAW pseudopotentials,
`1e-5 eV` electronic convergence, and `0.03 eV/Å` force convergence. Panel
surfaces use the source study’s lowest-surface-energy facets: fcc(111) for Ag,
Au, Cu, Ni, and Pt, and hcp(0001) for Ru.

This is a published **DFT** reference panel, not an experimental panel. Z3 must
not describe its resulting MAE as error against experiment.

## Conditions and uncertainty scope

Every row records:

- the facet and surface element;
- one adsorbate per source periodic cell;
- the cell area and derived areal coverage;
- the zero-temperature electronic-energy convention (no vibrational, entropic,
  solvent, or finite-temperature correction);
- the source-relaxed surface-state and adsorption-site scope; and
- an uncertainty field.

The source paper does not publish statistical per-row confidence intervals. To
avoid inventing them, `reference.uncertainty_ev` is explicitly labeled as a
three-term electronic-convergence proxy bound: three times the published
`1e-5 eV` SCF threshold. It is **not** a statistical interval and does not cover
functional, slab, k-point, geometry, dispersion, or model-form error. Consumers
must preserve that qualifier.

## Frozen delta split

The split is deterministic and family-stratified. Within each of the three
application families, candidate IDs are ordered by SHA-256 of the ID. The first
two become `delta_train`, the next two `delta_validation`, and the remainder
`confirmatory_test`, giving 6/6/20 rows. Confirmatory references are excluded
from fitting, model/correction selection, and threshold tuning.

The checkpoint artifact is intentionally an **unfitted fixture**, not a
fabricated trained model. It freezes the required model IDs, candidate IDs,
hash bindings, and no-leakage rules that an execution worker must populate from
real raw predictions.

## Rebuild

From the repository root, with the Python test environment active:

```bash
python tools/build_z3_adsorption_panel.py
sha256sum -c data/candidates/z3_catbench_bm_adsorption.lock.json.sha256
sha256sum -c data/candidates/z3_catbench_bm_delta_splits.lock.json.sha256
sha256sum -c data/candidates/z3_catbench_bm_delta_checkpoint.fixture.json.sha256
pytest -q python/tests/test_z3_adsorption_panel.py
```

The builder downloads only the pinned source when `/tmp/BM_dataset_adsorption.json`
is absent, rejects any source digest mismatch, sorts all JSON keys, and emits
byte-for-byte stable lock files and sidecars.
