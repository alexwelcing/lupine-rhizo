/**
 * lean-proof-promotion research workflow.
 *
 * Tracks a proof revision's theorems from the Lean build through inventory
 * sync (tools/atlas_theorem_sync.py) and into facet grounding. Each workflow
 * unit is one theorem promotion and carries:
 *
 *   - theorem name + module (Lean identity),
 *   - owning facet (canonical lowercase — who this theorem grounds),
 *   - source commit (proof repository revision),
 *   - build artifact + build manifest hash,
 *   - proof verdict (`pending` | `promote` | `review` | `reject`),
 *   - agenda task ID (the durable agenda node tracking the promotion),
 *   - inventory sync result (reported by the authoritative synchronizer),
 *   - trace IDs (Phoenix traces for the build/sync/evaluate spans).
 *
 * Agenda tie-in: creating a campaign stamps one `lean-formalization` agenda
 * task per unit carrying the theorem/module identity and a completion edge;
 * when a unit's verdict lands, the agenda task is completed (promote) or
 * blocked (reject) and the `formalizes` edge to the claim/verification task
 * it discharges is written. The synchronizer remains the single writer of
 * `atlas_theorems` — this workflow only records reported sync results and
 * reads the inventory back to gate promotion.
 */

import type { Env } from "../types";
import {
  addTaskEdge,
  completeAgendaTask,
  ensureAgendaSchema,
  updateAgendaTaskStatus,
} from "../agenda";
import { isApprovedExtension, isManagedFacet, normalizeFacet } from "../atlas/facetRegistry";
import {
  inspectLeanProofCampaign,
  LEAN_PROOF_PROMOTION_DESCRIPTOR,
  maintainLeanProofCampaign,
} from "./leanProofWorkflowOps";
import {
  workflowError,
  workflowJson,
  type ResearchWorkflowAdapter,
} from "./workflowTypes";

export const LEAN_PROOF_WORKFLOW_ID = "lean-proof-promotion";

export type LeanProofUnitStatus = "queued" | "enqueued" | "running" | "completed" | "failed";
export type LeanProofVerdict = "pending" | "promote" | "review" | "reject";
export type LeanProofSyncStatus = "pending" | "upserted" | "unchanged" | "failed";

