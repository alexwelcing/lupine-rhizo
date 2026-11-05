import { buildObservedManifoldMatrix, covarianceParticipationRatio, type ManifoldRecord, type ManifoldSelection } from "./observedManifoldMatrix";

export interface RunManifoldResult {
  vectorCount: number;
  descriptiveOnly: true;
  error?: string;
  matrix?: ManifoldSelection;
  properties?: string[];
  means?: number[];
  covarianceMatrix?: number[][];
  topEigenvalue?: number | null;
  traceCovariance?: number;
  participationRatio?: number | null;
  hyperRibbon?: boolean | null;
  participationRatioMethod?: string;
  principalDirection?: number[] | null;
  principalDirectionMethod?: string;
}

/** Existing POST /run calculation. Selection counts start after the explicit property, element and style filters. */
export async function analyzeRunManifold(db: D1Database, opts: {
  element?: string | null; excludeStyles?: string[]; onlyStyles?: string[];
} = {}): Promise<RunManifoldResult> {
  const element = opts.element ?? null;
  const excludeStyles = opts.excludeStyles ?? [];
  const onlyStyles = opts.onlyStyles ?? [];
  const properties = ["C11", "C12", "C44"];
  const conditions = ["property IN ('C11','C12','C44')"];
  const bindings: string[] = [];
  const bind = (value: string) => { bindings.push(value); return "?" + bindings.length; };
  if (element) conditions.push("element = " + bind(element));
  if (excludeStyles.length > 0) conditions.push("pair_style NOT IN (" + excludeStyles.map(bind).join(",") + ")");
  if (onlyStyles.length > 0) conditions.push("pair_style IN (" + onlyStyles.map(bind).join(",") + ")");
  const errorRows = await db.prepare(
    `SELECT element, potential_id, potential_label, property, reference, predicted, unit
     FROM records WHERE ${conditions.join(" AND ")}
     ORDER BY element, potential_id, property`
  ).bind(...bindings).all<ManifoldRecord>();

  // Keep the fixed elastic basis and each element/model identity.
  // Missing, invalid or conflicting observations cannot complete a vector.
  const observed = buildObservedManifoldMatrix(errorRows.results, properties);
  const vectors = observed.ok ? observed.errors.map(v => ({ v })) : [];

  if (observed.ok && vectors.length >= 3) {
    // Compute covariance matrix
    const n = vectors.length;
    const dim = properties.length;
    const means = new Array(dim).fill(0);
    for (const { v } of vectors) for (let j = 0; j < dim; j++) means[j] += v[j] / n;
    const cov: number[][] = Array.from({ length: dim }, () => new Array(dim).fill(0));
    for (const { v } of vectors) {
      for (let i = 0; i < dim; i++) for (let j = 0; j < dim; j++) {
        cov[i][j] += (v[i] - means[i]) * (v[j] - means[j]) / (n - 1);
      }
    }

    // Power iteration for top eigenvalue
    let ev = new Array(dim).fill(1 / Math.sqrt(dim));
    let directionAvailable = false;
    for (let iter = 0; iter < 100; iter++) {
      const next = new Array(dim).fill(0);
      for (let i = 0; i < dim; i++) for (let j = 0; j < dim; j++) next[i] += cov[i][j] * ev[j];
      const norm = Math.sqrt(next.reduce((s, x) => s + x * x, 0));
      if (!Number.isFinite(norm) || norm === 0) break;
      ev = next.map(x => x / norm);
      directionAvailable = true;
    }
    const Av = new Array(dim).fill(0);
    for (let i = 0; i < dim; i++) for (let j = 0; j < dim; j++) Av[i] += cov[i][j] * ev[j];
    const lambda1 = Av.reduce((s, x, i) => s + x * ev[i], 0);
    const traceC = cov.reduce((s, row, i) => s + row[i], 0);
    const PR = covarianceParticipationRatio(cov);

    return {
      vectorCount: vectors.length,
      matrix: observed.selection,
      properties,
      means: means.map(m => +m.toFixed(6)),
      covarianceMatrix: cov.map(row => row.map(x => +x.toFixed(6))),
      topEigenvalue: directionAvailable && Number.isFinite(lambda1) ? +lambda1.toFixed(6) : null,
      traceCovariance: +traceC.toFixed(6),
      participationRatio: PR === null ? null : +PR.toFixed(4),
      hyperRibbon: PR === null ? null : PR < 2.0,
      descriptiveOnly: true,
      participationRatioMethod: "trace-squared-over-full-covariance-frobenius-squared",
      ...(PR === null ? { error: "invalid_observed_covariance" } : {}),
      principalDirection: directionAvailable ? ev.map(x => +x.toFixed(4)) : null,
      principalDirectionMethod: "legacy power-iteration estimate; not a largest-eigenvalue certificate",
    };
  } else {
    return {
      error: observed.ok ? "Insufficient complete vectors" : observed.error,
      vectorCount: observed.selection?.complete_row_count ?? 0,
      matrix: observed.selection,
      descriptiveOnly: true,
    };
  }
}
