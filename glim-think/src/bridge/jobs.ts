/**
 * /bridge/* — herdr bridge job queue (control plane → local machines).
 *
 * herdr (the local terminal multiplexer that hosts coding agents) has no
 * inbound network surface, so the Worker never pushes to a machine. Instead
 * one bridge daemon per machine (tools/herdr-bridge/) polls this surface:
 *
 *   POST /bridge/jobs                 { machine_id, agent_kind?, prompt, campaign_id? }
 *   GET  /bridge/jobs/next?machine_id=X[&wait_seconds=N]
 *   POST /bridge/jobs/:id/result      { status, output_excerpt?, beat? }
 *
 * All three are gated by middleware/access.ts: the bridge presents the
 * dedicated HERDR_BRIDGE_TOKEN bearer (scoped to /bridge/* + POST /feed/beats,
 * mirroring the LUPINE_APP_TOKEN pattern); operators may also use the global
 * X-Internal-Token or a Cloudflare Access JWT.
 * Storage is D1 `herdr_bridge_jobs` (migration 0017). Lifecycle telemetry
 * rides the ordinary /feed/beats path; a result may carry a final beat which
 * is forwarded through ingestBeat so it lands in lab_beats and, when the
 * job has a campaign_id, in that campaign's CampaignConsole.
 * Architecture: docs/herdr-bridge.md.
 */
import type { Env } from "../types";
import { ingestBeat } from "../feed/beats";

export const BRIDGE_JOB_STATUSES = ["pending", "claimed", "done", "failed", "blocked", "timeout"] as const;
export type BridgeJobStatus = (typeof BRIDGE_JOB_STATUSES)[number];
const TERMINAL_STATUSES: ReadonlySet<string> = new Set(["done", "failed", "blocked", "timeout"]);

/** A claim older than this with attempts left is handed out again (bridge crashed mid-job). */
export const STALE_CLAIM_SECONDS = 2 * 60 * 60;
export const MAX_ATTEMPTS = 3;
const MAX_LONG_POLL_SECONDS = 20;
const LONG_POLL_STEP_MS = 2000;
const MAX_PROMPT_CHARS = 32_000;
const MAX_EXCERPT_CHARS = 8_000;
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

export interface BridgeJobRow {
  job_id: string;
  machine_id: string;
  agent_kind: string;
  prompt: string;
  campaign_id: string | null;
  status: string;
  attempts: number;
  created_at: number;
  claimed_at: number | null;
}

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

