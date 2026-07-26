# Z2 SOC/Tc runner input and output rows

The Z2 runner (`gcp/mlip-cell-runner/z2_soc_tc.py`) measures magnetic
anisotropy and Curie-temperature proxies from spin-polarized electronic
structure calculations. The MLIP relaxes the geometry; it does **not** supply
the spin-resolved energies. Final `mae_ranking` and `tc_prediction` rows always
come from the high-SOC tier.

This page is the user-facing row reference. The normative validation and
physics specification is `docs/z2_soc_tc_contract.md`.

## Completeness rule

A serialized measurement row is atomic and complete:

- `predictions` contains exactly one completed prediction for every fixture
  material, in fixture order;
- every required column is present and every numeric value is finite;
- MAE and Tc predictions contain complete FM and AFM evidence for x, y, and z;
- `n_structures`, `metrics.completed_material_count`, the fixture material
  count, and `len(predictions)` are equal; and
- `fixture_contract.release_ready` is `true` and
  `fixture_contract.blockers` is empty.

Rows are **always fully populated**. The runner never serializes abstention or
failure placeholders: no `null`, `NaN`, `Infinity`, empty sentinel strings,
`status: "failed"`, or `status: "abstained"` may appear in a measurement row.
If one requested material fails validation, relaxation, SCF convergence, SOC,
domain checks, or recomputation checks, the cell fails before row
serialization. Diagnostics belong in the cell error/log artifact, not in
`predictions`.

This is stricter than the older Z1 barrier row, which can carry per-path failure
records. A partial material list cannot define a valid magnetic ranking.

## Fidelity tiers and routing

| Tier | Requested as | Calculation | Permitted output | When it is used |
|---|---|---|---|---|
| Tier L | `low_collinear` | MLIP/FIRE geometry relaxation followed by scalar, collinear, spin-polarized FM and AFM calculations without SOC | `screening` only | Explicit low-cost diagnostics, and the mandatory first stage of `auto` |
| Tier H | `high_soc` | Tier-L prerequisites plus non-collinear/spinor SOC force-theorem energies for x, y, and z magnetization | `mae_ranking`, `tc_prediction`, or both | Explicitly requested, or after a successful Tier-L screen in `auto` |

Tier L tests whether the initialized magnetic moments survive and whether the
collinear AFM–FM splitting is ferromagnetic. It cannot measure MAE because a
scalar Hamiltonian has no magnetization-direction energy, and it cannot
produce a contract-valid 2D Tc because exchange anisotropy is unavailable.
Consequently:

- `requested_tier: "low_collinear"` requires
  `measurement_modes: ["screening"]`;
- `requested_tier: "high_soc"` or `"auto"` accepts `mae_ranking`,
  `tc_prediction`, or both, with canonical mode order MAE then Tc;
- `high_soc` still runs or loads the scalar FM/AFM prerequisites; and
- a failed Tier-L screen in `auto` fails the requested final measurement. There
  is no low-tier MAE/Tc fallback row.

## Input fixture

The root object uses schema `lupine.z2.soc_tc_fixture.v1`. Unknown keys are
rejected.

### Root fields

| Field | JSON type | Required | Meaning |
|---|---:|---:|---|
| `schema` | string | yes | Literal `lupine.z2.soc_tc_fixture.v1`. |
| `fixture_id` | string | yes | Non-empty stable fixture identifier. |
| `requested_tier` | enum string | yes | `low_collinear`, `high_soc`, or `auto`. |
| `measurement_modes` | array[string] | yes | Non-empty unique legal mode list. See routing above. |
| `materials` | array[object] | yes | Non-empty material list with unique IDs; locked campaigns require at least five. |
| `execution_protocol` | object | yes | Frozen geometry, scalar-SCF, SOC, screening, and Tc controls. |
| `reference_provenance` | object | yes | Exact `source_id`, absolute HTTPS `source_url`, and `sha256:<64 lowercase hex>` fields. |

### Material, structure, spin, and reference fields

