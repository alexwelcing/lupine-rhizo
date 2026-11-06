import { canonicalPublicJson, type DiscoveryPublication } from "./discoveryPublicationContracts";
import { decodePublicResearchActivity, publicActivitySha256, type PublicResearchActivity } from "./researchActivityContracts";
import { getPublicResearchActivity } from "./researchActivity";
import { database, readPublication, verifyProjection, assertCompatibleNodes, PublicationError,
  type PublicationEnv, type Database, type Projection, type PublicationNode, type PublicationEdge } from "./discoveryPublication";
import { decodeDiscoveryWithdrawal, type DiscoveryWithdrawal, type DiscoveryWithdrawalAck } from "./discoveryWithdrawalContracts";

const unavailable = () => new PublicationError("publication_unavailable", 503);
const conflict = () => new PublicationError("publication_conflict", 409);
const dependency = () => new PublicationError("publication_dependency_missing", 409);
const sorted = <T>(values:T[]) => values.sort((a,b)=>canonicalPublicJson(a)<canonicalPublicJson(b)?-1:canonicalPublicJson(a)>canonicalPublicJson(b)?1:0);
interface WithdrawalRow { id:string; publication_id:string; source_semantic_sha256:string; payload_sha256:string; record_sha256:string; projection_sha256:string; payload:string }
async function withdrawalRow(db:Database,id:string):Promise<WithdrawalRow|null> {
  return db.prepare(`SELECT id,publication_id,source_semantic_sha256,payload_sha256,record_sha256,projection_sha256,
    CASE WHEN length(CAST(payload AS BLOB))<=2048 THEN payload ELSE NULL END AS payload
    FROM public_discovery_withdrawals WHERE id=?`).bind(id).first<WithdrawalRow>();
}
async function originalPublication(db:Database,notice:DiscoveryWithdrawal):Promise<DiscoveryPublication> {
  const original=await readPublication(db,notice.publicationId);if(!original)throw dependency();
  if(original.row.record_sha256!==notice.recordSha256||original.row.evidence_sha256!==notice.evidenceSha256
    ||!original.publication.evidence.sources.some(source=>source.semanticSha256===notice.sourceSemanticSha256))throw conflict();
  await verifyProjection(db,original.publication,original.row);return original.publication;
}
async function noticeRecord(notice:DiscoveryWithdrawal,original:DiscoveryPublication):Promise<PublicResearchActivity> {
  const source=original.evidence.sources.find(item=>item.semanticSha256===notice.sourceSemanticSha256)!;
  const payloadSha256=await publicActivitySha256(canonicalPublicJson(notice));
  return decodePublicResearchActivity({schema:"lupine.public_research_activity.v1",id:notice.id,activityId:notice.id,
    evidenceKind:"workflow_repair",state:"completed",verification:"pending",
    title:("Source availability: "+original.record.title).slice(0,160).trim(),
    summary:"A cited source was withdrawn from the retained discovery feed. The original research report and its evidence remain unchanged.",
    observedAt:notice.observedAt,reviewedAt:notice.observedAt>original.record.reviewedAt?notice.observedAt:original.record.reviewedAt,
    datasets:[],findings:["The availability notice is linked to the exact original publication, public evidence and cited source identity."],
    limitations:["Feed withdrawal does not establish publisher retraction, falsity or scientific invalidation.",
      "This notice does not independently verify the source's present accessibility or the report's scientific conclusions."],
    nextStep:"Check source availability and seek a qualified replacement before relying on the affected evidence for new research.",
    sources:[{label:"Affected cited source",url:source.url}],
    hashes:[{label:"Source availability notice",sha256:payloadSha256},{label:"Original public record",sha256:notice.recordSha256},
      {label:"Original public evidence",sha256:notice.evidenceSha256}],repositoryLinks:[],releaseLinks:[],supersedes:null,correctionReason:null});
}
export function discoveryWithdrawalProjection(notice:DiscoveryWithdrawal,record:PublicResearchActivity):Projection {
  const id="publications/"+notice.id;
  const node:PublicationNode={id,type:"Source availability notice",title:record.title,description:record.summary,
    resource:"/research/activity/"+notice.id+"/evidence",tags:["source-availability","not-a-retraction"],timestamp:notice.observedAt,
    body:canonicalPublicJson({notice,meaning:record.summary,limitations:record.limitations}),sourceId:notice.id};
  return {nodes:[node],edges:sorted([
    {from:id,to:"publications/"+notice.publicationId,kind:"publication:availability-notice-for",label:"Original report preserved"},
    {from:id,to:"publication-sources/src-"+notice.sourceSemanticSha256,kind:"publication:source-withdrawn-from-feed",label:"Availability observation, not scientific retraction"},
  ])};
}
async function verifyWithdrawalProjection(db:Database,expected:Projection,id:string,digest:string):Promise<void> {
  if(await publicActivitySha256(canonicalPublicJson(expected))!==digest)throw unavailable();
  const documents=await db.prepare(`SELECT d.* FROM knowledge_documents d JOIN public_discovery_withdrawal_nodes m ON m.concept_id=d.concept_id
    WHERE m.notice_id=? ORDER BY d.concept_id LIMIT 3`).bind(id).all<Record<string,unknown>>();
  if(!documents.success)throw unavailable();
  const nodes:PublicationNode[]=documents.results.map(row=>{
    if(row.source_kind!=="public_discovery"||row.okf_version!=="0.1")throw unavailable();
    return {id:row.concept_id,type:row.type,title:row.title,description:row.description,resource:row.resource,
      tags:JSON.parse(row.tags_json as string),timestamp:row.timestamp,body:row.body_md,sourceId:row.source_id} as PublicationNode;
  });
  const edges=await db.prepare(`SELECT e.from_concept_id AS "from",e.to_concept_id AS "to",e.edge_kind AS kind,e.label
    FROM knowledge_edges e JOIN public_discovery_withdrawal_nodes m ON m.concept_id=e.from_concept_id
    WHERE m.notice_id=? AND e.edge_kind GLOB 'publication:*' LIMIT 4`).bind(id).all<PublicationEdge>();
  if(!edges.success||canonicalPublicJson({nodes:sorted(nodes),edges:sorted(edges.results)})!==canonicalPublicJson(expected))throw unavailable();
}
export async function readDiscoveryWithdrawal(db:Database,id:string) {
  const row=await withdrawalRow(db,id);if(!row)return null;
  if(typeof row.payload!=="string"||await publicActivitySha256(row.payload)!==row.payload_sha256)throw unavailable();
  let notice:DiscoveryWithdrawal;
  try{notice=await decodeDiscoveryWithdrawal(JSON.parse(row.payload));}catch{throw unavailable();}
  if(canonicalPublicJson(notice)!==row.payload||notice.id!==row.id||notice.publicationId!==row.publication_id||notice.sourceSemanticSha256!==row.source_semantic_sha256)throw unavailable();
  const original=await originalPublication(db,notice),expected=await noticeRecord(notice,original);
  const record=await getPublicResearchActivity({LEDGER:db} as PublicationEnv,id);
  if(!record||JSON.stringify(record)!==JSON.stringify(expected)||await publicActivitySha256(JSON.stringify(record))!==row.record_sha256)throw unavailable();
  const projection=discoveryWithdrawalProjection(notice,record);await verifyWithdrawalProjection(db,projection,id,row.projection_sha256);
  const sequence=await db.prepare("SELECT sequence FROM public_activity_archive_sequence WHERE record_id=?").bind(id).first<{sequence:number}>();
  const event=await db.prepare("SELECT event_id,event_kind,concept_id,summary,created_at FROM knowledge_events WHERE event_id=?")
    .bind("publication:"+id).first<Record<string,unknown>>();
  if(!sequence||!Number.isSafeInteger(sequence.sequence)||sequence.sequence<1||canonicalPublicJson(event)!==canonicalPublicJson({
    event_id:"publication:"+id,event_kind:"source-availability",concept_id:"publications/"+id,summary:record.title,created_at:record.reviewedAt}))throw unavailable();
  return {notice,record,row,projection};
}

