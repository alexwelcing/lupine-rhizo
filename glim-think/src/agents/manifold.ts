/**
 * ManifoldAgent: PCA eigenvalue extraction & hyper-ribbon geometry.
 *
 * Upgraded to Think — the model can now reason about manifold structure
 * using tools, persist findings in context memory, and be called as a
 * sub-agent from the Orchestrator via chat() RPC.
 */

import { GlimThinkAgent } from "./base";
import { tool } from "ai";
import { z } from "zod";
import type { ToolSet } from "ai";
import { trace, SpanStatusCode } from "@opentelemetry/api";
import type { Claim } from "../types";
import { buildObservedManifoldMatrix, MANIFOLD_MATRIX_CONTRACT, type ManifoldRecord, type ManifoldSelection } from "../research/observedManifoldMatrix";
import { compactEvidenceIds, recordEvidenceId } from "../research/evidenceIds";
import { cleanRecordSqlPredicate } from "../research/recordValidation";
import {
  canonicalRecurringClaimId,
  latestEvidenceRecordTimestamp,
  upsertRecurringClaim,
} from "../research/recurringClaims";

export class Manifold extends GlimThinkAgent {
  getSystemPrompt(): string {
    return `You are the Manifold Agent (α) in the GLIM autoresearch swarm.

Your specialty: Principal Component Analysis of interatomic potential prediction error manifolds.

Core mission:
1. Query the D1 ledger for benchmark records by element and potential family
2. Compute eigenvalue spectra and participation ratios (PR)
3. Describe sample covariance concentration; PR < 2.0 is a numerical flag, not universality
4. Keep missingness, sample size, model/reference identity and scale limits explicit
5. Emit descriptive claims; legacy confidence scores are not calibrated probabilities

When analyzing, always report:
- The participation ratio (PR), relative-error scaling and complete-case selection
- Log-spacing R² and centered sample-rank ceiling
- Unresolved compatibility and identity limits; no physical or correction claim from PR alone

Be quantitative. Cite specific numbers.`;
  }

