import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error Node-only SQLite test harness.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Node-only migration fixture reader.
import { readFileSync } from "node:fs";
import type { Env } from "../../types";
import { canonicalPublicJson, decodeDiscoveryPublication, DISCOVERY_ROLES, isDiscoveryEvidenceText, type DiscoveryEvidence, type DiscoveryPublication } from "../discoveryPublicationContracts";
import { discoveryProjection, discoveryPublicationPublicResponse, discoveryPublicationServiceResponse, publishDiscovery } from "../discoveryPublication";
import { archivePublicResearchActivity, researchActivityResponse } from "../researchActivity";
import { isPublicText, publicActivitySha256 } from "../researchActivityContracts";

const base=(import.meta as ImportMeta & {url:string}).url;
const migrations=["0021_public_research_activity.sql","0023_public_activity_archive.sql","0024_discovery_publication.sql"]
  .map(name=>readFileSync(new URL("../../../migrations/"+name,base),"utf8"));
const databases:InstanceType<typeof DatabaseSync>[]=[];
afterEach(()=>{for(const db of databases.splice(0))db.close();});
function harness(){
  const db=new DatabaseSync(":memory:");databases.push(db);db.exec("PRAGMA foreign_keys=ON");for(const sql of migrations)db.exec(sql);
  const queries:string[]=[];const hooks:{failBatchAt?:number;failReadback?:boolean;afterBatch?:()=>void}={};let batchCommitted=false;
  type Stmt=D1PreparedStatement & {sql:string;values:unknown[]};
  function statement(sql:string,values:unknown[]=[]):Stmt{return {
    sql,values,bind:(...bound:unknown[])=>statement(sql,[...values,...bound]),
    first:async()=>{if(batchCommitted&&hooks.failReadback)throw Error("simulated lost readback");return db.prepare(sql).get(...values)??null;},
    all:async()=>({success:true,results:db.prepare(sql).all(...values),meta:{}}),
    run:async()=>({success:true,results:[],meta:{changes:Number(db.prepare(sql).run(...values).changes)}}),
  } as unknown as Stmt;}
  const ledger={prepare:(sql:string)=>{queries.push(sql);return statement(sql);},batch:async(items:Stmt[])=>{
    db.exec("BEGIN");try{const results=[];for(const [i,item]of items.entries()){if(hooks.failBatchAt===i)throw Error("simulated storage failure");results.push(await item.run());}
      db.exec("COMMIT");batchCommitted=true;hooks.afterBatch?.();return results;
    }catch(error){db.exec("ROLLBACK");throw error;}
  }};
  const env={LEDGER:ledger} as unknown as Env;
  const scalar=(sql:string)=>Number(Object.values(db.prepare(sql).get()!)[0]);
  return {db,env,queries,hooks,scalar};
}
const hash=(n:number)=>n.toString(16).padStart(64,"0");
async function publication(index=0,priorReports:DiscoveryEvidence["priorReports"]=[],topicSeed=80):Promise<DiscoveryPublication>{
  const archiveSha256=hash(index+1),id="discovery-"+archiveSha256,at=`2026-10-01T10:0${index}:00.000Z`;
  const evidence:DiscoveryEvidence={schema:"lupine.public_discovery_report.v1",policy:"accepted-discovery-public/v1",
    topic:{id:"topic-"+hash(topicSeed),question:"Which evidence tests the proposed material effect?",parentTopicId:null,parentPublicationId:null,parentQuestionIndex:null},
    report:{schema:"lupine-discovery-report/v1",role:DISCOVERY_ROLES[index],summary:"The publication motivates a bounded hypothesis with missing experimental controls.",
      claims:[{statement:"The supplied publication reports a material association.",sourceReferences:["src-"+hash(90)],kind:"published-claim"}],
      concepts:[{name:"CrCoNi",kind:"material",sourceReferences:["src-"+hash(90)]}],
      assessments:index?[{targetRole:"evidence",claimIndex:0,verdict:"inconclusive",reason:"No independent experimental control was supplied.",sourceReferences:["src-"+hash(90)]}]:[],
      questions:["Which independent controls would distinguish the explanations?"],queries:["material controls"],disposition:"advance"},
    sources:[{reference:"src-"+hash(90),semanticSha256:hash(90),title:"A public materials paper",url:"https://arxiv.org/abs/2401.01234"}],priorReports,
    provenance:{provider:"minimax",model:"MiniMax-M3.1-Flash",modelIdentity:"controller-reported",completedAt:at,outputSha256:hash(91),receiptSha256:hash(92),archiveSha256},
    empiricalValidation:false,externalPeerReviewed:false,reviewBasis:"automated-contract-validation"};
  const record={schema:"lupine.public_research_activity.v1" as const,id,activityId:id,evidenceKind:"research_cycle" as const,state:"completed" as const,
    verification:"pending" as const,title:"Completed evidence report",summary:evidence.report.summary,observedAt:at,reviewedAt:at,datasets:[],
    findings:[evidence.report.claims[0].statement],limitations:["Automated contract checks are not empirical validation or external peer review.","Private archive commitments do not provide public raw-output reproducibility."],
    nextStep:evidence.report.questions[0],sources:[{label:"Public paper",url:evidence.sources[0].url}],
    hashes:[{label:"Public evidence",sha256:await publicActivitySha256(canonicalPublicJson(evidence))}],repositoryLinks:[],releaseLinks:[],supersedes:null,correctionReason:null};
  return {schema:"lupine.discovery_publication.v1",policy:"accepted-discovery-public/v1",producer:"lupine-research-team-v02",record,evidence};
}
async function repin(value:DiscoveryPublication){value.record.hashes[0].sha256=await publicActivitySha256(canonicalPublicJson(value.evidence));return value;}
const serviceRequest=(value:unknown,path="/publish")=>new Request("https://receiver.internal"+path,{method:"POST",headers:{"Content-Type":"application/json"},body:canonicalPublicJson(value)});
const publicRequest=(path:string)=>new Request("https://glim-think.example.org"+path);

