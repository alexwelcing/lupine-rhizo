import type { Env } from "../types";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";
import { acquireEvidenceBuffer, digest, readBounded, requireEvidenceOperator, EVIDENCE_OBJECT_MAX_BYTES } from "./evidenceObjects";

const ROOT = "/workspace/corpus";
const HASH = /^[a-f0-9]{64}$/;
const ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}$/;
const MAX_BODY = 1024 * 1024;
const MAX_ROWS = 20;
const MAX_OBJECTS = 16;
const encoder = new TextEncoder();
const json = (body: unknown, status = 200) => Response.json(body, { status, headers: WORKSPACE_PRIVATE_HEADERS });
class InputError extends Error {}
function fail(message: string): never { throw new InputError(message); }
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail("Expected an object");
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, keys: string[]) {
  if (Object.keys(value).some(k => !keys.includes(k))) fail("Unknown field");
}
function text(value: unknown, max: number, nullable = false): string | null {
  if (nullable && value === null) return null;
  if (typeof value !== "string" || !value.trim() || encoder.encode(value).length > max || /[\u0000-\u001f]/.test(value)) fail("Invalid text field");
  return value;
}
function hash(value: unknown): string { if (typeof value !== "string" || !HASH.test(value)) fail("Invalid SHA-256"); return value; }
function time(value: unknown): string | null {
  if (value === null) return null;
  const s = text(value, 64)!;
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$/.exec(s);
  if (!m) fail("Use original ISO timestamp with explicit timezone or null");
  const [year, month, day, hour, minute, second] = m.slice(1,7).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
  if (month<1 || month>12 || day<1 || day>days[month-1] || hour>23 || minute>59 || second>59 ||
    (m[7]!=="Z" && (Number(m[7].slice(1,3))>23 || Number(m[7].slice(4,6))>59)))
    fail("Invalid calendar timestamp");
  // Preserve timezone notation and sub-millisecond precision exactly.
  return s;
}
type Observation = {
  recordId: string; recordSha256: string; evidenceSha256: string;
  sourceId: string | null; studyId: string | null; locator: string;
  material: string | null; observable: string | null; unit: string | null;
  modelId: string | null; referenceKind: string | null;
  observedAt: string | null; reviewedAt: string | null; originalRowSha256: string | null;
  missingFields: string[]; recordJson: string;
};
type Qualification = { eventId: string; recordId: string; recordSha256: string; kind: string; reason: string; originalReviewedAt: string | null };
const observationKeys = ["recordId","recordSha256","evidenceSha256","sourceId","studyId","locator","material","observable","unit","modelId","referenceKind","observedAt","reviewedAt","originalRowSha256","missingFields","recordJson"];
async function observation(value: unknown): Promise<Observation> {
  const v = object(value); exactKeys(v, observationKeys);
  if (!Array.isArray(v.missingFields) || v.missingFields.length > 32) fail("Invalid missing fields");
  const missingFields = v.missingFields.map(x => text(x, 128)!);
  if (new Set(missingFields).size !== missingFields.length) fail("Duplicate missing field");
  if (typeof v.recordJson !== "string" || encoder.encode(v.recordJson).length > 65536) fail("Record JSON exceeds 64 KiB");
  let parsed: unknown;
  try { parsed = JSON.parse(v.recordJson); } catch { fail("Invalid record JSON"); }
  object(parsed);
  const recordSha256 = hash(v.recordSha256);
  if ((await digest(encoder.encode(v.recordJson))).hex !== recordSha256) fail("Record JSON hash mismatch");
  return {
    recordId: text(v.recordId,256)!, recordSha256, evidenceSha256: hash(v.evidenceSha256),
    sourceId: text(v.sourceId,256,true), studyId: text(v.studyId,256,true), locator: text(v.locator,1024)!,
    material: text(v.material,256,true), observable: text(v.observable,256,true), unit: text(v.unit,128,true),
    modelId: text(v.modelId,256,true), referenceKind: text(v.referenceKind,128,true),
    observedAt: time(v.observedAt), reviewedAt: time(v.reviewedAt),
    originalRowSha256: v.originalRowSha256 === null ? null : hash(v.originalRowSha256),
    missingFields, recordJson: v.recordJson,
  };
}
function qualification(value: unknown): Qualification {
  const v = object(value);
  exactKeys(v, ["eventId","recordId","recordSha256","kind","reason","originalReviewedAt"]);
  if (!["quarantine","annotation","correction"].includes(String(v.kind))) fail("Invalid qualification kind");
  return { eventId: text(v.eventId,256)!, recordId: text(v.recordId,256)!,
    recordSha256: hash(v.recordSha256), kind: String(v.kind), reason: text(v.reason,2048)!,
    originalReviewedAt: time(v.originalReviewedAt) };
}
type Receipt = { sha256: string; bytes: number; etag: string; verified_at: string };
function metadataMatches(obj: R2Object, sha: string) {
  return obj.customMetadata?.sha256 === sha && Number.isSafeInteger(obj.size) &&
    obj.size >= 0 && obj.size <= EVIDENCE_OBJECT_MAX_BYTES && !!obj.etag;
}
function sourceStillMatches(obj: R2Object | null, receipt: Receipt) {
  return obj && metadataMatches(obj, receipt.sha256) && obj.size === receipt.bytes && obj.etag === receipt.etag;
}
async function objectReceipt(request: Request, env: Env, sha: string) {
  if (!HASH.test(sha)) return json({ error: "Invalid object SHA-256" },400);
  if (!["GET","POST"].includes(request.method)) return json({error:"Method not allowed"},405);
  const db = env.PRIVATE_CORPUS!, bucket = env.PRIVATE_EVIDENCE!;
  if (request.method === "GET") {
    const receipt = await db.prepare("SELECT * FROM workspace_evidence_receipts WHERE sha256=?").bind(sha).first<Receipt>();
    return receipt ? json({ receipt, state:"readback_verified", scope:"original verification time; current bytes not re-read" }) : json({error:"Receipt not found"},404);
  }
  // This route has no request body. Its only read is the content-addressed private object.
  if ((request.headers.get("Content-Length") ?? "0") !== "0" || request.body) return json({error:"Verification request must have no body"},400);
  const release = acquireEvidenceBuffer();
  if (!release) return json({error:"Evidence operation in progress; no retry scheduled"},429);
  try {
    const obj = await bucket.get("sha256/"+sha);
    if (!obj) return json({error:"Private evidence object not found"},404);
    if (!metadataMatches(obj,sha)) { await obj.body.cancel().catch(()=>{}); return json({error:"Invalid evidence object metadata"},409); }
    const bytes = await readBounded(obj.body,obj.size);
    if ((await digest(bytes)).hex !== sha) return json({error:"Stored bytes failed SHA-256 verification"},409);
    const prior = await db.prepare("SELECT * FROM workspace_evidence_receipts WHERE sha256=?").bind(sha).first<Receipt>();
    if (prior) return sourceStillMatches(obj,prior) ? json({receipt:prior,state:"readback_verified",duplicate:true}) : json({error:"Receipt metadata conflict"},409);
    const at = new Date().toISOString();
    // Equality replay is a no-op; a divergent race invokes the immutable trigger.
    await db.prepare(`INSERT INTO workspace_evidence_receipts (sha256,bytes,etag,verified_at) VALUES (?,?,?,?)
      ON CONFLICT(sha256) DO UPDATE SET etag=excluded.etag
      WHERE workspace_evidence_receipts.etag<>excluded.etag OR workspace_evidence_receipts.bytes<>excluded.bytes`).bind(sha,bytes.byteLength,obj.etag,at).run();
    const receipt = await db.prepare("SELECT * FROM workspace_evidence_receipts WHERE sha256=?").bind(sha).first<Receipt>();
    return json({receipt,state:"readback_verified",scientificValidation:"not_assessed"},201);
  } finally { release(); }
}
async function importRecords(request: Request, env: Env, id: string) {
  if (!ID.test(id)) return json({error:"Invalid import identifier"},400);
  const db=env.PRIVATE_CORPUS!;
  if (request.method === "GET") {
    const item=await db.prepare("SELECT * FROM workspace_corpus_imports WHERE import_id=?").bind(id).first();
    return item ? json({import:item,state:"committed"}) : json({error:"Import not found"},404);
  }
  if (request.method !== "PUT") return json({error:"Method not allowed"},405);
  if ((request.headers.get("Content-Type")??"").split(";")[0].trim().toLowerCase()!=="application/json") return json({error:"Use application/json"},415);
  if (request.headers.has("Content-Encoding") && request.headers.get("Content-Encoding")!=="identity") return json({error:"Use original unencoded JSON"},415);
  const length=request.headers.get("Content-Length");
  if (length!==null && (!/^\d+$/.test(length) || !Number.isSafeInteger(Number(length)))) return json({error:"Invalid Content-Length"},400);
  const release=acquireEvidenceBuffer();
  if (!release) return json({error:"Evidence operation in progress; no retry scheduled"},429);
  try {
    let bytes: Uint8Array;
    try { bytes=await readBounded(request.body,length===null?null:Number(length),MAX_BODY); }
    catch(e) { if (e instanceof RangeError) throw e; fail("Invalid import body or length"); }
    const payloadSha=(await digest(bytes)).hex;
    const prior=await db.prepare("SELECT * FROM workspace_corpus_imports WHERE import_id=?").bind(id).first<{payload_sha256:string}>();
    if (prior) return prior.payload_sha256===payloadSha ? json({import:prior,state:"committed",duplicate:true}) : json({error:"Import identifier already has different bytes"},409);
    let parsed: unknown;
    try { parsed=JSON.parse(new TextDecoder("utf-8",{fatal:true,ignoreBOM:false}).decode(bytes)); } catch { fail("Invalid UTF-8 JSON"); }
    const v=object(parsed); exactKeys(v,["schema","observations","qualifications"]);
    if (v.schema!=="lupine-private-corpus-v1" || !Array.isArray(v.observations) || !Array.isArray(v.qualifications)) fail("Invalid import schema");
    if (v.observations.length>MAX_ROWS || v.qualifications.length>MAX_ROWS || !v.observations.length&&!v.qualifications.length) fail("Use 1-20 observations or qualifications per import");
    const rows: Observation[]=[];
    for (const row of v.observations) rows.push(await observation(row));
    const events=v.qualifications.map(qualification);
    if (new Set(rows.map(r=>JSON.stringify([r.recordId,r.recordSha256]))).size!==rows.length || new Set(events.map(e=>e.eventId)).size!==events.length) fail("Duplicate entry in import");
    const hashes=[...new Set(rows.map(r=>r.evidenceSha256))];
    if (hashes.length>MAX_OBJECTS) fail("Too many evidence objects in one import");
    for (const sha of hashes) {
      const receipt=await db.prepare("SELECT * FROM workspace_evidence_receipts WHERE sha256=?").bind(sha).first<Receipt>();
      if (!receipt) return json({error:"Evidence object requires a readback receipt",sha256:sha},409);
      if (!sourceStillMatches(await env.PRIVATE_EVIDENCE!.head("sha256/"+sha),receipt)) return json({error:"Evidence object changed since verification",sha256:sha},409);
    }
    const at=new Date().toISOString();
    const statements=[db.prepare(`INSERT INTO workspace_corpus_imports (import_id,payload_sha256,observation_count,qualification_count,committed_at) VALUES (?,?,?,?,?)
      ON CONFLICT(import_id) DO UPDATE SET payload_sha256=excluded.payload_sha256 WHERE workspace_corpus_imports.payload_sha256<>excluded.payload_sha256`).bind(id,payloadSha,rows.length,events.length,at)];
    for (const r of rows) {
      const projectionSha=(await digest(encoder.encode(JSON.stringify(r)))).hex;
      statements.push(db.prepare(`INSERT INTO workspace_corpus_observations
        (record_id,record_sha256,projection_sha256,evidence_sha256,source_id,study_id,locator,material,observable,unit,model_id,reference_kind,observed_at,reviewed_at,original_row_sha256,missing_fields_json,record_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(record_id,record_sha256) DO UPDATE SET projection_sha256=excluded.projection_sha256 WHERE workspace_corpus_observations.projection_sha256<>excluded.projection_sha256`)
        .bind(r.recordId,r.recordSha256,projectionSha,r.evidenceSha256,r.sourceId,r.studyId,r.locator,r.material,r.observable,r.unit,r.modelId,r.referenceKind,r.observedAt,r.reviewedAt,r.originalRowSha256,JSON.stringify(r.missingFields),r.recordJson));
      statements.push(db.prepare("INSERT INTO workspace_corpus_members (import_id,record_id,record_sha256) VALUES (?,?,?) ON CONFLICT DO NOTHING").bind(id,r.recordId,r.recordSha256));
    }
    for (const e of events) {
      const eventSha=(await digest(encoder.encode(JSON.stringify(e)))).hex;
      statements.push(db.prepare(`INSERT INTO workspace_corpus_qualifications
        (event_id,event_sha256,import_id,record_id,record_sha256,kind,reason,original_reviewed_at) VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(event_id) DO UPDATE SET event_sha256=excluded.event_sha256 WHERE workspace_corpus_qualifications.event_sha256<>excluded.event_sha256`)
        .bind(e.eventId,eventSha,id,e.recordId,e.recordSha256,e.kind,e.reason,e.originalReviewedAt));
    }
    // One D1 transaction: no import marker or partial rows survive a failed statement.
    await db.batch(statements);
    const committed=await db.prepare("SELECT * FROM workspace_corpus_imports WHERE import_id=?").bind(id).first();
    return json({import:committed,state:"committed",scientificValidation:"not_assessed",provenanceLink:"operator_supplied"},201);
  } finally { release(); }
}
async function queryRecords(url: URL, env: Env) {
  const allowed=new Set(["source_id","study_id","material","observable","model_id","after_id","after_sha256","limit","include_quarantined","import_id"]);
  for (const key of url.searchParams.keys()) if (!allowed.has(key) || url.searchParams.getAll(key).length!==1) fail("Unknown or repeated query parameter");
  const limitString=url.searchParams.get("limit")??"20";
  if (!/^\d+$/.test(limitString) || Number(limitString)<1 || Number(limitString)>50) fail("Limit must be 1-50");
  const limit=Number(limitString), clauses:string[]=[], args:(string|number)[]=[];
  for (const column of ["source_id","study_id","material","observable","model_id"]) {
    const v=url.searchParams.get(column);
    if (v!==null) { clauses.push("o."+column+"=?"); args.push(text(v,256)!); }
  }
  const afterId=url.searchParams.get("after_id"), afterHash=url.searchParams.get("after_sha256");
  if ((afterId===null)!==(afterHash===null)) fail("Both cursor fields are required");
  if (afterId!==null) { clauses.push("(o.record_id,o.record_sha256)>(?,?)"); args.push(text(afterId,256)!,hash(afterHash)); }
  const importId=url.searchParams.get("import_id");
  if (importId!==null) { if (!ID.test(importId)) fail("Invalid import identifier"); clauses.push("EXISTS (SELECT 1 FROM workspace_corpus_members m WHERE m.import_id=? AND m.record_id=o.record_id AND m.record_sha256=o.record_sha256)"); args.push(importId); }
  const include=url.searchParams.get("include_quarantined")??"false";
  if (!["true","false"].includes(include)) fail("Invalid quarantine option");
  if (include!=="true") clauses.push("NOT EXISTS (SELECT 1 FROM workspace_corpus_qualifications q WHERE q.record_id=o.record_id AND q.record_sha256=o.record_sha256 AND q.kind='quarantine')");
  // Return projections only, not whole 64 KiB source rows. Each page has a fixed cap.
  const columns="o.record_id,o.record_sha256,o.evidence_sha256,o.source_id,o.study_id,o.locator,o.material,o.observable,o.unit,o.model_id,o.reference_kind,o.observed_at,o.reviewed_at,o.original_row_sha256,o.missing_fields_json,EXISTS (SELECT 1 FROM workspace_corpus_qualifications q WHERE q.record_id=o.record_id AND q.record_sha256=o.record_sha256 AND q.kind=\'quarantine\') AS quarantined";
  const result=await env.PRIVATE_CORPUS!.prepare("SELECT "+columns+" FROM workspace_corpus_observations o"+(clauses.length?" WHERE "+clauses.join(" AND "):"")+" ORDER BY o.record_id,o.record_sha256 LIMIT ?").bind(...args,limit+1).all<Record<string,unknown>>();
  const hasMore=result.results.length>limit;
  const rows=result.results.slice(0,limit);
  // Aggregate qualifications are intentionally not claimed here; use the detail route.
  const last=rows.at(-1);
  return json({observations:rows,next:hasMore&&last?{after_id:last.record_id,after_sha256:last.record_sha256}:null,
    state:"imported",scientificValidation:"not_assessed",provenanceLink:"operator_supplied",
    includesQuarantined:include==="true",pagination:"live keyset; pin import_id for fixed membership"});
}
async function recordDetail(url: URL, env: Env) {
  const params=url.searchParams;
  if ([...params.keys()].some(k=>!["record_id","record_sha256"].includes(k)) || params.getAll("record_id").length!==1 || params.getAll("record_sha256").length!==1) fail("Use record_id and record_sha256");
  const id=text(params.get("record_id"),256)!, sha=hash(params.get("record_sha256"));
  const row=await env.PRIVATE_CORPUS!.prepare("SELECT o.*,EXISTS (SELECT 1 FROM workspace_corpus_qualifications q WHERE q.record_id=o.record_id AND q.record_sha256=o.record_sha256 AND q.kind=\'quarantine\') AS quarantined FROM workspace_corpus_observations o WHERE o.record_id=? AND o.record_sha256=?").bind(id,sha).first();
  if (!row) return json({error:"Observation not found"},404);
  // Qualifications also require pagination so a long review history stays bounded.
  return json({observation:row,state:"imported",scientificValidation:"not_assessed",provenanceLink:"operator_supplied"});
}