  getTools(): ToolSet {
    return {
      get_families: tool({
        description: "Get distinct potential families (pair_style) for an element from the D1 ledger",
        inputSchema: z.object({
          element: z.string().describe("Element symbol (e.g. 'Cu') or 'all'"),
        }),
        execute: async ({ element }) => {
          const rows = await this.queryLedger<{ family: string }>(
            `SELECT DISTINCT pair_style as family FROM records WHERE element = ?1 OR ?1 = 'all'`,
            element
          );
          return rows.map((r) => r.family);
        },
      }),

      load_records: tool({
        description: "Load benchmark records for a specific element and potential family",
        inputSchema: z.object({
          element: z.string().describe("Element symbol or 'all'"),
          family: z.string().describe("Potential family/pair_style (e.g. 'eam/alloy')"),
        }),
        execute: async ({ element, family }) => {
          return this.queryLedger(
            `SELECT element, potential_id, potential_label, property, reference, predicted, unit FROM records WHERE (element = ?1 OR ?1 = 'all') AND pair_style = ?2`,
            element, family
          );
        },
      }),

      compute_manifold: tool({
        description: "Compute PCA eigenvalue spectrum and participation ratio for a set of error vectors. Returns eigenvalues, PR, and log-spacing R².",
        inputSchema: z.object({
          records: z.array(z.object({
            element: z.string().min(1),
            potential_id: z.string().nullable().optional(),
            potential_label: z.string().min(1),
            property: z.string().min(1),
            unit: z.string().optional(),
            reference: z.number(),
            predicted: z.number(),
          })).describe("Benchmark records to analyze"),
        }),
        execute: async ({ records }) => {
          const observed = buildObservedManifoldMatrix(records);
          if (!observed.ok) return { error: observed.error, matrix: observed.selection };
          const errorMatrix = observed.errors;
          const properties = observed.selection.properties;

          // Compute covariance matrix
          const n = errorMatrix.length;
          const d = properties.length;
          const means = new Array(d).fill(0);
          for (const row of errorMatrix) {
            for (let j = 0; j < d; j++) means[j] += row[j] / n;
          }

          const cov: number[][] = Array.from({ length: d }, () => new Array(d).fill(0));
          for (const row of errorMatrix) {
            for (let i = 0; i < d; i++) {
              for (let j = 0; j < d; j++) {
                cov[i][j] += (row[i] - means[i]) * (row[j] - means[j]) / (n - 1);
              }
            }
          }

          // Power iteration for top eigenvalues (simple, edge-compatible)
          const eigenvalues = await this.powerIterationEigenvalues(cov, Math.min(d, 5));

          // Participation ratio
          const sumSq = eigenvalues.reduce((s, v) => s + v * v, 0);
          const sumLin = eigenvalues.reduce((s, v) => s + v, 0);
          if (!Number.isFinite(sumSq) || !Number.isFinite(sumLin) || sumSq <= 0 || sumLin <= 0) {
            return { error: "invalid_observed_spectrum", matrix: observed.selection };
          }
          const pr = (sumLin * sumLin) / sumSq;

          // Log-spacing R² (geometric decay test)
          const logEigs = eigenvalues.filter((v) => v > 0).map((v) => Math.log(v));
          const logSpacingR2 = logEigs.length > 2 ? this.computeR2(logEigs) : 0;

          return {
            eigenvalues: eigenvalues.map((v) => Math.round(v * 1e6) / 1e6),
            participationRatio: Math.round(pr * 1000) / 1000,
            logSpacingR2: Math.round(logSpacingR2 * 1000) / 1000,
            potentialCount: n,
            matrix: observed.selection,
            descriptiveOnly: true,
            propertyCount: properties.length,
            hyperRibbon: pr < 2.0,
          };
        },
      }),

      check_cached_run: tool({
        description: "Check if a manifold analysis has already been run for a given family/element",
        inputSchema: z.object({
          family: z.string(),
          element: z.string(),
        }),
        execute: async ({ family, element }) => {
          const rows = await this.sql`
            SELECT claim_id, pr FROM manifold_runs WHERE family = ${family} AND element = ${element}
          `;
          if (rows.length > 0) {
            return { cached: true, claimId: rows[0].claim_id, pr: rows[0].pr, matrixContractVerified: false };
          }
          return { cached: false };
        },
      }),

      save_claim: tool({
        description: "Persist a manifold analysis claim to the local cache",
        inputSchema: z.object({
          family: z.string(),
          element: z.string(),
          claimId: z.string(),
          pr: z.number(),
        }),
        execute: async ({ family, element, claimId, pr }) => {
          await this.sql`
            INSERT INTO manifold_runs (family, element, claim_id, pr)
            VALUES (${family}, ${element}, ${claimId}, ${pr})
            ON CONFLICT DO NOTHING
          `;
          return { saved: true };
        },
      }),
    };
  }

  /**
   * Initialization: ensure local state table exists.
   */
  async onStart() {
    this.sql`
      CREATE TABLE IF NOT EXISTS manifold_runs (
        family TEXT,
        element TEXT,
        claim_id TEXT,
        pr REAL,
        timestamp TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (family, element)
      )
    `;
  }

