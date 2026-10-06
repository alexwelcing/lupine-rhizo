import type { Env } from "../types";
import { checkAccess } from "../middleware/access";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";
import {
  decodePublicResearchActivity, publicActivityIdSchema, publicActivitySha256,
  PUBLIC_ACTIVITY_DEFAULT_LIMIT, PUBLIC_ACTIVITY_FEED_SCHEMA, PUBLIC_ACTIVITY_MAX_BYTES,
  PUBLIC_ACTIVITY_MAX_LIMIT, type PublicResearchActivity, type PublicResearchActivityFeed,
} from "./researchActivityContracts";

const PUBLIC_PATH = "/research/activity";
const IMPORT_PATH = "/workspace/research-activity/import";
const PUBLIC_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Cache-Control": "public, max-age=30, s-maxage=30",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
} as const;
const SELECT = `SELECT a.id, a.activity_id, a.observed_at, a.reviewed_at, a.supersedes_id, a.payload_sha256,
  CASE WHEN length(CAST(a.payload AS BLOB)) <= ${PUBLIC_ACTIVITY_MAX_BYTES} THEN a.payload ELSE NULL END AS payload
  FROM public_research_activity a`;
interface Row { id: string; activity_id: string; observed_at: string; reviewed_at: string; supersedes_id: string | null; payload_sha256: string; payload: string | null }
class InvalidRecord extends Error {}
class Conflict extends Error {}
const privateJson = (body: unknown, status = 200) => Response.json(body, { status, headers: WORKSPACE_PRIVATE_HEADERS });
const publicJson = (body: unknown, status = 200) => Response.json(body, { status, headers: {
  ...PUBLIC_HEADERS, ...(status >= 400 ? { "Cache-Control": "no-store" } : {}),
} });
const envelope = (items: PublicResearchActivity[], truncated = false): PublicResearchActivityFeed => ({ schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items, truncated });

async function decodeRow(row: Row): Promise<PublicResearchActivity> {
  try {
    if (typeof row.payload !== "string" || new TextEncoder().encode(row.payload).length > PUBLIC_ACTIVITY_MAX_BYTES ||
        await publicActivitySha256(row.payload) !== row.payload_sha256) throw new Error();
    const record = decodePublicResearchActivity(JSON.parse(row.payload));
    if (record.id !== row.id || record.activityId !== row.activity_id || record.observedAt !== row.observed_at ||
        record.reviewedAt !== row.reviewed_at || record.supersedes !== row.supersedes_id) throw new Error();
    return record;
  } catch { throw new InvalidRecord(); }
}

export async function listPublicResearchActivity(env: Pick<Env, "LEDGER">, limit = PUBLIC_ACTIVITY_DEFAULT_LIMIT): Promise<PublicResearchActivityFeed> {
  if (!Number.isInteger(limit) || limit < 1 || limit > PUBLIC_ACTIVITY_MAX_LIMIT) throw new RangeError();
  const rows = await env.LEDGER.prepare(`${SELECT}
    WHERE NOT EXISTS (SELECT 1 FROM public_research_activity successor WHERE successor.supersedes_id = a.id)
    ORDER BY a.observed_at DESC, a.id DESC LIMIT ?`).bind(limit + 1).all<Row>();
  if (!rows.success || !Array.isArray(rows.results)) throw new Error();
  // Validate the entire bounded page, including the lookahead row. Never return
  // partial successful data when any selected public record is malformed.
  const records = await Promise.all(rows.results.map(decodeRow));
  return envelope(records.slice(0, limit), records.length > limit);
}

export async function getPublicResearchActivity(env: Pick<Env, "LEDGER">, id: string): Promise<PublicResearchActivity | null> {
  publicActivityIdSchema.parse(id);
  const row = await env.LEDGER.prepare(`${SELECT} WHERE a.id = ?`).bind(id).first<Row>();
  return row ? decodeRow(row) : null;
}

function assertSuccessor(previous: PublicResearchActivity, record: PublicResearchActivity): void {
  if (record.activityId !== previous.activityId || record.evidenceKind !== previous.evidenceKind ||
      record.supersedes !== previous.id || record.observedAt < previous.observedAt || record.reviewedAt <= previous.reviewedAt) throw new Conflict();
  if (previous.state === "completed" || previous.state === "failed") {
    if (record.state !== previous.state || record.correctionReason === null) throw new Conflict();
  } else if (previous.state !== "planned" && record.state === "planned") throw new Conflict();
}

