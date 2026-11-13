# Data License

Unless a file says otherwise, first-party structured data, catalogs, manifests,
claim-status records, exported evidence databases, and replication datasets in
this repo are licensed under:

Creative Commons Attribution 4.0 International

SPDX-License-Identifier: CC-BY-4.0

See: https://creativecommons.org/licenses/by/4.0/

You may reuse, adapt and redistribute this data, including inside a company,
with attribution to Lupine Science. There is no share-alike obligation.

Individual prose, diagrams, and figures are covered by `LICENSE-CONTENT.md`.
Code is covered by the main `LICENSE` file (MIT).

## Third-party data

Third-party datasets and upstream scientific sources retain their original
notices and licenses, and CC BY 4.0 does not apply to them. This includes, for
example, interatomic potentials and reference values from OpenKIM (terms per
item), the NIST Interatomic Potentials Repository (terms per potential),
ColabFit (terms per dataset), the Materials Project, MatPES, published DFT-NEB
and adsorption benchmark panels, and the vendored potential tables under
`distill/lammps_runs/`. Data we derive from these sources keeps each item's
original terms where those terms require it. Per-source terms and stewardship
are recorded beside the data, for example in
`data/mlip_benchmarks/manifest_sources.json`; several entries there say to
verify the upstream terms before reuse, and that instruction stands. Keep
provenance beside imported data whenever possible.
