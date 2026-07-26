# Z2 spin-aware SOC/Tc runner contract

Status: implementation contract
Schema: `lupine.z2.soc_tc_fixture.v1`
Runner row ID: `soc_tc`

## Hypotheses and fail-closed rule

The confirmatory hypotheses are that the spin-aware stack (1) reproduces the complete held-out ordering of signed magnetocrystalline anisotropy energies (MAEs), including the easy-axis direction, and (2) predicts Curie temperature from the same FM/AFM spin evidence using the frozen nearest-neighbour analytical model.

A measurement is valid only when every requested material produces a finite, high-fidelity SOC result. One easy-axis error kills the MAE claim; Spearman rank correlation below 1 demotes it. A failed, non-converged, out-of-domain, or non-finite case fails the cell before a measurement row is serialized. The measurement output MUST NOT contain `null`, `NaN`, `Infinity`, empty-string sentinels, `status: "failed"`, `status: "abstained"`, or placeholder magnetic observables. Failure diagnostics belong in the cell error/log artifact, not in `predictions`.

This rule is intentionally stricter than the older generic fixture behavior in `python/lupine_distill/fixture_contract.py` and the Z1 barrier failure records in `gcp/mlip-cell-runner/z1_barrier.py`: an incomplete list cannot be interpreted as a magnetic ranking.

## Physics model

The model uses an MLIP only for geometry relaxation. Spin-resolved energies come from a spin-polarized electronic-structure backend. For each magnetic ordering `q ∈ {fm, afm}` and axis `a ∈ {x, y, z}`, let `E_q^a` be the finite total/force-theorem energy in eV per simulation cell.

The signed MAEs are

```text
MAE_xz = 1000 (E_fm^z - E_fm^x)   [meV cell^-1]
MAE_yz = 1000 (E_fm^z - E_fm^y)   [meV cell^-1].
```

Orientations are ranked by ascending `E_fm^a`; the first entry is the easy axis. Thus a negative `MAE_xz` means z is easier than x. Values within `orientation_tie_tolerance_mev` are tied and receive average ranks; the deterministic presentation order for tied labels is x, y, z.

For spin quantum number `S` and nearest-neighbour coordination `z_nn`, define the axis-resolved exchange constants from the AFM–FM splittings:

```text
J_parallel      = 1000 (E_afm^x - E_fm^x) / (2 z_nn S^2)   [meV]
J_perpendicular = 1000 (E_afm^z - E_fm^z) / (2 z_nn S^2)   [meV]
J               = (J_parallel + J_perpendicular) / 2        [meV]
Delta           = (J_perpendicular - J_parallel) / (2 J)    [dimensionless].
```

The final two equations are the Tiwari et al. Eq. (4) mapping. In particular, the contract MUST NOT substitute `J_parallel` for `J` or divide the exchange difference by `J_parallel`. For the independent regression case `J_parallel = 5.0 meV` and `J_perpendicular = 5.5 meV`, the required result is `J = 5.25 meV` and `Delta = 0.047619047619...`.

For each frozen method `m ∈ {green, mc, rnsw}`, Curie temperature is

```text
Tc_m = J (S^2 + theta_m S) /
       [2 k_B (alpha1_m - alpha2_m ln Delta)]   [K],
k_B = 0.08617333262 meV K^-1,
```

using the lattice-specific coefficients frozen in the panel. Tc is defined only for finite `J > 0`, `S > 0`, and `0 < Delta <= 0.2`. Inputs outside that published fit domain fail the cell; they are not clipped or imputed. This is a nearest-neighbour model, not an experimental Tc prediction: long-range exchange, itinerancy, substrates, and finite-size scaling are out of scope.

## Fidelity tiers and routing

### Tier L: `low_collinear`

Tier L is the mandatory fast screen in `auto` mode:

1. Relax one geometry with the selected MLIP/FIRE controls.
2. Run collinear, spin-polarized scalar FM and AFM calculations without SOC.
3. Require geometry convergence, both SCF calculations to converge, finite energies, all initialized magnetic sites to retain at least `minimum_local_moment_muB`, and the mean absolute final/initial local-moment ratio to be at least `minimum_moment_retention_fraction`.
4. Compute the collinear splitting `1000(E_afm - E_fm)/(2 z_nn S^2)` only as routing evidence and require it to be positive for promotion.

Tier L cannot measure magnetocrystalline anisotropy: a scalar Hamiltonian has no magnetization-direction energy. It also cannot produce a contract-valid 2D Tc because `Delta` is unavailable. A `requested_tier: "low_collinear"` fixture is therefore legal only with `measurement_modes: ["screening"]`; it emits a fully populated diagnostic screening row, never an MAE or Tc row.

### Tier H: `high_soc`

Tier H reuses the relaxed geometry and converged scalar FM/AFM states, then evaluates non-collinear/spinor SOC energies for x, y, and z magnetization. The default backend is the non-selfconsistent force-theorem SOC pass frozen by the panel. It derives the two MAEs, the full orientation ranking, `J_parallel`, `J_perpendicular`, `J`, `Delta`, and all three Tc estimates.

Tier H is invoked when either:

- `requested_tier` is `high_soc`; or
- `requested_tier` is `auto`, Tier L passes, and `measurement_modes` contains `mae_ranking` or `tc_prediction`.

`high_soc` still performs or loads the scalar FM/AFM prerequisite; it does not bypass it. In `auto`, a Tier L failure is a hard cell failure. There is no fallback low-tier MAE/Tc row. A valid `mae_ranking` or `tc_prediction` row therefore always has `fidelity_tier_used: "high_soc"`.

## Fixture input contract

The fixture is a JSON object. Unknown fields are rejected so that a misspelled spin or tier control cannot silently change the calculation.

### Root fields

| Field | JSON type | Required | Contract |
|---|---:|---:|---|
| `schema` | string | yes | Literal `lupine.z2.soc_tc_fixture.v1`. |
| `fixture_id` | string | yes | Non-empty stable identifier. |
| `requested_tier` | string enum | yes | `low_collinear`, `high_soc`, or `auto`. |
| `measurement_modes` | array[string] | yes | Non-empty, unique subset of `screening`, `mae_ranking`, `tc_prediction`; exact legal combinations below. |
| `materials` | array[object] | yes | Non-empty; `material_id` values unique. The locked campaign requires at least five. |
| `execution_protocol` | object | yes | Frozen numerical controls listed below. |
| `reference_provenance` | object | yes | Must contain a non-empty source identifier and SHA-256 lock. |

`reference_provenance` has exactly three string fields: `source_id` (non-empty
publication/dataset identifier), `source_url` (absolute `https://` URL), and
`sha256` (literal `sha256:` followed by 64 lowercase hexadecimal characters).
The legal tier/mode combinations are: `low_collinear` with exactly
`["screening"]`; and `auto` or `high_soc` with `mae_ranking`, `tc_prediction`,
or both, with no `screening` entry. Mode order is canonical:
`mae_ranking`, then `tc_prediction`.

### Material fields

| Field | JSON type | Unit | Required constraint |
|---|---:|---:|---|
| `material_id` | string | — | Non-empty and unique. |
| `formula` | string | — | Non-empty. |
| `lattice` | string enum | — | `honeycomb`, `hexagonal`, or `square`. |
| `spin` | float64 | ℏ | Finite and `> 0`. |
| `nearest_neighbors` | int64 | count | `>= 1`. |
| `magnetic_atom_indices` | array[int64] | zero-based index | Non-empty, unique, each in `[0, N)`. |
| `afm_signs` | array[int64] | — | Same length as magnetic indices; each exactly `-1` or `+1`; both signs present. |
| `structure` | object | — | Exact structure contract below. |
| `reference` | object | — | Required for confirmatory rows; exact reference contract below. |

