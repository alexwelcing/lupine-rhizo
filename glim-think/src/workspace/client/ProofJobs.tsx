import React, { useEffect, useRef, useState } from "react";
import { PROOF_MODEL, proofFeedSchema, proofId, type ProofFeed } from "../proofContracts";

const labels: Record<string,string> = { queued:"Queued", submitting:"Submission in progress", processing:"Provider processing", cancel_requested:"Cancellation requested", completion_unknown:"Status unknown — no automatic rerun", candidate_ready:"Draft ready · Lean check pending", failed:"Stopped", cancelled:"Cancelled", expired:"Provider job expired", invalid_result:"Result not accepted" };
export function ProofJobs() {
  const [connection,setConnection] = useState("");
  const intentId = useRef(crypto.randomUUID());
  const [recoverIds,setRecoverIds] = useState<Record<string,string>>({});
  const [feed,setFeed] = useState<ProofFeed | null>(null);
  const [error,setError] = useState(""); const [busy,setBusy] = useState(false);
  const [agenda,setAgenda] = useState(""); const [question,setQuestion] = useState("");
  const [task,setTask] = useState(""); const [context,setContext] = useState("");
  const [why,setWhy] = useState(""); const [parent,setParent] = useState(""); const [tokens,setTokens] = useState(16384);
  async function refresh(signal?: AbortSignal) {
    try {
      const r = await fetch("/workspace/proof-jobs",{credentials:"same-origin",cache:"no-store",signal});
      if (!r.ok) throw new Error("Proof jobs are unavailable. Sign in or try Refresh.");
      const next=proofFeedSchema.parse(await r.json()); if (!signal?.aborted) {setFeed(next);setError("");}
    } catch(e) { if (!signal?.aborted) setError(e instanceof Error ? e.message : "Unable to load proof jobs"); }
  }
  useEffect(() => {
    const controller=new AbortController(); void refresh(controller.signal);
    const timer=setInterval(() => {if (!document.hidden) void refresh(controller.signal);},30000);
    return () => {controller.abort();clearInterval(timer);};
  },[]);
  async function post(path: string, body: unknown) {
    const r=await fetch(path,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if (!r.ok) throw new Error(r.status===409 ? "This investigation already has a job or this ID was used. Inspect it before starting more work." : "The request was not confirmed. Refresh to inspect its saved state; do not submit it again under another ID.");
    return r.json();
  }
  async function queue(event: React.FormEvent) {
    event.preventDefault();setBusy(true);setError("");
    try {
      await post("/workspace/proof-jobs",{id:intentId.current,agendaTaskId:agenda,question,task,context,justification:why,maxOutputTokens:tokens,
        ...(parent ? {parentJobId:parent}:{}),reviewedForPrivateWorkspace:true,apiUseAuthorized:true});
      intentId.current=crypto.randomUUID();setTask("");setContext(""); await refresh();
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  async function cancel(id:string) {
    setBusy(true);setError("");try {await post(`/workspace/proof-jobs/${id}/cancel`,{});await refresh();}
    catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  async function checkConnection() {
    setBusy(true);try {
      const r=await fetch("/workspace/proof-jobs/connection",{credentials:"same-origin",cache:"no-store"});
      if(!r.ok)throw new Error("Connection check unavailable");
      const v=await r.json() as {available:boolean;model:string;diagnostic:string|null;observedAt:string};
      setConnection(v.available ? `API connection verified for ${v.model}. No inference was started.` : `API connection not confirmed: ${v.diagnostic ?? "unknown"}.`);
    }catch{setConnection("Connection check failed; no inference was started.");}finally{setBusy(false);}
  }
  async function recover(id:string) {
    setBusy(true);setError("");try {await post(`/workspace/proof-jobs/${id}/recover`,{batchId:recoverIds[id],reviewedProviderIdentity:true});await refresh();}
    catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  const date=(s:string|null) => s ? new Date(s).toLocaleString() : "Not yet observed";
  return <main className="workspace-main progress-main proof-main">
    <header className="progress-header"><div><p className="research-label">CLOUDFLARE RESEARCH WORKFLOW</p><h1>Proof jobs</h1><p>Opus drafts, saved progress, and results in one durable place.</p></div><button onClick={()=>void refresh()} disabled={busy}>Refresh</button></header>
    <div className="progress-scope"><p>Cloudflare coordinates the work. Anthropic processes the request asynchronously. A draft still needs a separate Lean check.</p></div>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="progress-feed">
      <button disabled={busy} onClick={()=>void checkConnection()}>Check API connection</button>
      {connection && <p role="status">{connection}</p>}
      {feed && <><p className="research-run-meta">Retrieved {date(feed.retrievedAt)} · {PROOF_MODEL} · No automatic model retries</p>
        {!feed.configuration.ready && <p className="notice">Native proof execution is not enabled here. {feed.configuration.credentialConfigured ? "An API credential is configured; activation and the output allowance still need to be set." : "This deployment needs its Anthropic API connection and output allowance."} Existing saved jobs remain visible.</p>}
        <details className="proof-compose"><summary>New proof job</summary><form onSubmit={queue}>
          <p>Queue one reviewed brief using the configured Anthropic API allowance. Do not paste raw private archives, credentials, or local machine paths.</p>
          <label>Investigation ID<input required value={agenda} onChange={e=>setAgenda(e.target.value)} maxLength={64}/></label>
          <label>Research question<textarea required value={question} onChange={e=>setQuestion(e.target.value)} maxLength={4000}/></label>
          <label>Proof task<textarea required value={task} onChange={e=>setTask(e.target.value)} maxLength={12000}/></label>
          <label>Reviewed mathematical context<textarea required value={context} onChange={e=>setContext(e.target.value)} maxLength={80000}/></label>
          <label>Why this next step<textarea required value={why} onChange={e=>setWhy(e.target.value)} maxLength={2000}/></label>
          <label>Prior cloud job ID (if this is a distinct follow-up)<input value={parent} onChange={e=>setParent(e.target.value)} maxLength={64}/></label>
          <label>Maximum output tokens<input type="number" min={1024} max={feed.configuration.maxOutputTokens ?? 128000} value={tokens} onChange={e=>setTokens(Number(e.target.value))}/></label>
          <p>The provider may queue the request. There is no five-minute reasoning cutoff; the provider's own batch expiration applies. Only the final candidate and receipt are retained here.</p>
          <button disabled={busy || !feed.configuration.ready || !proofId.safeParse(agenda).success}>Queue Opus proof</button>
        </form></details>
        {feed.jobs.length===0 && <div className="feed-placeholder"><h2>No cloud proof jobs yet</h2><p>Earlier local attempts are separate records. Moving the workflow here does not restart them.</p></div>}
        {feed.jobs.map(job=><article className="research-run" key={job.id}>
          <header><div className="research-topline"><span>{labels[job.displayStatus]}</span></div><h2>{job.request.question}</h2><p>{job.request.justification}</p>
            <p className="research-run-meta">Created {date(job.createdAt)} · Provider last observed {date(job.observedAt)}</p></header>
          <div className="research-stage-results"><p>Investigation: {job.request.agendaTaskId}</p>
            {job.displayStatus==="completion_unknown" && <p>Completion is unconfirmed. This investigation remains reserved to prevent duplicate execution.</p>}
            {job.provider && <p>Provider state: {job.provider.processing_status.replaceAll("_"," ")} · expires {date(job.provider.expires_at)}</p>}
            {job.failureCode && <p>Last diagnostic: {job.failureCode.replaceAll("_"," ")}</p>}
            {job.candidate && <><h3>Returned draft</h3><p>{job.candidate.proof_scope}</p><p><strong>Compilation has not run.</strong> No theorem is marked proved by this result.</p>
              <details><summary>Lean source</summary><pre>{job.candidate.lean_source}</pre></details>
              <h4>Remaining obligations</h4><ul>{job.candidate.remaining_obligations.map((v,i)=><li key={i}>{v}</li>)}</ul>
              <h4>Assumptions</h4><ul>{job.candidate.assumptions.map((v,i)=><li key={i}>{v}</li>)}</ul></>}
            <details><summary>Execution record</summary><p>Job {job.id}</p><p>Provider batch {job.batchId ?? "Not confirmed"}</p><p>Candidate fingerprint {job.candidateSha256 ?? "Not available"}</p><p>Cloud API job · exact Opus model · no tools · no automatic resubmission</p></details>
            {job.status==="completion_unknown" && !job.batchId && <details className="proof-compose"><summary>Recover an existing provider result</summary>
              <p>Enter the original batch ID from Anthropic. Recovery reads that batch and requires a finished result matching this exact job. It never starts another request.</p>
              <label>Existing provider batch ID<input value={recoverIds[job.id] ?? ""} onChange={e=>setRecoverIds({...recoverIds,[job.id]:e.target.value})}/></label>
              <button disabled={busy || !/^msgbatch_[A-Za-z0-9]+$/.test(recoverIds[job.id] ?? "")} onClick={()=>void recover(job.id)}>Verify and collect original result</button>
            </details>}
            {job.active && job.status!=="cancel_requested" && !(job.status==="completion_unknown" && !job.batchId) && <button disabled={busy} onClick={()=>void cancel(job.id)}>Request cancellation</button>}
          </div></article>)}
        {feed.truncated && <p>Showing the 20 newest jobs. Older records remain available by job ID.</p>}</>}
    </section>
  </main>;
}