async function queryQualifications(url: URL, env: Env) {
  const p=url.searchParams, allowed=new Set(["record_id","record_sha256","after_event_id","limit"]);
  for (const key of p.keys()) if (!allowed.has(key)||p.getAll(key).length!==1) fail("Unknown or repeated query parameter");
  const id=text(p.get("record_id"),256)!, sha=hash(p.get("record_sha256"));
  const ls=p.get("limit")??"20";
  if (!/^\d+$/.test(ls)||Number(ls)<1||Number(ls)>50) fail("Limit must be 1-50");
  const limit=Number(ls), after=p.get("after_event_id"), args:(string|number)[]=[id,sha];
  if (after!==null) args.push(text(after,256)!);
  args.push(limit+1);
  const result=await env.PRIVATE_CORPUS!.prepare("SELECT * FROM workspace_corpus_qualifications WHERE record_id=? AND record_sha256=?"+(after===null?"":" AND event_id>?")+" ORDER BY event_id LIMIT ?").bind(...args).all<Record<string,unknown>>();
  const rows=result.results.slice(0,limit);
  return json({qualifications:rows,next:result.results.length>limit?{after_event_id:rows.at(-1)!.event_id}:null,scope:"original events; correction does not replace observations"});
}


/** Deterministic input for per-source analysis; no inferred relation or model call. */
async function sourceContext(url: URL, env: Env) {
  const p=url.searchParams, allowed=new Set(["source_id","after_id","after_sha256","limit","import_id"]);
  for (const key of p.keys()) if (!allowed.has(key)||p.getAll(key).length!==1) fail("Unknown or repeated source context parameter");
  const sourceId=text(p.get("source_id"),256)!;
  const ls=p.get("limit")??"10";
  if (!/^\d+$/.test(ls)||Number(ls)<1||Number(ls)>20) fail("Source context limit must be 1-20");
  const query=new URL(url);
  query.searchParams.set("limit",ls);
  // A source analysis must see exclusions, not silently select only favored rows.
  query.searchParams.set("include_quarantined","true");
  const page=await (await queryRecords(query,env)).json() as {
    observations: Record<string,unknown>[]; next: unknown;
  };
  const nodes=page.observations.map(r=>{
    const revision=new URLSearchParams({record_id:String(r.record_id),record_sha256:String(r.record_sha256)});
    return {
      kind:"imported_observation",recordId:r.record_id,recordSha256:r.record_sha256,
      sourceId:r.source_id,studyId:r.study_id,
      anchor:{kind:"retained_record_container",objectSha256:r.evidence_sha256,locator:r.locator,
        linkValidation:"operator_supplied",primaryDocumentClosure:"not_verified"},
      material:r.material,observable:r.observable,unit:r.unit,modelId:r.model_id,
      referenceKind:r.reference_kind,observedAt:r.observed_at,reviewedAt:r.reviewed_at,
      originalRowSha256:r.original_row_sha256,
      missingFields:JSON.parse(String(r.missing_fields_json)) as string[],
      protection:"immutable_original",
      quarantined:!!r.quarantined,
      qualificationHistory:{complete:false,href:ROOT+"/qualifications?"+revision},
      originalRecordHref:ROOT+"/observation?"+revision,
    };
  });
  const context={
    schema:"lupine-source-context-v1",sourceId,nodes,next:page.next,
    scope:"one bounded page of imported projections; not a complete source analysis",
    membership:p.get("import_id")===null?"live":{importId:p.get("import_id")},
    qualificationState:"live; full history must be collected separately",
    semanticRelations:[],
    analysis:{state:"not_run",modelCalls:0,scientificValidation:"not_assessed",
      comparability:"not_assessed",calibration:"not_assessed"},
    budgets:{maxRecords:20,maxResponseBytes:262144,tokenCount:null},
  };
  // Fingerprint exactly the serialized bundle, not unseen source or review history.
  const contextJson=JSON.stringify(context);
  const response={context,contextSha256:(await digest(encoder.encode(contextJson))).hex,
    fingerprintScope:"JSON.stringify(context) UTF-8 bytes only; not a persisted snapshot"};
  if (encoder.encode(JSON.stringify(response)).length>262144) fail("Source context exceeds response budget; request fewer rows");
  return json(response);
}