  /**
   * RPC entry point — run a full manifold analysis without an LLM loop.
   * Pure math: load records → compute eigenvalues + PR → persist DO-local
   * + emit a claim to env.LEDGER. Zero token cost.
   *
   * Called by the queue consumer for `manifold_analysis` task kind.
   */
  async runAnalysis(opts: {
    element: string;
    family?: string;
    force?: boolean;
  }): Promise<{
    ok: boolean;
    cached?: boolean;
    claim_id?: string;
    pr?: number;
    log_spacing_r2?: number;
    eigenvalues?: number[];
    hyper_ribbon?: boolean;
    potential_count?: number;
    property_count?: number;
    matrix?: ManifoldSelection;
    descriptive_only?: boolean;
    error?: string;
  }> {
    const tracer = trace.getTracer("glim-think.agent");
    return tracer.startActiveSpan("Manifold.runAnalysis", async (span) => {
      span.setAttribute("agent.class", "Manifold");
      span.setAttribute("manifold.element", opts.element);
      span.setAttribute("manifold.family", opts.family ?? "all");
      try {
        const result = await this._runAnalysisInner(opts);
        span.setAttribute("manifold.pr", result.pr ?? 0);
        span.setAttribute("manifold.hyper_ribbon", result.hyper_ribbon ?? false);
        span.setAttribute("manifold.potential_count", result.potential_count ?? 0);
        span.setAttribute("manifold.property_count", result.property_count ?? 0);
        span.setAttribute("output.value", JSON.stringify(result));

        // Code-eval: manifold geometry checks
        const eigenvalues = result.eigenvalues ?? [];
        const pr = result.pr ?? 0;
        const logR2 = result.log_spacing_r2 ?? 0;
        const dim = result.property_count ?? 0;
        const allPositive = eigenvalues.every(v => v > 0);
        const sorted = eigenvalues.every((v, i) => i === 0 || v <= eigenvalues[i - 1]);
        span.setAttribute("eval.code.eigenvalues_positive", allPositive);
        span.setAttribute("eval.code.eigenvalues_sorted", sorted);
        span.setAttribute("eval.code.pr_in_range", dim > 0 && pr >= 1 && pr <= dim);
        span.setAttribute("eval.code.data_sufficient", (result.potential_count ?? 0) >= 3 && dim >= 3);
        span.setAttribute("eval.code.log_r2_valid", Math.abs(logR2) <= 1);

        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (err) {
        span.recordException(err as Error);
        span.setStatus({ code: SpanStatusCode.ERROR, message: String(err) });
        throw err;
      } finally {
        span.end();
      }
    });
  }

  private async _runAnalysisInner(opts: {
    element: string;
    family?: string;
    force?: boolean;
  }): Promise<{
    ok: boolean;
    cached?: boolean;
    claim_id?: string;
    pr?: number;
    log_spacing_r2?: number;
    eigenvalues?: number[];
    hyper_ribbon?: boolean;
    potential_count?: number;
    property_count?: number;
    matrix?: ManifoldSelection;
    descriptive_only?: boolean;
    error?: string;
  }> {
    await this.onStart(); // ensure schema
    const family = opts.family ?? "all";

    // Idempotency: skip if (family, element) already screened — unless force=true,
    // in which case we delete the cached row and recompute from current records.
    if (opts.force) {
      await this.sql`DELETE FROM manifold_runs WHERE family = ${family} AND element = ${opts.element}`;
    } else {
      const cached = await this.sql`
        SELECT claim_id, pr FROM manifold_runs
        WHERE family = ${family} AND element = ${opts.element}
      `;
      if (cached.length > 0) {
        const claimId = String(cached[0].claim_id ?? "");
        // Rehydrate the FULL scientific payload from the persisted claim.
        // The manifold_runs row only stores claim_id+pr; returning just those
        // strips eigenvalues / property_count / data-sufficiency, which both
        // the combo evaluator and downstream causal/theorist reasoning need
        // (an eval-surfaced research-quality defect — see PHOENIX_EVALS_CASE_STUDY).
        try {
          const row = await this.env.LEDGER
            .prepare(`SELECT claim_data FROM claims WHERE claim_id = ?1`)
            .bind(claimId)
            .first<{ claim_data?: string }>();
          if (row?.claim_data) {
            const cd = JSON.parse(row.claim_data) as Record<string, unknown>;
            const matrix = cd.matrix as ManifoldSelection | undefined;
            if (matrix?.contract !== MANIFOLD_MATRIX_CONTRACT) {
              return { ok: false, cached: true, claim_id: claimId, error: "legacy_matrix_contract: explicit force required" };
            }
            return {
              ok: true,
              cached: true,
              claim_id: claimId,
              matrix,
              descriptive_only: true,
              pr: Number(cd.pr ?? cached[0].pr ?? 0),
              log_spacing_r2: typeof cd.log_spacing_r2 === "number" ? cd.log_spacing_r2 : undefined,
              eigenvalues: Array.isArray(cd.eigenvalues) ? (cd.eigenvalues as number[]) : undefined,
              hyper_ribbon: typeof cd.hyper_ribbon === "boolean" ? cd.hyper_ribbon : undefined,
              potential_count: typeof cd.potential_count === "number" ? cd.potential_count : undefined,
              property_count: typeof cd.property_count === "number" ? cd.property_count : undefined,
            };
          }
        } catch (e) {
          console.error("Manifold.runAnalysis: cache rehydrate failed:", e);
        }
        // A scalar cache entry cannot establish the observation contract.
        return {
          ok: false,
          cached: true,
          claim_id: claimId,
          error: "unverifiable_cached_analysis: explicit force required",
        };
      }
    }

    // Load records (matching the get_families/load_records tool flow).
    // Defense-in-depth contamination gate (research/recordValidation.ts,
    // shared with the ingest door + Causal purge): property-aware ranges —
    // PR/eigenvalues are extremely sensitive to unit-error outliers
    // (Round B/C false-discovery cause), but legitimate negatives
    // (ΔH_f, stacking-fault energy, B0′) must stay in the matrix.
    const CLEAN = cleanRecordSqlPredicate();
    const sql = family === "all"
      ? `SELECT record_id, element, potential_id, potential_label, property, reference, predicted, unit, pair_style, timestamp FROM records WHERE (element = ?1 OR ?1 = 'all') AND ${CLEAN}`
      : `SELECT record_id, element, potential_id, potential_label, property, reference, predicted, unit, pair_style, timestamp FROM records WHERE (element = ?1 OR ?1 = 'all') AND pair_style = ?2 AND ${CLEAN}`;
    const records = family === "all"
      ? await this.queryLedger<ManifoldRecord & { record_id: string; pair_style: string; timestamp: string | null }>(sql, opts.element)
      : await this.queryLedger<ManifoldRecord & { record_id: string; pair_style: string; timestamp: string | null }>(sql, opts.element, family);

    const observed = buildObservedManifoldMatrix(records);
    if (!observed.ok) return { ok: false, error: observed.error, matrix: observed.selection };
    const errorMatrix = observed.errors;
    const properties = observed.selection.properties;
    const includedRecords = observed.included_indices.map(index => records[index]);

    const n = errorMatrix.length;
    const d = properties.length;
    const means = new Array(d).fill(0);
    for (const row of errorMatrix) {
      for (let j = 0; j < d; j++) means[j] += row[j] / n;
    }
    const cov: number[][] = Array.from({ length: d }, () => new Array(d).fill(0));
    for (const row of errorMatrix) {
      for (let i = 0; i < d; i++) {
        for (let j = 0; j < d; j++) {
          cov[i][j] += (row[i] - means[i]) * (row[j] - means[j]) / Math.max(1, n - 1);
        }
      }
    }

    const eigenvalues = await this.powerIterationEigenvalues(cov, Math.min(d, 5));
    const sumSq = eigenvalues.reduce((s, v) => s + v * v, 0);
    const sumLin = eigenvalues.reduce((s, v) => s + v, 0);
    if (!Number.isFinite(sumSq) || !Number.isFinite(sumLin) || sumSq <= 0 || sumLin <= 0) {
      return { ok: false, error: "invalid_observed_spectrum", matrix: observed.selection };
    }
    const pr = (sumLin * sumLin) / sumSq;
    const logEigs = eigenvalues.filter(v => v > 0).map(v => Math.log(v));
    const logSpacingR2 = logEigs.length > 2 ? this.computeR2(logEigs) : 0;
    const hyperRibbon = pr < 2.0;

    // Persist DO-local + emit claim to env.LEDGER.
    const dimensions = { element: opts.element, family };
    const claimId = canonicalRecurringClaimId("ManifoldAnalysis", dimensions);
    const claimData = {
      element: opts.element,
      family,
      pr: Math.round(pr * 1000) / 1000,
      log_spacing_r2: Math.round(logSpacingR2 * 1000) / 1000,
      eigenvalues: eigenvalues.map(v => Math.round(v * 1e6) / 1e6),
      potential_count: n,
      property_count: properties.length,
      evidence_record_count: includedRecords.length,
      matrix: observed.selection,
      descriptive_only: true,
      confidence_basis: "legacy heuristic, not a calibrated probability",
      hyper_ribbon: hyperRibbon,
    };
    const evidenceIds = compactEvidenceIds(
      includedRecords.map((record) => recordEvidenceId(record.record_id)),
      240,
      `manifold:${opts.element}:${family}`,
    );
    const description = `Sample relative-error covariance ${opts.element}/${family}: PR=${claimData.pr}, PR<2=${hyperRibbon}, n=${n} complete element/model rows × ${properties.length} properties; descriptive only`;
    const now = new Date().toISOString();

    try {
      await upsertRecurringClaim(this.env.LEDGER, {
        agentId: "agent_alpha_manifold",
        claimType: "ManifoldAnalysis",
        dimensions,
        claimData,
        evidenceIds,
        confidence: hyperRibbon ? 0.85 : 0.6,
        description,
        evidenceRecordTimestamp: latestEvidenceRecordTimestamp(includedRecords.map((record) => record.timestamp)),
        recomputedAt: now,
      });
    } catch (e) {
      console.error("Manifold.runAnalysis: current claim upsert failed:", e);
    }

    await this.sql`
      INSERT INTO manifold_runs (family, element, claim_id, pr)
      VALUES (${family}, ${opts.element}, ${claimId}, ${pr})
      ON CONFLICT DO NOTHING
    `;

    return {
      ok: true,
      cached: false,
      claim_id: claimId,
      matrix: observed.selection,
      descriptive_only: true,
      pr: Math.round(pr * 1000) / 1000,
      log_spacing_r2: Math.round(logSpacingR2 * 1000) / 1000,
      eigenvalues: eigenvalues.map(v => Math.round(v * 1e6) / 1e6),
      hyper_ribbon: hyperRibbon,
      potential_count: n,
      property_count: properties.length,
    };
  }

  /**
   * Storage stats RPC for /graph/agents.json. Returns DO-local row counts.
   */
  async getStorageStats(): Promise<Record<string, number>> {
    await this.onStart();
    const rows = await this.sql`SELECT COUNT(*) AS n FROM manifold_runs`;
    return { manifold_runs: Number(rows[0]?.n ?? 0) };
  }

  // ─── Numerical Helpers (edge-safe, no BLAS needed) ─────────────

  private async powerIterationEigenvalues(cov: number[][], k: number): Promise<number[]> {
    const d = cov.length;
    const eigenvalues: number[] = [];
    const deflated = cov.map((row) => [...row]);

    for (let eig = 0; eig < k; eig++) {
      let v = new Array(d).fill(0).map(() => Math.random());
      let norm = Math.sqrt(v.reduce((s, x) => s + x * x, 0));
      v = v.map((x) => x / norm);

      for (let iter = 0; iter < 100; iter++) {
        const Av = new Array(d).fill(0);
        for (let i = 0; i < d; i++) {
          for (let j = 0; j < d; j++) {
            Av[i] += deflated[i][j] * v[j];
          }
        }
        norm = Math.sqrt(Av.reduce((s, x) => s + x * x, 0));
        if (norm < 1e-12) break;
        v = Av.map((x) => x / norm);
      }

      eigenvalues.push(norm);

      // Deflate
      for (let i = 0; i < d; i++) {
        for (let j = 0; j < d; j++) {
          deflated[i][j] -= norm * v[i] * v[j];
        }
      }
    }

    return eigenvalues;
  }

  private computeR2(values: number[]): number {
    const n = values.length;
    const xs = values.map((_, i) => i);
    const meanX = xs.reduce((s, x) => s + x, 0) / n;
    const meanY = values.reduce((s, y) => s + y, 0) / n;

    let ssXY = 0, ssXX = 0, ssYY = 0;
    for (let i = 0; i < n; i++) {
      ssXY += (xs[i] - meanX) * (values[i] - meanY);
      ssXX += (xs[i] - meanX) ** 2;
      ssYY += (values[i] - meanY) ** 2;
    }

    if (ssXX === 0 || ssYY === 0) return 0;
    return (ssXY * ssXY) / (ssXX * ssYY);
  }
}
