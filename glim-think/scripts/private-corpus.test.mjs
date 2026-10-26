import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import ts from "typescript";
import { DatabaseSync } from "node:sqlite";

// Transpile this small route and its real Access middleware entirely in memory.
const urls = new Map();
function loadTs(path) {
  path = resolve(path);
  if (urls.has(path)) return urls.get(path);
  let js = ts.transpileModule(readFileSync(path, "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  js = js.replace(/from\s+["'](\.\.?\/[^"']+)["']/g, (_, relative) =>
    'from "' + loadTs(resolve(dirname(path), relative + ".ts")) + '"');
  const url = "data:text/javascript;base64," + Buffer.from(js).toString("base64");
  urls.set(path, url);
  return url;
}

const { default: acceptance } = await import(loadTs("src/privateEvidenceAcceptance.ts"));
const { corpusResponse: route } = await import(loadTs("src/workspace/corpus.ts"));
const { evidenceObjectsResponse } = await import(loadTs("src/workspace/evidenceObjects.ts"));
const { dispatchPrivateEvidence } = await import(loadTs("src/workspace/evidenceDispatch.ts"));
const hash = async bytes => Buffer.from(await crypto.subtle.digest("SHA-256", bytes)).toString("hex");
const raw = new TextEncoder().encode("synthetic public source bytes for integration checks\n");
const sha = await hash(raw);
const root = "https://research.example/workspace/corpus";
const schema = readFileSync("corpus-migrations/0001_private_corpus.sql","utf8");
const reviewSchema = readFileSync("corpus-migrations/0002_review_revisions.sql","utf8");
test("private corpus D1 and R2 integration", async t => {
  const keys = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"]);
  const jwk = await crypto.subtle.exportKey("jwk", keys.publicKey);
  const segment = value => Buffer.from(JSON.stringify(value)).toString("base64url");
  async function token(email = "operator@example.test") {
    const input = segment({ alg: "RS256", kid: "evidence-test" }) + "." + segment({
      aud: "private-evidence-test", iss: "https://evidence-test.cloudflareaccess.com",
      exp: Math.floor(Date.now() / 1000) + 600, email,
    });
    return input + "." + Buffer.from(await crypto.subtle.sign("RSASSA-PKCS1-v1_5", keys.privateKey,
      new TextEncoder().encode(input))).toString("base64url");
  }
  const jwt = await token();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async input => {
    assert.equal(String(input), "https://evidence-test.cloudflareaccess.com/cdn-cgi/access/certs");
    return Response.json({ keys: [{ ...jwk, kid: "evidence-test" }] });
  };
  t.after(() => { globalThis.fetch = originalFetch; });

  function harness(options={}) {
    const sql=new DatabaseSync(":memory:");
    sql.exec("PRAGMA foreign_keys=ON;"+schema+(options.legacySchema?"":reviewSchema));
    const objects=new Map([["sha256/"+sha,{bytes:raw,etag:"source-v1",metadata:{sha256:sha}}]]);
    let reads=0,writes=0, batches=0, storageReads=0;
    function statement(query,bindings=[]) {
      return {query,bindings,
        bind(...args){return statement(query,args)},
        async first(){reads++;return sql.prepare(query).get(...bindings)??null},
        async all(){reads++;return {success:true,results:sql.prepare(query).all(...bindings)}},
        async run(){writes++;sql.prepare(query).run(...bindings);return {success:true}}
      };
    }
    const db={prepare:statement,async batch(statements){
      batches++;sql.exec("BEGIN");
      try {
        for(let i=0;i<statements.length;i++){
          if(options.failAt===i) throw new Error("synthetic statement failure");
          const s=statements[i];sql.prepare(s.query).run(...s.bindings);writes++;
        }
        sql.exec("COMMIT");
      } catch(e) {sql.exec("ROLLBACK");throw e}
      if(options.lostAcknowledgement)throw new Error("synthetic acknowledgement lost after commit");
      return statements.map(()=>({success:true}));
    }};
    function r2Object(key) {
      storageReads++; const o=objects.get(key); if(!o)return null;
      return {key,size:o.bytes.length,etag:o.etag,customMetadata:o.metadata,
        body:new ReadableStream({start(c){c.enqueue(o.bytes.slice());c.close()}})};
    }
    const bucket={async get(key){return r2Object(key)},async head(key){const o=r2Object(key);if(o)delete o.body;return o}};
    const env={ADMIN_EMAIL:"operator@example.test",CF_ACCESS_TEAM_DOMAIN:"evidence-test",CF_ACCESS_AUD:"private-evidence-test",
      PRIVATE_EVIDENCE_ENABLED:"true",PRIVATE_CORPUS_ENABLED:"true",PRIVATE_EVIDENCE:bucket,ARTIFACTS:{},PRIVATE_CORPUS:db,LEDGER:new Proxy({},{get(){throw new Error("Runtime ledger must not be accessed")}})};
    t.after(()=>sql.close());
    return {env,sql,objects,stats:()=>({reads,writes,batches,storageReads})};
  }
  function req(path,method="GET",body,headers={}) {
    return new Request(root+path,{method,headers:{"Cf-Access-Jwt-Assertion":jwt,...(body===undefined?{}:{"Content-Type":"application/json"}),...headers},
      ...(body===undefined?{}:{body:typeof body==="string"?body:JSON.stringify(body),duplex:"half"})});
  }
  async function row(id="row-01",overrides={}) {
    const recordJson=JSON.stringify({reported:111,reference:110,unknownUncertainty:null});
    return {recordId:id,recordSha256:await hash(new TextEncoder().encode(recordJson)),evidenceSha256:sha,sourceId:"source-A",studyId:"study-A",
      locator:"Table 1 / C11",material:"synthetic-cubic",observable:"C11",unit:"GPa",modelId:"model-A",referenceKind:"DFT",
      observedAt:"2020-01-02T00:00:00Z",reviewedAt:null,originalRowSha256:null,missingFields:["uncertainty","temperature"],recordJson,...overrides};
  }
  const payload=(observations=[],qualifications=[])=>({schema:"lupine-private-corpus-v1",observations,qualifications});
  const event=(r,overrides={})=>({eventId:"event-01",recordId:r.recordId,recordSha256:r.recordSha256,kind:"quarantine",reason:"synthetic incompatible reference",
    originalReviewedAt:"2021-02-03T00:00:00Z",...overrides});
  async function verified(h) {const r=await route(req("/objects/"+sha,"POST"),h.env);assert.equal(r.status,201,await r.clone().text());return r.json()}
  async function put(h,id,p) {return route(req("/imports/"+id,"PUT",p),h.env)}
  const count=(h,table)=>h.sql.prepare("SELECT COUNT(*) n FROM "+table).get().n;
  await t.test("strict Access and feature gates deny before any storage access",async()=>{
    const h=harness();
    h.env.DEV_MODE="true";h.env.INTERNAL_TASK_TOKEN="legacy";
    assert.equal((await route(req("/observations","GET",undefined,{"Cf-Access-Jwt-Assertion":"","X-Internal-Token":"legacy"}),h.env)).status,403);
    assert.equal((await route(req("/observations","GET",undefined,{"Cf-Access-Jwt-Assertion":await token("wrong@example.test")}),h.env)).status,403);
    assert.equal((await route(req("/observations","GET",undefined,{Origin:"https://wrong.example"}),h.env)).status,403);
    h.env.PRIVATE_CORPUS_ENABLED="false";
    assert.equal((await route(req("/observations"),h.env)).status,503);
    assert.deepEqual(h.stats(),{reads:0,writes:0,batches:0,storageReads:0});
  });
  await t.test("readback hashes bytes and preserves the original receipt on duplicate verification",async()=>{
    const h=harness();const first=await verified(h);
    assert.equal(first.receipt.sha256,sha);assert.equal(first.scientificValidation,"not_assessed");
    const again=await route(req("/objects/"+sha,"POST"),h.env);
    assert.equal(again.status,200);assert.deepEqual((await again.json()).receipt,first.receipt);
    const get=await route(req("/objects/"+sha),h.env);
    assert.equal(get.headers.get("Cache-Control"),"private, no-store");
    assert.equal((await get.json()).scope,"original verification time; current bytes not re-read");
    assert.equal(count(h,"workspace_evidence_receipts"),1);
  });
  await t.test("corrupt, missing, oversized and changed objects cannot gain receipts",async()=>{
    const h=harness();h.objects.get("sha256/"+sha).bytes=new Uint8Array([1,2,3]);
    assert.equal((await route(req("/objects/"+sha,"POST"),h.env)).status,409);
    assert.equal(count(h,"workspace_evidence_receipts"),0);
    h.objects.clear();assert.equal((await route(req("/objects/"+sha,"POST"),h.env)).status,404);
    h.objects.set("sha256/"+sha,{bytes:raw,etag:"x",metadata:{sha256:"wrong"}});
    assert.equal((await route(req("/objects/"+sha,"POST"),h.env)).status,409);
    h.env.PRIVATE_EVIDENCE.get=async()=>({size:26214401,etag:"x",customMetadata:{sha256:sha},body:new ReadableStream()});
    assert.equal((await route(req("/objects/"+sha,"POST"),h.env)).status,409);
  });
  await t.test("imports require verified source objects with unchanged metadata",async()=>{
    const h=harness(),p=payload([await row()]);
    assert.equal((await put(h,"import-A",p)).status,409);
    await verified(h);h.objects.get("sha256/"+sha).etag="external-mutation";
    assert.equal((await put(h,"import-A",p)).status,409);
    assert.equal(count(h,"workspace_corpus_imports"),0);
  });
  await t.test("schema, row byte hashes, sizes and duplicate input entries fail before writes",async()=>{
    const h=harness();await verified(h);const r=await row();
    for(const bad of [
      {...payload([r]),extra:"unsupported"},
      payload([{...r,recordSha256:"a".repeat(64)}]),
      payload([{...r,observedAt:"yesterday"}]),
      payload([{...r,observedAt:"2021-02-30T00:00:00Z"}]),
      payload([{...r,observedAt:"2020-01-01T00:00:00+24:00"}]),
      payload([{...r,material:undefined}]),
      payload([r,r]),payload(Array.from({length:21},(_,i)=>({...r,recordId:String(i)}))),
      payload([{...r,recordJson:"x".repeat(65537)}]),
      payload([{...r,missingFields:["x","x"]}]),
      payload([]),
    ]) assert.equal((await put(h,"bad",bad)).status,400);
    assert.equal((await route(req("/imports/big","PUT","x".repeat(1024*1024+1)),h.env)).status,413);
    assert.equal((await route(req("/imports/short","PUT","{}",{"Content-Length":"20"}),h.env)).status,400);
    assert.equal(count(h,"workspace_corpus_imports"),0);
  });
  await t.test("atomic import retains exact row bytes, identifiers, missingness and original times",async()=>{
    const h=harness();await verified(h);
    const r=await row("row-01",{observedAt:"2020-01-02T03:04:05.123456+00:00"}),s=await row("row-02",{studyId:"study-B",unit:null,reviewedAt:"2021-04-05T03:04:05.123456789+05:30"});
    const response=await put(h,"batch-A",payload([r,s]));
    assert.equal(response.status,201,await response.clone().text());const result=await response.json();
    assert.equal(result.state,"committed");assert.equal(result.scientificValidation,"not_assessed");
    assert.equal(result.provenanceLink,"operator_supplied");assert.equal(result.import.observation_count,2);
    assert.equal(count(h,"workspace_corpus_observations"),2);
    const details=await route(req("/observation?record_id="+r.recordId+"&record_sha256="+r.recordSha256),h.env);
    const d=(await details.json()).observation;
    assert.equal(d.record_json,r.recordJson);assert.equal(d.record_sha256,r.recordSha256);assert.equal(d.observed_at,r.observedAt);assert.equal(d.reviewed_at,null);
    assert.deepEqual(JSON.parse(d.missing_fields_json),r.missingFields);
    const q=await route(req("/observations?study_id=study-B"),h.env);const data=await q.json();
    assert.equal(data.observations.length,1);assert.equal(data.observations[0].unit,null);assert.equal(data.observations[0].reviewed_at,s.reviewedAt);
    assert.equal("record_json" in data.observations[0],false);
  });

  await t.test("unknown source and study identities stay null without fabricated identifiers",async()=>{
    const h=harness();await verified(h);
    const r=await row("unknown-identity",{sourceId:null,studyId:null,missingFields:["sourceId","studyId"]});
    assert.equal((await put(h,"unknown-identity",payload([r]))).status,201);
    const result=await route(req("/observations"),h.env);
    const list=(await result.json()).observations;
    assert.equal(list[0].source_id,null);assert.equal(list[0].study_id,null);
    assert.deepEqual(JSON.parse(list[0].missing_fields_json),["sourceId","studyId"]);
    const stored=h.sql.prepare("SELECT record_json FROM workspace_corpus_observations").get();
    assert.equal(stored.record_json,r.recordJson);
  });

  await t.test("same import bytes are an idempotent no-op; divergent bytes conflict",async()=>{
    const h=harness();await verified(h);const p=payload([await row()]);
    assert.equal((await put(h,"same",p)).status,201);
    const stats=h.stats();const repeat=await put(h,"same",p);assert.equal(repeat.status,200);assert.equal((await repeat.json()).duplicate,true);
    assert.equal(h.stats().batches,stats.batches);
    assert.equal((await put(h,"same",{...p,schema:"other"})).status,409);
    assert.equal(count(h,"workspace_corpus_imports"),1);
  });
  await t.test("shared rows deduplicate, while conflicting projection rolls back the entire new import",async()=>{
    const h=harness();await verified(h);const r=await row();
    await put(h,"one",payload([r]));assert.equal((await put(h,"two",payload([r]))).status,201);
    assert.equal(count(h,"workspace_corpus_observations"),1);assert.equal(count(h,"workspace_corpus_members"),2);
    const conflict=await put(h,"three",payload([await row("new-row"),{...r,unit:"eV"}]));
    assert.equal(conflict.status,409,await conflict.clone().text());
    assert.equal(count(h,"workspace_corpus_imports"),2);assert.equal(count(h,"workspace_corpus_observations"),1);
    assert.equal((await route(req("/imports/three"),h.env)).status,404);
  });
  await t.test("injected middle-statement failure leaves no partial manifest or rows",async()=>{
    const h=harness({failAt:2});await verified(h);
    const r=await put(h,"interrupted",payload([await row()]));
    assert.equal(r.status,503);assert.match((await r.json()).error,/no retry performed/);
    assert.equal(count(h,"workspace_corpus_imports"),0);assert.equal(count(h,"workspace_corpus_observations"),0);
    assert.equal(h.stats().batches,1);
  });
  await t.test("lost acknowledgement is unknown until read-only import receipt collection",async()=>{
    const h=harness({lostAcknowledgement:true});await verified(h);
    assert.equal((await put(h,"ack-lost",payload([await row()]))).status,503);
    const writes=h.stats().writes;
    const receipt=await route(req("/imports/ack-lost"),h.env);assert.equal(receipt.status,200);assert.equal((await receipt.json()).state,"committed");
    assert.equal(h.stats().writes,writes);assert.equal(h.stats().batches,1);
  });
  await t.test("qualification events target exact row versions and never overwrite their values",async()=>{
    const h=harness();await verified(h);const r=await row(),other=await row("row-02");
    await put(h,"initial",payload([r,other]));
    const e=event(r);assert.equal((await put(h,"review",payload([],[e,event(r,{eventId:"event-02",kind:"correction",reason:"Keep original; replacement pending"})]))).status,201);
    const q=await route(req("/observations"),h.env);assert.deepEqual((await q.json()).observations.map(o=>o.record_id),["row-02"]);
    const all=await route(req("/observations?include_quarantined=true"),h.env);const rows=(await all.json()).observations;
    assert.equal(rows.length,2);assert.equal(rows[0].quarantined,1);
    const history=await route(req("/qualifications?record_id="+r.recordId+"&record_sha256="+r.recordSha256+"&limit=1"),h.env);
    assert.equal(history.status,200,await history.clone().text());
    const data=await history.json();assert.equal(data.qualifications[0].kind,"quarantine");assert.equal(data.next.after_event_id,"event-01");
    const detail=await route(req("/observation?record_id="+r.recordId+"&record_sha256="+r.recordSha256),h.env);
    assert.equal((await detail.json()).observation.record_json,r.recordJson);
    assert.equal((await put(h,"bad-review",payload([],[{...e,reason:"changed"}]))).status,409);
    assert.equal((await put(h,"orphan",payload([],[event(r,{eventId:"orphan",recordId:"absent"})]))).status,503);
    assert.equal(count(h,"workspace_corpus_imports"),2);
  });
  await t.test("keyset pagination, exact filters and fixed import membership stay bounded",async()=>{
    const h=harness();await verified(h);const rs=await Promise.all([row("a"),row("b"),row("c",{studyId:"study-B"})]);await put(h,"pages",payload(rs));
    const page=await route(req("/observations?limit=2&import_id=pages"),h.env);const p=await page.json();
    assert.deepEqual(p.observations.map(x=>x.record_id),["a","b"]);assert.equal(p.next.after_id,"b");
    const second=await route(req("/observations?limit=2&import_id=pages&after_id=b&after_sha256="+p.next.after_sha256),h.env);
    assert.deepEqual((await second.json()).observations.map(x=>x.record_id),["c"]);
    for (const query of ["?limit=51","?limit=-1","?after_id=a","?study_id=x&study_id=y","?include_quarantined=maybe","?raw=true"])assert.equal((await route(req("/observations"+query),h.env)).status,400);
    assert.equal((await route(req("/observations?study_id="+encodeURIComponent("' OR 1=1 --")),h.env)).status,200);
    const plan=h.sql.prepare("EXPLAIN QUERY PLAN SELECT record_id FROM workspace_corpus_observations WHERE material=? AND observable=? ORDER BY record_id,record_sha256 LIMIT 20").all("synthetic-cubic","C11");
    assert.ok(plan.some(x=>x.detail.includes("idx_workspace_corpus_material_observable")));
  });
  await t.test("SQL enforces immutable history against updates and deletions",async()=>{
    const h=harness();await verified(h);await put(h,"immutable",payload([await row()]));
    for(const table of ["workspace_evidence_receipts","workspace_corpus_imports","workspace_corpus_observations","workspace_corpus_members"])
      assert.throws(()=>h.sql.exec("DELETE FROM "+table),/immutable/);
    assert.throws(()=>h.sql.exec("UPDATE workspace_corpus_observations SET unit='eV'"),/immutable/);
  });
  await t.test("body buffering is shared with object upload and releases after completion",async()=>{
    const h=harness();await verified(h);
    const shared = await import(loadTs("src/workspace/evidenceObjects.ts"));
    const release=shared.acquireEvidenceBuffer();assert.ok(release);
    try {
      assert.equal((await put(h,"busy",payload([await row()]))).status,429);
      assert.equal((await evidenceObjectsResponse(new Request("https://research.example/workspace/evidence-objects/"+sha,{method:"PUT",headers:{"Cf-Access-Jwt-Assertion":jwt},body:raw}),h.env)).status,429);
    } finally { release(); }
    assert.equal((await put(h,"after-busy",payload([await row()]))).status,201);
  });
  await t.test("server routes the corpus before generic body parsing",()=>{
    const source=readFileSync("src/server.ts","utf8");
    assert.ok(source.indexOf("await corpusResponse(request, env)")<source.indexOf("const bodyText ="));
  });
  await t.test("private corpus requires a distinct database and bypasses request telemetry",async()=>{
    const h=harness();let fallbacks=0;
    const fallback=async()=>{fallbacks++;return new Response("public")};
    const privateResponse=await dispatchPrivateEvidence(req("/observations"),Object.freeze({...h.env}),fallback);
    assert.equal(privateResponse.status,200);assert.equal(fallbacks,0);
    await dispatchPrivateEvidence(new Request("https://research.example/health"),h.env,fallback);
    assert.equal(fallbacks,1);
    const duplicateSlash=await dispatchPrivateEvidence(new Request("https://research.example/workspace//corpus/observations"),h.env,fallback);
    assert.equal(duplicateSlash.status,400);assert.equal(fallbacks,1);
    const db=h.env.PRIVATE_CORPUS;h.env.PRIVATE_CORPUS=h.env.LEDGER;
    assert.equal((await route(req("/observations"),h.env)).status,503);
    delete h.env.PRIVATE_CORPUS;assert.equal((await route(req("/observations"),h.env)).status,503);
    h.env.PRIVATE_CORPUS=db;
    const source=readFileSync("src/server.ts","utf8");
    assert.match(source,/return dispatchPrivateEvidence\(request, env, \(\) =>/);
    assert.match(source,/env = \{ \.\.\.env \};\s+traceEnv\(env\)/);
  });

  await t.test("source context preserves exact revisions, unknowns and quarantines without inference",async()=>{
    const h=harness();await verified(h);
    const a=await row("a"),b=await row("b",{studyId:null,unit:null}),other=await row("other",{sourceId:"source-B"});
    await put(h,"sources",payload([a,b,other],[event(b)]));
    const before=h.stats();
    const response=await route(req("/source-context?source_id=source-A&limit=1&import_id=sources"),h.env);
    assert.equal(response.status,200,await response.clone().text());
    assert.match(response.headers.get("Cache-Control"),/no-store/);
    const {context,contextSha256}=await response.json();
    assert.equal(contextSha256,await hash(new TextEncoder().encode(JSON.stringify(context))));
    assert.deepEqual(context.nodes.map(n=>n.recordId),["a"]);
    assert.equal(context.nodes[0].recordSha256,a.recordSha256);
    assert.equal(context.nodes[0].anchor.objectSha256,sha);
    assert.equal(context.nodes[0].anchor.kind,"retained_record_container");
    assert.equal(context.nodes[0].anchor.primaryDocumentClosure,"not_verified");
    assert.deepEqual(context.nodes[0].missingFields,a.missingFields);
    assert.deepEqual(context.semanticRelations,[]);
    assert.equal(context.analysis.state,"not_run");assert.equal(context.analysis.modelCalls,0);
    const after=new URLSearchParams({source_id:"source-A",limit:"1",import_id:"sources",...context.next});
    const second=await (await route(req("/source-context?"+after),h.env)).json();
    assert.equal(second.context.nodes[0].recordId,"b");
    assert.equal(second.context.nodes[0].quarantined,true);
    assert.equal(second.context.nodes[0].unit,null);assert.equal(second.context.nodes[0].studyId,null);
    assert.equal(second.context.nodes[0].qualificationHistory.complete,false);
    assert.equal(second.context.next,null);
    assert.equal(h.stats().writes,before.writes);assert.equal(h.stats().storageReads,before.storageReads);
    const plan=h.sql.prepare("EXPLAIN QUERY PLAN SELECT record_id FROM workspace_corpus_observations WHERE source_id=? ORDER BY record_id,record_sha256 LIMIT 20").all("source-A");
    assert.ok(plan.some(x=>x.detail.includes("idx_workspace_corpus_source")));
    const filtered=await (await route(req("/observations?source_id=source-B"),h.env)).json();
    assert.deepEqual(filtered.observations.map(o=>o.record_id),["other"]);
  });
  await t.test("source context is Access protected, bounded and never hides qualifications",async()=>{
    const h=harness();
    const noAccess=await route(new Request(root+"/source-context?source_id=source-A"),h.env);
    assert.equal(noAccess.status,403);assert.equal(h.stats().reads,0);
    for(const query of ["","?source_id=","?source_id=a&source_id=b","?source_id=a&limit=21",
      "?source_id=a&include_quarantined=false","?source_id=a&after_id=x","?source_id=a&raw=true"])
      assert.equal((await route(req("/source-context"+query),h.env)).status,400);
    assert.equal((await route(req("/source-context?source_id=a","POST"),h.env)).status,405);
    const absent=await (await route(req("/source-context?source_id=absent"),h.env)).json();
    assert.equal(absent.context.nodes.length,0);
    assert.equal(absent.context.analysis.scientificValidation,"not_assessed");
  });

  await t.test("every qualification changes source context even when quarantine is unchanged",async()=>{
    const h=harness();await verified(h);const r=await row();
    await put(h,"original",payload([r]));
    const get=async()=> (await route(req("/source-context?source_id=source-A"),h.env)).json();
    const before=await get();
    await put(h,"annotation",payload([],[event(r,{kind:"annotation",reason:"Original uncertainty requires review"})]));
    const annotated=await get();
    assert.equal(before.context.nodes[0].quarantined,false);
    assert.equal(annotated.context.nodes[0].quarantined,false);
    assert.notEqual(annotated.contextSha256,before.contextSha256);
    await put(h,"correction",payload([],[event(r,{eventId:"correction",kind:"correction",reason:"Source protocol differs"})]));
    const corrected=await get();
    assert.notEqual(corrected.contextSha256,annotated.contextSha256);
  });

  await t.test("conditional source reads reject stale page fingerprints without writes",async()=>{
    const h=harness();await verified(h);const r=await row();
    await put(h,"conditional",payload([r]));
    const url="/source-context?source_id=source-A";
    const before=await (await route(req(url),h.env)).json();
    assert.equal((await route(req(url+"&expected_context_sha256="+before.contextSha256),h.env)).status,200);
    await put(h,"new-review",payload([],[event(r,{kind:"correction"})]));
    const writes=h.stats().writes;
    const stale=await route(req(url+"&expected_context_sha256="+before.contextSha256),h.env);
    assert.equal(stale.status,409);
    const changed=await stale.json();assert.equal(changed.state,"context_changed");
    assert.notEqual(changed.contextSha256,before.contextSha256);
    assert.equal(h.stats().writes,writes);
    assert.equal((await route(req(url+"&expected_context_sha256=invalid"),h.env)).status,400);
  });
  await t.test("review history pins one revision across empty and nonempty pages",async()=>{
    const h=harness();await verified(h);const r=await row();
    await put(h,"history",payload([r],[event(r,{eventId:"b",kind:"annotation"}),event(r,{eventId:"c",kind:"correction"})]));
    const url="/qualifications?record_id="+r.recordId+"&record_sha256="+r.recordSha256;
    const first=await (await route(req(url+"&limit=1&expected_revision=2"),h.env)).json();
    assert.equal(first.qualificationRevision,"2");
    assert.deepEqual(first.next,{after_event_id:"b",expected_revision:"2"});
    const last=await (await route(req(url+"&limit=1&after_event_id=b&expected_revision=2"),h.env)).json();
    assert.equal(last.qualifications[0].event_id,"c");assert.equal(last.next,null);
    const empty=await (await route(req(url+"&after_event_id=z&expected_revision=2"),h.env)).json();
    assert.deepEqual(empty.qualifications,[]);assert.equal(empty.qualificationRevision,"2");
    // An insertion before a previously returned cursor must not be silently missed.
    await put(h,"earlier-key",payload([],[event(r,{eventId:"a",kind:"annotation"})]));
    assert.equal((await route(req(url+"&after_event_id=b&expected_revision=2"),h.env)).status,409);
    assert.equal((await route(req(url+"&after_event_id=z&expected_revision=2"),h.env)).status,409);
    for(const v of ["-1","01","1.5","9007199254740992"])
      assert.equal((await route(req(url+"&expected_revision="+v),h.env)).status,400);
    const plan=h.sql.prepare("EXPLAIN QUERY PLAN SELECT event_id FROM workspace_corpus_qualifications WHERE record_id=? AND record_sha256=? AND event_id>? ORDER BY event_id LIMIT 2").all(r.recordId,r.recordSha256,"a");
    assert.ok(plan.some(x=>x.detail.includes("idx_workspace_corpus_qualification_page")));
  });
  await t.test("review heads advance only for committed new events, not replays or rolled back imports",async()=>{
    const h=harness();await verified(h);const r=await row(),e=event(r,{kind:"annotation"});
    await put(h,"first",payload([r],[e]));
    const current=()=>h.sql.prepare("SELECT revision FROM workspace_corpus_review_heads").get().revision;
    assert.equal(current(),1);
    assert.equal((await put(h,"same-event-new-import",payload([],[e]))).status,201);assert.equal(current(),1);
    const bad=await put(h,"rollback-review",payload([],[event(r,{eventId:"new"}),event(r,{eventId:"orphan",recordId:"absent"})]));
    assert.equal(bad.status,503);assert.equal(current(),1);
    assert.equal(count(h,"workspace_corpus_qualifications"),1);
    assert.equal((await route(req("/imports/rollback-review"),h.env)).status,404);
    assert.throws(()=>h.sql.exec("DELETE FROM workspace_corpus_review_heads"),/immutable/);
  });
  await t.test("review migration backfills old events and does not reset later revisions",async()=>{
    const h=harness({legacySchema:true});await verified(h);const r=await row();
    await put(h,"legacy",payload([r],[event(r),event(r,{eventId:"old-correction",kind:"correction"})]));
    h.sql.exec(reviewSchema);
    const current=()=>h.sql.prepare("SELECT revision FROM workspace_corpus_review_heads").get().revision;
    assert.equal(current(),2);
    await put(h,"new",payload([],[event(r,{eventId:"new",kind:"annotation"})]));assert.equal(current(),3);
    h.sql.exec(reviewSchema);assert.equal(current(),3);
    const context=await (await route(req("/source-context?source_id=source-A"),h.env)).json();
    assert.equal(context.context.nodes[0].qualificationHistory.revision,"3");
  });
  await t.test("unknown acknowledgement keeps the committed review revision recoverable read-only",async()=>{
    const h=harness({lostAcknowledgement:true});await verified(h);const r=await row();
    assert.equal((await put(h,"unknown-review",payload([r],[event(r,{kind:"annotation"})]))).status,503);
    const writes=h.stats().writes;
    const receipt=await (await route(req("/imports/unknown-review"),h.env)).json();
    assert.equal(receipt.state,"committed");
    const context=await (await route(req("/source-context?source_id=source-A"),h.env)).json();
    assert.equal(context.context.nodes[0].qualificationHistory.revision,"1");
    assert.equal(h.stats().writes,writes);assert.equal(h.stats().batches,1);
  });


  const acceptanceEnv = h => Object.fromEntries(
    ["ADMIN_EMAIL","CF_ACCESS_TEAM_DOMAIN","CF_ACCESS_AUD","PRIVATE_EVIDENCE",
      "PRIVATE_EVIDENCE_ENABLED","PRIVATE_CORPUS","PRIVATE_CORPUS_ENABLED"]
      .map(key=>[key,h.env[key]]));
  await t.test("acceptance has no execution handlers or public and research routes",async()=>{
    assert.deepEqual(Object.keys(acceptance),["fetch"]);
    const env=new Proxy({}, {get(){throw Error("An unrelated route touched a binding")}});
    for(const path of ["/artifacts/hash","/run","/fleet/run","/feed","/workspace/research-runs","/agents/research-workspace/test","/health","/"]){
      const response=await acceptance.fetch(new Request("https://acceptance.example"+path,{method:"POST"}),env);
      assert.equal(response.status,404);assert.match(response.headers.get("Cache-Control"),/no-store/);
    }
  });
  await t.test("acceptance rejects unexpected bindings and bypass flags before storage or inference",async()=>{
    const h=harness();
    for(const key of ["LEDGER","ARTIFACTS","AI","RESEARCH_QUEUE","ORCHESTRATOR","ANTHROPIC_API_KEY","DEV_MODE","INTERNAL_TASK_TOKEN"]){
      const env=acceptanceEnv(h);
      Object.defineProperty(env,key,{enumerable:true,get(){throw Error("Unexpected binding was read")}});
      const response=await acceptance.fetch(req("/observations"),env);
      assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:"Private acceptance configuration rejected"});
    }
    assert.deepEqual(h.stats(),{reads:0,writes:0,batches:0,storageReads:0});
  });
  await t.test("acceptance reuses operator Access and same-origin denial with disabled defaults",async()=>{
    const h=harness(),env=acceptanceEnv(h);
    assert.equal((await acceptance.fetch(req("/observations","GET",undefined,{"Cf-Access-Jwt-Assertion":""}),env)).status,403);
    assert.equal((await acceptance.fetch(req("/observations","GET",undefined,{"Cf-Access-Jwt-Assertion":await token("other@example.test")}),env)).status,403);
    assert.equal((await acceptance.fetch(req("/observations","GET",undefined,{Origin:"https://other.example"}),env)).status,403);
    assert.equal((await acceptance.fetch(req("/observations"),{...env,PRIVATE_CORPUS_ENABLED:"false"})).status,503);
    assert.deepEqual(h.stats(),{reads:0,writes:0,batches:0,storageReads:0});
  });
  await t.test("acceptance executes the same bounded private receipt import and context path",async()=>{
    const h=harness(),env=acceptanceEnv(h);
    const receipt=await acceptance.fetch(req("/objects/"+sha,"POST"),env);assert.equal(receipt.status,201);
    const r=await row();const imported=await acceptance.fetch(req("/imports/acceptance","PUT",payload([r])),env);
    assert.equal(imported.status,201,await imported.clone().text());
    const read=await acceptance.fetch(req("/source-context?source_id=source-A&import_id=acceptance"),env);
    const out=await read.json();assert.equal(read.status,200);assert.equal(out.context.nodes[0].recordSha256,r.recordSha256);
    assert.equal(out.context.analysis.modelCalls,0);
    const bytes=await acceptance.fetch(new Request("https://research.example/workspace/evidence-objects/"+sha,
      {headers:{"Cf-Access-Jwt-Assertion":jwt}}),env);
    assert.equal(bytes.status,200);assert.equal(await hash(await bytes.arrayBuffer()),sha);
  });
  await t.test("acceptance sanitizes failures and canonical-path rejections without fallback execution",async()=>{
    const h=harness(),env=acceptanceEnv(h);
    assert.equal((await acceptance.fetch(req("//observations"),env)).status,400);
    env.PRIVATE_CORPUS={prepare(){throw Error("PRIVATE_SQL_AND_CREDENTIAL_MARKER")}};
    const response=await acceptance.fetch(req("/observations"),env);
    assert.equal(response.status,503);assert.doesNotMatch(await response.text(),/PRIVATE_SQL_AND_CREDENTIAL_MARKER/);
    assert.equal(h.stats().writes,0);
  });
  await t.test("checked-in acceptance configuration declares disabled storage and no public endpoints",()=>{
    const config=JSON.parse(readFileSync("wrangler.private-evidence-acceptance.json","utf8"));
    assert.equal(config.name,"glim-private-evidence-acceptance");
    assert.equal(config.main,"src/privateEvidenceAcceptance.ts");
    assert.equal(config.workers_dev,false);assert.equal(config.preview_urls,false);
    assert.deepEqual(config.observability,{enabled:false});
    assert.deepEqual(config.vars,{PRIVATE_EVIDENCE_ENABLED:"false",PRIVATE_CORPUS_ENABLED:"false"});
    assert.deepEqual(Object.keys(config).sort(),["name","main","compatibility_date","workers_dev","preview_urls","observability","vars"].sort());
  });

});
