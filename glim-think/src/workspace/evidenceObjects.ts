import type { Env } from "../types";
import { checkAccess } from "../middleware/access";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";

/** The private routes require no research execution or public-serving bindings.
 * Optional public bindings exist only to reject accidental aliasing in the main Worker.
 */
export type PrivateEvidenceEnv = Pick<Env,
  "ADMIN_EMAIL" | "CF_ACCESS_TEAM_DOMAIN" | "CF_ACCESS_AUD" |
  "PRIVATE_EVIDENCE" | "PRIVATE_EVIDENCE_ENABLED" | "PRIVATE_CORPUS" | "PRIVATE_CORPUS_ENABLED"
> & Partial<Pick<Env, "ARTIFACTS" | "LEDGER">>;

export const EVIDENCE_OBJECT_MAX_BYTES = 25 * 1024 * 1024;
const ROOT = "/workspace/evidence-objects";
const HASH = /^[a-f0-9]{64}$/;
// Bound buffering to one upload per isolate; GET/HEAD remain streaming.
let bufferInFlight = false;
export function acquireEvidenceBuffer(): (() => void) | null {
  if (bufferInFlight) return null;
  bufferInFlight = true;
  return () => { bufferInFlight = false; };
}
const json = (body: unknown, status = 200) =>
  Response.json(body, { status, headers: WORKSPACE_PRIVATE_HEADERS });

export async function readBounded(body: ReadableStream<Uint8Array> | null, declared: number | null, cap = EVIDENCE_OBJECT_MAX_BYTES): Promise<Uint8Array> {
  if (declared !== null && declared > cap) {
    await body?.cancel().catch(() => {});
    throw new RangeError("Object too large");
  }
  const chunks: Uint8Array[] = [];
  let bytes = 0;
  if (body) {
    const reader = body.getReader();
    try {
      for (;;) {
        const part = await reader.read();
        if (part.done) break;
        bytes += part.value.byteLength;
        if (bytes > cap) {
          await reader.cancel().catch(() => {});
          throw new RangeError("Object too large");
        }
        chunks.push(part.value);
      }
    } finally { reader.releaseLock(); }
  }
  if (declared !== null && declared !== bytes) throw new Error("Length mismatch");
  const result = new Uint8Array(bytes);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
  return result;
}

export async function digest(bytes: Uint8Array): Promise<{ hex: string; raw: ArrayBuffer }> {
  const raw = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return { raw, hex: Array.from(new Uint8Array(raw), b => b.toString(16).padStart(2, "0")).join("") };
}
function validObject(object: R2Object, hash: string): boolean {
  return Number.isSafeInteger(object.size) && object.size >= 0 &&
    object.size <= EVIDENCE_OBJECT_MAX_BYTES && object.customMetadata?.sha256 === hash;
}

export async function requireEvidenceOperator(request: Request, env: PrivateEvidenceEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (request.headers.has("Origin") && request.headers.get("Origin") !== url.origin)
    return json({ error: "Same-origin request required" }, 403);
  if (!env.ADMIN_EMAIL?.trim()) return json({ error: "Operator is not configured" }, 403);
  // Deliberately omit DEV_MODE and all legacy service-token bypasses.
  const denial = await checkAccess(request, {
    CF_ACCESS_AUD: env.CF_ACCESS_AUD, CF_ACCESS_TEAM_DOMAIN: env.CF_ACCESS_TEAM_DOMAIN,
  } as Env, [env.ADMIN_EMAIL]);
  if (denial) return json({ error: "Verified operator Access required" }, 403);
  return null;
}

/** Private immutable bytes only. Stored bytes are not admitted scientific evidence.
 * No public ARTIFACTS fallback, source fetching, model calls, or automatic retries.
 * PRIVATE_EVIDENCE must bind a distinct bucket with all public access disabled.
 */
