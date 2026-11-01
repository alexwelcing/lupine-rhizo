import { canonical, parseCodingTask, RUNNER_LIMITS, sha256, validId, type CodingTask } from './runner-contract';

export const CODING_SCHEDULER_LIMITS = { queue:128, active:4, history:32, settlementSeconds:30, gateRetryMs:900_000 } as const;
export interface CodingSchedulerStore {
  get<T>(key:string):Promise<T|undefined>;
  put<T>(key:string,value:T):Promise<void>;
  transaction<T>(fn:(tx:CodingSchedulerStore)=>Promise<T>):Promise<T>;
  setAlarm(at:number):Promise<void>;
  deleteAlarm():Promise<void>;
}
export type CodingSchedulerPolicy = {
  schema:'lupine.coding-scheduler-policy.v1'; policyId:string; ownerId:string; enabled:boolean;
  maxConcurrent:number; maxDailyAttempts:number; maxLifetimeAttempts:number;
  maxDailyReservedSeconds:number; maxLifetimeReservedSeconds:number; pollIntervalMs:number;
};
export type CodingSchedulerReason = 'authorized'|'admission-paused'|'gate-ready'|'quota-wait'|'route-unavailable'|'gate-unavailable'|'gate-blocked'|'daily-budget'|'lifetime-budget'|'concurrency-limit'|'authorization-rejected'|'authorization-unknown'|'dispatch-unconfirmed'|'running'|'terminal-confirmed'|'observation-unavailable'|'observation-expired'|'task-expired'|'operator-stopped';
export type CodingSchedulerGate = {state:'ready';reason:'gate-ready';receiptSha256:string}|{state:'wait';reason:'quota-wait'|'route-unavailable'|'gate-unavailable';nextCheckAtMs?:number}|{state:'blocked';reason:'gate-blocked'};
export type CodingSchedulerIdentity = {taskId:string;attemptId:string;inputSha256:string;ownerId:string};
/** Supplied by a trusted adapter reading the existing Runner and ledger, never by guest/model data. */
export type CodingSchedulerObservation = CodingSchedulerIdentity & {
  status:'claimed'|'preparing'|'executing'|'collecting'|'finalizing'|'succeeded'|'failed'|'unknown';
  ledgerRecorded:boolean;cleanupConfirmed:boolean;
  terminal:null|{receiptJson:string;receiptSha256:string};
};
export interface CodingSchedulerDependencies {
  claimAgenda(task:CodingTask,inputSha256:string,ownerId:string):Promise<{authorized:true;receiptSha256:string}|{authorized:false}>;
  /** Metadata-only freshness/quota check. It must not invoke a model or dispatch guest work. */
  gate(task:CodingTask):Promise<CodingSchedulerGate>;
  submit(task:CodingTask):Promise<unknown>;
  status(identity:CodingSchedulerIdentity):Promise<CodingSchedulerObservation|null>;
  now?:()=>number;
  callbackTimeoutMs?:number;
}
type SchedulerState = 'authorization-unknown'|'queued'|'dispatching'|'running'|'unknown'|'terminal'|'blocked'|'expired';
type Dispatch = {policySha256:string;gateReceiptSha256:string;atMs:number;utcDay:string;reservedSeconds:number;observationUntilMs:number};
export type CodingSchedulerRecord = CodingSchedulerIdentity & {
  schema:'lupine.coding-scheduler-task.v1';authorizationId:string;enqueueSha256:string;manifestJson:string;
  createdAtMs:number;notBeforeMs:number;expiresAtMs:number;authorizationReceiptSha256:string|null;
  state:SchedulerState;reason:CodingSchedulerReason;nextCheckAtMs:number|null;dispatch:Dispatch|null;
  terminal:null|{receiptJson:string;receiptSha256:string;observedAtMs:number};
};
type Event = {sequence:number;atMs:number;attemptId:string|null;kind:string;reason:CodingSchedulerReason;receiptSha256:string|null};
type Index = {schema:'lupine.coding-scheduler-index.v1';policySha256:string|null;queue:string[];active:string[];held:string[];recent:string[];history:Event[];
  lifetimeAttempts:number;lifetimeReservedSeconds:number;lastNowMs:number;day:string|null;nextWakeAtMs:number|null;sequence:number};
