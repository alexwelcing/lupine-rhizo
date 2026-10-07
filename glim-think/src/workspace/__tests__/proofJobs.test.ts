import { afterEach, describe, expect, it, vi } from "vitest";
// @ts-expect-error Test-only Node SQLite.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Test-only fixture loading.
import { readFileSync } from "node:fs";
import { advanceProofJob, enqueueProof, listProofJobs, requestProofCancellation, recoverProofJob, tickProofJobs, type ProofEnv } from "../proofJobs";
import { batchBody, boundedText, collectCandidate, proofConfiguration } from "../proofProvider";
import { displayedProofStatus, PROOF_MODEL, proofRequestSchema, type ProofRequest } from "../proofContracts";
const fixtureBase=(import.meta as ImportMeta & {url:string}).url;
const migration=readFileSync(new URL("../../../migrations/0022_proof_jobs.sql",fixtureBase),"utf8");
const dbs: InstanceType<typeof DatabaseSync>[]=[];
afterEach(()=>{vi.unstubAllGlobals();for(const db of dbs.splice(0))db.close();});
function harness() {
  const db=new DatabaseSync(":memory:");dbs.push(db);db.exec(migration);
  const stmt=(sql:string,values:unknown[]=[]):D1PreparedStatement=>({
    bind:(...v:unknown[])=>stmt(sql,v),first:async()=>db.prepare(sql).get(...values)??null,
    all:async()=>({success:true,results:db.prepare(sql).all(...values)}),
    run:async()=>({success:true,results:[],meta:{changes:Number(db.prepare(sql).run(...values).changes)}}),
  } as unknown as D1PreparedStatement);
  const env:ProofEnv={LEDGER:{prepare:stmt} as D1Database,ANTHROPIC_API_KEY:"test-key",PROOF_JOBS_ENABLED:"true",PROOF_API_MAX_TOKENS:"32768"};
  return {db,env};
}
const request:ProofRequest={id:"proof-1",agendaTaskId:"periodic-certificate",question:"Does this finite certificate suffice?",task:"Draft a proof for the supplied lemma",context:"Finite integers and real distances",justification:"Resolve the finite enumeration obligation",maxOutputTokens:16384,reviewedForPrivateWorkspace:true,apiUseAuthorized:true};
const batch=(ended=false)=>({id:"msgbatch_test",type:"message_batch",processing_status:ended?"ended":"in_progress",request_counts:{processing:ended?0:1,succeeded:ended?1:0,errored:0,canceled:0,expired:0},created_at:"2026-10-07T03:00:00Z",ended_at:ended?"2026-10-07T03:30:00Z":null,expires_at:"2026-10-08T03:00:00Z",cancel_initiated_at:null,results_url:ended?"https://evil.test/leak-key":null});
const candidate={schema_version:1,job_id:"proof-1",artifact_kind:"lean_source_candidate",lean_source:"theorem smoke : True := by trivial",proof_scope:"A smoke fixture, not a research result",assumptions:[],remaining_obligations:[],verification_notes:"Not checked",compilation:"not_run"};
const result=()=>({custom_id:"proof-1",result:{type:"succeeded",message:{id:"msg_test",type:"message",role:"assistant",model:PROOF_MODEL,stop_reason:"end_turn",usage:{input_tokens:10,output_tokens:20},content:[{type:"thinking",thinking:"private-reasoning"},{type:"text",text:JSON.stringify(candidate)}]}}});
function provider() {
  const fn=vi.fn(async(input:string,init?:RequestInit)=>{
    expect(input.startsWith("https://api.anthropic.com/v1/messages/batches")).toBe(true);
    expect(init?.redirect).toBe("error");
    if(input.endsWith("/results"))return new Response(JSON.stringify(result())+"\n");
    return Response.json(batch(init?.method==="GET"));
  });vi.stubGlobal("fetch",fn);return fn;
}