function safeJson(text: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(text || "{}") as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface EnqueueBody {
  machine_id: string;
  agent_kind: string;
  prompt: string;
  campaign_id: string | null;
}

function validateEnqueue(raw: Record<string, unknown> | null): EnqueueBody | string {
  if (!raw) return "body must be a JSON object";
  const machineId = typeof raw.machine_id === "string" ? raw.machine_id.trim() : "";
  if (!ID_PATTERN.test(machineId)) return "machine_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}";
  const agentKind = typeof raw.agent_kind === "string" && raw.agent_kind.trim()
    ? raw.agent_kind.trim().toLowerCase()
    : "hermes";
  if (!/^[a-z][a-z0-9_-]{0,31}$/.test(agentKind)) return "agent_kind must be a short lowercase identifier";
  const prompt = typeof raw.prompt === "string" ? raw.prompt.trim() : "";
  if (!prompt) return "prompt must be a non-empty string";
  if (prompt.length > MAX_PROMPT_CHARS) return `prompt exceeds ${MAX_PROMPT_CHARS} characters`;
  let campaignId: string | null = null;
  if (raw.campaign_id !== undefined && raw.campaign_id !== null) {
    if (typeof raw.campaign_id !== "string" || !raw.campaign_id.trim()) return "campaign_id must be a non-empty string when present";
    campaignId = raw.campaign_id.trim();
  }
  return { machine_id: machineId, agent_kind: agentKind, prompt, campaign_id: campaignId };
}

export async function enqueueBridgeJob(env: Env, body: EnqueueBody): Promise<BridgeJobRow> {
  const jobId = crypto.randomUUID();
  const now = nowSeconds();
  await env.LEDGER
    .prepare(
      `INSERT INTO herdr_bridge_jobs
         (job_id, machine_id, agent_kind, prompt, campaign_id, status, attempts, created_at, updated_at)
       VALUES (?1, ?2, ?3, ?4, ?5, 'pending', 0, ?6, ?6)`,
    )
    .bind(jobId, body.machine_id, body.agent_kind, body.prompt, body.campaign_id, now)
    .run();
  return {
    job_id: jobId,
    machine_id: body.machine_id,
    agent_kind: body.agent_kind,
    prompt: body.prompt,
    campaign_id: body.campaign_id,
    status: "pending",
    attempts: 0,
    created_at: now,
    claimed_at: null,
  };
}

/**
 * Atomically claim the oldest dispatchable job for a machine. A single
 * UPDATE with a sub-select keeps two bridges with the same machine_id (or a
 * restart racing its own stale poll) from both receiving the same job.
 */
export async function claimNextBridgeJob(env: Env, machineId: string): Promise<BridgeJobRow | null> {
  const now = nowSeconds();
  const row = await env.LEDGER
    .prepare(
      `UPDATE herdr_bridge_jobs
          SET status = 'claimed', attempts = attempts + 1, claimed_at = ?2, updated_at = ?2
        WHERE job_id = (
          SELECT job_id FROM herdr_bridge_jobs
           WHERE machine_id = ?1
             AND (status = 'pending'
                  OR (status = 'claimed' AND claimed_at < ?3 AND attempts < ?4))
           ORDER BY created_at ASC
           LIMIT 1
        )
        RETURNING job_id, machine_id, agent_kind, prompt, campaign_id, status, attempts, created_at, claimed_at`,
    )
    .bind(machineId, now, now - STALE_CLAIM_SECONDS, MAX_ATTEMPTS)
    .first<BridgeJobRow>();
  return row ?? null;
}

interface ResultBody {
  status: BridgeJobStatus;
  output_excerpt: string | null;
  beat: Record<string, unknown> | null;
}

function validateResult(raw: Record<string, unknown> | null): ResultBody | string {
  if (!raw) return "body must be a JSON object";
  const status = typeof raw.status === "string" ? raw.status.trim() : "";
  if (!TERMINAL_STATUSES.has(status)) return "status must be one of done, failed, blocked, timeout";
  let excerpt: string | null = null;
  if (raw.output_excerpt !== undefined && raw.output_excerpt !== null) {
    if (typeof raw.output_excerpt !== "string") return "output_excerpt must be a string";
    excerpt = raw.output_excerpt.slice(0, MAX_EXCERPT_CHARS);
  }
  let beat: Record<string, unknown> | null = null;
  if (raw.beat !== undefined && raw.beat !== null) {
    if (typeof raw.beat !== "object" || Array.isArray(raw.beat)) return "beat must be an object";
    beat = raw.beat as Record<string, unknown>;
  }
  return { status: status as BridgeJobStatus, output_excerpt: excerpt, beat };
}

export async function handleBridgeRoute(
  request: Request,
  env: Env,
  url: URL,
  bodyText: string,
): Promise<Response | null> {
  if (!url.pathname.startsWith("/bridge/")) return null;
  const method = request.method;

  try {
    if (url.pathname === "/bridge/jobs" && method === "POST") {
      const validated = validateEnqueue(safeJson(bodyText));
      if (typeof validated === "string") return json({ error: validated }, 400);
      const job = await enqueueBridgeJob(env, validated);
      return json({ ok: true, job }, 201);
    }

    if (url.pathname === "/bridge/jobs/next" && method === "GET") {
      const machineId = (url.searchParams.get("machine_id") ?? "").trim();
      if (!ID_PATTERN.test(machineId)) return json({ error: "machine_id query parameter is required" }, 400);
      const waitSeconds = Math.min(
        Math.max(parseInt(url.searchParams.get("wait_seconds") ?? "0", 10) || 0, 0),
        MAX_LONG_POLL_SECONDS,
      );
      const deadline = Date.now() + waitSeconds * 1000;
      let job = await claimNextBridgeJob(env, machineId);
      while (!job && Date.now() + LONG_POLL_STEP_MS <= deadline) {
        await sleep(LONG_POLL_STEP_MS);
        job = await claimNextBridgeJob(env, machineId);
      }
      if (!job) return new Response(null, { status: 204 });
      return json({ ok: true, job });
    }

    const resultMatch = /^\/bridge\/jobs\/([^/]+)\/result$/.exec(url.pathname);
    if (resultMatch && method === "POST") {
      let jobId: string;
      try {
        jobId = decodeURIComponent(resultMatch[1]);
      } catch {
        return json({ error: "invalid job id encoding" }, 400);
      }
      if (!ID_PATTERN.test(jobId)) return json({ error: "invalid job id" }, 400);
      const validated = validateResult(safeJson(bodyText));
      if (typeof validated === "string") return json({ error: validated }, 400);

      const existing = await env.LEDGER
        .prepare(`SELECT job_id, machine_id, agent_kind, prompt, campaign_id, status, attempts, created_at, claimed_at
                    FROM herdr_bridge_jobs WHERE job_id = ?1`)
        .bind(jobId)
        .first<BridgeJobRow>();
      if (!existing) return json({ error: "job not found" }, 404);
      if (TERMINAL_STATUSES.has(existing.status)) {
        return json({ error: `job already ${existing.status}`, job_id: jobId, status: existing.status }, 409);
      }

      // Forward the closing beat through the canonical ingest path so it
      // gets the same validation, lab_beats insert, and campaign-console
      // fan-in as any other beat. Auth already happened at the /bridge/*
      // gate, so we skip the producer credential check.
      let beatId: string | null = null;
      if (validated.beat) {
        const beat: Record<string, unknown> = {
          ...validated.beat,
          metrics: {
            ...((validated.beat.metrics as Record<string, unknown> | undefined) ?? {}),
            job_id: jobId,
            machine_id: existing.machine_id,
            ...(existing.campaign_id ? { campaign_id: existing.campaign_id } : {}),
            source: "herdr-bridge",
          },
        };
        const beatResponse = await ingestBeat(env, JSON.stringify(beat));
        if (!beatResponse.ok) {
          const detail = await beatResponse.text();
          return json({ error: "result beat rejected; job left claimed for retry", detail }, beatResponse.status);
        }
        beatId = typeof beat.beat_id === "string" ? beat.beat_id : null;
      }

      const now = nowSeconds();
      await env.LEDGER
        .prepare(
          `UPDATE herdr_bridge_jobs
              SET status = ?2, output_excerpt = ?3, result_beat_id = ?4, completed_at = ?5, updated_at = ?5
            WHERE job_id = ?1`,
        )
        .bind(jobId, validated.status, validated.output_excerpt, beatId, now)
        .run();
      return json({ ok: true, job_id: jobId, status: validated.status, beat_id: beatId });
    }

    return json({ error: "unknown bridge route" }, 404);
  } catch (e) {
    console.error("bridge route failed:", e);
    return json({ error: String(e) }, 500);
  }
}