/** Exact immutable additive notice: one D1 transaction and verified readback.
 * No old report, projection, source, timestamp or public scientific claim changes. */
export async function publishDiscoveryWithdrawal(env:PublicationEnv,input:unknown):Promise<DiscoveryWithdrawalAck> {
  const notice=await decodeDiscoveryWithdrawal(input),db=database(env),original=await originalPublication(db,notice);
  const record=await noticeRecord(notice,original),payload=canonicalPublicJson(notice),payloadSha256=await publicActivitySha256(payload),
    recordText=JSON.stringify(record),recordSha256=await publicActivitySha256(recordText),projection=discoveryWithdrawalProjection(notice,record),
    projectionSha256=await publicActivitySha256(canonicalPublicJson(projection));
  const previous=await withdrawalRow(db,notice.id),oldRecord=await getPublicResearchActivity({LEDGER:db} as PublicationEnv,notice.id);
  if(previous&&(previous.payload!==payload||previous.payload_sha256!==payloadSha256||previous.record_sha256!==recordSha256
    ||previous.projection_sha256!==projectionSha256||previous.publication_id!==notice.publicationId||previous.source_semantic_sha256!==notice.sourceSemanticSha256))throw conflict();
  if(oldRecord&&JSON.stringify(oldRecord)!==recordText)throw conflict();
  await assertCompatibleNodes(db,projection);
  const statements=[
    db.prepare(`INSERT INTO public_research_activity(id,activity_id,observed_at,reviewed_at,supersedes_id,payload_sha256,payload)
      VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING`).bind(record.id,record.activityId,record.observedAt,record.reviewedAt,null,recordSha256,recordText),
    db.prepare(`INSERT INTO public_discovery_withdrawals(id,publication_id,source_semantic_sha256,payload_sha256,record_sha256,projection_sha256,payload)
      VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING`).bind(notice.id,notice.publicationId,notice.sourceSemanticSha256,payloadSha256,recordSha256,projectionSha256,payload),
    db.prepare(`INSERT INTO knowledge_documents(concept_id,type,title,description,resource,tags_json,timestamp,body_md,source_kind,source_id,okf_version,created_at,updated_at)
      SELECT json_extract(value,'$.id'),json_extract(value,'$.type'),json_extract(value,'$.title'),json_extract(value,'$.description'),
      json_extract(value,'$.resource'),json_extract(value,'$.tags'),json_extract(value,'$.timestamp'),json_extract(value,'$.body'),
      'public_discovery',json_extract(value,'$.sourceId'),'0.1',?,? FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`)
      .bind(record.reviewedAt,record.reviewedAt,canonicalPublicJson(projection.nodes)),
    db.prepare(`INSERT INTO public_discovery_withdrawal_nodes(notice_id,concept_id) SELECT ?,json_extract(value,'$.id') FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`)
      .bind(notice.id,canonicalPublicJson(projection.nodes)),
    db.prepare(`INSERT INTO knowledge_edges(from_concept_id,to_concept_id,edge_kind,label,created_at)
      SELECT json_extract(value,'$.from'),json_extract(value,'$.to'),json_extract(value,'$.kind'),json_extract(value,'$.label'),?
      FROM json_each(?) WHERE true ON CONFLICT DO NOTHING`).bind(record.reviewedAt,canonicalPublicJson(projection.edges)),
    db.prepare(`INSERT INTO knowledge_events(event_id,event_kind,concept_id,summary,created_at) VALUES(?,'source-availability',?,?,?) ON CONFLICT DO NOTHING`)
      .bind("publication:"+notice.id,"publications/"+notice.id,record.title,record.reviewedAt),
  ];
  try{const results=await db.batch(statements);if(results.some(result=>!result.success))throw unavailable();}
  catch{const saved=await withdrawalRow(db,notice.id).catch(()=>null);if(saved&&saved.payload!==payload)throw conflict();
    await assertCompatibleNodes(db,projection);throw unavailable();}
  const saved=await readDiscoveryWithdrawal(db,notice.id);
  if(!saved||saved.row.payload_sha256!==payloadSha256)throw unavailable();
  return {schema:"lupine.discovery_source_withdrawal_ack.v1",id:notice.id,payloadSha256,duplicate:previous!==null,knowledgeProjected:true};
}
