/** Observed rows for the existing manifold consumer; no missing-value imputation. */
export const MANIFOLD_MATRIX_CONTRACT = "observed-complete-cases-v1" as const;

export interface ManifoldRecord {
  element: string;
  potential_label: string;
  potential_id?: string | null;
  property: string;
  reference: number;
  predicted: number;
  unit?: string;
}

export interface ManifoldSelection {
  contract: typeof MANIFOLD_MATRIX_CONTRACT;
  row_unit: "element-and-potential-identity";
  scaling: "relative-error-by-reference";
  input_record_count: number;
  input_row_count: number;
  complete_row_count: number;
  excluded_row_count: number;
  missing_cell_count: number;
  invalid_cell_count: number;
  conflicting_cell_count: number;
  duplicate_record_count: number;
  label_identity_row_count: number;
  properties: string[];
  centered_rank_ceiling: number;
}

export type ObservedMatrix =
  | { ok: false; error: string; selection?: ManifoldSelection }
  | { ok: true; errors: number[][]; included_indices: number[]; selection: ManifoldSelection };

/**
 * One row per element and supplied potential ID (label fallback is disclosed).
 * Identical repeated cells do not add samples. Conflicting cells exclude their row.
 * The property set is fixed before complete-case selection: supplied explicitly,
 * or derived from all input properties when no basis is supplied.
 * This establishes an observed matrix, not artifact independence or compatibility.
 */
export function buildObservedManifoldMatrix(records: readonly ManifoldRecord[], requiredProperties?: readonly string[]): ObservedMatrix {
  if (records.some(r => !r.element || !r.potential_label || !r.property)) {
    return { ok: false, error: "missing_observation_identity" };
  }
  const properties = [...new Set(requiredProperties ?? records.map(r => r.property))].sort();
  if (requiredProperties && (properties.length !== requiredProperties.length
    || properties.some(p => !p) || records.some(r => !properties.includes(r.property)))) {
    return { ok: false, error: "invalid_required_properties" };
  }
  if (properties.length < 2 || properties.length > 5) {
    return { ok: false, error: "unsupported_property_count: require 2 to 5 for the complete spectrum" };
  }
  const groups = new Map<string, { cells: Map<string, number[]>; labelIdentity: boolean }>();
  records.forEach((r, index) => {
    const id = r.potential_id || r.potential_label;
    const key = JSON.stringify([r.element, r.potential_id ? "id" : "label", id]);
    if (!groups.has(key)) groups.set(key, { cells: new Map(), labelIdentity: !r.potential_id });
    const group = groups.get(key)!;
    const cell = group.cells.get(r.property) ?? [];
    cell.push(index);
    group.cells.set(r.property, cell);
  });
  const selection: ManifoldSelection = {
    contract: MANIFOLD_MATRIX_CONTRACT,
    row_unit: "element-and-potential-identity",
    scaling: "relative-error-by-reference",
    input_record_count: records.length,
    input_row_count: groups.size,
    complete_row_count: 0,
    excluded_row_count: 0,
    missing_cell_count: 0,
    invalid_cell_count: 0,
    conflicting_cell_count: 0,
    duplicate_record_count: 0,
    label_identity_row_count: 0,
    properties,
    centered_rank_ceiling: 0,
  };
  const errors: number[][] = [];
  const included_indices: number[] = [];
  for (const [, group] of [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const row: number[] = [];
    const indices: number[] = [];
    let eligible = true;
    for (const property of properties) {
      const cell = group.cells.get(property);
      if (!cell) {
        selection.missing_cell_count++;
        eligible = false;
        continue;
      }
      selection.duplicate_record_count += cell.length - 1;
      const first = records[cell[0]];
      const valid = cell.every(i => {
        const r = records[i];
        return Number.isFinite(r.reference) && r.reference !== 0
          && Number.isFinite(r.predicted)
          && Number.isFinite((r.predicted - r.reference) / r.reference);
      });
      if (!valid) {
        selection.invalid_cell_count++;
        eligible = false;
        continue;
      }
      if (cell.some(i => records[i].reference !== first.reference
        || records[i].predicted !== first.predicted || records[i].unit !== first.unit)) {
        selection.conflicting_cell_count++;
        eligible = false;
        continue;
      }
      row.push((first.predicted - first.reference) / first.reference);
      indices.push(...cell);
    }
    if (eligible) {
      errors.push(row);
      included_indices.push(...indices);
      if (group.labelIdentity) selection.label_identity_row_count++;
    }
  }
  selection.complete_row_count = errors.length;
  selection.excluded_row_count = selection.input_row_count - errors.length;
  selection.centered_rank_ceiling = Math.min(properties.length, Math.max(0, errors.length - 1));
  if (errors.length < 2) {
    return { ok: false, error: "insufficient_complete_observations", selection };
  }
  if (!properties.some((_, j) => errors.some(row => row[j] !== errors[0][j]))) {
    return { ok: false, error: "no_observed_variation", selection };
  }
  return { ok: true, errors, included_indices, selection };
}

/**
 * Participation ratio of a supplied covariance matrix:
 * (tr C)^2 / tr(C^2) = (tr C)^2 / sum_ij C_ij^2 for symmetric C.
 * Off-diagonal terms are essential. Scaling avoids squaring large/small units.
 * This calculation does not establish that a source matrix is a valid covariance.
 */
export function covarianceParticipationRatio(cov: readonly (readonly number[])[]): number | null {
  const dim = cov.length;
  if (!dim || cov.some(row => row.length !== dim || row.some(x => !Number.isFinite(x)))) return null;
  const scale = Math.max(...cov.flatMap(row => [...row].map(Math.abs)));
  if (scale === 0) return null;
  let trace = 0;
  let frobeniusSquared = 0;
  for (let i = 0; i < dim; i++) {
    trace += cov[i][i] / scale;
    for (let j = 0; j < dim; j++) frobeniusSquared += (cov[i][j] / scale) ** 2;
  }
  const pr = trace ** 2 / frobeniusSquared;
  return trace > 0 && Number.isFinite(pr) && pr > 0 ? pr : null;
}