| Field | JSON type | Unit | Meaning and constraints |
|---|---:|---:|---|
| `material_id` | string | — | Non-empty identity, unique in the fixture. |
| `formula` | string | — | Non-empty chemical formula. |
| `lattice` | enum string | — | `honeycomb`, `hexagonal`, or `square`; selects the frozen Tc coefficients. |
| `spin` | float64 | ℏ | Finite spin quantum number `S > 0`. |
| `nearest_neighbors` | int64 | count | Nearest-neighbour coordination `z_nn >= 1`. |
| `magnetic_atom_indices` | array[int64] | zero-based atom index | Non-empty unique magnetic sites, each in `[0,N)`. |
| `afm_signs` | array[int64] | — | One `-1` or `+1` per magnetic site, with both signs represented. |
| `structure.symbols` | array[string] | — | `N >= 1` valid element symbols. |
| `structure.positions_angstrom` | `(N,3)` float64 array | Å | Finite Cartesian positions. |
| `structure.cell_angstrom` | `(3,3)` float64 array | Å | Finite nonsingular cell in ASE row-vector convention. |
| `structure.pbc` | 3-element bool array | — | Periodicity; a 2D material normally uses `[true,true,false]`. |
| `structure.initial_magmoms` | `N`-element float64 array | μB | Explicit finite initial moments, including zeros on nonmagnetic atoms. |
| `reference.mae_xz_mev_per_cell` | float64 | meV cell⁻¹ | Finite signed reference `1000(E_z-E_x)`. |
| `reference.mae_yz_mev_per_cell` | float64 | meV cell⁻¹ | Finite signed reference `1000(E_z-E_y)`. |
| `reference.exchange_mev` | float64 | meV | Positive reference mean exchange `J`. |
| `reference.exchange_anisotropy` | float64 | 1 | Reference `Δ` in `(0,0.2]`. |
| `reference.tc_k` | object[float64] | K | Exactly positive finite `green`, `mc`, and `rnsw` estimates. |
| `reference.tc_envelope_k` | 2-element float64 array | K | Positive `[low,high]`, with `low <= high`. |

For the FM calculation, each magnetic site starts at `2S μB`. For AFM it
starts at `2S * afm_sign μB`. These ordering-specific values override the
corresponding entries in `structure.initial_magmoms`; supplied moments on
nonmagnetic sites are retained.

`execution_protocol` fixes the following controls:

- positive float64: `geometry_force_convergence_ev_per_angstrom`,
  `gpaw_plane_wave_cutoff_ev`, `gpaw_kpoint_density_per_angstrom`,
  `gpaw_fermi_width_ev`, `gpaw_convergence_energy_ev`,
  `minimum_local_moment_muB`, `minimum_moment_retention_fraction`, and
  `orientation_tie_tolerance_mev`;
- positive int64: `geometry_maximum_steps` and
  `gpaw_maximum_scf_iterations`;
- exact finite `[theta,phi]` pairs for x, y, and z in `soc_axes_degrees`; and
- exact method strings `geometry_method`, `scalar_method`, `soc_method`,
  `tc_model`, and `failure_policy` from the normative contract.

`minimum_moment_retention_fraction` must be in `(0,1]`.

### Example fixture

This one-material fixture is a compact local example. A locked campaign fixture
uses the same shape but must contain at least its frozen minimum material count
(currently five). The all-zero hash is an explanatory value and must be
replaced by the actual content lock before execution.

