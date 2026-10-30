import type { Env } from "../types";
import { getPublicResearchActivity } from "./researchActivity";
import { publicActivitySha256 } from "./researchActivityContracts";
import { canonicalPublicJson, decodeDiscoveryEvidence, decodeDiscoveryPublication, DISCOVERY_ENVELOPE_MAX_BYTES,
  publicationIdSchema, type DiscoveryEvidence, type DiscoveryPublication, type DiscoveryPublicationAck } from "./discoveryPublicationContracts";

type Database = Pick<D1Database, "prepare" | "batch">;
type PublicationEnv = Pick<Env, "LEDGER">;
export class PublicationError extends Error {
  constructor(readonly code: "publication_conflict" | "publication_dependency_missing" | "publication_unavailable", readonly status: number) { super(code); }
}
const conflict = () => new PublicationError("publication_conflict", 409);
const unavailable = () => new PublicationError("publication_unavailable", 503);
const dependency = () => new PublicationError("publication_dependency_missing", 409);
function database(env: PublicationEnv): Database {
  // First read is primary; the same D1 session joins readback to this write.
  const db = env.LEDGER as D1Database & { withSession?: (constraint: string) => Database };
  return db.withSession ? db.withSession("first-primary") : db;
}
export interface PublicationNode {
  id: string; type: string; title: string; description: string | null; resource: string | null;
  tags: string[]; timestamp: string | null; body: string; sourceId: string;
}
export interface PublicationEdge { from: string; to: string; kind: string; label: string | null }
interface Projection { nodes: PublicationNode[]; edges: PublicationEdge[] }
interface EvidenceRow { publication_id: string; evidence_sha256: string; record_sha256: string; projection_sha256: string; payload: string }
const reportNode = (id: string) => "publications/" + id;
const topicNode = (id: string) => "publication-topics/" + id;
const sourceNode = (id: string) => "publication-sources/" + id;
const sorted = <T>(values: T[]) => values.sort((a, b) => {
  const left=canonicalPublicJson(a),right=canonicalPublicJson(b);return left<right?-1:left>right?1:0;
});

/** Deterministic immutable projection into Rhizo's existing knowledge tables. */
export function discoveryProjection(publication: DiscoveryPublication): Projection {
  const { record, evidence: e } = publication, root = reportNode(record.id), nodes: PublicationNode[] = [], edges: PublicationEdge[] = [];
  const add = (id: string, type: string, title: string, body: unknown, sourceId: string, timestamp: string | null = e.provenance.completedAt,
    resource: string | null = "/research/activity/" + record.id + "/evidence", tags: string[] = []) => {
    nodes.push({ id, type, title, description: null, resource, tags, timestamp, body: canonicalPublicJson(body), sourceId });
  };
  const edge = (from: string, to: string, kind: string, label: string | null = null) => edges.push({ from, to, kind: "publication:" + kind, label });
  const provenance = (from: string, refs: string[]) => refs.forEach(ref => edge(from, sourceNode(ref), "derived-from"));
  add(root, "Published discovery report", record.title, { summary: e.report.summary, role: e.report.role, provenance: e.provenance,
    empiricalValidation: false, externalPeerReviewed: false, reviewBasis: e.reviewBasis, limitations: record.limitations }, record.id,
    e.provenance.completedAt, "/research/activity/" + record.id + "/evidence", [e.report.role, "automated-contract-validation"]);
  add(topicNode(e.topic.id), "Discovery topic", e.topic.question, { question: e.topic.question, parentTopicId: e.topic.parentTopicId }, e.topic.id,
    null, null);
  edge(root, topicNode(e.topic.id), "addresses");
  for (const source of e.sources) {
    add(sourceNode(source.reference), "Published source", source.title, source, source.reference, null, source.url);
    edge(root, sourceNode(source.reference), "derived-from");
  }
  for (const prior of e.priorReports) edge(root, reportNode(prior.publicationId), "follows-role", prior.role);
  if (e.topic.parentPublicationId) {
    edge(root, reportNode(e.topic.parentPublicationId), "follows-publication");
    edge(root, reportNode(e.topic.parentPublicationId)+"/questions/"+e.topic.parentQuestionIndex, "follows-question");
  }
  e.report.claims.forEach((claim, i) => {
    const id = root + "/claims/" + i;
    add(id, claim.kind === "published-claim" ? "Published source claim" : "Agent hypothesis", claim.statement, claim, record.id);
    edge(root, id, "contains-claim"); provenance(id, claim.sourceReferences);
  });
  e.report.concepts.forEach((concept, i) => {
    const id = root + "/concepts/" + i;
    add(id, "Research concept", concept.name, concept, record.id, e.provenance.completedAt, null, [concept.kind]);
    edge(root, id, "mentions-concept"); provenance(id, concept.sourceReferences);
  });
  e.report.assessments.forEach((assessment, i) => {
    const id = root + "/assessments/" + i, prior = e.priorReports.find(item => item.role === assessment.targetRole)!;
    add(id, "Claim assessment", assessment.reason, assessment, record.id);
    edge(root, id, "contains-assessment");
    edge(id, reportNode(prior.publicationId) + "/claims/" + assessment.claimIndex, assessment.verdict);
    provenance(id, assessment.sourceReferences);
  });
  e.report.questions.forEach((question, i) => {
    const id = root + "/questions/" + i;
    add(id, "Research question", question, { question, query: e.report.queries[i] ?? null }, record.id);
    edge(root, id, "raises-question");
  });
  return { nodes: sorted(nodes), edges: sorted(edges) };
}