describe("native cloud proof lifecycle with real SQLite",()=>{
  it("submits once, survives a new tick, and retains only the checked candidate",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);
    await tickProofJobs(h.env);expect((await listProofJobs(h.env)).jobs[0].status).toBe("processing");
    await tickProofJobs(h.env);const job=(await listProofJobs(h.env)).jobs[0];
    expect(job.status).toBe("candidate_ready");expect(job.active).toBe(false);expect(job.candidate?.compilation).toBe("not_run");
    expect(job.candidateSha256).toMatch(/^[a-f0-9]{64}$/);expect(f.mock.calls.filter(c=>c[1]?.method==="POST")).toHaveLength(1);
    expect(JSON.stringify(h.db.prepare("SELECT * FROM proof_jobs").get())).not.toContain("private-reasoning");
    await tickProofJobs(h.env);expect(f).toHaveBeenCalledTimes(3);
  });
  it("atomically fences concurrent ticks and enforces one active job per investigation",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);
    await expect(enqueueProof(h.env,{...request,id:"proof-2"})).rejects.toThrow("already_active");
    await Promise.all([advanceProofJob(h.env,request.id),advanceProofJob(h.env,request.id)]);
    expect(f.mock.calls.filter(c=>c[1]?.method==="POST")).toHaveLength(1);
  });
  it("acknowledges identical creation without replay, rejects changed IDs",async()=>{
    const h=harness();await enqueueProof(h.env,request);expect((await enqueueProof(h.env,request)).duplicate).toBe(true);
    await expect(enqueueProof(h.env,{...request,task:"different"})).rejects.toThrow("conflict");
  });
  it("keeps a lost POST response unknown and never submits again",async()=>{
    const h=harness();const f=vi.fn(async()=>{throw new TypeError("connection lost");});vi.stubGlobal("fetch",f);
    await enqueueProof(h.env,request);await tickProofJobs(h.env);await tickProofJobs(h.env);await advanceProofJob(h.env,request.id);
    expect(f).toHaveBeenCalledOnce();expect((await listProofJobs(h.env)).jobs[0]).toMatchObject({status:"completion_unknown",active:true});
  });
  it("recovers a lost acknowledgement only by matching a finished provider result",async()=>{
    const h=harness();await enqueueProof(h.env,request);h.db.exec("UPDATE proof_jobs SET status='completion_unknown'");
    const f=provider();const recovered=await recoverProofJob(h.env,request.id,{batchId:"msgbatch_test",reviewedProviderIdentity:true});
    expect(recovered.status).toBe("candidate_ready");expect(recovered.active).toBe(false);
    expect(f.mock.calls.every(c=>c[1]?.method==="GET")).toBe(true);
    await tickProofJobs(h.env);expect(f).toHaveBeenCalledTimes(2);
  });
  it("does not release unknown work based only on delivery or an unrelated result",async()=>{
    const h=harness();await enqueueProof(h.env,request);h.db.exec("UPDATE proof_jobs SET status='completion_unknown'");
    vi.stubGlobal("fetch",vi.fn(async()=>Response.json(batch())));
    await expect(recoverProofJob(h.env,request.id,{batchId:"msgbatch_test",reviewedProviderIdentity:true})).rejects.toThrow("waiting");
    const f=provider();const entry=result();entry.custom_id="another-proof";
    f.mockResolvedValueOnce(Response.json(batch(true))).mockResolvedValueOnce(Response.json(entry));
    await expect(recoverProofJob(h.env,request.id,{batchId:"msgbatch_test",reviewedProviderIdentity:true})).rejects.toThrow("mismatch");
    expect((await listProofJobs(h.env)).jobs[0]).toMatchObject({active:true,batchId:null});
  });
  it("survives a crash after intent was stored without replaying the provider POST",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);
    h.db.exec("UPDATE proof_jobs SET status='submitting'");await tickProofJobs(h.env);expect(f).not.toHaveBeenCalled();
    expect((await listProofJobs(h.env)).jobs[0].status).toBe("completion_unknown");
  });
  it("keeps confirmed failures immutable and requires an explicitly distinct follow-up",async()=>{
    const h=harness();const f=vi.fn(async()=>new Response("untrusted secret",{status:403}));vi.stubGlobal("fetch",f);
    await enqueueProof(h.env,request);await tickProofJobs(h.env);await tickProofJobs(h.env);
    expect(f).toHaveBeenCalledOnce();expect((await listProofJobs(h.env)).jobs[0]).toMatchObject({status:"failed",active:false,failureCode:"provider_http_403"});
    expect((await enqueueProof(h.env,request)).duplicate).toBe(true);
    const next=await enqueueProof(h.env,{...request,id:"proof-2",parentJobId:"proof-1",justification:"A distinct corrected hypothesis"});expect(next.job.status).toBe("queued");
  });
  it("cancels queued work without a model call",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);await requestProofCancellation(h.env,request.id);await tickProofJobs(h.env);
    expect(f).not.toHaveBeenCalled();expect((await listProofJobs(h.env)).jobs[0]).toMatchObject({status:"cancelled",active:false});
  });
  it("preserves cancellation requested during submission and sends cancellation once",async()=>{
    const h=harness();let count=0;
    const f=vi.fn(async(url:string,init?:RequestInit)=>{
      if(init?.method==="POST" && !url.endsWith("cancel")){await requestProofCancellation(h.env,request.id);return Response.json(batch());}
      if(url.endsWith("cancel")){count++;throw new TypeError("lost cancellation acknowledgement");}
      return Response.json(batch());
    });vi.stubGlobal("fetch",f);await enqueueProof(h.env,request);await tickProofJobs(h.env);
    expect((await listProofJobs(h.env)).jobs[0].status).toBe("cancel_requested");
    await tickProofJobs(h.env);await tickProofJobs(h.env);expect(count).toBe(1);expect((await listProofJobs(h.env)).jobs[0].active).toBe(true);
  });
  it("can accept a real completion even if cancellation arrived too late",async()=>{
    const h=harness();provider();await enqueueProof(h.env,request);await tickProofJobs(h.env);await requestProofCancellation(h.env,request.id);await tickProofJobs(h.env);
    expect((await listProofJobs(h.env)).jobs[0].status).toBe("candidate_ready");
  });
  it("recovers GET failures without replaying inference",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);await tickProofJobs(h.env);
    f.mockRejectedValueOnce(new TypeError("temporary read outage"));await tickProofJobs(h.env);await tickProofJobs(h.env);
    expect((await listProofJobs(h.env)).jobs[0].status).toBe("candidate_ready");expect(f.mock.calls.filter(c=>c[1]?.method==="POST")).toHaveLength(1);
  });
  it("pausing submission still permits collecting an already submitted provider job",async()=>{
    const h=harness();provider();await enqueueProof(h.env,request);await tickProofJobs(h.env);h.env.PROOF_JOBS_ENABLED="false";await tickProofJobs(h.env);
    expect((await listProofJobs(h.env)).jobs[0].status).toBe("candidate_ready");
  });
  it("reports stale observations as unknown without releasing the active reservation",async()=>{
    const h=harness();await enqueueProof(h.env,request);h.db.exec("UPDATE proof_jobs SET status='processing',observed_at='2026-01-01T00:00:00Z'");
    expect((await listProofJobs(h.env)).jobs[0]).toMatchObject({displayStatus:"completion_unknown",active:true});
    expect(displayedProofStatus("candidate_ready",null,"2020-01-01T00:00:00Z")).toBe("candidate_ready");
  });
  it("requires API activation, credential and a bounded configured budget",async()=>{
    const h=harness();h.env.ANTHROPIC_API_KEY=undefined;
    expect(proofConfiguration(h.env).ready).toBe(false);await expect(enqueueProof(h.env,request)).rejects.toThrow("not_enabled");
    h.env.ANTHROPIC_API_KEY="key";h.env.PROOF_API_MAX_TOKENS="2048";await expect(enqueueProof(h.env,request)).rejects.toThrow("budget");
    h.env.PROOF_API_MAX_TOKENS="NaN";expect(proofConfiguration(h.env).ready).toBe(false);
  });
  it("rejects execution-shaped extras, unreviewed input, local paths and unknown parents",async()=>{
    const h=harness();for(const extra of [{model:"fable"},{command:"run"},{reviewedForPrivateWorkspace:false},{context:"/home/alex/private"},{apiUseAuthorized:false}])expect(proofRequestSchema.safeParse({...request,...extra}).success).toBe(false);
    await expect(enqueueProof(h.env,{...request,parentJobId:"missing"})).rejects.toThrow("parent");
  });
  it("detects corrupt persisted inputs before inference",async()=>{
    const h=harness();const f=provider();await enqueueProof(h.env,request);h.db.exec("UPDATE proof_jobs SET request_sha256='wrong'");await tickProofJobs(h.env);expect(f).not.toHaveBeenCalled();
    await expect(listProofJobs(h.env)).rejects.toThrow("fingerprint");
  });
});

