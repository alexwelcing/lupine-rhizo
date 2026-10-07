import type { Env } from "../types";
import { checkAccess } from "../middleware/access";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";
import { batchSchema, displayedProofStatus, PROOF_BODY_BYTES, proofCandidateSchema, proofHash, proofId, proofRequestSchema, recoverProofSchema, type ProofJob, type ProofRequest, type ProofStatus } from "./proofContracts";
import { boundedText, inspectProofConnection, cancelBatch, collectCandidate, proofConfiguration, ProviderError, readBatch, submitBatch, type ProofApiEnv } from "./proofProvider";

export type ProofEnv = Pick<Env, "LEDGER" | "ADMIN_EMAIL" | "CF_ACCESS_TEAM_DOMAIN" | "CF_ACCESS_AUD" | "PROOF_ACCESS_TEAM_DOMAIN" | "PROOF_ACCESS_AUD" | "PROOF_ADMIN_EMAIL"> & ProofApiEnv;
interface Row {
  id: string; agenda_id: string; request_json: string; request_sha256: string; status: ProofStatus;
  batch_id: string | null; provider_json: string | null; candidate_json: string | null; candidate_sha256: string | null;
  receipt_json: string | null; failure_code: string | null; created_at: string; updated_at: string;
  observed_at: string | null; cancel_sent: number; active: number; poll_token: string | null; poll_until: string | null;
}
const now = () => new Date().toISOString();
const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { ...WORKSPACE_PRIVATE_HEADERS, "X-Robots-Tag": "noindex, nofollow" } });
const getRow = (env: ProofEnv, id: string) => env.LEDGER.prepare("SELECT * FROM proof_jobs WHERE id=?").bind(id).first<Row>();
async function view(row: Row): Promise<ProofJob> {
  if (await proofHash(row.request_json) !== row.request_sha256) throw new Error("Stored request fingerprint mismatch");
  const request = proofRequestSchema.parse(JSON.parse(row.request_json));
  if (request.id !== row.id || request.agendaTaskId !== row.agenda_id) throw new Error("Stored request identity mismatch");
  const candidate = row.candidate_json ? proofCandidateSchema.parse(JSON.parse(row.candidate_json)) : null;
  if (candidate && (candidate.job_id !== row.id || row.status !== "candidate_ready" || await proofHash(row.candidate_json!) !== row.candidate_sha256)) throw new Error("Stored candidate fingerprint mismatch");
  if (row.status === "candidate_ready" && !candidate) throw new Error("Missing candidate");
  const provider = row.provider_json ? batchSchema.parse(JSON.parse(row.provider_json)) : null;
  if (provider && provider.id !== row.batch_id) throw new Error("Stored batch identity mismatch");
  return { id: row.id, request, status: row.status, displayStatus: displayedProofStatus(row.status,row.observed_at,row.updated_at),
    createdAt: row.created_at, updatedAt: row.updated_at, observedAt: row.observed_at, active: Boolean(row.active),
    batchId: row.batch_id, provider, candidate, candidateSha256: row.candidate_sha256, failureCode: row.failure_code };
}
export async function listProofJobs(env: ProofEnv) {
  const rows = await env.LEDGER.prepare("SELECT * FROM proof_jobs ORDER BY created_at DESC,id DESC LIMIT 21").all<Row>();
  if (!rows.success) throw new Error("Proof storage unavailable");
  return { jobs: await Promise.all(rows.results.slice(0,20).map(view)), truncated: rows.results.length > 20, retrievedAt: now(), configuration: proofConfiguration(env) };
}
export async function enqueueProof(env: ProofEnv, raw: unknown) {
  const request = proofRequestSchema.parse(raw); const data = JSON.stringify(request); const hash = await proofHash(data);
  if (new TextEncoder().encode(data).length > PROOF_BODY_BYTES) throw new ProviderError("brief_too_large",true);
  const prior = await getRow(env,request.id);
  if (prior) {
    if (prior.request_sha256 !== hash) throw new ProviderError("job_id_conflict",true);
    return { job: await view(prior), duplicate: true };
  }
  const config = proofConfiguration(env);
  if (!config.ready) throw new ProviderError("native_proof_api_not_enabled",true);
  if (request.maxOutputTokens > config.maxOutputTokens!) throw new ProviderError("output_budget_exceeds_configuration",true);
  if (request.parentJobId) {
    const parent = await getRow(env,request.parentJobId);
    if (!parent || parent.active || parent.agenda_id !== request.agendaTaskId) throw new ProviderError("parent_must_be_terminal_in_same_agenda",true);
  }
  const at = now();
  try {
    await env.LEDGER.prepare("INSERT INTO proof_jobs(id,agenda_id,request_json,request_sha256,status,created_at,updated_at) VALUES (?,?,?,?,'queued',?,?)")
      .bind(request.id,request.agendaTaskId,data,hash,at,at).run();
  } catch {
    const existing = await getRow(env,request.id);
    if (existing?.request_sha256 === hash) return { job: await view(existing), duplicate: true };
    throw new ProviderError("agenda_or_job_already_active",true);
  }
  return { job: await view((await getRow(env,request.id))!), duplicate: false };
}
export async function requestProofCancellation(env: ProofEnv, id: string) {
  const existing = await getRow(env,id);
  if (existing?.status === "completion_unknown" && !existing.batch_id) throw new ProviderError("provider_identity_required_for_cancellation",true);
  const at = now();
  await env.LEDGER.prepare(`UPDATE proof_jobs SET status=CASE WHEN status='queued' THEN 'cancelled' ELSE 'cancel_requested' END,
    active=CASE WHEN status='queued' THEN 0 ELSE active END,updated_at=? WHERE id=? AND active=1`).bind(at,id).run();
  const row = await getRow(env,id); return row ? view(row) : null;
}
/** Recover only a finished provider batch whose result independently matches this job.
 * This path performs GETs only, never a new submission or a cancellation retry. */