async function evidenceRow(db: Database, id: string): Promise<EvidenceRow | null> {
  return db.prepare(`SELECT publication_id,evidence_sha256,record_sha256,projection_sha256,
    CASE WHEN length(CAST(payload AS BLOB))<=32768 THEN payload ELSE NULL END AS payload
    FROM public_discovery_evidence WHERE publication_id=?`).bind(id).first<EvidenceRow>();
}
async function readPublication(db: Database, id: string): Promise<{ publication: DiscoveryPublication; row: EvidenceRow } | null> {
  const row = await evidenceRow(db, id);
  if (!row) return null;
  if (typeof row.payload !== "string" || await publicActivitySha256(row.payload) !== row.evidence_sha256) throw unavailable();
  const record = await getPublicResearchActivity({ LEDGER: db } as PublicationEnv, id);
  if (!record || await publicActivitySha256(JSON.stringify(record)) !== row.record_sha256) throw unavailable();
  try {
    const evidence = decodeDiscoveryEvidence(JSON.parse(row.payload));
    if (canonicalPublicJson(evidence) !== row.payload) throw unavailable();
    const publication = await decodeDiscoveryPublication({ schema: "lupine.discovery_publication.v1", policy: "accepted-discovery-public/v1",
      producer: "lupine-research-team-v02", record, evidence });
    return { publication, row };
  } catch { throw unavailable(); }
}
async function validateLineage(db: Database, publication: DiscoveryPublication): Promise<void> {
  const e = publication.evidence;
  for (const [index,prior] of e.priorReports.entries()) {
    const saved = await readPublication(db, prior.publicationId);
    if (!saved) throw dependency();
    const p = saved.publication.evidence;
    if (p.report.role !== prior.role || canonicalPublicJson(p.topic)!==canonicalPublicJson(e.topic) ||
        canonicalPublicJson(p.priorReports)!==canonicalPublicJson(e.priorReports.slice(0,index)) || p.provenance.completedAt > e.provenance.completedAt ||
        e.report.assessments.some(assessment => assessment.targetRole === prior.role && assessment.claimIndex >= p.report.claims.length)) throw conflict();
    await verifyProjection(db, saved.publication, saved.row);
  }
  if (e.topic.parentPublicationId) {
    const parent = await readPublication(db, e.topic.parentPublicationId);
    if (!parent) throw dependency();
    const p = parent.publication.evidence;
    if (p.topic.id !== e.topic.parentTopicId || p.report.role !== "principal" || p.provenance.completedAt > e.provenance.completedAt ||
        p.report.questions[e.topic.parentQuestionIndex!]!==e.topic.question) throw conflict();
    await verifyProjection(db, parent.publication, parent.row);
  }
}
async function verifyProjection(db: Database, publication: DiscoveryPublication, row: EvidenceRow): Promise<Projection> {
  const expected = discoveryProjection(publication);
  if (await publicActivitySha256(canonicalPublicJson(expected)) !== row.projection_sha256) throw unavailable();
  const documents = await db.prepare(`SELECT d.* FROM knowledge_documents d JOIN public_discovery_nodes m ON m.concept_id=d.concept_id
    WHERE m.publication_id=? ORDER BY d.concept_id LIMIT 101`).bind(publication.record.id).all<Record<string, unknown>>();
  if (!documents.success) throw unavailable();
  let nodes: PublicationNode[];
  try { nodes = documents.results.map(d => {
    if (d.source_kind !== "public_discovery" || d.okf_version !== "0.1") throw unavailable();
    return { id: d.concept_id, type: d.type, title: d.title, description: d.description, resource: d.resource,
      tags: JSON.parse(d.tags_json as string), timestamp: d.timestamp, body: d.body_md, sourceId: d.source_id } as PublicationNode;
  }); } catch { throw unavailable(); }
  const outgoing = await db.prepare(`SELECT e.from_concept_id AS "from",e.to_concept_id AS "to",e.edge_kind AS kind,e.label
    FROM knowledge_edges e JOIN public_discovery_nodes m ON m.concept_id=e.from_concept_id
    WHERE m.publication_id=? AND e.edge_kind GLOB 'publication:*' LIMIT 201`).bind(publication.record.id).all<PublicationEdge>();
  if (!outgoing.success || canonicalPublicJson({ nodes: sorted(nodes), edges: sorted(outgoing.results) }) !== canonicalPublicJson(expected)) throw unavailable();
  return expected;
}
async function assertCompatibleNodes(db: Database, projection: Projection): Promise<void> {
  const rows=await db.prepare(`SELECT * FROM knowledge_documents WHERE concept_id IN
    (SELECT json_extract(value,'$.id') FROM json_each(?)) LIMIT 101`).bind(canonicalPublicJson(projection.nodes)).all<Record<string,unknown>>();
  if(!rows.success)throw unavailable();
  for(const row of rows.results){
    const expected=projection.nodes.find(node=>node.id===row.concept_id);
    let actual:PublicationNode;
    try{actual={id:row.concept_id,type:row.type,title:row.title,description:row.description,resource:row.resource,
      tags:JSON.parse(row.tags_json as string),timestamp:row.timestamp,body:row.body_md,sourceId:row.source_id} as PublicationNode;}
    catch{throw conflict();}
    if(row.source_kind!=="public_discovery"||row.okf_version!=="0.1"||canonicalPublicJson(actual)!==canonicalPublicJson(expected))throw conflict();
  }
}