The runner initializes each magnetic site to `2 S * afm_sign` μB for AFM and `2 S` μB for FM. Nonmagnetic sites retain the structure's supplied initial moment. This ordering-specific initialization is authoritative over the corresponding entries in `structure.initial_magmoms`.

### Structure fields

| Field | JSON type | Unit | Constraint |
|---|---:|---:|---|
| `symbols` | array[string] | — | Length `N >= 1`; valid element symbols. |
| `positions_angstrom` | array[array[float64]] | Å | Finite shape `(N, 3)`. Cartesian coordinates. |
| `cell_angstrom` | array[array[float64]] | Å | Finite, nonsingular shape `(3, 3)`; ASE row-vector convention. |
| `pbc` | array[bool] | — | Length 3. A 2D panel normally uses `[true, true, false]`. |
| `initial_magmoms` | array[float64] | μB | Finite length `N`; required, including explicit zeros on nonmagnetic atoms. |

### Reference fields

| Field | JSON type | Unit | Constraint |
|---|---:|---:|---|
| `mae_xz_mev_per_cell` | float64 | meV cell^-1 | Finite, signed. |
| `mae_yz_mev_per_cell` | float64 | meV cell^-1 | Finite, signed. |
| `exchange_mev` | float64 | meV | Finite and positive; Eq. (4) mean exchange. |
| `exchange_anisotropy` | float64 | 1 | Finite in `(0, 0.2]`. |
| `tc_k` | object | K | Exactly `green`, `mc`, and `rnsw`, each finite and `> 0`. |
| `tc_envelope_k` | array[float64] | K | Exactly `[low, high]`, finite, `0 < low <= high`. |

### Required execution controls

`execution_protocol` contains finite positive float64 values `geometry_force_convergence_ev_per_angstrom`, `gpaw_plane_wave_cutoff_ev`, `gpaw_kpoint_density_per_angstrom`, `gpaw_fermi_width_ev`, `gpaw_convergence_energy_ev`, `minimum_local_moment_muB`, `minimum_moment_retention_fraction`, and `orientation_tie_tolerance_mev`; positive int64 values `geometry_maximum_steps` and `gpaw_maximum_scf_iterations`; and `soc_axes_degrees` with exactly finite x/y/z `[theta, phi]` pairs. `minimum_moment_retention_fraction` is in `(0, 1]`.

The remaining protocol fields are exact strings: `geometry_method` =
`mlip_fire_relaxation`, `scalar_method` =
`gpaw_pbe_collinear_spin_polarized`, `soc_method` =
`gpaw_nonselfconsistent_force_theorem_xyz`, `tc_model` =
`tiwari_eq3_eq4_nearest_neighbor`, and `failure_policy` =
`fail cell without measurement-row serialization`. No other protocol keys are
accepted.

## Measurement output envelope

Each requested mode is serialized as one row-native JSON object, matching the Z1 shape:

| Field | JSON type | Contract |
|---|---:|---|
| `predictions` | array[object] | Exactly one completed prediction per fixture material, in fixture order. |
| `score` | float64 | Finite in `[0, 1]`. |
| `score_unit` | string | Literal `row_native_physical_score`. |
| `metrics` | object | Mode-specific aggregate schema below. |
| `row_spec` | object | Exactly `row_id`, `measurement_mode`, `requested_tier`, `execution_protocol`, and `measurement`. |
| `fixture_contract` | object | Validator result; `release_ready` must be `true` and `blockers` must be `[]`. |
| `n_structures` | int64 | Equals both `len(materials)` and `len(predictions)`. |

Every prediction includes `material_id` (string), `formula` (string), `status` (literal `completed`), and `fidelity_tier_used` (literal `high_soc` for either final mode). All floats are JSON numbers originating from float64 calculations and must be finite.

