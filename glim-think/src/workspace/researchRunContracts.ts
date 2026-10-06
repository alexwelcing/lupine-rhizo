import { z } from "zod";

export const RESEARCH_RUN_MAX_BYTES = 196_608;
export const RESEARCH_PACKET_MAX_BYTES = 49_152;
const text = (max = 6000) => z.string().min(1).max(max).refine(value => value.trim().length > 0);
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const timestamp = z.string().datetime({ offset: true });
const strings = (min = 1, max = 12) => z.array(text()).min(min).max(max);
const source = z.strictObject({ id: text(80), title: text(600), url: text(2000),
  publication_kind: z.enum(["peer_reviewed", "preprint", "primary_research_report"]),
  year: z.number().int().min(1900).max(2100), supports: text(), limitations: text() });
const experiment = z.strictObject({ design: text(), baseline: text(), measurement: text(), decision_rule: text(),
  estimated_compute_minutes: z.number().finite().min(0).max(1440), execution: z.literal("not_started") });
const proposal = z.strictObject({ id: text(80), hypothesis: text(), mechanism: text(),
  closest_prior_art: z.array(z.strictObject({ source_ids: z.array(text(80)).min(1).max(12), overlap: text(), difference: text() })).min(1).max(12),
  possible_novelty: text(), novelty_status: z.literal("unverified"), competing_explanations: strings(),
  falsifier: text(), cheap_discriminating_experiment: experiment, priority_reason: text() });
export const discoveryPacketSchema = z.strictObject({ role: z.literal("proposer"), research_question: text(), synthesis: text(),
  sources: z.array(source).min(2).max(8), proposals: z.array(proposal).min(1).max(3),
  independent_critique: z.strictObject({ status: z.literal("required"), questions_for_critic: strings() }),
  decision: z.strictObject({ status: z.literal("awaiting_independent_critique"), rationale: text() }) });
export const critiquePacketSchema = z.strictObject({ role: z.literal("critic"), reviewed_job_id: id, reviewed_packet_sha256: hash,
  verdict: z.enum(["advance_to_preregistration", "revise", "reject"]),
  source_checks: z.array(z.strictObject({ source_id: text(80), status: z.enum(["provided_only", "verified", "contradicted", "unverified"]), reason: text() })).min(1).max(12),
  critiques: z.array(z.strictObject({ proposal_id: text(80), prior_art_overlap: text(), confounds: strings(),
    discriminating_experiment_assessment: text(), decision: z.enum(["advance_to_preregistration", "revise", "reject"]), required_changes: strings(0) })).min(1).max(3),
  strongest_alternative: text(), next_step: text(), execution: z.literal("not_started") });
export const decisionPacketSchema = z.strictObject({ role: z.literal("adjudicator"), reviewed_job_id: id, reviewed_packet_sha256: hash,
  critique_job_id: id, critique_packet_sha256: hash, selected_proposal_id: text(80),
  recommendation: z.enum(["investigate", "revise", "reject", "insufficient_evidence"]), reason: text(),
  response_to_critique: z.array(z.strictObject({ critique_point: text(), response: text(), change: text() })).min(1).max(12),
  revised_hypothesis: text(), closest_prior_art_boundary: text(), novelty_status: z.literal("unverified"),
  competing_explanation: text(), falsifier: text(), source_ids: z.array(text(80)).min(1).max(12),
  cheap_discriminating_experiment: experiment, publication: z.literal("held") });
export const scientificPacketSchema = z.discriminatedUnion("role", [discoveryPacketSchema, critiquePacketSchema, decisionPacketSchema]);
export type ScientificPacket = z.infer<typeof scientificPacketSchema>;
export const terminalStatusSchema = z.enum(["completed", "blocked", "failed", "timeout", "output_limit", "interrupted", "invalid_result", "policy_violation", "launch_unknown", "launch_failed", "transport_unknown", "status_unknown", "poll_timeout"]);
export const researchReceiptSchema = z.strictObject({ jobId: id, jobSha256: hash, status: terminalStatusSchema,
  completionUnknown: z.boolean(), automaticRetry: z.literal(false), modelExecutionStarted: z.boolean(),
  sessionId: text(200).nullable(), model: text(600).nullable(), startedAt: timestamp.nullable(), finishedAt: timestamp.nullable(),
  resultSha256: hash.nullable(), receiptOrigin: z.enum(["local_cli", "controller_transport"]) });
const stageFields = { stage: z.enum(["discovery", "independent_critique", "pi_decision"]), jobId: id.nullable(),
  provider: z.enum(["codex", "claude"]), role: z.enum(["proposer", "critic", "adjudicator"]), machineId: id.nullable(),
  status: z.union([z.enum(["not_started", "pending"]), terminalStatusSchema]), receipt: researchReceiptSchema.nullable() };
const runFields = { schemaVersion: z.literal(1), id: id, question: text(), status: z.enum(["running", "completed", "stopped"]),
  startedAt: timestamp, finishedAt: timestamp.nullable(), capturedAt: timestamp, error: text(1000).nullable(),
  experiment: z.literal("not_started"), publication: z.literal("held") };
export const researchRunImportSchema = z.strictObject({ ...runFields,
  stages: z.array(z.strictObject({ ...stageFields, packetJson: z.string().max(RESEARCH_PACKET_MAX_BYTES).nullable() })).length(3) });
export const researchRunSchema = z.strictObject({ ...runFields,
  stages: z.array(z.strictObject({ ...stageFields, result: scientificPacketSchema.nullable() })).length(3) });