export async function recoverProofJob(env: ProofEnv, id: string, raw: unknown) {
  const input = recoverProofSchema.parse(raw);
  const row = await getRow(env,id);
  if (!row) throw new ProviderError("job_not_found",true);
  if (row.batch_id === input.batchId && !row.active) return view(row);
  if (row.status !== "completion_unknown" || row.batch_id || !row.active) throw new ProviderError("job_not_recoverable",true);
  await view(row); // Validate stored identity before considering external evidence.
  const batch = await readBatch(env,input.batchId);
  if (batch.processing_status !== "ended") throw new ProviderError("recovery_waiting_for_provider_result",true);
  const result = await collectCandidate(env,input.batchId,id);
  await env.LEDGER.prepare(`UPDATE proof_jobs SET batch_id=?,provider_json=?,status=?,active=0,candidate_json=?,candidate_sha256=?,receipt_json=?,failure_code=?,observed_at=?,updated_at=?
    WHERE id=? AND status='completion_unknown' AND batch_id IS NULL AND active=1 AND (poll_until IS NULL OR poll_until < ?)`)
    .bind(batch.id,JSON.stringify(batch),result.status,result.candidate ? JSON.stringify(result.candidate) : null,result.hash,JSON.stringify(result.receipt),result.status === "candidate_ready" ? null : result.status,now(),now(),id,now()).run();
  const saved = (await getRow(env,id))!;
  if (saved.batch_id !== batch.id) throw new ProviderError("recovery_state_conflict",true);
  return view(saved);
}
function failureCode(error: unknown) { return error instanceof ProviderError ? error.code : "provider_or_storage_response_invalid"; }

/** A scheduled visit performs short network operations. It never holds inference open. */
export async function advanceProofJob(env: ProofEnv, id: string): Promise<void> {
  const token = crypto.randomUUID(); const at = now();
  const lease = new Date(Date.now()+120000).toISOString();
  const row = await env.LEDGER.prepare(`UPDATE proof_jobs SET poll_token=?,poll_until=? WHERE id=? AND active=1 AND (poll_until IS NULL OR poll_until < ?) RETURNING *`)
    .bind(token,lease,id,at).first<Row>();
  if (!row) return;
  const update = async (sql: string, ...values: unknown[]) => env.LEDGER.prepare(`UPDATE proof_jobs SET ${sql} WHERE id=? AND poll_token=? AND active=1`).bind(...values,id,token).run();
  try {
    if (!row.batch_id) {
      if (row.status !== "queued") {
        await update("status='completion_unknown',failure_code='submission_unconfirmed',updated_at=?",now()); return;
      }
      const config = proofConfiguration(env); if (!config.ready) return;
      const request: ProofRequest = (await view(row)).request;
      if (request.maxOutputTokens > config.maxOutputTokens!) {
        await update("status='failed',active=0,failure_code='configured_budget_reduced',updated_at=?",now()); return;
      }
      // Persist intent BEFORE POST. A crash/lost response can never resubmit it.
      const reserved = await env.LEDGER.prepare("UPDATE proof_jobs SET status='submitting',updated_at=? WHERE id=? AND poll_token=? AND status='queued' AND active=1 RETURNING id").bind(now(),id,token).first();
      if (!reserved) return;
      try {
        const batch = await submitBatch(env,request);
        await update("status=CASE WHEN status='cancel_requested' THEN status ELSE 'processing' END,batch_id=?,provider_json=?,observed_at=?,updated_at=?,failure_code=NULL",batch.id,JSON.stringify(batch),now(),now());
      } catch (error) {
        const definitive = error instanceof ProviderError && error.definitive;
        await update("status=?,active=?,failure_code=?,updated_at=?",definitive ? "failed" : "completion_unknown",definitive ? 0 : 1,failureCode(error),now());
      }
      return;
    }
    // Read-only polls are safe to repeat. They never create another model request.
    if (row.status === "cancel_requested" && row.cancel_sent === 0) {
      const reserved = await env.LEDGER.prepare("UPDATE proof_jobs SET cancel_sent=1 WHERE id=? AND poll_token=? AND cancel_sent=0 AND active=1 RETURNING id").bind(id,token).first();
      if (reserved) { try { await cancelBatch(env,row.batch_id); } catch (error) { await update("failure_code=?",failureCode(error)); } }
    }
    const batch = await readBatch(env,row.batch_id);
    await update("status=CASE WHEN status='cancel_requested' OR ?='canceling' THEN 'cancel_requested' ELSE 'processing' END,provider_json=?,observed_at=?,updated_at=?,failure_code=NULL",batch.processing_status,JSON.stringify(batch),now(),now());
    if (batch.processing_status !== "ended") return;
    try {
      const result = await collectCandidate(env,row.batch_id,id);
      await update("status=?,active=0,candidate_json=?,candidate_sha256=?,receipt_json=?,failure_code=?,updated_at=?",result.status,result.candidate ? JSON.stringify(result.candidate) : null,result.hash,JSON.stringify(result.receipt),result.status === "candidate_ready" ? null : result.status,now());
    } catch (error) {
      // A transport failure while retrieving results is recoverable by GET only.
      if (error instanceof TypeError || (error instanceof Error && ["TimeoutError","AbortError"].includes(error.name)) || (error instanceof ProviderError && /^provider_http_(429|5\d\d)$/.test(error.code))) {
        await update("failure_code=?",failureCode(error));
      } else await update("status='invalid_result',active=0,failure_code=?,updated_at=?",failureCode(error),now());
    }
  } catch (error) {
    await update("failure_code=?,updated_at=?",failureCode(error),now());
  } finally {
    await env.LEDGER.prepare("UPDATE proof_jobs SET poll_token=NULL,poll_until=NULL WHERE id=? AND poll_token=?").bind(id,token).run();
  }
}
export async function tickProofJobs(env: ProofEnv) {
  const rows = await env.LEDGER.prepare("SELECT id FROM proof_jobs WHERE active=1 AND NOT (status='completion_unknown' AND batch_id IS NULL) AND (status <> 'queued' OR ?=1) ORDER BY updated_at LIMIT 5").bind(proofConfiguration(env).ready ? 1 : 0).all<{id:string}>();
  if (!rows.success) throw new Error("Proof storage unavailable");
  for (const row of rows.results) await advanceProofJob(env,row.id);
}

