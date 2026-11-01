import { DurableObject } from 'cloudflare:workers';
import { codingFetch } from './runner-http';
import { admitCodingAttempt, recordCodingTerminal } from './ledger';
import { CodingRunnerCore, type RunnerContainer, type RunnerStore, type RunnerBlobs } from './runner-core';
import { assertRunner, publicCodingState } from './runner-contract';

export interface CodingRunnerEnv {
  CODING_RUNNER: DurableObjectNamespace<CodingRunner>;
  CODING_EVIDENCE: R2Bucket; LEDGER: D1Database;
  RUNNER_OPERATOR_TOKEN?:string; CODING_AGENT_ID?:string;
  CF_ACCESS_TEAM_DOMAIN?:string;CF_ACCESS_AUD?:string;ADMIN_EMAIL?:string;
}
export class CodingRunner extends DurableObject<CodingRunnerEnv>{
  private core:CodingRunnerCore;
  constructor(ctx:DurableObjectState,env:CodingRunnerEnv){
    super(ctx,env);
    const container=ctx.container as unknown as RunnerContainer|undefined;
    // Construction/status never starts a container. Missing binding is rejected on admission.
    this.core=new CodingRunnerCore({store:ctx.storage as unknown as RunnerStore,container:container as RunnerContainer,blobs:env.CODING_EVIDENCE as unknown as RunnerBlobs,
      admit:input=>admitCodingAttempt(env.LEDGER,input),terminal:input=>recordCodingTerminal(env.LEDGER,input)});
  }
  async submit(raw:unknown){
    assertRunner(this.ctx.container,'Coding container binding unavailable',503);
    const result=await this.core.submit(raw,this.env.CODING_AGENT_ID??'cloudflare-coding-runner');
    if(result.created)this.ctx.waitUntil(this.core.run().catch(()=>{}));
    return {created:result.created,attempt:publicCodingState(result.state)};
  }
  async reconcile(){await this.core.reconcileTerminal();return this.status();}
  async status(){return publicCodingState(await this.core.status());}
  async evidence(hash:string):Promise<Response>{
    assertRunner(/^[0-9a-f]{64}$/.test(hash),'Invalid evidence digest');
    const state=await this.core.status();assertRunner(state,'Attempt not found',404);
    const ref=[...state.evidence,...(state.receipt?[state.receipt]:[])].find(r=>r.sha256===hash);
    assertRunner(ref,'Evidence is not attached to this attempt',404);
    const body=await this.env.CODING_EVIDENCE.get(ref.artifactKey);assertRunner(body&&body.size===ref.bytes,'Evidence unavailable',503);
    return new Response(body.body,{headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Type':'application/octet-stream','Content-Disposition':`attachment; filename="${ref.kind}-${hash}.bin"`,'Content-Length':String(ref.bytes),'X-Content-SHA256':ref.sha256}});
  }
  async alarm(){if(this.ctx.container)await this.core.alarm();}
}
export default {fetch:codingFetch};
