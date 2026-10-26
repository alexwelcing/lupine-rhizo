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

const { corpusResponse: route } = await import(loadTs("src/workspace/corpus.ts"));
const { evidenceObjectsResponse } = await import(loadTs("src/workspace/evidenceObjects.ts"));
const { dispatchPrivateEvidence } = await import(loadTs("src/workspace/evidenceDispatch.ts"));
const hash = async bytes => Buffer.from(await crypto.subtle.digest("SHA-256", bytes)).toString("hex");
const raw = new TextEncoder().encode("synthetic public source bytes for integration checks\n");
const sha = await hash(raw);
const root = "https://research.example/workspace/corpus";
const schema = readFileSync("corpus-migrations/0001_private_corpus.sql","utf8");
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
    sql.exec("PRAGMA foreign_keys=ON;"+schema);
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

});