/** Explicitly reviewed public projection only. Does not read any private table. */
export async function importPublicResearchActivity(env: Pick<Env, "LEDGER">, value: unknown): Promise<{ record: PublicResearchActivity; duplicate: boolean }> {
  const record = decodePublicResearchActivity(value);
  const payload = JSON.stringify(record);
  const fingerprint = await publicActivitySha256(payload);
  const old = await env.LEDGER.prepare(`${SELECT} WHERE a.id = ?`).bind(record.id).first<Row>();
  if (old) {
    const saved = await decodeRow(old);
    if (old.payload_sha256 === fingerprint) return { record: saved, duplicate: true };
    throw new Conflict(); // IDs and their payloads are immutable, including terminal records.
  }
  const latest = await env.LEDGER.prepare(`${SELECT} WHERE a.activity_id = ?
    AND NOT EXISTS (SELECT 1 FROM public_research_activity successor WHERE successor.supersedes_id = a.id)`).bind(record.activityId).first<Row>();
  if (latest) assertSuccessor(await decodeRow(latest), record);
  else if (record.supersedes !== null) throw new Conflict();

  // Root and predecessor unique indexes resolve concurrent roots/successors.
  // ON CONFLICT does not mutate an existing record or manufacture a retry.
  const saved = await env.LEDGER.prepare(`INSERT INTO public_research_activity
    (id, activity_id, observed_at, reviewed_at, supersedes_id, payload_sha256, payload)
    VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING`)
    .bind(record.id, record.activityId, record.observedAt, record.reviewedAt, record.supersedes, fingerprint, payload).run();
  if (!saved.success) throw new Error();
  if (saved.meta.changes !== 1) throw new Conflict();
  return { record, duplicate: false };
}

async function readBounded(request: Request): Promise<string> {
  const length = request.headers.get("Content-Length");
  if (length && (!/^\d+$/.test(length) || Number(length) > PUBLIC_ACTIVITY_MAX_BYTES)) throw new RangeError();
  const reader = request.body?.getReader();
  if (!reader) throw new SyntaxError();
  const chunks: Uint8Array[] = []; let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > PUBLIC_ACTIVITY_MAX_BYTES) { await reader.cancel(); throw new RangeError(); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const buffer = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.length; }
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(buffer);
}

/** Public GET is the sole Access exception; imports independently verify the
 * operator with no DEV_MODE, legacy internal-token, or service-token bypass. */
export async function researchActivityResponse(request: Request, env: Env): Promise<Response | null> {
  const url = new URL(request.url);
  const isPublic = url.pathname === PUBLIC_PATH || url.pathname.startsWith(`${PUBLIC_PATH}/`);
  const isImport = url.pathname === IMPORT_PATH;
  if (!isPublic && !isImport) return null;
  if (isPublic) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: PUBLIC_HEADERS });
    if (request.method !== "GET") return new Response(null, { status: 405, headers: { ...PUBLIC_HEADERS, Allow: "GET, OPTIONS", "Cache-Control": "no-store" } });
    try {
      if (url.pathname === PUBLIC_PATH) {
        if ([...url.searchParams.keys()].some(key => key !== "limit") || url.searchParams.getAll("limit").length > 1) return publicJson({ error: "Invalid activity query" }, 400);
        const supplied = url.searchParams.get("limit");
        if (supplied !== null && !/^[1-9]\d?$/.test(supplied)) return publicJson({ error: "Invalid activity limit" }, 400);
        const limit = supplied === null ? PUBLIC_ACTIVITY_DEFAULT_LIMIT : Number(supplied);
        if (limit > PUBLIC_ACTIVITY_MAX_LIMIT) return publicJson({ error: "Invalid activity limit" }, 400);
        return publicJson(await listPublicResearchActivity(env, limit));
      }
      const id = url.pathname.slice(PUBLIC_PATH.length + 1);
      if (url.search || !publicActivityIdSchema.safeParse(id).success) return publicJson({ error: "Activity not found" }, 404);
      const record = await getPublicResearchActivity(env, id);
      return record ? publicJson(envelope([record])) : publicJson({ error: "Activity not found" }, 404);
    } catch {
      // No malformed payload, raw database error, private path or identity is echoed.
      return publicJson({ error: "Public research activity is unavailable", code: "research_activity_unavailable" }, 503);
    }
  }
  if (request.method !== "POST") return privateJson({ error: "Use POST" }, 405);
  if (request.headers.get("Origin") !== url.origin) return privateJson({ error: "Same-origin operator import required" }, 403);
  if (!env.ADMIN_EMAIL?.trim()) return privateJson({ error: "Research operator is not configured" }, 403);
  const denial = await checkAccess(request, { CF_ACCESS_AUD: env.CF_ACCESS_AUD, CF_ACCESS_TEAM_DOMAIN: env.CF_ACCESS_TEAM_DOMAIN } as Env, [env.ADMIN_EMAIL]);
  if (denial) return privateJson({ error: "Verified operator Access is required" }, 403);
  if (url.search || request.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "application/json") return privateJson({ error: "Use application/json without query parameters" }, 415);
  let value: unknown;
  try { value = JSON.parse(await readBounded(request)); decodePublicResearchActivity(value); }
  catch (error) { return privateJson({ error: error instanceof RangeError ? "Public activity exceeds the size limit" : "Public activity failed reviewed-projection validation" }, error instanceof RangeError ? 413 : 400); }
  try {
    const { record, duplicate } = await importPublicResearchActivity(env, value);
    return privateJson({ id: record.id, activityId: record.activityId, state: record.state, duplicate });
  } catch (error) {
    return privateJson(error instanceof Conflict
      ? { error: "Activity conflicts with immutable history or a newer reviewed record", code: "research_activity_conflict" }
      : { error: "Public activity storage is unavailable", code: "research_activity_unavailable" }, error instanceof Conflict ? 409 : 503);
  }
}