describe("public discovery contract",()=>{
  it("retains one exact scientific token without relaxing ordinary paths or activity-v1 text",async()=>{
    const p=await publication();p.evidence.report.summary="Compare the KOKKOS/GPU/OPENMP package family.";await repin(p);
    expect((await decodeDiscoveryPublication(p)).evidence.report.summary).toBe(p.evidence.report.summary);
    expect(isPublicText(p.evidence.report.summary)).toBe(false);
    p.record.summary=p.evidence.report.summary;await expect(decodeDiscoveryPublication(p)).rejects.toThrow();
    for(const text of ["KOKKOS/GPU/OPENMP","The KOKKOS/GPU/OPENMP.","Use (KOKKOS/GPU/OPENMP), then compare."])
      expect(isDiscoveryEvidenceText(text),text).toBe(true);
    for(const text of ["work/KOKKOS/GPU/OPENMP","/KOKKOS/GPU/OPENMP","KOKKOS/GPU/OPENMP/private","KOKKOS/GPU/OPENMP.txt",
      "xKOKKOS/GPU/OPENMP","KOKKOS/GPU/OPENMPx","αKOKKOS/GPU/OPENMP","KOKKOS/GPU/OPENMPα","KOKKOS/GPU/OPENMP-other",
      "kokkos/gpu/openmp","OTHER/GPU/OPENMP","KOKKOS/GPU/OPENMP and work/private/file","KOKKOS/GPU/OPENMP user@example.org"])
      expect(isDiscoveryEvidenceText(text),text).toBe(false);
  });
  it("pins the exact canonical evidence, identity, source and model attribution",async()=>{
    const p=await publication();expect(await decodeDiscoveryPublication(p)).toEqual(p);
    for(const mutate of [(v:DiscoveryPublication)=>{v.record.hashes[0].sha256=hash(0);},(v:DiscoveryPublication)=>{v.record.id="discovery-"+hash(15);},
      (v:DiscoveryPublication)=>{v.record.verification="source_checked";},(v:DiscoveryPublication)=>{v.record.sources=[];},
      (v:DiscoveryPublication)=>{v.evidence.sources[0].reference="src-"+hash(99);},(v:DiscoveryPublication)=>{v.evidence.report.claims[0].sourceReferences=["src-"+hash(99)];}]){
      const bad=structuredClone(p);mutate(bad);await expect(decodeDiscoveryPublication(bad)).rejects.toThrow();}
  });
  it.each(["/Users/person/private.txt","user@example.org","Bearer abcdefghijklmno","work/private/result.txt","<script>bad</script>","private\nsecond line"])("quarantines unsafe report text %s",async text=>{
    const p=await publication();p.evidence.report.claims[0].statement=text;await repin(p);await expect(decodeDiscoveryPublication(p)).rejects.toThrow();
  });
  it("rejects unknown private fields, source credentials and descriptor access without evaluation",async()=>{
    const p=await publication();let called=false;const bad={...p};Object.defineProperty(bad,"evidence",{get(){called=true;return p.evidence;}});
    await expect(decodeDiscoveryPublication(bad)).rejects.toThrow();expect(called).toBe(false);
    await expect(decodeDiscoveryPublication({...p,privatePrompt:"hidden"})).rejects.toThrow();
    p.evidence.sources[0].url="https://arxiv.org/a?token=secret";await repin(p);await expect(decodeDiscoveryPublication(p)).rejects.toThrow();
  });
});

