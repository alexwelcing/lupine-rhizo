/**
 * Ops surface for the lean-proof-promotion workflow: descriptor, inspection
 * snapshot, and agenda maintenance. Self-contained by design (mirrors the
 * mlipWorkflowOps / mlipDiscoveryWorkflowOps split) — it reads the
 * lean_proof_* tables directly and never imports the adapter module, so the
 * import graph stays one-directional.
 */

import type { Env } from "../types";
import {
  insertWorkflowAgendaTasks,
  summarizeActionKinds,
  workflowActionPath,
  workflowRuntimeContext,
} from "./workflowOps";
import {
  workflowError,
  workflowJson,
  type ResearchWorkflowDescriptor,
  type WorkflowAction,
  type WorkflowOpsSnapshot,
} from "./workflowTypes";

const WORKFLOW_ID = "lean-proof-promotion";

export const LEAN_PROOF_PROMOTION_DESCRIPTOR: ResearchWorkflowDescriptor = {
  workflow_id: WORKFLOW_ID,
  label: "Lean proof promotion into the ATLAS theorem inventory",
  unit_kind: "lean_proof_unit",
  version: 1,
  purpose:
    "Track a proof revision's theorems from the Lean build through atlas_theorems inventory sync and into facet grounding, gated on verified or registry-approved extended status.",
  git: {
    owners: [
      "glim-think/src/research",
      "glim-think/src/agenda.ts",
      "glim-think/src/atlas",
      "tools/atlas_theorem_sync.py",
      "lean-spec",
    ],
    files: [
      "glim-think/src/research/leanProofWorkflow.ts",
      "glim-think/src/research/leanProofWorkflowOps.ts",
      "glim-think/src/research/workflowRegistry.ts",
      "glim-think/src/agenda.ts",
      "glim-think/src/atlas/theorems.ts",
      "glim-think/src/atlas/facetRegistry.ts",
      "tools/atlas_theorem_sync.py",
    ],
    checks: [
      "just think-lint",
      "npm --prefix glim-think run test -- src/research/__tests__/leanProofWorkflow.test.ts",
      "lake build (lean-spec)",
      "python tools/test_atlas_theorem_sync.py",
    ],
  },
  cloudflare: {
    routes: [
      "GET /research/workflows",
      "GET /research/workflows/lean-proof-promotion",
      "POST /research/workflows/lean-proof-promotion/campaigns",
      "GET /research/workflows/lean-proof-promotion/campaigns/:campaign_id",
      "GET /research/workflows/lean-proof-promotion/campaigns/:campaign_id/units",
      "GET /research/workflows/lean-proof-promotion/campaigns/:campaign_id/units/next",
      "GET /research/workflows/lean-proof-promotion/campaigns/:campaign_id/ops",
      "POST /research/workflows/lean-proof-promotion/campaigns/:campaign_id/maintain",
      "POST /research/workflows/lean-proof-promotion/campaigns/:campaign_id/enqueue",
      "POST /research/workflows/lean-proof-promotion/campaigns/:campaign_id/units/:unit_id/enqueue",
      "POST /research/workflows/lean-proof-promotion/campaigns/:campaign_id/units/:unit_id/evaluate",
      "POST /research/workflows/lean-proof-promotion/campaigns/:campaign_id/units/:unit_id/result",
    ],
    bindings: ["LEDGER", "CONFIG"],
    queue_consumers: [],
  },
  phoenix: {
    lifecycle_spans: ["hypothesis.verdict"],
    evaluators: ["lean_proof.promotion_gate"],
    annotations: ["lean_proof.promotion_verdict"],
  },
  extension_contract: {
    adapter_methods: [
      "describe",
      "createCampaign",
      "getCampaign",
      "listUnits",
      "nextUnits",
      "enqueueCampaign",
      "enqueueUnit",
      "evaluateUnit",
      "inspectCampaign",
      "maintainCampaign",
      "recordUnitResult",
    ],
    evidence_required: [
      "unit_id",
      "theorem_name + module",
      "owning facet",
      "source_commit (proof revision)",
      "build artifact / build_manifest_hash",
      "proof verdict",
      "agenda task id + formalizes completion edge",
      "inventory sync result",
      "trace_ids",
    ],
  },
};

interface LeanProofOpsUnit {
  unit_id: string;
  theorem_name: string;
  module: string;
  facet: string;
  status: string;
  verdict: string;
  sync_status: string;
  build_manifest_hash: string | null;
  agenda_task_id: string | null;
}

async function loadOpsState(
  env: Env,
  campaignId: string,
): Promise<{ campaign: Record<string, unknown>; units: LeanProofOpsUnit[] } | null> {
  try {
    const campaign = await env.LEDGER.prepare(
      `SELECT * FROM lean_proof_campaigns WHERE campaign_id = ?`,
    ).bind(campaignId).first<Record<string, unknown>>();
    if (!campaign) return null;
    const { results } = await env.LEDGER.prepare(
      `SELECT unit_id, theorem_name, module, facet, status, verdict, sync_status, build_manifest_hash, agenda_task_id
         FROM lean_proof_units WHERE campaign_id = ? ORDER BY created_at ASC, unit_id ASC`,
    ).bind(campaignId).all<LeanProofOpsUnit>();
    return { campaign, units: results ?? [] };
  } catch {
    return null;
  }
}