export type ResearchRunImport = z.infer<typeof researchRunImportSchema>;
export type ResearchRun = z.infer<typeof researchRunSchema>;
export type ResearchRunStage = ResearchRun["stages"][number];
export interface ResearchRunsFeed { runs: ResearchRun[]; truncated: boolean }

/** Validate original packet bytes before projecting them into safe display data. */
export async function decodeResearchRun(input: unknown): Promise<ResearchRun> {
  const saved = researchRunImportSchema.parse(input);
  const stages = await Promise.all(saved.stages.map(async stage => {
    const { packetJson, ...metadata } = stage;
    let result: ScientificPacket | null = null;
    if (packetJson !== null) {
      if (new TextEncoder().encode(packetJson).length > RESEARCH_PACKET_MAX_BYTES) throw new Error("Packet is too large");
      result = scientificPacketSchema.parse(JSON.parse(packetJson));
      if (await sha256(packetJson) !== stage.receipt?.resultSha256) throw new Error("Result fingerprint mismatch");
    }
    return { ...metadata, result };
  }));
  const run = researchRunSchema.parse({ ...saved, stages });
  const expected = [["discovery", "codex", "proposer"], ["independent_critique", "claude", "critic"], ["pi_decision", "codex", "adjudicator"]];
  const assigned = new Set<string>();
  for (const [index, stage] of stages.entries()) {
    if ([stage.stage, stage.provider, stage.role].some((value, field) => value !== expected[index][field])) throw new Error("Wrong stage identity or order");
    if (stage.jobId) { if (assigned.has(stage.jobId)) throw new Error("Duplicate job identity"); assigned.add(stage.jobId); }
    if (stage.status === "not_started") {
      if (stage.jobId || stage.receipt || stage.result || stage.machineId) throw new Error("Unstarted stage has execution data");
      continue;
    }
    if (!stage.jobId || !stage.machineId) throw new Error("Missing job identity");
    if (index > 0 && stages[index - 1].status !== "completed") throw new Error("Stage started before its prerequisite completed");
    if (stage.status === "pending") {
      if (stage.receipt || stage.result) throw new Error("Pending stage has terminal data");
      continue;
    }
    const receipt = stage.receipt;
    if (!receipt || receipt.jobId !== stage.jobId || receipt.status !== stage.status) throw new Error("Mismatched receipt");
    if (stage.status === "completed") {
      if (!stage.result || stage.result.role !== stage.role || receipt.completionUnknown || !receipt.modelExecutionStarted || !receipt.sessionId || !receipt.resultSha256 || receipt.receiptOrigin !== "local_cli") throw new Error("Unverified completion");
    } else if (stage.result || receipt.resultSha256) throw new Error("Failed stage contains a result");
  }
  if (run.status === "completed" && stages.some(s => s.status !== "completed")) throw new Error("Incomplete cycle claimed completion");
  if ((run.status === "running") !== (run.finishedAt === null)) throw new Error("Inconsistent cycle finish time");
  if (Date.parse(run.capturedAt) < Date.parse(run.startedAt) || (run.finishedAt && (Date.parse(run.finishedAt) < Date.parse(run.startedAt) || Date.parse(run.capturedAt) < Date.parse(run.finishedAt)))) throw new Error("Inconsistent cycle dates");
  const discovery = stages[0].result;
  if (discovery?.role === "proposer") {
    const sourceIds = new Set(discovery.sources.map(s => s.id));
    const proposalIds = new Set(discovery.proposals.map(p => p.id));
    if (sourceIds.size !== discovery.sources.length || proposalIds.size !== discovery.proposals.length) throw new Error("Duplicate source or proposal");
    const external = new Set<string>();
    for (const s of discovery.sources) {
      if (s.url === `urn:lupine:${stages[0].jobId}:context` && s.publication_kind === "primary_research_report") continue;
      const url = new URL(s.url);
      if (url.protocol !== "https:" || !url.hostname || url.username || url.password) throw new Error("Unsafe source URL");
      external.add(s.url);
    }
    if (external.size < 2) throw new Error("Two external sources are required");
    for (const p of discovery.proposals) for (const prior of p.closest_prior_art) for (const sourceId of prior.source_ids) if (!sourceIds.has(sourceId)) throw new Error("Unresolved source");
    const critique = stages[1].result;
    if (critique?.role === "critic") {
      if (critique.reviewed_job_id !== stages[0].jobId || critique.reviewed_packet_sha256 !== stages[0].receipt?.resultSha256) throw new Error("Critique references a different discovery");
      const reviewed = new Set(critique.critiques.map(c => c.proposal_id));
      if (reviewed.size !== critique.critiques.length || reviewed.size !== proposalIds.size || [...reviewed].some(p => !proposalIds.has(p))) throw new Error("Incomplete proposal critique");
      if (critique.source_checks.some(s => !sourceIds.has(s.source_id) || s.status === "verified")) throw new Error("Tool-free critic cannot verify sources");
    }
    const decision = stages[2].result;
    if (decision?.role === "adjudicator") {
      if (decision.reviewed_job_id !== stages[0].jobId || decision.reviewed_packet_sha256 !== stages[0].receipt?.resultSha256 || decision.critique_job_id !== stages[1].jobId || decision.critique_packet_sha256 !== stages[1].receipt?.resultSha256) throw new Error("Decision references different packets");
      if (!proposalIds.has(decision.selected_proposal_id) || decision.source_ids.some(s => !sourceIds.has(s))) throw new Error("Decision references unknown evidence");
    }
  }
  return run;
}

export async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}