describe("atomic publication and existing knowledge graph",()=>{
  it("interoperates with all eight actual backfill projections including exact child question and scientific token",async()=>{
    const h=harness(),ids=["10ca49d0","c30e4536","4d7efdc8","eded7c5f","a01e7f49","7cdb95c9","82c5f7c9","292d0f6f"];
    const pending=ids.map(id=>JSON.parse(readFileSync(new URL(`./fixtures/discovery-publication-backfill-20261030-${id}.json`,base),"utf8")) as DiscoveryPublication);
    const published=new Set<string>();let scientificToken=false;
    while(pending.length){
      const index=pending.findIndex(p=>p.evidence.priorReports.every(prior=>published.has(prior.publicationId))&&
        (!p.evidence.topic.parentPublicationId||published.has(p.evidence.topic.parentPublicationId)));
      expect(index,"Every backfill dependency must be available in the finite fixture set").toBeGreaterThanOrEqual(0);
      const [p]=pending.splice(index,1),ack=await publishDiscovery(h.env,p);published.add(ack.id);
      const response=(await discoveryPublicationPublicResponse(publicRequest(`/research/activity/${p.record.id}/evidence`),h.env))!;
      const body=await response.text();expect(response.status).toBe(200);expect(await publicActivitySha256(body)).toBe(ack.evidenceSha256);
      if(body.includes("KOKKOS/GPU/OPENMP"))scientificToken=true;
    }
    expect(published.size).toBe(8);expect(scientificToken).toBe(true);
    expect(h.scalar("SELECT count(*) FROM knowledge_edges WHERE edge_kind='publication:follows-question'")).toBeGreaterThan(0);
  });
  it("interoperates with all four actual accepted producer projections and exact retries",async()=>{
    const h=harness();
    for(let i=0;i<4;i++){
      const p=JSON.parse(readFileSync(new URL(`./fixtures/discovery-publication-accepted-20261030-${i}.json`,base),"utf8"));
      const accepted=await discoveryPublicationServiceResponse(serviceRequest(p),h.env);
      expect(accepted.status,await accepted.clone().text()).toBe(200);
      const ack=await accepted.json() as any;expect(ack.id).toBe(p.record.id);
      expect(ack.evidenceSha256).toBe(p.record.hashes.find((item:any)=>item.label==="Public evidence").sha256);
      const read=(await discoveryPublicationPublicResponse(publicRequest(`/research/activity/${p.record.id}/evidence`),h.env))!;
      expect(await publicActivitySha256(await read.text())).toBe(ack.evidenceSha256);
      expect((await publishDiscovery(h.env,p)).duplicate).toBe(true);
    }
    expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(4);
  });
  it("commits record, evidence, archive sequence and real knowledge nodes together, then reads back",async()=>{
    const h=harness(),p=await publication(),ack=await publishDiscovery(h.env,p);
    expect(ack).toMatchObject({schema:"lupine.discovery_publication_ack.v1",id:p.record.id,duplicate:false,knowledgeProjected:true});
    expect(h.scalar("SELECT count(*) FROM public_research_activity")).toBe(1);expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(1);
    expect(h.scalar("SELECT count(*) FROM knowledge_documents")).toBe(discoveryProjection(p).nodes.length);
    expect(h.scalar("SELECT count(*) FROM knowledge_edges")).toBe(discoveryProjection(p).edges.length);
    expect((await archivePublicResearchActivity(h.env)).records[0].id).toBe(p.record.id);
    expect(h.queries.some(sql=>/workspace_research|FROM claims|FROM hypotheses/.test(sql))).toBe(false);
  });
  it("identical retries preserve all counts and timestamps; changed same-ID evidence conflicts",async()=>{
    const h=harness(),p=await publication();await publishDiscovery(h.env,p);
    const before=h.db.prepare("SELECT * FROM knowledge_documents ORDER BY concept_id").all();
    expect((await publishDiscovery(h.env,p)).duplicate).toBe(true);expect(h.scalar("SELECT count(*) FROM public_activity_archive_sequence")).toBe(1);
    expect(h.db.prepare("SELECT * FROM knowledge_documents ORDER BY concept_id").all()).toEqual(before);
    p.evidence.report.summary="Changed content under an existing identity.";await repin(p);
    await expect(publishDiscovery(h.env,p)).rejects.toMatchObject({code:"publication_conflict"});
  });
  it("rolls every table back when a transaction step fails",async()=>{
    const h=harness();h.hooks.failBatchAt=4;await expect(publishDiscovery(h.env,await publication())).rejects.toMatchObject({code:"publication_unavailable"});
    for(const table of ["public_research_activity","public_discovery_evidence","public_activity_archive_sequence","knowledge_documents","public_discovery_nodes","knowledge_edges"])
      expect(h.scalar("SELECT count(*) FROM "+table)).toBe(0);
  });
  it("never acknowledges uncertain readback; exact retry reconciles the committed data",async()=>{
    const h=harness(),p=await publication();h.hooks.failReadback=true;await expect(publishDiscovery(h.env,p)).rejects.toThrow();
    expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(1);h.hooks.failReadback=false;
    expect((await publishDiscovery(h.env,p)).duplicate).toBe(true);
  });
  it("repairs a missing projection on exact duplicate without changing immutable evidence",async()=>{
    const h=harness(),p=await publication();await publishDiscovery(h.env,p);
    h.db.exec("DROP TRIGGER publication_edges_delete; DELETE FROM knowledge_edges;");h.db.exec(migrations[2]);
    const before=h.db.prepare("SELECT * FROM public_discovery_evidence").all();
    expect((await discoveryPublicationPublicResponse(publicRequest(`/research/activity/${p.record.id}/evidence`),h.env))?.status).toBe(503);
    expect((await publishDiscovery(h.env,p)).duplicate).toBe(true);expect(h.db.prepare("SELECT * FROM public_discovery_evidence").all()).toEqual(before);
    expect(h.scalar("SELECT count(*) FROM knowledge_edges")).toBe(discoveryProjection(p).edges.length);
  });
  it("rejects missing priors, wrong topic and invalid claim target; commits exact cross-publication assessments",async()=>{
    const h=harness(),first=await publication(),second=await publication(1,[{role:"evidence",publicationId:first.record.id}]);
    await expect(publishDiscovery(h.env,second)).rejects.toMatchObject({code:"publication_dependency_missing"});await publishDiscovery(h.env,first);
    const bad=structuredClone(second);bad.evidence.report.assessments[0].claimIndex=5;await repin(bad);await expect(publishDiscovery(h.env,bad)).rejects.toMatchObject({code:"publication_conflict"});
    const wrong=structuredClone(second);wrong.evidence.topic.id="topic-"+hash(100);await repin(wrong);await expect(publishDiscovery(h.env,wrong)).rejects.toMatchObject({code:"publication_conflict"});
    await publishDiscovery(h.env,second);
    expect(h.db.prepare("SELECT * FROM knowledge_edges WHERE edge_kind='publication:inconclusive'").get()?.to_concept_id).toBe("publications/"+first.record.id+"/claims/0");
    expect(h.scalar("SELECT count(*) FROM knowledge_documents WHERE type='Published source'")).toBe(1);
    expect(h.scalar("SELECT count(*) FROM knowledge_documents WHERE type='Discovery topic'")).toBe(1);
  });
  it("rejects a reviewer mixing E2 with methods that retained E1, without any publication writes",async()=>{
    const h=harness(),e1=await publication();await publishDiscovery(h.env,e1);
    const methods=await publication(1,[{role:"evidence",publicationId:e1.record.id}]);await publishDiscovery(h.env,methods);
    const e2=await publication();e2.evidence.provenance.archiveSha256=hash(61);e2.record.id=e2.record.activityId="discovery-"+hash(61);
    e2.evidence.provenance.completedAt=e2.record.observedAt=e2.record.reviewedAt="2026-10-01T10:01:30.000Z";await repin(e2);await publishDiscovery(h.env,e2);
    const reviewer=await publication(2,[{role:"evidence",publicationId:e2.record.id},{role:"methods",publicationId:methods.record.id}]);
    const before=h.db.prepare("SELECT * FROM public_activity_archive_sequence ORDER BY sequence").all();
    await expect(publishDiscovery(h.env,reviewer)).rejects.toMatchObject({code:"publication_conflict"});
    expect(h.db.prepare("SELECT * FROM public_activity_archive_sequence ORDER BY sequence").all()).toEqual(before);
    expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(3);
    expect(h.db.prepare("SELECT * FROM knowledge_documents WHERE concept_id=?").get("publications/"+reviewer.record.id)).toBeUndefined();
  });
  it("requires the exact immutable topic question and origin across role stages",async()=>{
    const h=harness(),first=await publication();await publishDiscovery(h.env,first);
    for(const patch of [{question:"Changed stage question."},{parentTopicId:"topic-"+hash(77)},
      {parentTopicId:"topic-"+hash(77),parentPublicationId:"discovery-"+hash(78),parentQuestionIndex:1}]){
      const methods=await publication(1,[{role:"evidence",publicationId:first.record.id}]);Object.assign(methods.evidence.topic,patch);await repin(methods);
      await expect(publishDiscovery(h.env,methods)).rejects.toMatchObject({code:"publication_conflict"});
    }
    expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(1);
  });
  it("protects immutable knowledge and rejects private graph endpoints",async()=>{
    const h=harness(),p=await publication();await publishDiscovery(h.env,p);
    expect(()=>h.db.exec("UPDATE knowledge_documents SET title='changed' WHERE source_kind='public_discovery'")).toThrow();
    expect(()=>h.db.exec("DELETE FROM knowledge_edges WHERE edge_kind GLOB 'publication:*'")).toThrow();
    h.db.exec("INSERT INTO knowledge_documents(concept_id,type,title) VALUES('private/topic','private','private content')");
    expect(()=>h.db.prepare("INSERT INTO knowledge_edges(from_concept_id,to_concept_id,edge_kind) VALUES(?,?,'publication:bad')")
      .run("publications/"+p.record.id,"private/topic")).toThrow();
  });
  it("fails a contradictory shared source identity without partial writes",async()=>{
    const h=harness(),first=await publication();await publishDiscovery(h.env,first);
    const second=await publication(1,[{role:"evidence",publicationId:first.record.id}]);second.evidence.sources[0].title="A different source under the same semantic identity.";await repin(second);
    await expect(publishDiscovery(h.env,second)).rejects.toMatchObject({code:"publication_conflict"});
    expect(h.scalar("SELECT count(*) FROM public_discovery_evidence")).toBe(1);
    expect(h.scalar("SELECT count(*) FROM public_research_activity")).toBe(1);
  });
  it("requires an exact published principal parent rather than an arbitrary publication link",async()=>{
    const h=harness(),first=await publication();await publishDiscovery(h.env,first);
    const child=await publication();child.evidence.provenance.archiveSha256=hash(44);child.record.id=child.record.activityId="discovery-"+hash(44);
    child.evidence.topic.id="topic-"+hash(45);child.evidence.topic.parentTopicId=first.evidence.topic.id;child.evidence.topic.parentPublicationId=first.record.id;child.evidence.topic.parentQuestionIndex=0;await repin(child);
    await expect(publishDiscovery(h.env,child)).rejects.toMatchObject({code:"publication_conflict"});
    child.evidence.topic.parentPublicationId="discovery-"+hash(46);await repin(child);
    await expect(publishDiscovery(h.env,child)).rejects.toMatchObject({code:"publication_dependency_missing"});
  });
  it("joins an exact principal question and rejects a fabricated or incorrect question index",async()=>{
    const h=harness(),priors:DiscoveryEvidence["priorReports"]=[];let principal:DiscoveryPublication|undefined;
    for(let i=0;i<4;i++){const p=await publication(i,[...priors]);await publishDiscovery(h.env,p);priors.push({role:p.evidence.report.role,publicationId:p.record.id});principal=p;}
    const child=await publication();child.evidence.provenance.archiveSha256=hash(50);child.record.id=child.record.activityId="discovery-"+hash(50);
    child.evidence.provenance.completedAt=child.record.observedAt=child.record.reviewedAt="2026-10-01T11:00:00.000Z";
    child.evidence.topic={id:"topic-"+hash(51),question:principal!.evidence.report.questions[0],parentTopicId:principal!.evidence.topic.id,
      parentPublicationId:principal!.record.id,parentQuestionIndex:0};await repin(child);
    const bad=structuredClone(child);bad.evidence.topic.question="A different unsupported origin question.";await repin(bad);
    await expect(publishDiscovery(h.env,bad)).rejects.toMatchObject({code:"publication_conflict"});
    const wrong=structuredClone(child);wrong.evidence.topic.parentQuestionIndex=2;await repin(wrong);
    await expect(publishDiscovery(h.env,wrong)).rejects.toMatchObject({code:"publication_conflict"});
    await publishDiscovery(h.env,child);
    expect(h.db.prepare("SELECT to_concept_id FROM knowledge_edges WHERE edge_kind='publication:follows-question'").get()?.to_concept_id)
      .toBe("publications/"+principal!.record.id+"/questions/0");
  });
});