```json
{
  "schema": "lupine.z2.soc_tc_fixture.v1",
  "fixture_id": "example-cr2-high-soc",
  "requested_tier": "high_soc",
  "measurement_modes": ["tc_prediction"],
  "materials": [
    {
      "material_id": "example-cr2",
      "formula": "Cr2",
      "lattice": "honeycomb",
      "spin": 1.5,
      "nearest_neighbors": 3,
      "magnetic_atom_indices": [0, 1],
      "afm_signs": [1, -1],
      "structure": {
        "symbols": ["Cr", "Cr"],
        "positions_angstrom": [[0.0, 0.0, 7.5], [1.75, 3.0311, 7.5]],
        "cell_angstrom": [[7.0, 0.0, 0.0], [-3.5, 6.0622, 0.0], [0.0, 0.0, 15.0]],
        "pbc": [true, true, false],
        "initial_magmoms": [3.0, 3.0]
      },
      "reference": {
        "mae_xz_mev_per_cell": -1.0,
        "mae_yz_mev_per_cell": -1.2,
        "exchange_mev": 5.25,
        "exchange_anisotropy": 0.047619047619047616,
        "tc_k": {
          "green": 95.47390240469808,
          "mc": 74.80539839533992,
          "rnsw": 49.9352071799864
        },
        "tc_envelope_k": [49.9352071799864, 95.47390240469808]
      }
    }
  ],
  "execution_protocol": {
    "geometry_method": "mlip_fire_relaxation",
    "geometry_force_convergence_ev_per_angstrom": 0.05,
    "geometry_maximum_steps": 200,
    "scalar_method": "gpaw_pbe_collinear_spin_polarized",
    "gpaw_plane_wave_cutoff_ev": 500.0,
    "gpaw_kpoint_density_per_angstrom": 6.0,
    "gpaw_fermi_width_ev": 0.05,
    "gpaw_convergence_energy_ev": 0.000001,
    "gpaw_maximum_scf_iterations": 200,
    "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
    "soc_axes_degrees": {
      "x": [90.0, 0.0],
      "y": [90.0, 90.0],
      "z": [0.0, 0.0]
    },
    "tc_model": "tiwari_eq3_eq4_nearest_neighbor",
    "minimum_local_moment_muB": 0.5,
    "minimum_moment_retention_fraction": 0.5,
    "orientation_tie_tolerance_mev": 0.001,
    "failure_policy": "fail cell without measurement-row serialization"
  },
  "reference_provenance": {
    "source_id": "illustrative-example-replace-before-execution",
    "source_url": "https://example.org/replace-with-locked-source",
    "sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

## Output envelope

Each requested mode produces a separate row-native JSON object, following the
same outer shape as the Z1 barrier runner.

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `predictions` | array[object] | — | Exactly one completed mode-specific prediction per fixture material, in fixture order. |
| `score` | float64 | `[0,1]` | Finite normalized mode score. |
| `score_unit` | string | `row_native_physical_score` | Score convention. |
| `metrics` | object | — | Exact mode-specific aggregate fields below. |
| `row_spec` | object | — | Exact `row_id`, `measurement_mode`, `requested_tier`, `execution_protocol`, and `measurement`. |
| `fixture_contract` | object | — | Exact fixture validation result below. |
| `n_structures` | int64 | count | Number of fixture materials and predictions. |

`fixture_contract` has exactly:

| Column | JSON type | Meaning |
|---|---:|---|
| `schema` | string | Fixture schema. |
| `fixture_id` | string | Stable fixture identity. |
| `material_count` | int64 | Number of fixture materials. |
| `minimum_material_count` | int64 | Frozen minimum for this row. |
| `release_ready` | bool | Always `true` in a serialized measurement row. |
| `blockers` | array | Always empty in a serialized measurement row. |

`row_spec` has exactly:

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `row_id` | string | `soc_tc` | Runner row identity. |
| `measurement_mode` | string | `mae_ranking` or `tc_prediction` | Mode represented by this row. |
| `requested_tier` | string | `high_soc` or `auto` | Fixture routing request. The measured tier remains high SOC. |
| `execution_protocol` | object | — | Exact frozen protocol copied from the validated fixture. |
| `measurement` | object | — | Exact mode-specific metric, unit, minimum count, and threshold/tolerance fields below. |

For `mae_ranking`, `row_spec.measurement` contains metric
`magnetocrystalline_anisotropy_rank_correlation`, unit `spearman_rho`, the
integer `minimum_material_count`, and `acceptance_threshold: 1.0`. For
`tc_prediction`, it contains metric `tc_rnsw_mae_k`, unit `K`, the integer
minimum, and positive finite `tc_error_tolerance_k`.

## MAE ranking row

### Prediction columns

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `material_id` | string | — | Fixture material identity. |
| `formula` | string | — | Chemical formula. |
| `status` | string | `completed` | Completion state; no other value is serializable. |
| `fidelity_tier_used` | string | `high_soc` | Tier that supplied the measurement. |
| `orientation_energies_ev` | object[float64] | eV cell⁻¹ | Exactly x, y, z FM force-theorem-corrected energies. |
| `mae_xz_mev_per_cell` | float64 | meV cell⁻¹ | Signed `1000(E_z-E_x)`. Negative means z is easier than x. |
| `mae_yz_mev_per_cell` | float64 | meV cell⁻¹ | Signed `1000(E_z-E_y)`. Negative means z is easier than y. |
| `ranked_orientations` | array[string] | permutation of x, y, z | Orientations from lowest to highest energy. Tied labels are presented x, y, z. |
| `orientation_ranks` | object[float64] | 1 | Exact x, y, z average ranks in `[1,3]`; ties receive average rank. |
| `easy_axis` | string | x, y, or z | First minimum-energy orientation after the frozen tie policy. |
| `ordering_evidence` | object | — | Complete FM and AFM scalar/SOC evidence described below. |

### Aggregate metric columns

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `primary_metric` | string | `magnetocrystalline_anisotropy_rank_correlation` | Metric identity. |
| `magnetocrystalline_anisotropy_rank_correlation` | float64 | Spearman ρ in `[-1,1]` | Complete-panel correlation of predicted and reference signed MAE ordering. |
| `easy_axis_errors` | int64 | count, `>=0` | Number of materials whose predicted easy axis differs from reference. |
| `completed_material_count` | int64 | count | Completed prediction count; equals fixture size. |
| `minimum_material_count` | int64 | count | Frozen minimum panel size. |
| `measurement_complete` | bool | `true` | Atomic completeness assertion. |
| `acceptance_threshold` | float64 | `1.0` | Required Spearman correlation. |

The MAE score is nonzero only when the row is complete, ρ equals 1, and
`easy_axis_errors` is zero.

## Tc prediction row

### Prediction columns

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `material_id` | string | — | Fixture material identity. |
| `formula` | string | — | Chemical formula. |
| `status` | string | `completed` | Completion state; no other value is serializable. |
| `fidelity_tier_used` | string | `high_soc` | Tier that supplied the measurement. |
| `exchange_parallel_mev` | float64 | meV | `J_parallel = 1000(E_afm^x-E_fm^x)/(2 z_nn S²)`. |
| `exchange_perpendicular_mev` | float64 | meV | `J_perpendicular = 1000(E_afm^z-E_fm^z)/(2 z_nn S²)`. |
| `exchange_mev` | float64 | meV | Positive `J=(J_parallel+J_perpendicular)/2`. |
| `exchange_anisotropy` | float64 | 1 | `Δ=(J_perpendicular-J_parallel)/(2J)`, in `(0,0.2]`. |
| `tc_green_k` | float64 | K | Positive Green-function fitted estimate. |
| `tc_mc_k` | float64 | K | Positive Monte-Carlo fitted estimate. |
| `tc_rnsw_k` | float64 | K | Positive renormalized-spin-wave fitted estimate. |
| `ordering_evidence` | object | — | Complete FM and AFM scalar/SOC evidence described below. |

The exchange definition is the Tiwari et al. Eq. (4) mapping. Do not substitute
`J_parallel` for `J`, and do not divide the exchange difference by
`J_parallel`.

### Aggregate metric columns

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `primary_metric` | string | `tc_rnsw_mae_k` | Metric identity. |
| `tc_rnsw_mae_k` | float64 | K | Mean absolute error of RNSW Tc over the complete panel. |
| `tc_envelope_coverage` | float64 | fraction `[0,1]` | Fraction of RNSW predictions inside each material's reference method envelope. |
| `completed_material_count` | int64 | count | Completed prediction count; equals fixture size. |
| `minimum_material_count` | int64 | count | Frozen minimum panel size. |
| `measurement_complete` | bool | `true` | Atomic completeness assertion. |

With tolerance `T_tol = row_spec.measurement.tc_error_tolerance_k`, the Tc
score is `max(0, 1 - tc_rnsw_mae_k/T_tol)`.

## Ordering evidence columns

Both `ordering_evidence.fm` and `ordering_evidence.afm` contain every field in
this table.

| Column | JSON type | Unit / values | Meaning |
|---|---:|---:|---|
| `ordering` | string | `fm` or `afm` | Ordering identity matching the parent key. |
| `scalar_total_energy_ev` | float64 | eV cell⁻¹ | Converged scalar total energy. |
| `scalar_band_energy_ev` | float64 | eV cell⁻¹ | Scalar band-energy reference for force-theorem correction. |
| `soc_band_energies_ev` | object[float64] | eV cell⁻¹ | Exact x, y, z SOC band energies. |
| `orientation_energies_ev` | object[float64] | eV cell⁻¹ | Exact x, y, z corrected energies. |
| `soc_method` | string | frozen identifier | SOC backend used. |
| `geometry_method` | string | frozen identifier | Geometry relaxation method used. |

For axis `a`, the corrected orientation energy is

```text
E_ordering^a = scalar_total_energy_ev
             + soc_band_energies_ev[a]
             - scalar_band_energy_ev.
