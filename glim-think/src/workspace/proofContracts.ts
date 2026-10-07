import { z } from "zod";

export const PROOF_MODEL = "claude-opus-5-5";
export const PROOF_BODY_BYTES = 128 * 1024;
export const PROOF_RESULT_BYTES = 2 * 1024 * 1024;
export const PROOF_CANDIDATE_BYTES = 56000;
export const PROOF_STALE_MS = 15 * 60 * 1000;
export const proofId = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/);
export const fingerprint = z.string().regex(/^[a-f0-9]{64}$/);
const text = (limit: number) => z.string().trim().min(1).max(limit);
const reviewedText = (limit: number) => text(limit).refine(value =>
  !/(?:\/Users\/|\/home\/|[A-Z]:\\Users\\|BEGIN .*PRIVATE KEY|cfast_[A-Za-z0-9]+)/i.test(value), "Exclude private paths and credentials");

/** Native cloud jobs accept newly reviewed briefs, never private archive imports. */
export const proofRequestSchema = z.object({
  id: proofId, agendaTaskId: proofId, question: reviewedText(4000),
  task: reviewedText(12000), context: reviewedText(80000),
  parentJobId: proofId.optional(), justification: reviewedText(2000),
  maxOutputTokens: z.number().int().min(1024).max(128000),
  reviewedForPrivateWorkspace: z.literal(true), apiUseAuthorized: z.literal(true),
}).strict().superRefine((v, ctx) => {
  if (v.parentJobId === v.id) ctx.addIssue({ code: "custom", message: "A job cannot be its own parent" });
});
export type ProofRequest = z.infer<typeof proofRequestSchema>;
export const recoverProofSchema = z.object({ batchId: z.string().regex(/^msgbatch_[A-Za-z0-9]+$/), reviewedProviderIdentity: z.literal(true) }).strict();
export const proofCandidateSchema = z.object({
  schema_version: z.literal(1), job_id: proofId, artifact_kind: z.literal("lean_source_candidate"),
  lean_source: text(32000), proof_scope: text(3000),
  assumptions: z.array(text(600)).max(12), remaining_obligations: z.array(text(800)).max(12),
  verification_notes: text(2000), compilation: z.literal("not_run"),
}).strict();
export type ProofCandidate = z.infer<typeof proofCandidateSchema>;
export const proofStatuses = ["queued", "submitting", "processing", "cancel_requested", "completion_unknown", "candidate_ready", "failed", "cancelled", "expired", "invalid_result"] as const;
export type ProofStatus = typeof proofStatuses[number];
const stamp = z.iso.datetime({ offset: true });
export const batchSchema = z.object({
  id: z.string().regex(/^msgbatch_[A-Za-z0-9]+$/), type: z.literal("message_batch"),
  processing_status: z.enum(["in_progress", "canceling", "ended"]),
  request_counts: z.object({ processing: z.number().int().min(0), succeeded: z.number().int().min(0), errored: z.number().int().min(0), canceled: z.number().int().min(0), expired: z.number().int().min(0) }).strict(),
  created_at: stamp, ended_at: stamp.nullable(), expires_at: stamp,
  cancel_initiated_at: stamp.nullable(), results_url: z.string().nullable(),
}).strip().superRefine((v, ctx) => {
  if (Object.values(v.request_counts).reduce((a,b) => a+b,0) !== 1) ctx.addIssue({ code: "custom", message: "Expected exactly one provider request" });
  if (v.processing_status === "ended" && (!v.ended_at || v.request_counts.processing !== 0)) ctx.addIssue({ code: "custom", message: "Invalid terminal batch" });
});
export type Batch = z.infer<typeof batchSchema>;
export const proofJobSchema = z.object({
  id: proofId, request: proofRequestSchema, status: z.enum(proofStatuses), displayStatus: z.enum(proofStatuses),
  createdAt: stamp, updatedAt: stamp, observedAt: stamp.nullable(), active: z.boolean(),
  batchId: z.string().nullable(), provider: batchSchema.nullable(),
  candidate: proofCandidateSchema.nullable(), candidateSha256: fingerprint.nullable(), failureCode: z.string().nullable(),
});
export type ProofJob = z.infer<typeof proofJobSchema>;
export const proofFeedSchema = z.object({
  jobs: z.array(proofJobSchema).max(20), truncated: z.boolean(), retrievedAt: stamp,
  configuration: z.object({ enabled: z.boolean(), credentialConfigured: z.boolean(), maxOutputTokens: z.number().int().nullable(), ready: z.boolean() }),
});
export type ProofFeed = z.infer<typeof proofFeedSchema>;
export function displayedProofStatus(status: ProofStatus, observedAt: string | null, updatedAt: string, now = Date.now()): ProofStatus {
  return ["processing", "submitting"].includes(status) && now - Date.parse(observedAt ?? updatedAt) > PROOF_STALE_MS ? "completion_unknown" : status;
}
export async function proofHash(text: string) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text))), byte => byte.toString(16).padStart(2,"0")).join("");
}