`fixture_contract` has exactly `schema` (the fixture schema string),
`fixture_id` (string), `material_count` (int64), `minimum_material_count`
(int64), `release_ready` (literal `true`), and `blockers` (literal empty array).
For `mae_ranking`, `row_spec.measurement` has exactly `metric` =
`magnetocrystalline_anisotropy_rank_correlation`, `unit` = `spearman_rho`,
`minimum_material_count` (int64), and `acceptance_threshold` (float64 `1.0`).
For `tc_prediction`, it has exactly `metric` = `tc_rnsw_mae_k`, `unit` = `K`,
`minimum_material_count` (int64), and finite positive float64
`tc_error_tolerance_k`.

### `mae_ranking` prediction schema

| Column | JSON type | Unit / allowed values | Meaning |
|---|---:|---:|---|
| `material_id` | string | — | Fixture identity. |
| `formula` | string | — | Chemical formula. |
| `status` | string | `completed` | Complete case only. |
| `fidelity_tier_used` | string | `high_soc` | Actual tier. |
| `orientation_energies_ev` | object[float64] | eV cell^-1 | Exactly x, y, z FM SOC energies. |
| `mae_xz_mev_per_cell` | float64 | meV cell^-1 | `1000(E_z-E_x)`. |
| `mae_yz_mev_per_cell` | float64 | meV cell^-1 | `1000(E_z-E_y)`. |
| `ranked_orientations` | array[string] | permutation of x, y, z | Lowest to highest energy; x/y/z tie presentation. |
| `orientation_ranks` | object[float64] | dimensionless | Exactly x, y, z average ranks in `[1, 3]`. |
| `easy_axis` | string | x, y, or z | First minimum-energy orientation after tie policy. |
| `ordering_evidence` | object | — | Exact FM and AFM evidence schema below. |

The MAE aggregate `metrics` has exactly: `primary_metric` (literal `magnetocrystalline_anisotropy_rank_correlation`), `magnetocrystalline_anisotropy_rank_correlation` (float64 in `[-1,1]`), `easy_axis_errors` (int64 `>= 0`), `completed_material_count` (int64), `minimum_material_count` (int64), `measurement_complete` (literal `true` for serialized rows), and `acceptance_threshold` (float64, frozen at `1.0`). `score` is nonzero only for a complete row with rho `= 1` and zero easy-axis errors.

### `tc_prediction` prediction schema

| Column | JSON type | Unit / allowed values | Meaning |
|---|---:|---:|---|
| `material_id` | string | — | Fixture identity. |
| `formula` | string | — | Chemical formula. |
| `status` | string | `completed` | Complete case only. |
| `fidelity_tier_used` | string | `high_soc` | Actual tier. |
| `exchange_parallel_mev` | float64 | meV | `J_parallel` from x-axis splitting. |
| `exchange_perpendicular_mev` | float64 | meV | `J_perpendicular` from z-axis splitting. |
| `exchange_mev` | float64 | meV | `(J_parallel+J_perpendicular)/2`, positive. |
| `exchange_anisotropy` | float64 | 1 | `(J_perpendicular-J_parallel)/(2J)`, in `(0,0.2]`. |
| `tc_green_k` | float64 | K | Green-function fit estimate, positive. |
| `tc_mc_k` | float64 | K | Monte-Carlo fit estimate, positive. |
| `tc_rnsw_k` | float64 | K | Renormalized-spin-wave fit estimate, positive. |
| `ordering_evidence` | object | — | Same exact FM/AFM evidence as the MAE row. |

The Tc aggregate `metrics` has exactly: `primary_metric` (literal `tc_rnsw_mae_k`), `tc_rnsw_mae_k` (finite float64, K), `tc_envelope_coverage` (finite float64 in `[0,1]`), `completed_material_count` (int64), `minimum_material_count` (int64), and `measurement_complete` (literal `true`). The row score is `max(0, 1 - tc_rnsw_mae_k / tc_error_tolerance_k)` with a finite positive tolerance frozen in `row_spec.measurement`.

### Ordering evidence schema

Both `ordering_evidence.fm` and `.afm` contain exactly:

| Field | JSON type | Unit / values |
|---|---:|---:|
| `ordering` | string | `fm` or `afm`, matching the parent key. |
| `scalar_total_energy_ev` | float64 | eV cell^-1. |
| `scalar_band_energy_ev` | float64 | eV cell^-1. |
| `soc_band_energies_ev` | object[float64] | Exactly x, y, z; eV cell^-1. |
| `orientation_energies_ev` | object[float64] | Exactly x, y, z force-theorem-corrected energies; eV cell^-1. |
| `soc_method` | string | Frozen backend identifier. |
| `geometry_method` | string | Frozen MLIP relaxation identifier. |

The corrected energy is `scalar_total_energy_ev + soc_band_energies_ev[a] - scalar_band_energy_ev` for each axis `a`.

## Low-tier screening row

A `measurement_mode: "screening"` row uses the same output envelope. Each prediction has `material_id`, `formula`, `status: "completed"`, `fidelity_tier_used: "low_collinear"`, finite `fm_scalar_energy_ev`, finite `afm_scalar_energy_ev`, finite `collinear_exchange_screen_mev`, finite `minimum_final_local_moment_muB`, finite `moment_retention_fraction`, boolean `promotable_to_high_soc`, and `screening_reasons`, an array containing zero or more unique values from `local_moment_below_threshold`, `moment_retention_below_threshold`, and `nonferromagnetic_exchange`. `promotable_to_high_soc` is true exactly when this array is empty. A finite but non-promotable low-tier screen is a fully populated diagnostic result; in `auto` mode it stops routing and fails the requested final measurement. Numerical failure or non-convergence still fails the cell without a row. Screening rows never enter MAE/Tc acceptance statistics.

The screening aggregate `metrics` has exactly `primary_metric` (literal
`promotable_fraction`), `promotable_fraction` (finite float64 in `[0,1]`),
`completed_material_count` (int64), `minimum_material_count` (int64), and
`measurement_complete` (literal `true`). Its score equals
`promotable_fraction`. `row_spec.measurement` has exactly `metric` =
`promotable_fraction`, `unit` = `fraction`, and `minimum_material_count`
(int64).

## Serialization acceptance criteria

Before writing a row, the runner MUST validate all of the following atomically:

1. Root keys and mode-specific keys are exact; no unknown or omitted columns.
2. `n_structures == completed_material_count == len(predictions) == len(fixture.materials)` and the count meets the frozen minimum.
3. Material IDs are unique and exactly preserve fixture order.
4. Every status is `completed`; every required string is non-empty; every float is finite and every integer is a JSON integer rather than a boolean.
5. Every final MAE/Tc prediction reports `high_soc` and contains complete FM and AFM x/y/z evidence.
6. `ranked_orientations` is a permutation of x/y/z and is consistent with the energy/tie policy; MAEs, exchanges, anisotropy, and Tc values recompute from evidence within the frozen numerical tolerance.
7. Tc rows satisfy `J > 0`, `0 < Delta <= 0.2`, and positive finite method estimates.
8. MAE aggregate ranks use the complete locked panel; no failed case may be dropped before Spearman correlation.
9. The serialized JSON passes a recursive forbidden-value check for null, non-finite numbers, empty placeholder strings, and abstention/failure tokens.

If any criterion fails, serialization raises a cell-level error and writes no measurement row. This is the sole permitted failure behavior.

## Traceability

- Z1 row-native envelope: `gcp/mlip-cell-runner/z1_barrier.py:290-363`.
- Generic fixture structure and validation pattern: `python/lupine_distill/fixture_contract.py:71-177` and `:258-337`.
- Locked Z2 hypotheses and gates: `campaigns/v1/z2.campaign-manifest.v1.json:10-34`.
- Frozen panel structures, spin fields, references, and protocol: `data/candidates/z2_soc_tc_panel.lock.json`.
- Preregistration boundary: `docs/plans/2026-07-21-z2-soc-tc-amendment.md`.
- Tc analytical fit: Tiwari et al., *Phys. Rev. Research* **3**, 043024 (2021), DOI `10.1103/PhysRevResearch.3.043024`, Eq. (3), Eq. (4), and Supplemental Table 1.