/** Private projection API. Does not calculate scientific discrepancies or admit comparability. */
export async function corpusResponse(request: Request, env: Env): Promise<Response|null> {
  const url=new URL(request.url);
  if (url.pathname!==ROOT && !url.pathname.startsWith(ROOT+"/")) return null;
  const denial=await requireEvidenceOperator(request,env); if (denial) return denial;
  if (env.PRIVATE_CORPUS_ENABLED!=="true" || env.PRIVATE_EVIDENCE_ENABLED!=="true" || !env.PRIVATE_CORPUS || env.PRIVATE_CORPUS===env.LEDGER || !env.PRIVATE_EVIDENCE || env.PRIVATE_EVIDENCE===env.ARTIFACTS) return json({error:"Private corpus is not configured"},503);
  try {
    if (url.pathname.startsWith(ROOT+"/objects/")) { if(url.search) fail("Unexpected query parameters"); return await objectReceipt(request,env,url.pathname.slice((ROOT+"/objects/").length)); }
    if (url.pathname.startsWith(ROOT+"/imports/")) { if(url.search) fail("Unexpected query parameters"); return await importRecords(request,env,url.pathname.slice((ROOT+"/imports/").length)); }
    if (["/observations","/observation","/qualifications","/source-context"].some(p=>url.pathname===ROOT+p)) {
      if (request.method!=="GET") return json({error:"Method not allowed"},405);
      return url.pathname===ROOT+"/source-context" ? await sourceContext(url,env) : url.pathname===ROOT+"/observations" ? await queryRecords(url,env) : url.pathname===ROOT+"/qualifications" ? await queryQualifications(url,env) : await recordDetail(url,env);
    }
    return json({error:"Corpus route not found"},404);
  } catch (e) {
    if (e instanceof InputError) return json({error:e.message},400);
    if (e instanceof RangeError) return json({error:"Body exceeds route limit"},413);
    if (e instanceof Error && /immutable (?:corpus|evidence)/.test(e.message)) return json({error:"Immutable evidence conflict; transaction rejected"},409);
    return json({error:"Corpus operation failed; outcome may be unknown. Collect the receipt with GET; no retry performed."},503);
  }
}