export async function inspectLeanProofCampaign(
  env: Env,
  campaignId: string,
): Promise<WorkflowOpsSnapshot | Response> {
  const state = await loadOpsState(env, campaignId);
  if (!state) return workflowError(`Campaign '${campaignId}' not found`, 404);
  const { units } = state;

  const pendingVerdict = units.filter((unit) => unit.verdict === "pending");
  const rejected = units.filter((unit) => unit.verdict === "reject");
  const missingBuildHash = units.filter((unit) => !unit.build_manifest_hash);
  const failedSync = units.filter((unit) => unit.sync_status === "failed");
  const queued = units.filter((unit) => unit.status === "queued");

  const actions: WorkflowAction[] = [];

  for (const unit of pendingVerdict.slice(0, 10)) {
    actions.push({
      action_id: `evaluate:${unit.unit_id}`,
      kind: "evaluate_unit",
      label: `Evaluate promotion gate for ${unit.theorem_name}`,
      reason: "The unit has no durable verdict yet; classify the synced inventory row (verified / approved-extended promotes, imported reviews, failed or missing rejects).",
      priority: 1,
      unit_id: unit.unit_id,
      route: {
        method: "POST",
        path: workflowActionPath(WORKFLOW_ID, campaignId, unit.unit_id, "evaluate"),
      },
      can_auto_execute: true,
      surfaces: ["cloudflare", "ledger", "agenda"],
    });
  }

  for (const unit of rejected.slice(0, 5)) {
    actions.push({
      action_id: `inspect-failure:${unit.unit_id}`,
      kind: "inspect_failure",
      label: `Inspect rejected proof promotion ${unit.theorem_name}`,
      reason: "A rejected unit blocks facet grounding for this theorem and should be classified before more proof capacity is spent.",
      priority: 1,
      unit_id: unit.unit_id,
      can_auto_execute: false,
      surfaces: ["git", "cloudflare", "ledger", "agenda"],
    });
  }

  for (const unit of missingBuildHash.slice(0, 5)) {
    actions.push({
      action_id: `repair-input:${unit.unit_id}`,
      kind: "repair_input",
      label: `Attach build manifest hash for ${unit.theorem_name}`,
      reason: "The unit cannot pass the promotion gate until the lake build artifact hash is recorded.",
      priority: 2,
      unit_id: unit.unit_id,
      route: {
        method: "POST",
        path: workflowActionPath(WORKFLOW_ID, campaignId, unit.unit_id, "result"),
      },
      can_auto_execute: false,
      surfaces: ["git", "ledger", "agenda"],
    });
  }

  for (const unit of queued.slice(0, 5)) {
    actions.push({
      action_id: `enqueue:${unit.unit_id}`,
      kind: "enqueue_unit",
      label: `Dispatch lean build for ${unit.theorem_name}`,
      reason: "The unit is queued; the lean-spec toolchain lane runs lake build and the synchronizer reports back via /result.",
      priority: 2,
      unit_id: unit.unit_id,
      route: {
        method: "POST",
        path: workflowActionPath(WORKFLOW_ID, campaignId, unit.unit_id, "enqueue"),
      },
      can_auto_execute: true,
      surfaces: ["cloudflare", "ledger", "agenda"],
    });
  }

  if (actions.length === 0) {
    actions.push({
      action_id: "summarize-campaign",
      kind: "summarize_campaign",
      label: "Summarize lean proof promotion state",
      reason: "No pending verdicts, rejections, or missing build inputs remain.",
      priority: 3,
      can_auto_execute: true,
      surfaces: ["phoenix", "ledger", "agenda"],
    });
  }

  const allPromoted = units.length > 0 && units.every((unit) => unit.verdict === "promote");
  const snapshotState: WorkflowOpsSnapshot["state"] =
    rejected.length > 0 || failedSync.length > 0
      ? "failed"
      : missingBuildHash.length > 0
        ? "needs_input"
        : allPromoted
          ? "complete"
          : pendingVerdict.length > 0 || queued.length > 0
            ? "active"
            : "ready";

  const counters: Record<string, number> = {
    units_total: units.length,
    units_pending_verdict: pendingVerdict.length,
    units_promoted: units.filter((unit) => unit.verdict === "promote").length,
    units_review: units.filter((unit) => unit.verdict === "review").length,
    units_rejected: rejected.length,
    units_missing_build_hash: missingBuildHash.length,
    units_sync_failed: failedSync.length,
    units_queued: queued.length,
    ...Object.fromEntries(
      Object.entries(summarizeActionKinds(actions)).map(([key, value]) => [`actions_${key}`, value]),
    ),
  };

  return {
    workflow_id: WORKFLOW_ID,
    campaign_id: campaignId,
    generated_at: new Date().toISOString(),
    state: snapshotState,
    descriptor: LEAN_PROOF_PROMOTION_DESCRIPTOR,
    counters,
    ...workflowRuntimeContext(env, LEAN_PROOF_PROMOTION_DESCRIPTOR),
    next_actions: actions.sort((a, b) => a.priority - b.priority || a.action_id.localeCompare(b.action_id)),
  };
}

export async function maintainLeanProofCampaign(
  env: Env,
  campaignId: string,
  bodyText: string,
): Promise<Response> {
  const body = JSON.parse(bodyText || "{}") as { mode?: "agenda"; limit?: number };
  const mode = body.mode ?? "agenda";
  if (mode !== "agenda") return workflowError("Only agenda maintenance is implemented for this workflow", 400);
  const snapshot = await inspectLeanProofCampaign(env, campaignId);
  if (snapshot instanceof Response) return snapshot;
  const agenda = await insertWorkflowAgendaTasks(env, snapshot, body.limit ?? 10);
  return workflowJson({
    workflow_id: WORKFLOW_ID,
    campaign_id: campaignId,
    mode,
    agenda,
    state: snapshot.state,
    counters: snapshot.counters,
    next_actions: snapshot.next_actions.slice(0, Math.max(1, Math.trunc(body.limit ?? 10))),
  });
}