/** Always independently enforce operator Access, including on the main server. */
export async function proofJobsResponse(request: Request, env: ProofEnv): Promise<Response | null> {
  const url = new URL(request.url); const root = "/workspace/proof-jobs";
  if (url.pathname !== root && !url.pathname.startsWith(root+"/")) return null;
  const clean = { CF_ACCESS_TEAM_DOMAIN: env.PROOF_ACCESS_TEAM_DOMAIN ?? env.CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD: env.PROOF_ACCESS_AUD ?? env.CF_ACCESS_AUD } as Env;
  const operator = env.PROOF_ADMIN_EMAIL ?? env.ADMIN_EMAIL;
  if (!operator?.trim()) return json({error:"Operator not configured"},403);
  const denial = await checkAccess(request,clean,[operator]); if (denial) return json({error:"Operator sign-in required"},403);
  if (request.headers.get("Origin") && request.headers.get("Origin") !== url.origin) return json({error:"Same origin required"},403);
  try {
    if (request.method === "GET" && url.pathname === root+"/connection") return json({...await inspectProofConnection(env),observedAt:now()});
    if (request.method === "GET" && url.pathname === root) return json(await listProofJobs(env));
    const segments = url.pathname.slice(root.length+1).split("/");
    if (request.method === "GET" && segments.length === 1 && proofId.safeParse(segments[0]).success) {
      const row = await getRow(env,segments[0]); return row ? json({job:await view(row),receipt:row.receipt_json ? JSON.parse(row.receipt_json) : null}) : json({error:"Not found"},404);
    }
    if (request.method !== "POST" || !request.headers.get("Content-Type")?.startsWith("application/json")) return json({error:"JSON POST required"},405);
    const body = JSON.parse(await boundedText(new Response(request.body),PROOF_BODY_BYTES));
    if (url.pathname === root) return json(await enqueueProof(env,body),201);
    if (segments.length === 2 && proofId.safeParse(segments[0]).success && segments[1] === "cancel" && JSON.stringify(body) === "{}") {
      const job = await requestProofCancellation(env,segments[0]); return job ? json({job}) : json({error:"Not found"},404);
    }
    if (segments.length === 2 && proofId.safeParse(segments[0]).success && segments[1] === "recover") return json({job:await recoverProofJob(env,segments[0],body)});
    return json({error:"Not found"},404);
  } catch (error) {
    if (error instanceof ProviderError) return json({error:error.code},error.code.includes("already_active") || error.code.includes("conflict") ? 409 : error.code.includes("not_enabled") ? 503 : 400);
    if (error instanceof SyntaxError || (error instanceof Error && error.name === "ZodError")) return json({error:"Invalid proof request"},400);
    return json({error:"Proof storage unavailable"},503);
  }
}