/** One transactional D1 batch; retries repair only the exact immutable projection. */
export async function publishDiscovery(env: PublicationEnv, input: unknown): Promise<DiscoveryPublicationAck> {
  const publication = await decodeDiscoveryPublication(input), { record, evidence } = publication, db = database(env);
  const payload = JSON.stringify(record), recordSha256 = await publicActivitySha256(payload);
  const evidenceText = canonicalPublicJson(evidence), evidenceSha256 = await publicActivitySha256(evidenceText);
  const projection = discoveryProjection(publication), projectionSha256 = await publicActivitySha256(canonicalPublicJson(projection));
  const previous = await evidenceRow(db, record.id);
  const previousRecord = await getPublicResearchActivity({LEDGER:db} as PublicationEnv,record.id);
  if(previousRecord && await publicActivitySha256(JSON.stringify(previousRecord))!==recordSha256)throw conflict();
  if (previous && (previous.payload !== evidenceText || previous.record_sha256 !== recordSha256 || previous.evidence_sha256 !== evidenceSha256 ||
      previous.projection_sha256 !== projectionSha256)) throw conflict();
  await validateLineage(db, publication);
  await assertCompatibleNodes(db,projection);
  const statements = [
    db.prepare(`INSERT INTO public_research_activity(id,activity_id,observed_at,reviewed_at,supersedes_id,payload_sha256,payload)
      VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING`).bind(record.id, record.activityId, record.observedAt, record.reviewedAt, null, recordSha256, payload),
    db.prepare(`INSERT INTO public_discovery_evidence(publication_id,evidence_sha256,record_sha256,projection_sha256,payload)
      VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING`).bind(record.id,evidenceSha256,recordSha256,projectionSha256,evidenceText),
    db.prepare(`INSERT INTO knowledge_documents(concept_id,type,title,description,resource,tags_json,timestamp,body_md,source_kind,source_id,okf_version,created_at,updated_at)
      SELECT json_extract(value,'$.id'),json_extract(value,'$.type'),json_extract(value,'$.title'),json_extract(value,'$.description'),
      json_extract(value,'$.resource'),json_extract(value,'$.tags'),json_extract(value,'$.timestamp'),json_extract(value,'$.body'),
      'public_discovery',json_extract(value,'$.sourceId'),'0.1',?,? FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`)
      .bind(record.reviewedAt,record.reviewedAt,canonicalPublicJson(projection.nodes)),
    db.prepare(`INSERT INTO public_discovery_nodes(publication_id,concept_id) SELECT ?,json_extract(value,'$.id') FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`)
      .bind(record.id,canonicalPublicJson(projection.nodes)),
    db.prepare(`INSERT INTO knowledge_edges(from_concept_id,to_concept_id,edge_kind,label,created_at)
      SELECT json_extract(value,'$.from'),json_extract(value,'$.to'),json_extract(value,'$.kind'),json_extract(value,'$.label'),?
      FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`).bind(record.reviewedAt,canonicalPublicJson(projection.edges)),
    db.prepare(`INSERT INTO knowledge_events(event_id,event_kind,concept_id,summary,created_at) VALUES(?,'publication',?,?,?) ON CONFLICT DO NOTHING`)
      .bind("publication:" + record.id,reportNode(record.id),record.title,record.reviewedAt),
  ];
  try {
    const results = await db.batch(statements);
    if (results.some(result => !result.success)) throw unavailable();
  } catch (error) {
    if (error instanceof PublicationError) throw error;
    // Never expose SQL, stored data or private error details. A conflicting
    // immutable identity is distinct from unknown storage completion.
    const existing = await evidenceRow(db, record.id).catch(() => null);
    if (existing && (existing.payload !== evidenceText || existing.record_sha256 !== recordSha256)) throw conflict();
    await assertCompatibleNodes(db,projection);
    throw unavailable();
  }
  const saved = await readPublication(db, record.id);
  if (!saved || saved.row.evidence_sha256 !== evidenceSha256 || saved.row.record_sha256 !== recordSha256) throw unavailable();
  await verifyProjection(db,saved.publication,saved.row);
  return { schema: "lupine.discovery_publication_ack.v1", id: record.id, activityId: record.activityId,
    recordSha256,evidenceSha256,duplicate: previous !== null,knowledgeProjected:true };
}