describe("service boundary and public retrieval",()=>{
  it("exposes only fixed bounded canonical POST on the binding and retains protected browser import",async()=>{
    const h=harness(),p=await publication();expect((await discoveryPublicationServiceResponse(serviceRequest(p),h.env)).status).toBe(200);
    expect((await discoveryPublicationServiceResponse(serviceRequest(p,"/elsewhere"),h.env)).status).toBe(404);
    expect((await discoveryPublicationServiceResponse(new Request("https://receiver.internal/publish"),h.env)).status).toBe(405);
    expect((await researchActivityResponse(new Request("https://glim-think.example.org/workspace/research-activity/import",{
      method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer fake"},body:JSON.stringify(p.record)}),h.env))?.status).toBe(403);
    expect(await discoveryPublicationPublicResponse(serviceRequest(p),h.env)).toBe(null);
    const noncanonical=new Request("https://receiver.internal/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
    expect((await discoveryPublicationServiceResponse(noncanonical,h.env)).status).toBe(400);
    const oversized=new Request("https://receiver.internal/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:"x".repeat(65537)});
    expect((await discoveryPublicationServiceResponse(oversized,h.env)).status).toBe(413);
  });
  it("serves exact hash-pinned evidence bytes and fails closed on corruption",async()=>{
    const h=harness(),p=await publication();await publishDiscovery(h.env,p);
    const r=(await discoveryPublicationPublicResponse(publicRequest(`/research/activity/${p.record.id}/evidence`),h.env))!;
    expect(r.status).toBe(200);expect(r.headers.get("Access-Control-Allow-Origin")).toBe("*");
    const body=await r.text();expect(body).toBe(canonicalPublicJson(p.evidence));expect(await publicActivitySha256(body)).toBe(p.record.hashes[0].sha256);
    h.db.exec("DROP TRIGGER public_discovery_evidence_update; UPDATE public_discovery_evidence SET evidence_sha256='"+hash(0)+"'");
    const corrupted=(await discoveryPublicationPublicResponse(publicRequest(`/research/activity/${p.record.id}/evidence`),h.env))!;
    expect(corrupted.status).toBe(503);expect(await corrupted.text()).not.toContain(p.evidence.report.summary);
  });
  it("provides snapshot-bounded public KG pages excluding unrelated records",async()=>{
    const h=harness(),first=await publication();await publishDiscovery(h.env,first);
    const second=await publication(1,[{role:"evidence",publicationId:first.record.id}]);await publishDiscovery(h.env,second);
    h.db.exec("INSERT INTO knowledge_documents(concept_id,type,title,body_md) VALUES('private/secret','private','private','DO-NOT-PUBLISH')");
    const r=(await discoveryPublicationPublicResponse(publicRequest("/research/knowledge?limit=1"),h.env))!;const page=await r.json() as any;
    expect(r.status).toBe(200);expect(page.coverage).toEqual({complete:false,returned:1});expect(page.publicationIds).toEqual([first.record.id]);
    expect(JSON.stringify(page)).not.toContain("DO-NOT-PUBLISH");
    const last=(await discoveryPublicationPublicResponse(publicRequest(`/research/knowledge?limit=1&after=${page.cursor.nextAfter}&snapshot=${page.cursor.snapshot}`),h.env))!;
    expect((await last.json() as any).coverage.complete).toBe(true);
    for(const query of ["limit=11","after=-1","after=1&after=2","snapshot=999","unknown=1"])
      expect((await discoveryPublicationPublicResponse(publicRequest("/research/knowledge?"+query),h.env))?.status).toBe(400);
  });
});