describe("provider result boundaries",()=>{
  it.each(["wrong model","tool call","wrong job","truncation","multiple results","oversized candidate"])("rejects %s",async(kind)=>{
    const h=harness();const entry=result();
    if(kind==="wrong model")entry.result.message.model="claude-fable-5-1";
    if(kind==="tool call")entry.result.message.content=[{type:"tool_use",text:"execute"}];
    if(kind==="wrong job")entry.custom_id="other";
    if(kind==="truncation")entry.result.message.stop_reason="max_tokens";
    if(kind==="oversized candidate")entry.result.message.content=[{type:"text",text:"x".repeat(56001)}];
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify(entry)+(kind==="multiple results"?"\n"+JSON.stringify(entry):""))));
    await expect(collectCandidate(h.env,"msgbatch_test","proof-1")).rejects.toThrow();
  });
  it.each(["errored","canceled","expired"])("records provider %s honestly",async(type)=>{
    const h=harness();vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({custom_id:"proof-1",result:{type}}))));
    expect((await collectCandidate(h.env,"msgbatch_test","proof-1")).candidate).toBeNull();
  });
  it("never follows provider result URLs and strips reasoning even when large",async()=>{
    const h=harness();const entry=result();entry.result.message.content[0].thinking="x".repeat(900000);
    const f=vi.fn(async(_url: string)=>new Response(JSON.stringify(entry)));vi.stubGlobal("fetch",f);
    const got=await collectCandidate(h.env,"msgbatch_test","proof-1");expect(got.status).toBe("candidate_ready");
    expect(JSON.stringify(got).length).toBeLessThan(2000);expect(f.mock.calls[0]?.[0]).toBe("https://api.anthropic.com/v1/messages/batches/msgbatch_test/results");
  });
  it("bounds network frames and never saves a partial response",async()=>{await expect(boundedText(new Response("12345"),4)).rejects.toThrow("too_large");});
  it("pins Opus with no tools and one request, while bounding the returned candidate separately",()=>{
    const body=batchBody(request);expect(body.requests).toHaveLength(1);expect(body.requests[0].params).toMatchObject({model:PROOF_MODEL,tools:[],max_tokens:16384});
    expect(body.requests[0].params).not.toHaveProperty("stream");expect(JSON.stringify(body)).not.toContain("fable");
  });
});
