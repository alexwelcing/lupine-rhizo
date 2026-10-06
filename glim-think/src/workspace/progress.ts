import type { Env } from "../types";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";
import { progressClipSchema, PROGRESS_PAYLOAD_MAX_BYTES, type ProgressFeed } from "./progressContracts";

export const PROGRESS_PAGE_SIZE = 20;
// Bound row count and stored bytes before returning data from D1. An oversized
// payload becomes an explicit invalid-record error, never a partial success.
export const PROGRESS_LIST_SQL = `SELECT id, created_at,
  CASE WHEN length(CAST(payload AS BLOB)) <= ${PROGRESS_PAYLOAD_MAX_BYTES} THEN payload ELSE NULL END AS payload
  FROM workspace_progress ORDER BY created_at DESC, id DESC LIMIT ${PROGRESS_PAGE_SIZE + 1}`;

interface ProgressRow { id: string; created_at: string; payload: string | null }
class InvalidProgressRecord extends Error {}

/** Reads only the newest saved analyses; never invokes models or starts work. */
export async function listWorkspaceProgress(env: Pick<Env, "LEDGER">): Promise<ProgressFeed> {
  const result = await env.LEDGER.prepare(PROGRESS_LIST_SQL).all<ProgressRow>();
  if (!result.success || !Array.isArray(result.results)) throw new Error("Progress storage unavailable");
  const rows = result.results;
  const clips = rows.slice(0, PROGRESS_PAGE_SIZE).map(row => {
    try {
      if (typeof row.payload !== "string" || new TextEncoder().encode(row.payload).byteLength > PROGRESS_PAYLOAD_MAX_BYTES) throw new Error("Invalid payload");
      const clip = progressClipSchema.parse(JSON.parse(row.payload));
      if (clip.id !== row.id || clip.createdAt !== row.created_at) throw new Error("Mismatched record metadata");
      return clip;
    } catch {
      throw new InvalidProgressRecord("Progress feed contains an invalid saved record");
    }
  });
  return { clips, truncated: rows.length > PROGRESS_PAGE_SIZE };
}

/** Invoke only after the caller's Access/same-origin checks. */
export async function workspaceProgressResponse(env: Pick<Env, "LEDGER">): Promise<Response> {
  try {
    return Response.json(await listWorkspaceProgress(env), { headers: WORKSPACE_PRIVATE_HEADERS });
  } catch (error) {
    const invalid = error instanceof InvalidProgressRecord;
    return Response.json({
      error: invalid ? "Progress feed contains an invalid saved record." : "Progress feed is unavailable. Try again after its storage is ready.",
      code: invalid ? "invalid_progress_data" : "progress_unavailable",
    }, { status: 503, headers: WORKSPACE_PRIVATE_HEADERS });
  }
}