type Day = {utcDay:string;reservedAttempts:number;reservedSeconds:number;carriedAttemptIds:string[]};
const INDEX='scheduler/index';
const recordKey=(id:string)=>'scheduler/task/'+id;
const HASH=/^[0-9a-f]{64}$/;
const encoder=new TextEncoder();
const initial=():Index=>({schema:'lupine.coding-scheduler-index.v1',policySha256:null,queue:[],active:[],held:[],recent:[],history:[],lifetimeAttempts:0,lifetimeReservedSeconds:0,lastNowMs:0,day:null,nextWakeAtMs:null,sequence:0});
export class CodingSchedulerError extends Error {constructor(readonly code:'invalid-input'|'conflict'|'clock-regressed'|'unavailable',message:string){super(message);}}
function requireThat(value:unknown,message:string):asserts value {if(!value)throw new CodingSchedulerError('invalid-input',message);}
const int=(n:unknown,min:number,max:number)=>Number.isSafeInteger(n)&&Number(n)>=min&&Number(n)<=max;
const remove=(a:string[],id:string)=>a.filter(x=>x!==id);
export const codingReservationSeconds=(task:CodingTask)=>task.timeoutSeconds+RUNNER_LIMITS.setupSeconds+RUNNER_LIMITS.captureSeconds+CODING_SCHEDULER_LIMITS.settlementSeconds;
function policy(value:CodingSchedulerPolicy):CodingSchedulerPolicy {
  const p=structuredClone(value);
  requireThat(p.schema==='lupine.coding-scheduler-policy.v1'&&validId(p.policyId)&&validId(p.ownerId)&&typeof p.enabled==='boolean','Invalid scheduler policy identity');
  requireThat(int(p.maxConcurrent,1,4)&&int(p.maxDailyAttempts,1,100)&&int(p.maxLifetimeAttempts,p.maxDailyAttempts,10000),'Invalid scheduler attempt limits');
  requireThat(int(p.maxDailyReservedSeconds,1,345600)&&int(p.maxLifetimeReservedSeconds,p.maxDailyReservedSeconds,31_622_400)&&int(p.pollIntervalMs,5000,60000),'Invalid scheduler time limits');
  requireThat(Object.keys(p).sort().join(',')==='enabled,maxConcurrent,maxDailyAttempts,maxDailyReservedSeconds,maxLifetimeAttempts,maxLifetimeReservedSeconds,ownerId,policyId,pollIntervalMs,schema','Unexpected scheduler policy fields');
  return p;
}