```

## Worked fixture-to-row example

For the example fixture above, suppose the high-SOC backend returns these
corrected splittings:

```text
J_parallel      = 1000[-99.93250 - (-100.00000)] / (2*3*1.5^2) = 5.00 meV
J_perpendicular = 1000[-99.92675 - (-100.00100)] / (2*3*1.5^2) = 5.50 meV
J               = (5.00 + 5.50)/2                              = 5.25 meV
Delta           = (5.50 - 5.00)/(2*5.25)                       = 0.047619...
```

The corresponding fully populated local `tc_prediction` row is:

```json
{
  "predictions": [
    {
      "material_id": "example-cr2",
      "formula": "Cr2",
      "status": "completed",
      "fidelity_tier_used": "high_soc",
      "exchange_parallel_mev": 5.0,
      "exchange_perpendicular_mev": 5.5,
      "exchange_mev": 5.25,
      "exchange_anisotropy": 0.047619047619047616,
      "tc_green_k": 95.47390240469808,
      "tc_mc_k": 74.80539839533992,
      "tc_rnsw_k": 49.9352071799864,
      "ordering_evidence": {
        "fm": {
          "ordering": "fm",
          "scalar_total_energy_ev": -100.0005,
          "scalar_band_energy_ev": -20.0,
          "soc_band_energies_ev": {"x": -19.9995, "y": -19.9993, "z": -20.0005},
          "orientation_energies_ev": {"x": -100.0, "y": -99.9998, "z": -100.001},
          "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
          "geometry_method": "mlip_fire_relaxation"
        },
        "afm": {
          "ordering": "afm",
          "scalar_total_energy_ev": -99.93,
          "scalar_band_energy_ev": -19.99,
          "soc_band_energies_ev": {"x": -19.9925, "y": -19.9923, "z": -19.98675},
          "orientation_energies_ev": {"x": -99.9325, "y": -99.9323, "z": -99.92675},
          "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
          "geometry_method": "mlip_fire_relaxation"
        }
      }
    }
  ],
  "score": 1.0,
  "score_unit": "row_native_physical_score",
  "metrics": {
    "primary_metric": "tc_rnsw_mae_k",
    "tc_rnsw_mae_k": 0.0,
    "tc_envelope_coverage": 1.0,
    "completed_material_count": 1,
    "minimum_material_count": 1,
    "measurement_complete": true
  },
  "row_spec": {
    "row_id": "soc_tc",
    "measurement_mode": "tc_prediction",
    "requested_tier": "high_soc",
    "execution_protocol": {
      "geometry_method": "mlip_fire_relaxation",
      "geometry_force_convergence_ev_per_angstrom": 0.05,
      "geometry_maximum_steps": 200,
      "scalar_method": "gpaw_pbe_collinear_spin_polarized",
      "gpaw_plane_wave_cutoff_ev": 500.0,
      "gpaw_kpoint_density_per_angstrom": 6.0,
      "gpaw_fermi_width_ev": 0.05,
      "gpaw_convergence_energy_ev": 0.000001,
      "gpaw_maximum_scf_iterations": 200,
      "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
      "soc_axes_degrees": {"x": [90.0, 0.0], "y": [90.0, 90.0], "z": [0.0, 0.0]},
      "tc_model": "tiwari_eq3_eq4_nearest_neighbor",
      "minimum_local_moment_muB": 0.5,
      "minimum_moment_retention_fraction": 0.5,
      "orientation_tie_tolerance_mev": 0.001,
      "failure_policy": "fail cell without measurement-row serialization"
    },
    "measurement": {
      "metric": "tc_rnsw_mae_k",
      "unit": "K",
      "minimum_material_count": 1,
      "tc_error_tolerance_k": 25.0
    }
  },
  "fixture_contract": {
    "schema": "lupine.z2.soc_tc_fixture.v1",
    "fixture_id": "example-cr2-high-soc",
    "material_count": 1,
    "minimum_material_count": 1,
    "release_ready": true,
    "blockers": []
  },
  "n_structures": 1
}
```

The one-material minimum shown here is only for the compact local example. The
locked campaign row replaces it with the campaign's frozen minimum and contains
one complete prediction per locked material.

## Low-tier screening row

A low-tier prediction contains `material_id`, `formula`, `status` (`completed`),
`fidelity_tier_used` (`low_collinear`), `fm_scalar_energy_ev` and
`afm_scalar_energy_ev` (eV cell⁻¹), `collinear_exchange_screen_mev` (meV),
`minimum_final_local_moment_muB` (μB), `moment_retention_fraction`
(dimensionless), `promotable_to_high_soc` (bool), and `screening_reasons`.
Reasons are unique values from `local_moment_below_threshold`,
`moment_retention_below_threshold`, and `nonferromagnetic_exchange`.

Its aggregate metric is `promotable_fraction`; the exact metric object also
contains `completed_material_count`, `minimum_material_count`, and
`measurement_complete: true`. A finite non-promotable screen is a complete
diagnostic row, but in `auto` it stops routing and no final MAE/Tc row is
written. Numerical failure or non-convergence writes no screening row.

## Physics boundary

The Tc values are nearest-neighbour analytical estimates from Tiwari et al.,
*Phys. Rev. Research* **3**, 043024 (2021), Eqs. (3)–(4). They are defined only
for finite `J > 0`, `S > 0`, and `0 < Δ <= 0.2`; the runner fails rather than
clipping or imputing out-of-domain values. Long-range exchange, itinerancy,
substrate effects, and finite-size scaling are outside this row contract.
