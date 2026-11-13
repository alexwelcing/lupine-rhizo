import { DurableObject } from 'cloudflare:workers';
import { canonical, sha256, assertRunner } from './runner-contract';
import { createDurableCodingScheduler } from './scheduler-storage';
import { getCodingAttempt } from './ledger';
import type { CodingScheduler, CodingSchedulerPolicy, CodingSchedulerGate, CodingSchedulerNoModelDispatchInput } from './scheduler-state';
import type { CodingRunnerEnv } from './runner-worker';
import { codingBrokerCall } from './model-bridge';

export { claimScheduledAgenda } from './scheduler-agenda';
import { claimScheduledAgenda } from './scheduler-agenda';

export class CodingSchedule extends DurableObject<CodingRunnerEnv> {
  private scheduler:CodingScheduler;
  constructor(ctx:DurableObjectState,env:CodingRunnerEnv){
    super(ctx,env);
    this.scheduler=createDurableCodingScheduler(ctx.storage,{
      claimAgenda:(task,hash,owner)=>claimScheduledAgenda(env.LEDGER,task,hash,owner),
      gate:async(task):Promise<CodingSchedulerGate>=>{
        const blob=await env.CODING_EVIDENCE.head(task.source.artifactKey);
        if(!blob||blob.size!==task.source.bytes)return {state:'blocked',reason:'gate-blocked'};
        if(!task.model)return {state:'ready',reason:'gate-ready',receiptSha256:await sha256(canonical({sourceSha256:task.source.sha256,observedAt:Date.now(),model:null}))};
        if(!env.CODING_MODELS)return {state:'wait',reason:'route-unavailable'};
        const ready=await codingBrokerCall(env,'ready',{model:task.model.model});
        if(ready.allowed!==true)return {state:'wait',reason:'quota-wait',nextCheckAtMs:Date.now()+900000};
        return {state:'ready',reason:'gate-ready',receiptSha256:await sha256(canonical(ready))};
      },
      submit:task=>env.CODING_RUNNER.getByName(task.attemptId).submit(task),
      status:async identity=>{
        const state=await env.CODING_RUNNER.getByName(identity.attemptId).status();
        if(!state)return null;
        const record=await getCodingAttempt(env.LEDGER,identity.attemptId);
        return {...identity,status:state.status,ledgerRecorded:state.ledgerRecorded&&!!record?.terminal,cleanupConfirmed:state.cleanupConfirmed,
          inputSha256:state.inputSha256,taskId:state.taskId,attemptId:state.attemptId,ownerId:record?.ownerId??identity.ownerId,
          runnerTerminalReceiptSha256:state.receipt?.sha256??null,
          terminal:record?.terminal?{receiptJson:record.terminal.receiptJson,receiptSha256:record.terminal.receiptSha256}:null};
      },
    });
  }
  configure(policy:CodingSchedulerPolicy,expectedPolicySha256:string|null){assertRunner(policy?.ownerId===(this.env.CODING_AGENT_ID??'cloudflare-coding-runner'),'Scheduler owner must match the configured runner');return this.scheduler.configure(policy,expectedPolicySha256);}
  enqueue(value:Parameters<typeof this.scheduler.enqueue>[0]){return this.scheduler.enqueue(value);}
  status(){return this.scheduler.status();}
  stopQueued(attemptId:string){return this.scheduler.stopQueued(attemptId);}
  reconcile(attemptId:string,disposition?:CodingSchedulerNoModelDispatchInput){return this.scheduler.reconcile(attemptId,disposition);}
  async tick(){await this.scheduler.tick();return this.scheduler.status();}
  async alarm(){await this.scheduler.tick();}
}