export async function evidenceObjectsResponse(request: Request, env: PrivateEvidenceEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname !== ROOT && !url.pathname.startsWith(ROOT + "/")) return null;
  const denial = await requireEvidenceOperator(request, env);
  if (denial) return denial;
  if (!["PUT", "GET", "HEAD"].includes(request.method))
    return json({ error: "Method not allowed" }, 405);
  const hash = url.pathname.slice(ROOT.length + 1);
  if (!HASH.test(hash)) return json({ error: "Use one lowercase SHA-256 identifier" }, 400);
  const bucket = env.PRIVATE_EVIDENCE;
  if (env.PRIVATE_EVIDENCE_ENABLED !== "true" || !bucket || bucket === env.ARTIFACTS)
    return json({ error: "Private evidence storage is not configured" }, 503);
  const key = "sha256/" + hash;
  const uploading = request.method === "PUT";
  const release = uploading ? acquireEvidenceBuffer() : null;
  if (uploading && !release) return json({ error: "An upload is already in progress; no retry scheduled" }, 429);
  try {
    if (request.method === "PUT") {
      const encoding = request.headers.get("Content-Encoding");
      if (encoding && encoding.toLowerCase() !== "identity")
        return json({ error: "Upload original unencoded bytes" }, 415);
      const length = request.headers.get("Content-Length");
      if (length !== null && !/^[0-9]+$/.test(length))
        return json({ error: "Invalid Content-Length" }, 400);
      const declared = length === null ? null : Number(length);
      if (declared !== null && !Number.isSafeInteger(declared))
        return json({ error: "Invalid Content-Length" }, 400);
      let bytes: Uint8Array;
      try { bytes = await readBounded(request.body, declared); }
      catch (e) { return json({ error: e instanceof RangeError ? "Object exceeds 25 MiB" : "Invalid object body" }, e instanceof RangeError ? 413 : 400); }
      const fingerprint = await digest(bytes);
      if (fingerprint.hex !== hash) return json({ error: "SHA-256 does not match uploaded bytes" }, 422);
      const existing = await bucket.get(key);
      if (existing) {
        if (!validObject(existing, hash)) {
          await existing.body.cancel().catch(() => {});
          return json({ error: "Existing object integrity conflict" }, 409);
        }
        const prior = await readBounded(existing.body, existing.size);
        if ((await digest(prior)).hex !== hash)
          return json({ error: "Existing object integrity conflict" }, 409);
        return json({ sha256: hash, bytes: prior.byteLength, duplicate: true, state: "stored", evidenceStatus: "unreviewed" });
      }
      const object = await bucket.put(key, bytes, {
        onlyIf: new Headers({ "If-None-Match": "*" }),
        sha256: fingerprint.raw,
        customMetadata: { sha256: hash },
        httpMetadata: { contentType: "application/octet-stream", cacheControl: "private, no-store" },
      });
      if (!object) return json({ error: "Concurrent write; verify stored bytes before another action" }, 409);
      if (!validObject(object, hash) || object.size !== bytes.byteLength)
        return json({ error: "Storage acknowledgement could not be verified; no retry performed" }, 502);
      return json({ sha256: hash, bytes: bytes.byteLength, duplicate: false, state: "stored", evidenceStatus: "unreviewed" }, 201);
    }
    const object = request.method === "HEAD" ? await bucket.head(key) : await bucket.get(key);
    if (!object) return json({ error: "Object not found" }, 404);
    if (!validObject(object, hash)) {
      if ("body" in object) await (object as R2ObjectBody).body.cancel().catch(() => {});
      return json({ error: "Stored object metadata is invalid" }, 502);
    }
    const headers = new Headers(WORKSPACE_PRIVATE_HEADERS);
    headers.set("Content-Type", "application/octet-stream");
    headers.set("Content-Disposition", 'attachment; filename="' + hash + '.bin"');
    headers.set("Content-Length", String(object.size));
    headers.set("X-Content-SHA256", hash);
    headers.set("Content-Security-Policy", "default-src 'none'; sandbox");
    // The client must hash GET bytes before marking migration readback verified.
    return new Response(request.method === "HEAD" ? null : (object as R2ObjectBody).body, { headers });
  } catch {
    return json({ error: "Evidence storage unavailable; outcome may be unknown; no retry performed" }, 503);
  } finally {
    release?.();
  }
}