const publicHeaders = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Cache-Control": "public, max-age=30",
  "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Content-Type": "application/json; charset=utf-8" };
const response = (value: unknown, status = 200) => new Response(canonicalPublicJson(value), { status, headers: { ...publicHeaders, ...(status >= 400 ? { "Cache-Control": "no-store" } : {}) } });
function cursor(params: URLSearchParams,key: string,fallback?: number): number | undefined {
  const values=params.getAll(key); if(values.length>1 || values.length && !/^(0|[1-9]\d*)$/.test(values[0])) throw Error();
  const n=values.length?Number(values[0]):fallback; if(n!==undefined&&!Number.isSafeInteger(n))throw Error(); return n;
}
export async function discoveryPublicationPublicResponse(request: Request, env: PublicationEnv): Promise<Response | null> {
  const url = new URL(request.url), match = /^\/research\/activity\/([^/]+)\/evidence$/.exec(url.pathname);
  if (!match && url.pathname !== "/research/knowledge") return null;
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:publicHeaders});
  if (request.method !== "GET") return response({error:"Use GET"},405);
  if (match && (!publicationIdSchema.safeParse(match[1]).success || url.search)) return response({error:"Publication not found"},404);
  try {
    const db=database(env);
    if (match) {
      const saved=await readPublication(db,match[1]); if(!saved)return response({error:"Publication not found"},404);
      await verifyProjection(db,saved.publication,saved.row);
      return new Response(saved.row.payload,{headers:publicHeaders});
    }
    let after:number,limit:number,snapshot:number|undefined;
    try { if([...url.searchParams.keys()].some(key=>!["after","snapshot","limit"].includes(key)))throw Error();
      after=cursor(url.searchParams,"after",0)!;limit=cursor(url.searchParams,"limit",10)!;snapshot=cursor(url.searchParams,"snapshot");
      if(limit<1||limit>10||snapshot!==undefined&&snapshot<after)throw Error();
    } catch { return response({error:"Invalid knowledge cursor or limit"},400); }
    const maximum=await db.prepare("SELECT COALESCE(MAX(sequence),0) AS maximum FROM public_activity_archive_sequence").first<{maximum:number}>();
    if(!maximum||!Number.isSafeInteger(maximum.maximum))throw unavailable();
    const upper=snapshot??maximum.maximum;if(upper>maximum.maximum||after>upper)return response({error:"Invalid knowledge cursor"},400);
    const selected=await db.prepare(`SELECT s.sequence,e.publication_id FROM public_activity_archive_sequence s
      JOIN public_discovery_evidence e ON e.publication_id=s.record_id WHERE s.sequence>? AND s.sequence<=? ORDER BY s.sequence LIMIT ?`)
      .bind(after,upper,limit+1).all<{sequence:number;publication_id:string}>();
    if(!selected.success)throw unavailable();
    const nodes=new Map<string,PublicationNode>(),edges=new Map<string,PublicationEdge>(),hashes:unknown[]=[],publicationIds:string[]=[];
    for(const item of selected.results){
      const saved=await readPublication(db,item.publication_id);if(!saved)throw unavailable();
      const projection=await verifyProjection(db,saved.publication,saved.row);
      // Verify the lookahead too; do not claim a successful partial page around corruption.
      if(publicationIds.length===limit)continue;
      publicationIds.push(item.publication_id);for(const node of projection.nodes)nodes.set(node.id,node);for(const edge of projection.edges)edges.set(canonicalPublicJson(edge),edge);
      hashes.push({id:item.publication_id,recordSha256:saved.row.record_sha256,evidenceSha256:saved.row.evidence_sha256,projectionSha256:saved.row.projection_sha256});
    }
    const more=selected.results.length>limit;
    return response({schema:"lupine.public_discovery_knowledge.v1",publicationIds,nodes:sorted([...nodes.values()]),edges:sorted([...edges.values()]),hashes,
      cursor:{after,snapshot:upper,nextAfter:more?selected.results[limit-1].sequence:null},coverage:{complete:!more,returned:publicationIds.length}});
  } catch { return response({error:"Public discovery knowledge is unavailable",code:"publication_unavailable"},503); }
}