/** A single serialized authority. Once dispatch intent exists, no code path submits that task again. */
export class CodingScheduler {
  constructor(private readonly store:CodingSchedulerStore,private readonly deps:CodingSchedulerDependencies){}
  private now(){const n=(this.deps.now??Date.now)();requireThat(int(n,1,8_640_000_000_000_000),'Invalid server clock');return n;}
  private async call<T>(operation:()=>Promise<T>):Promise<T>{
    let timer:ReturnType<typeof setTimeout>|undefined;const promise=Promise.resolve().then(operation);void promise.catch(()=>{});
    try{return await Promise.race([promise,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new CodingSchedulerError('unavailable','Scheduler callback outcome unavailable')),this.deps.callbackTimeoutMs??10000);})]);}
    finally{if(timer!==undefined)clearTimeout(timer);}
  }
  private async context(tx:CodingSchedulerStore){
    const index=(await tx.get<Index>(INDEX))??initial(),now=this.now();
    if(now<index.lastNowMs)throw new CodingSchedulerError('clock-regressed','Server clock moved backwards; scheduler held');
    index.lastNowMs=now;const day=new Date(now).toISOString().slice(0,10);let daily=await tx.get<Day>('scheduler/day/'+day);
    if(!daily){daily={utcDay:day,reservedAttempts:0,reservedSeconds:0,carriedAttemptIds:[]};
      for(const id of index.active){const record=await tx.get<CodingSchedulerRecord>(recordKey(id));if(record?.dispatch){daily.reservedAttempts++;daily.reservedSeconds+=record.dispatch.reservedSeconds;daily.carriedAttemptIds.push(id);}}
      await tx.put('scheduler/day/'+day,daily);
    }
    index.day=day;const selected=index.policySha256?await tx.get<CodingSchedulerPolicy>('scheduler/policy/'+index.policySha256):undefined;
    return {index,now,daily,policy:selected};
  }
  private async event(tx:CodingSchedulerStore,index:Index,now:number,id:string|null,kind:string,reason:CodingSchedulerReason,receiptSha256:string|null=null){
    const event:Event={sequence:++index.sequence,atMs:now,attemptId:id,kind,reason,receiptSha256};
    await tx.put('scheduler/event/'+event.sequence.toString().padStart(12,'0'),event);
    index.history=[...index.history,event].slice(-CODING_SCHEDULER_LIMITS.history);
    if(id)index.recent=[...remove(index.recent,id),id].slice(-CODING_SCHEDULER_LIMITS.history);
  }
  private async persist(tx:CodingSchedulerStore,index:Index,now:number,p?:CodingSchedulerPolicy){
    let next:number|null=null;
    for(const id of [...index.active,...(p?.enabled?index.queue:[])]){
      const r=await tx.get<CodingSchedulerRecord>(recordKey(id));if(!r)continue;
      const at=r.nextCheckAtMs;if(at!==null)next=next===null?Math.max(now+1,at):Math.min(next,Math.max(now+1,at));
    }
    index.nextWakeAtMs=next;await tx.put(INDEX,index);if(next===null)await tx.deleteAlarm();else await tx.setAlarm(next);
  }
  async configure(supplied:CodingSchedulerPolicy,expectedPolicySha256:string|null){
    const value=policy(supplied),hash=await sha256(canonical(value));
    return this.store.transaction(async tx=>{const c=await this.context(tx);
      if(c.index.policySha256!==expectedPolicySha256&&c.index.policySha256!==hash)throw new CodingSchedulerError('conflict','Policy revision conflict');
      if(c.policy&&c.policy.ownerId!==value.ownerId)throw new CodingSchedulerError('conflict','Scheduler owner is immutable');
      if(c.index.policySha256!==hash){await tx.put('scheduler/policy/'+hash,value);c.index.policySha256=hash;await this.event(tx,c.index,c.now,null,'policy',value.enabled?'authorized':'admission-paused',hash);}
      await this.persist(tx,c.index,c.now,value);return {policySha256:hash,policy:value};
    });
  }
  async enqueue(supplied:{task:unknown;authorizationId:string;expiresAtMs:number;notBeforeMs?:number}){
    const task=parseCodingTask(supplied.task),authorizationId=supplied.authorizationId,expiresAtMs=supplied.expiresAtMs,notBeforeMs=supplied.notBeforeMs??0;
    requireThat(validId(authorizationId)&&int(expiresAtMs,1,8_640_000_000_000_000)&&int(notBeforeMs,0,expiresAtMs-1),'Invalid task authorization interval');
    const manifestJson=canonical(task);requireThat(encoder.encode(manifestJson).length<=RUNNER_LIMITS.manifestBytes,'Manifest exceeds bound');
    const inputSha256=await sha256(manifestJson),enqueueSha256=await sha256(canonical({inputSha256,authorizationId,expiresAtMs,notBeforeMs}));
    const admission=await this.store.transaction(async tx=>{const c=await this.context(tx);requireThat(c.policy,'Scheduler is not configured');
      const old=await tx.get<CodingSchedulerRecord>(recordKey(task.attemptId)),priorTask=await tx.get<string>('scheduler/task-id/'+task.taskId);
      if(old){if(old.enqueueSha256!==enqueueSha256||old.taskId!==task.taskId)throw new CodingSchedulerError('conflict','Immutable task authorization conflict');return {created:false,record:old};}
      if(priorTask)throw new CodingSchedulerError('conflict','Task already has a scheduler attempt');
      requireThat(expiresAtMs>c.now&&expiresAtMs<=c.now+7*86400000,'Authorization must expire within seven days');
      requireThat(c.index.queue.length+c.index.held.length<CODING_SCHEDULER_LIMITS.queue,'Scheduler queue/holds at capacity');
      const record:CodingSchedulerRecord={schema:'lupine.coding-scheduler-task.v1',taskId:task.taskId,attemptId:task.attemptId,inputSha256,ownerId:c.policy.ownerId,authorizationId,enqueueSha256,manifestJson,
        createdAtMs:c.now,notBeforeMs,expiresAtMs,authorizationReceiptSha256:null,state:'authorization-unknown',reason:'authorization-unknown',nextCheckAtMs:null,dispatch:null,terminal:null};
      await tx.put(recordKey(task.attemptId),record);await tx.put('scheduler/task-id/'+task.taskId,task.attemptId);c.index.held.push(task.attemptId);
      await this.event(tx,c.index,c.now,task.attemptId,'authorization-intent','authorization-unknown');await this.persist(tx,c.index,c.now,c.policy);return {created:true,record};
    });
    if(!admission.created)return admission;
    let proof:{authorized:true;receiptSha256:string}|{authorized:false};
    try{proof=await this.call(()=>this.deps.claimAgenda(structuredClone(task),inputSha256,admission.record.ownerId));}catch{return admission;}
    if(proof.authorized&&!HASH.test(proof.receiptSha256))return admission;
    const record=await this.store.transaction(async tx=>{const c=await this.context(tx),r=(await tx.get<CodingSchedulerRecord>(recordKey(task.attemptId)))!;
      requireThat(r.state==='authorization-unknown'&&r.enqueueSha256===enqueueSha256,'Authorization state changed');
      if(!proof.authorized){r.state='blocked';r.reason='authorization-rejected';}
      else if(c.now>=r.expiresAtMs){r.state='expired';r.reason='task-expired';c.index.held=remove(c.index.held,r.attemptId);}
      else{r.authorizationReceiptSha256=proof.receiptSha256;r.state='queued';r.reason='authorized';r.nextCheckAtMs=Math.max(c.now,r.notBeforeMs);c.index.held=remove(c.index.held,r.attemptId);c.index.queue.push(r.attemptId);}
      await tx.put(recordKey(r.attemptId),r);await this.event(tx,c.index,c.now,r.attemptId,'authorization-outcome',r.reason,r.authorizationReceiptSha256);await this.persist(tx,c.index,c.now,c.policy);return r;
    });return {created:true,record};
  }
  private async terminalMatches(r:CodingSchedulerRecord,o:CodingSchedulerObservation){
    if(o.taskId!==r.taskId||o.attemptId!==r.attemptId||o.inputSha256!==r.inputSha256||o.ownerId!==r.ownerId)throw new CodingSchedulerError('conflict','Runner identity mismatch');
    if(!o.ledgerRecorded||!o.cleanupConfirmed||!o.terminal||!['succeeded','failed','unknown'].includes(o.status))return null;
    requireThat(typeof o.terminal.receiptJson==='string'&&encoder.encode(o.terminal.receiptJson).length<=65536&&HASH.test(o.terminal.receiptSha256),'Invalid bounded terminal receipt');
    requireThat(await sha256(o.terminal.receiptJson)===o.terminal.receiptSha256,'Terminal receipt hash mismatch');
    const p=JSON.parse(o.terminal.receiptJson);
    requireThat(p.schema==='lupine.coding-terminal.v1'&&p.taskId===r.taskId&&p.attemptId===r.attemptId&&p.inputSha256===r.inputSha256&&p.ownerId===r.ownerId&&p.outcome===o.status&&p.cleanupConfirmed===true,'Terminal receipt identity mismatch');
    // An execution-unknown result never releases its scheduler concurrency hold automatically.
    return o.status==='unknown'?'unknown':'settled';
  }
  private async observe(attemptId:string,force=false){
    const before=await this.store.get<CodingSchedulerRecord>(recordKey(attemptId));if(!before?.dispatch||before.terminal||(!force&&(before.nextCheckAtMs===null||before.nextCheckAtMs>this.now())))return;
    let observation:CodingSchedulerObservation|null=null,terminal:'settled'|'unknown'|null=null;
    try{observation=await this.call(()=>this.deps.status({taskId:before.taskId,attemptId:before.attemptId,inputSha256:before.inputSha256,ownerId:before.ownerId}));if(observation)terminal=await this.terminalMatches(before,observation);}catch{observation=null;}
    await this.store.transaction(async tx=>{const c=await this.context(tx),r=await tx.get<CodingSchedulerRecord>(recordKey(attemptId));if(!r?.dispatch||r.terminal)return;
      if(terminal&&observation?.terminal){r.terminal={...observation.terminal,observedAtMs:c.now};r.state=terminal==='settled'?'terminal':'unknown';r.reason=terminal==='settled'?'terminal-confirmed':'dispatch-unconfirmed';r.nextCheckAtMs=null;if(terminal==='settled')c.index.active=remove(c.index.active,attemptId);}
      else{r.state=observation&&observation.status!=='unknown'?'running':'unknown';r.reason=c.now>=r.dispatch.observationUntilMs?'observation-expired':observation?(observation.status==='unknown'?'dispatch-unconfirmed':'running'):'observation-unavailable';
        r.nextCheckAtMs=c.now>=r.dispatch.observationUntilMs?null:Math.min(r.dispatch.observationUntilMs,c.now+(c.policy?.pollIntervalMs??60000));}
      await tx.put(recordKey(attemptId),r);await this.event(tx,c.index,c.now,attemptId,'observation',r.reason,r.terminal?.receiptSha256??null);await this.persist(tx,c.index,c.now,c.policy);
    });
  }
  /** Explicit metadata-only recovery after automatic observation expiry; never resubmits. */
  async reconcile(attemptId:string){requireThat(validId(attemptId),'Invalid attempt');await this.observe(attemptId,true);return this.status();}
  /** Stops only undispatched authorization. It cannot cancel a running guest or refund a reservation. */
  async stopQueued(attemptId:string){requireThat(validId(attemptId),'Invalid attempt');await this.store.transaction(async tx=>{
    const c=await this.context(tx),r=await tx.get<CodingSchedulerRecord>(recordKey(attemptId));requireThat(r,'Attempt unavailable');
    if(r.dispatch)throw new CodingSchedulerError('conflict','Dispatched attempts cannot be stopped by queue control');
    if(r.reason==='operator-stopped')return;
    r.state='blocked';r.reason='operator-stopped';r.nextCheckAtMs=null;c.index.queue=remove(c.index.queue,attemptId);if(!c.index.held.includes(attemptId))c.index.held.push(attemptId);
    await tx.put(recordKey(attemptId),r);await this.event(tx,c.index,c.now,attemptId,'operator-stop',r.reason);await this.persist(tx,c.index,c.now,c.policy);
  });return this.status();}
  async tick(){
    const first=await this.store.transaction(async tx=>{const c=await this.context(tx);await this.persist(tx,c.index,c.now,c.policy);return c.index;});
    for(const id of first.active.slice(0,CODING_SCHEDULER_LIMITS.active))await this.observe(id);
    // Inspect a bounded queue, but admit at most maxConcurrent tasks and never synthesize work.
    let gateChecks=0;
    for(const attemptId of first.queue.slice(0,CODING_SCHEDULER_LIMITS.queue)){
      const ready=await this.store.transaction(async tx=>{const c=await this.context(tx),r=await tx.get<CodingSchedulerRecord>(recordKey(attemptId));
        if(!r||r.state!=='queued'||!c.policy?.enabled)return null;
        if(c.now>=r.expiresAtMs){r.state='expired';r.reason='task-expired';r.nextCheckAtMs=null;c.index.queue=remove(c.index.queue,attemptId);await tx.put(recordKey(attemptId),r);await this.event(tx,c.index,c.now,attemptId,'expiry',r.reason);await this.persist(tx,c.index,c.now,c.policy);return null;}
        if(r.nextCheckAtMs===null||r.nextCheckAtMs>c.now)return null;
        if(c.index.active.length>=c.policy.maxConcurrent){r.reason='concurrency-limit';r.nextCheckAtMs=Math.min(r.expiresAtMs,c.now+c.policy.pollIntervalMs);await tx.put(recordKey(attemptId),r);await this.persist(tx,c.index,c.now,c.policy);return null;}
        return r;
      });if(!ready)continue;if(gateChecks++>=4)break;
      const task=parseCodingTask(JSON.parse(ready.manifestJson));let gate:CodingSchedulerGate;
      try{gate=await this.call(()=>this.deps.gate(structuredClone(task)));if(!gate||!['ready','wait','blocked'].includes(gate.state))throw Error();}catch{gate={state:'wait',reason:'gate-unavailable'};}
      const selected=await this.store.transaction(async tx=>{const c=await this.context(tx),r=await tx.get<CodingSchedulerRecord>(recordKey(attemptId));if(!r||r.state!=='queued'||!c.policy?.enabled||c.now>=r.expiresAtMs||c.index.active.length>=c.policy.maxConcurrent)return null;
        if(gate.state!=='ready'||!HASH.test(gate.receiptSha256)){
          if(gate.state==='blocked'){r.state='blocked';r.reason='gate-blocked';r.nextCheckAtMs=null;c.index.queue=remove(c.index.queue,attemptId);c.index.held.push(attemptId);}
          else{r.reason=gate.state==='wait'&&['quota-wait','route-unavailable','gate-unavailable'].includes(gate.reason)?gate.reason:'gate-unavailable';
            const proposed=gate.state==='wait'&&int(gate.nextCheckAtMs,c.now+1000,c.now+CODING_SCHEDULER_LIMITS.gateRetryMs)?gate.nextCheckAtMs!:c.now+CODING_SCHEDULER_LIMITS.gateRetryMs;
            r.nextCheckAtMs=Math.min(r.expiresAtMs,proposed);}
          await tx.put(recordKey(attemptId),r);await this.event(tx,c.index,c.now,attemptId,'gate',r.reason);await this.persist(tx,c.index,c.now,c.policy);return null;
        }
        const seconds=codingReservationSeconds(task);
        if(c.index.lifetimeAttempts+1>c.policy.maxLifetimeAttempts||c.index.lifetimeReservedSeconds+seconds>c.policy.maxLifetimeReservedSeconds){r.reason='lifetime-budget';r.nextCheckAtMs=r.expiresAtMs;}
        else if(c.daily.reservedAttempts+1>c.policy.maxDailyAttempts||c.daily.reservedSeconds+seconds>c.policy.maxDailyReservedSeconds){r.reason='daily-budget';r.nextCheckAtMs=Math.min(r.expiresAtMs,Date.parse(c.daily.utcDay+'T00:00:00Z')+86400000);}
        else{
          const dispatch:Dispatch={policySha256:c.index.policySha256!,gateReceiptSha256:gate.receiptSha256,atMs:c.now,utcDay:c.daily.utcDay,reservedSeconds:seconds,observationUntilMs:c.now+(seconds+60)*1000};
          r.dispatch=dispatch;r.state='dispatching';r.reason='dispatch-unconfirmed';r.nextCheckAtMs=c.now+c.policy.pollIntervalMs;c.index.queue=remove(c.index.queue,attemptId);c.index.active.push(attemptId);
          c.index.lifetimeAttempts++;c.index.lifetimeReservedSeconds+=seconds;c.daily.reservedAttempts++;c.daily.reservedSeconds+=seconds;
          await tx.put('scheduler/day/'+c.daily.utcDay,c.daily);await tx.put('scheduler/dispatch/'+attemptId,{...dispatch,taskId:r.taskId,attemptId,inputSha256:r.inputSha256,ownerId:r.ownerId});
        }
        await tx.put(recordKey(attemptId),r);await this.event(tx,c.index,c.now,attemptId,r.dispatch?'dispatch-intent':'budget',r.reason,r.dispatch?.gateReceiptSha256??null);await this.persist(tx,c.index,c.now,c.policy);return r.dispatch?r:null;
      });
      if(!selected)continue;
      // The durable transition is the only permission to send. A thrown/lost acknowledgement is held.
      try{await this.call(()=>this.deps.submit(structuredClone(task)));}catch{/* Inspect the existing exact attempt; never call submit again. */}
    }
    return this.status();
  }
  async status(){
    return this.store.transaction(async tx=>{const c=await this.context(tx);await tx.put(INDEX,c.index);
      const ids=[...new Set([...c.index.active,...c.index.queue,...c.index.held,...c.index.recent])];const tasks=[];
      for(const id of ids){const r=await tx.get<CodingSchedulerRecord>(recordKey(id));if(r)tasks.push({taskId:r.taskId,attemptId:r.attemptId,inputSha256:r.inputSha256,authorizationId:r.authorizationId,state:r.state,reason:r.reason,createdAtMs:r.createdAtMs,expiresAtMs:r.expiresAtMs,nextCheckAtMs:r.nextCheckAtMs,reservedSeconds:r.dispatch?.reservedSeconds??0,terminalReceiptSha256:r.terminal?.receiptSha256??null});}
      return {schema:'lupine.coding-scheduler-status.v1' as const,observedAtMs:c.now,policySha256:c.index.policySha256,policy:c.policy??null,nextWakeAtMs:c.index.nextWakeAtMs,
        units:{attempts:'durable dispatch intentions; no refunds',seconds:'full guest wall envelope plus 30 seconds settlement; reserved, not measured billing'},
        lifetime:{attempts:c.index.lifetimeAttempts,reservedSeconds:c.index.lifetimeReservedSeconds},daily:c.daily,
        counts:{queued:c.index.queue.length,active:c.index.active.length,held:c.index.held.length},tasks,history:c.index.history};
    });
  }
}