export interface LeanProofCampaignRecord {
  campaign_id: string;
  title: string;
  facet: string;
  proof_repository: string;
  proof_revision: string;
  status: "draft" | "active" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface LeanProofUnitRecord {
  unit_id: string;
  campaign_id: string;
  theorem_name: string;
  module: string;
  facet: string;
  source_commit: string;
  build_artifact: string | null;
  build_manifest_hash: string | null;
  status: LeanProofUnitStatus;
  verdict: LeanProofVerdict;
  agenda_task_id: string | null;
  completion_target_task_id: string | null;
  sync_status: LeanProofSyncStatus;
  sync_detail: string | null;
  trace_ids_json: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLeanProofCampaignInput {
  campaign_id?: string;
  title?: string;
  facet: string;
  proof_revision: string;
  proof_repository?: string;
  units: Array<{
    theorem_name: string;
    module?: string;
    build_artifact?: string;
    build_manifest_hash?: string;
    /** Existing agenda task this proof discharges (completion-edge target). */
    agenda_task_id?: string;
    trace_ids?: string[];
  }>;
}

export interface LeanProofUnitResultInput {
  campaign_id: string;
  unit_id: string;
  status?: LeanProofUnitStatus;
  verdict?: LeanProofVerdict;
  build_artifact?: string;
  build_manifest_hash?: string;
  sync_status?: LeanProofSyncStatus;
  sync_detail?: string;
  trace_ids?: string[];
}

const DEFAULT_PROOF_REPOSITORY = "lupine-science/open-distillation-factory";

export async function ensureLeanProofSchema(env: Env): Promise<void> {
  await env.LEDGER.prepare(`
    CREATE TABLE IF NOT EXISTS lean_proof_campaigns (
      campaign_id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      facet TEXT NOT NULL,
      proof_repository TEXT NOT NULL,
      proof_revision TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )
  `).run();
  await env.LEDGER.prepare(`
    CREATE TABLE IF NOT EXISTS lean_proof_units (
      unit_id TEXT PRIMARY KEY,
      campaign_id TEXT NOT NULL,
      theorem_name TEXT NOT NULL,
      module TEXT NOT NULL,
      facet TEXT NOT NULL,
      source_commit TEXT NOT NULL,
      build_artifact TEXT,
      build_manifest_hash TEXT,
      status TEXT NOT NULL DEFAULT 'queued',
      verdict TEXT NOT NULL DEFAULT 'pending',
      agenda_task_id TEXT,
      completion_target_task_id TEXT,
      sync_status TEXT NOT NULL DEFAULT 'pending',
      sync_detail TEXT,
      trace_ids_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_lean_proof_units_campaign
    ON lean_proof_units(campaign_id, status, verdict)
  `).run();
}

function theoremSlug(theoremName: string): string {
  const leaf = theoremName.split(".").pop() ?? theoremName;
  return leaf.replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 80) || "theorem";
}

function defaultModule(theoremName: string): string {
  const idx = theoremName.lastIndexOf(".");
  return idx > 0 ? theoremName.slice(0, idx) : theoremName;
}

export function unitTraceIds(unit: Pick<LeanProofUnitRecord, "trace_ids_json">): string[] {
  try {
    const parsed = JSON.parse(unit.trace_ids_json) as unknown;
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

export function unitView(unit: LeanProofUnitRecord) {
  return {
    ...unit,
    unit_kind: "lean_proof_unit",
    trace_ids: unitTraceIds(unit),
  };
}

/**
 * The promotion gate: given the theorem's current inventory row (newest
 * first), decide whether the unit may be promoted. Pure + exported for
 * focused tests. The synchronizer owns status writes; this gate only reads.
 */
export function verdictForTheoremRow(
  row: { status: string; lifecycle_status?: string | null; build_manifest_hash?: string | null } | null,
  unit: Pick<LeanProofUnitRecord, "facet" | "module" | "build_manifest_hash">,
): { verdict: LeanProofVerdict; explanation: string } {
  if (!row) {
    return { verdict: "reject", explanation: "theorem is absent from the atlas_theorems inventory — sync has not landed" };
  }
  if (row.lifecycle_status && row.lifecycle_status !== "active") {
    return { verdict: "review", explanation: `inventory row is ${row.lifecycle_status}, not active` };
  }
  if (row.status === "failed") {
    return { verdict: "reject", explanation: "inventory row carries failed proof status" };
  }
  if (row.status === "imported") {
    return { verdict: "review", explanation: "inventory row is imported but not yet verified" };
  }
  if (row.status === "extended" && !isApprovedExtension(unit.facet, unit.module)) {
    return { verdict: "review", explanation: "extended row is outside the registry extension policy for this facet+module" };
  }
  if (
    unit.build_manifest_hash &&
    row.build_manifest_hash &&
    unit.build_manifest_hash !== row.build_manifest_hash
  ) {
    return { verdict: "review", explanation: "build manifest hash drift between the unit and the synced inventory row" };
  }
  return { verdict: "promote", explanation: `inventory row is ${row.status} and active` };
}

async function insertUnitAgendaTask(
  env: Env,
  campaignId: string,
  unit: {
    unit_id: string;
    theorem_name: string;
    module: string;
    facet: string;
    source_commit: string;
    completion_target_task_id: string | null;
  },
): Promise<string> {
  await ensureAgendaSchema(env);
  const taskId = `lean-proof:${unit.unit_id}`;
  await env.LEDGER.prepare(`
    INSERT OR IGNORE INTO intelligence_tasks
    (task_id, title, domain, specialty, horizon, priority, payload, due_at)
    VALUES (?1, ?2, 'lean-formalization', 'verification', 'now', 1, ?3, datetime('now', '+2 days'))
  `).bind(
    taskId,
    `Promote Lean proof ${unit.theorem_name} @ ${unit.source_commit.slice(0, 12)}`,
    JSON.stringify({
      workflow_id: LEAN_PROOF_WORKFLOW_ID,
      campaign_id: campaignId,
      unit_id: unit.unit_id,
      theorem: { name: unit.theorem_name, module: unit.module, facet: unit.facet },
      source_commit: unit.source_commit,
      completion_edge: unit.completion_target_task_id
        ? { kind: "formalizes", to_task_id: unit.completion_target_task_id }
        : null,
    }),
  ).run();
  if (unit.completion_target_task_id) {
    await addTaskEdge(env, taskId, unit.completion_target_task_id, "formalizes");
  }
  return taskId;
}

export async function createLeanProofCampaign(
  env: Env,
  input: CreateLeanProofCampaignInput,
): Promise<{ campaign_id: string; units_created: number; unit_ids: string[] }> {
  if (!input || typeof input !== "object") throw new Error("body must be an object");
  const facet = normalizeFacet(String(input.facet ?? ""));
  if (!isManagedFacet(facet)) {
    throw new Error(`facet '${input.facet}' is not an ATLAS-managed facet (${["causal", "experiment", "manifold", "theorist"].join(", ")})`);
  }
  if (typeof input.proof_revision !== "string" || !input.proof_revision.trim()) {
    throw new Error("proof_revision (source commit) is required");
  }
  if (!Array.isArray(input.units) || input.units.length === 0) {
    throw new Error("units must be a non-empty array of theorem promotions");
  }
  await ensureLeanProofSchema(env);
  const campaignId = (input.campaign_id?.trim() || `lean-proof:${facet}:${input.proof_revision.trim().slice(0, 12)}`).slice(0, 160);
  const proofRepository = input.proof_repository?.trim() || DEFAULT_PROOF_REPOSITORY;
  await env.LEDGER.prepare(`
    INSERT INTO lean_proof_campaigns
    (campaign_id, title, facet, proof_repository, proof_revision, status)
    VALUES (?1, ?2, ?3, ?4, ?5, 'active')
    ON CONFLICT(campaign_id) DO UPDATE SET
      title = excluded.title,
      proof_repository = excluded.proof_repository,
      proof_revision = excluded.proof_revision,
      status = 'active',
      updated_at = datetime('now')
  `).bind(
    campaignId,
    input.title?.trim() || `Lean proof promotion ${facet} @ ${input.proof_revision.trim().slice(0, 12)}`,
    facet,
    proofRepository,
    input.proof_revision.trim(),
  ).run();

  const unitIds: string[] = [];
  for (const [index, raw] of input.units.entries()) {
    if (typeof raw.theorem_name !== "string" || !raw.theorem_name.trim()) {
      throw new Error(`units[${index}].theorem_name is required`);
    }
    const theoremName = raw.theorem_name.trim();
    const module = raw.module?.trim() || defaultModule(theoremName);
    const slug = theoremSlug(theoremName);
    const unitId = `${campaignId}:${slug}`.slice(0, 200);
    const completionTarget = raw.agenda_task_id?.trim() || null;
    await env.LEDGER.prepare(`
      INSERT INTO lean_proof_units
      (unit_id, campaign_id, theorem_name, module, facet, source_commit,
       build_artifact, build_manifest_hash, completion_target_task_id, trace_ids_json)
      VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
      ON CONFLICT(unit_id) DO UPDATE SET
        theorem_name = excluded.theorem_name,
        module = excluded.module,
        source_commit = excluded.source_commit,
        build_artifact = COALESCE(excluded.build_artifact, lean_proof_units.build_artifact),
        build_manifest_hash = COALESCE(excluded.build_manifest_hash, lean_proof_units.build_manifest_hash),
        completion_target_task_id = COALESCE(excluded.completion_target_task_id, lean_proof_units.completion_target_task_id),
        updated_at = datetime('now')
    `).bind(
      unitId,
      campaignId,
      theoremName,
      module,
      facet,
      input.proof_revision.trim(),
      raw.build_artifact ?? null,
      raw.build_manifest_hash ?? null,
      completionTarget,
      JSON.stringify(raw.trace_ids ?? []),
    ).run();
    const agendaTaskId = await insertUnitAgendaTask(env, campaignId, {
      unit_id: unitId,
      theorem_name: theoremName,
      module,
      facet,
      source_commit: input.proof_revision.trim(),
      completion_target_task_id: completionTarget,
    });
    await env.LEDGER.prepare(`
      UPDATE lean_proof_units SET agenda_task_id = ?2, updated_at = datetime('now')
      WHERE unit_id = ?1 AND agenda_task_id IS NULL
    `).bind(unitId, agendaTaskId).run();
    unitIds.push(unitId);
  }
  return { campaign_id: campaignId, units_created: unitIds.length, unit_ids: unitIds };
}

export async function getLeanProofCampaign(
  env: Env,
  campaignId: string,
): Promise<{
  campaign: LeanProofCampaignRecord;
  units: LeanProofUnitRecord[];
  summary: Record<string, number>;
} | null> {
  await ensureLeanProofSchema(env);
  const campaign = await env.LEDGER.prepare(
    `SELECT * FROM lean_proof_campaigns WHERE campaign_id = ?`,
  ).bind(campaignId).first<LeanProofCampaignRecord>();
  if (!campaign) return null;
  const { results } = await env.LEDGER.prepare(
    `SELECT * FROM lean_proof_units WHERE campaign_id = ? ORDER BY created_at ASC, unit_id ASC`,
  ).bind(campaignId).all<LeanProofUnitRecord>();
  const units = results ?? [];
  const summary: Record<string, number> = { units: units.length };
  for (const unit of units) {
    summary[`status_${unit.status}`] = (summary[`status_${unit.status}`] ?? 0) + 1;
    summary[`verdict_${unit.verdict}`] = (summary[`verdict_${unit.verdict}`] ?? 0) + 1;
    summary[`sync_${unit.sync_status}`] = (summary[`sync_${unit.sync_status}`] ?? 0) + 1;
  }
  return { campaign, units, summary };
}

async function loadUnit(env: Env, campaignId: string, unitId: string): Promise<LeanProofUnitRecord | null> {
  await ensureLeanProofSchema(env);
  return env.LEDGER.prepare(
    `SELECT * FROM lean_proof_units WHERE campaign_id = ? AND unit_id = ?`,
  ).bind(campaignId, unitId).first<LeanProofUnitRecord>();
}

/**
 * Record a reported unit result — proof verdict, build artifact/hash, the
 * synchronizer's inventory sync result, and trace IDs — then drive the
 * agenda: promote completes the unit's agenda task and writes the
 * `formalizes` completion edge; reject blocks it.
 */
export async function recordLeanProofUnitResult(
  env: Env,
  input: LeanProofUnitResultInput,
): Promise<{ unit_id: string; status: LeanProofUnitStatus; verdict: LeanProofVerdict; agenda_task_id: string | null; agenda: string }> {
  const unit = await loadUnit(env, input.campaign_id, input.unit_id);
  if (!unit) throw new Error(`Unit '${input.unit_id}' not found in campaign '${input.campaign_id}'`);
  const status: LeanProofUnitStatus = input.status ?? unit.status;
  const verdict: LeanProofVerdict = input.verdict ?? unit.verdict;
  const traceIds = input.trace_ids ?? unitTraceIds(unit);
  await env.LEDGER.prepare(`
    UPDATE lean_proof_units SET
      status = ?2,
      verdict = ?3,
      build_artifact = COALESCE(?4, build_artifact),
      build_manifest_hash = COALESCE(?5, build_manifest_hash),
      sync_status = ?6,
      sync_detail = COALESCE(?7, sync_detail),
      trace_ids_json = ?8,
      updated_at = datetime('now')
    WHERE unit_id = ?1
  `).bind(
    input.unit_id,
    status,
    verdict,
    input.build_artifact ?? null,
    input.build_manifest_hash ?? null,
    input.sync_status ?? unit.sync_status,
    input.sync_detail ?? null,
    JSON.stringify(traceIds),
  ).run();

  let agenda = "unchanged";
  if (unit.agenda_task_id) {
    if (verdict === "promote") {
      await completeAgendaTask(
        env,
        unit.agenda_task_id,
        JSON.stringify({
          verdict,
          theorem: unit.theorem_name,
          module: unit.module,
          source_commit: unit.source_commit,
          sync_status: input.sync_status ?? unit.sync_status,
          trace_ids: traceIds,
        }),
        input.build_artifact ?? unit.build_artifact ?? undefined,
      );
      if (unit.completion_target_task_id) {
        await addTaskEdge(env, unit.agenda_task_id, unit.completion_target_task_id, "formalizes");
      }
      agenda = "completed";
    } else if (verdict === "reject") {
      await updateAgendaTaskStatus(
        env,
        unit.agenda_task_id,
        "blocked",
        JSON.stringify({ verdict, theorem: unit.theorem_name, reason: input.sync_detail ?? "promotion gate rejected" }),
      );
      agenda = "blocked";
    }
  }
  return { unit_id: input.unit_id, status, verdict, agenda_task_id: unit.agenda_task_id, agenda };
}

/**
 * Evaluate a unit against the synced inventory: read the theorem's current
 * `atlas_theorems` row, apply the promotion gate, persist the verdict, and
 * drive the agenda edge. The gate never re-runs the proof — it classifies
 * the synchronizer's recorded status.
 */
export async function evaluateLeanProofUnit(
  env: Env,
  campaignId: string,
  unitId: string,
): Promise<{
  unit_id: string;
  verdict: LeanProofVerdict;
  explanation: string;
  theorem_row: { status: string; lifecycle_status: string | null; build_manifest_hash: string | null } | null;
}> {
  const unit = await loadUnit(env, campaignId, unitId);
  if (!unit) throw new Error(`Unit '${unitId}' not found in campaign '${campaignId}'`);
  const row = await env.LEDGER.prepare(
    `SELECT status, lifecycle_status, build_manifest_hash
       FROM atlas_theorems
      WHERE facet = ? AND theorem_name = ? AND module = ?
      ORDER BY created_at DESC
      LIMIT 1`,
  ).bind(unit.facet, unit.theorem_name, unit.module).first<{
    status: string;
    lifecycle_status: string | null;
    build_manifest_hash: string | null;
  }>();
  const gate = verdictForTheoremRow(row ?? null, unit);
  const status: LeanProofUnitStatus =
    gate.verdict === "promote" ? "completed" : gate.verdict === "reject" ? "failed" : "running";
  await recordLeanProofUnitResult(env, {
    campaign_id: campaignId,
    unit_id: unitId,
    status,
    verdict: gate.verdict,
    sync_detail: gate.explanation,
  });
  return { unit_id: unitId, verdict: gate.verdict, explanation: gate.explanation, theorem_row: row ?? null };
}

/**
 * Transition queued units to `enqueued`. The Lean build itself runs in the
 * lean-spec toolchain lane (`lake build` + tools/atlas_theorem_sync.py);
 * this workflow records the dispatch and awaits results via /result.
 */
export async function enqueueLeanProofUnits(
  env: Env,
  campaignId: string,
  opts: { limit?: number; onlyUnitId?: string } = {},
): Promise<{ dispatched: string[]; considered: number }> {
  const state = await getLeanProofCampaign(env, campaignId);
  if (!state) throw new Error(`Campaign '${campaignId}' not found`);
  const limit = Math.min(Math.max(Math.trunc(opts.limit ?? 10), 1), 100);
  const queued = state.units
    .filter((unit) => unit.status === "queued")
    .filter((unit) => !opts.onlyUnitId || unit.unit_id === opts.onlyUnitId)
    .slice(0, limit);
  const dispatched: string[] = [];
  for (const unit of queued) {
    await env.LEDGER.prepare(
      `UPDATE lean_proof_units SET status = 'enqueued', updated_at = datetime('now') WHERE unit_id = ? AND status = 'queued'`,
    ).bind(unit.unit_id).run();
    dispatched.push(unit.unit_id);
  }
  return { dispatched, considered: queued.length };
}

export const leanProofPromotionAdapter: ResearchWorkflowAdapter = {
  workflow_id: LEAN_PROOF_WORKFLOW_ID,
  label: "Lean proof promotion into the ATLAS theorem inventory",

  describe() {
    return LEAN_PROOF_PROMOTION_DESCRIPTOR;
  },

  async createCampaign(env, bodyText) {
    try {
      const body = JSON.parse(bodyText || "{}") as CreateLeanProofCampaignInput;
      const result = await createLeanProofCampaign(env, body);
      return workflowJson({ workflow_id: LEAN_PROOF_WORKFLOW_ID, ...result }, { status: 202 });
    } catch (e) {
      return workflowError(e instanceof Error ? e.message : String(e), 400);
    }
  },

  async getCampaign(env, campaignId) {
    const state = await getLeanProofCampaign(env, campaignId);
    if (!state) return workflowError(`Campaign '${campaignId}' not found`, 404);
    return workflowJson({
      workflow_id: LEAN_PROOF_WORKFLOW_ID,
      campaign: state.campaign,
      units: state.units.map(unitView),
      summary: state.summary,
    });
  },

  async listUnits(env, campaignId) {
    const state = await getLeanProofCampaign(env, campaignId);
    if (!state) return workflowError(`Campaign '${campaignId}' not found`, 404);
    return workflowJson({
      workflow_id: LEAN_PROOF_WORKFLOW_ID,
      campaign_id: campaignId,
      units: state.units.map(unitView),
      summary: state.summary,
    });
  },

  async nextUnits(env, campaignId, limit) {
    const state = await getLeanProofCampaign(env, campaignId);
    if (!state) return workflowError(`Campaign '${campaignId}' not found`, 404);
    const units = state.units
      .filter((unit) => unit.status === "queued")
      .slice(0, limit)
      .map(unitView);
    return workflowJson({ workflow_id: LEAN_PROOF_WORKFLOW_ID, campaign_id: campaignId, units });
  },

  async enqueueCampaign(env, campaignId, bodyText) {
    try {
      const body = JSON.parse(bodyText || "{}") as { limit?: number };
      const result = await enqueueLeanProofUnits(env, campaignId, { limit: body.limit });
      return workflowJson({ workflow_id: LEAN_PROOF_WORKFLOW_ID, campaign_id: campaignId, ...result });
    } catch (e) {
      return workflowError(e instanceof Error ? e.message : String(e), 400);
    }
  },

  async enqueueUnit(env, campaignId, unitId) {
    try {
      const result = await enqueueLeanProofUnits(env, campaignId, { limit: 1, onlyUnitId: unitId });
      if (result.dispatched.length === 0) return workflowError(`Unit '${unitId}' is not queued`, 409);
      return workflowJson({ workflow_id: LEAN_PROOF_WORKFLOW_ID, campaign_id: campaignId, unit_id: unitId, ...result });
    } catch (e) {
      return workflowError(e instanceof Error ? e.message : String(e), 400);
    }
  },

  async evaluateUnit(env, campaignId, unitId) {
    try {
      const evaluation = await evaluateLeanProofUnit(env, campaignId, unitId);
      return workflowJson({
        workflow_id: LEAN_PROOF_WORKFLOW_ID,
        campaign_id: campaignId,
        evaluator_name: "lean_proof.promotion_gate",
        ...evaluation,
      });
    } catch (e) {
      return workflowError(e instanceof Error ? e.message : String(e), 400);
    }
  },

  inspectCampaign(env, campaignId) {
    return inspectLeanProofCampaign(env, campaignId);
  },

  maintainCampaign(env, campaignId, bodyText) {
    return maintainLeanProofCampaign(env, campaignId, bodyText);
  },

  async recordUnitResult(env, campaignId, unitId, bodyText) {
    try {
      const body = JSON.parse(bodyText || "{}") as Omit<LeanProofUnitResultInput, "campaign_id" | "unit_id">;
      const result = await recordLeanProofUnitResult(env, {
        campaign_id: campaignId,
        unit_id: unitId,
        status: ["queued", "enqueued", "running", "completed", "failed"].includes(String(body.status))
          ? body.status
          : undefined,
        verdict: ["pending", "promote", "review", "reject"].includes(String(body.verdict))
          ? body.verdict
          : undefined,
        build_artifact: typeof body.build_artifact === "string" ? body.build_artifact : undefined,
        build_manifest_hash: typeof body.build_manifest_hash === "string" ? body.build_manifest_hash : undefined,
        sync_status: ["pending", "upserted", "unchanged", "failed"].includes(String(body.sync_status))
          ? body.sync_status
          : undefined,
        sync_detail: typeof body.sync_detail === "string" ? body.sync_detail : undefined,
        trace_ids: Array.isArray(body.trace_ids)
          ? body.trace_ids.filter((v): v is string => typeof v === "string")
          : undefined,
      });
      return workflowJson({ workflow_id: LEAN_PROOF_WORKFLOW_ID, campaign_id: campaignId, ...result });
    } catch (e) {
      return workflowError(e instanceof Error ? e.message : String(e), 400);
    }
  },
};