/** Named service entrypoint calls this; the public default Worker never does. */
export async function discoveryPublicationServiceResponse(request: Request, env: PublicationEnv): Promise<Response> {
  const url=new URL(request.url), headers={"Content-Type":"application/json","Cache-Control":"no-store"};
  const reply=(body:unknown,status:number)=>new Response(JSON.stringify(body),{status,headers});
  if(url.pathname!=="/publish"||url.search)return reply({error:"Not found"},404);
  if(request.method!=="POST")return reply({error:"Use POST"},405);
  if(request.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase()!=="application/json")return reply({error:"Use application/json"},415);
  let input:unknown;
  try {
    const reader=request.body?.getReader();if(!reader)throw Error();const chunks:Uint8Array[]=[];let size=0;
    while(true){const item=await reader.read();if(item.done)break;size+=item.value.byteLength;
      if(size>DISCOVERY_ENVELOPE_MAX_BYTES){void reader.cancel().catch(()=>{});return reply({error:"Publication too large"},413);}chunks.push(item.value);}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    const text=new TextDecoder("utf-8",{fatal:true,ignoreBOM:false}).decode(bytes);input=JSON.parse(text);
    // Producer sends the fixed canonical envelope. This also rejects duplicate
    // object keys and alternate serialized meanings before any database access.
    if(canonicalPublicJson(input)!==text)throw Error();
    await decodeDiscoveryPublication(input);
  } catch {return reply({error:"Invalid public publication",code:"publication_invalid"},400);}
  try {return reply(await publishDiscovery(env,input),200);}
  catch(error){return error instanceof PublicationError?reply({error:error.code,code:error.code},error.status):reply({error:"Publication storage unavailable",code:"publication_unavailable"},503);}
}
