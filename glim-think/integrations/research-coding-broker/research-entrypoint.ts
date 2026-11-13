/** Installation target: research-service/cloudflare/coding-model-broker.ts.
 * Copy the standalone core beside it. This entrypoint is service-binding only;
 * the existing public fetch handler must NOT forward requests here. */
import {DurableObject,WorkerEntrypoint} from 'cloudflare:workers';
import {CodingModelBrokerCore,CODING_MODEL,BrokerError,brokerHash,brokerCanonical,type BrokerArchive,type BrokerProvider,type BrokerStore,type BrokerPermit,type Json} from './model-broker-core';
import {createMiniMaxSubscriptionRunner,type MiniMaxRunnerAuthority} from '../runtime/subscription-minimax-runner';
import {MINIMAX_SUBSCRIPTION,type MiniMaxSubscriptionConfig} from '../runtime/subscription-minimax';
import type {MiniMaxAccount} from './minimax-account';
import {workerMiniMaxFetch} from './coding-model-worker-fetch';

const CONSUMER='lupine-coding-runner-v01';
const PROTOCOL='lupine.coding-model-broker.v1';
interface Env {
 MINIMAX_SUBSCRIPTION_KEY:string;MINIMAX_POLICY_SHA256:string;MINIMAX_CREDENTIAL_GENERATION_SHA256:string;
 MINIMAX_ACCOUNT:DurableObjectNamespace<MiniMaxAccount>;MEMORY:R2Bucket;
 CODING_MODEL_BROKER:DurableObjectNamespace<CodingModelBroker>;
}
type BindingProps={consumerService:string;protocol:string};
const identity=(s:unknown):s is string=>typeof s==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(s);
const sha=(s:unknown):s is string=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
const json=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});

/** This wrapper is deliberately local to the new composition. Frozen Bun
 * runtime sources remain byte-identical. Request redirects never forward keys. */
export function privateArchive(bucket:R2Bucket):BrokerArchive {
 return {
  async put(key,bytes){
   if(!/^(coding-model-private\/|minimax-private\/)/.test(key)||bytes.length>2*1024*1024)throw Error('private-archive-contract');
   const existing=await bucket.get(key);
   if(existing){if(existing.size!==bytes.length)throw Error('private-archive-conflict');const old=new Uint8Array(await existing.arrayBuffer());if(old.length!==bytes.length||await brokerHash(old)!==await brokerHash(bytes))throw Error('private-archive-conflict');return}
   await bucket.put(key,bytes,{onlyIf:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/json'}});
   const read=await bucket.get(key);if(!read||read.size!==bytes.length)throw Error('private-archive-absent');const actual=new Uint8Array(await read.arrayBuffer());
   if(actual.length!==bytes.length||await brokerHash(actual)!==await brokerHash(bytes))throw Error('private-archive-readback');
  },
  async get(key){if(!key.startsWith('coding-model-private/'))throw Error('private-read-scope');const o=await bucket.get(key);if(!o)return null;if(o.size>2*1024*1024)throw Error('private-archive-size');return new Uint8Array(await o.arrayBuffer())}
 };
}

function authority(env:Env):MiniMaxRunnerAuthority {
 const stub=env.MINIMAX_ACCOUNT.getByName('lupine-team-minimax');
 return {credit:()=>stub.credit(),observeCredit:i=>stub.observeCredit(i),observeQuota:i=>stub.observeQuota(i),status:m=>stub.status(m),get:id=>stub.get(id),claim:(i,b)=>stub.claim(i,b),settle:r=>stub.settle(r),markUnknown:(id,r)=>stub.markUnknown(id,r)};
}
async function runner(env:Env,signal:AbortSignal) {
 if(!sha(env.MINIMAX_POLICY_SHA256)||!sha(env.MINIMAX_CREDENTIAL_GENERATION_SHA256))throw Error('broker-policy-not-configured');
 const status=await env.MINIMAX_ACCOUNT.getByName('lupine-team-minimax').status(CODING_MODEL);
 if(status.policySha256!==env.MINIMAX_POLICY_SHA256||status.credentialGenerationSha256!==env.MINIMAX_CREDENTIAL_GENERATION_SHA256)throw Error('broker-policy-mismatch');
 const selected=status.policy?.configs.find(c=>c.model===CODING_MODEL);
 if(!selected||selected.accountScope!=='lupine-team-minimax')throw Error('broker-model-not-configured');
 const config:MiniMaxSubscriptionConfig={...selected,maxOutputTokens:Math.min(4096,selected.maxOutputTokens)};
 return createMiniMaxSubscriptionRunner({key:env.MINIMAX_SUBSCRIPTION_KEY,config,policySha256:env.MINIMAX_POLICY_SHA256,credentialGenerationSha256:env.MINIMAX_CREDENTIAL_GENERATION_SHA256,
  authority:authority(env),archive:privateArchive(env.MEMORY),fetch:workerMiniMaxFetch(signal)});
}
export function providerAdapter(env:Env):BrokerProvider {
 return {
  policySha256:env.MINIMAX_POLICY_SHA256,credentialGenerationSha256:env.MINIMAX_CREDENTIAL_GENERATION_SHA256,
  async ready(signal){
   if(signal.aborted)return {allowed:false,reason:'cancelled'};
   const s=await env.MINIMAX_ACCOUNT.getByName('lupine-team-minimax').status(CODING_MODEL);
   // A fresh authenticated quota is acquired by messages(). Do not deadlock
   // admission on a stale quota while a valid credits-OFF proof is available.
   const proof=s.credit?.receipt,now=Date.now();
   const allowed=s.policySha256===env.MINIMAX_POLICY_SHA256&&s.credentialGenerationSha256===env.MINIMAX_CREDENTIAL_GENERATION_SHA256
    &&s.decision.state!=='busy'&&s.decision.state!=='attention'&&!!proof&&proof.autoCreditUsage==='off'&&proof.observedAt<=now&&now-proof.observedAt<=MINIMAX_SUBSCRIPTION.creditControlMaxAgeMs;
   return {allowed,reason:allowed?'fresh-quota-required-at-dispatch':'included-route-not-ready'};
  },
  async invoke(input){
   const r=await (await runner(env,input.signal)).messages({requestId:input.requestId,jobId:input.jobId,seatId:input.seatId,purpose:'primary',body:input.body,signal:input.signal});
   if(r.decision.allowed&&r.operation?.state==='completed'&&r.receipt?.toolsPermitted&&r.receipt.usageComplete&&r.privateResult&&r.operation.outcomeReceiptSha256){
    const m=r.privateResult.message;
    const digest=await brokerHash(brokerCanonical(r.receipt));
    if(digest!==r.operation.outcomeReceiptSha256||m.model!==CODING_MODEL||!Array.isArray(m.content)||!['end_turn','tool_use'].includes(String(m.stop_reason)))throw Error('broker-settlement-join');
    return {state:'completed',model:CODING_MODEL,content:m.content as Json[],stop_reason:m.stop_reason as 'end_turn'|'tool_use',usage:r.receipt.usage as unknown as Json,receiptSha256:digest,settlementConfirmed:true};
   }
   if(r.noDispatch?.providerRequestSent===false&&r.noDispatch.providerClaimAttempted===false)return {state:'not-dispatched',reason:'authenticated-no-dispatch'};
   return {state:'unknown',reason:'included-operation-not-releasable'};
  }
 };
}

export class CodingModelBroker extends DurableObject<Env> {
 private core:CodingModelBrokerCore;
 constructor(ctx:DurableObjectState,env:Env){super(ctx,env);const store:BrokerStore={transaction:fn=>ctx.storage.transaction(tx=>fn({get:k=>tx.get(k),put:async(k,v)=>{await tx.put(k,v)}}))};
  this.core=new CodingModelBrokerCore({store,archive:privateArchive(env.MEMORY),provider:providerAdapter(env),consumerService:CONSUMER});
 }
 open(permit:BrokerPermit){return this.core.open(permit)}
 // A bounded JSON wire avoids recursively instantiating the platform's RPC
 // serializer type over Json while preserving the exact checked turn bytes.
 async invoke(turnJson:string):Promise<string>{if(typeof turnJson!=='string'||new TextEncoder().encode(turnJson).length>300*1024)throw Error('invalid-turn-wire');return JSON.stringify(await this.core.invoke(JSON.parse(turnJson)))}
 status(){return this.core.status()}
 close(identity:{attemptId:string;inputSha256:string}){return this.core.close(identity)}
}

export class CodingModelBrokerEntrypoint extends WorkerEntrypoint<Env,BindingProps> {
 async fetch(request:Request):Promise<Response>{
  if(this.ctx.props?.consumerService!==CONSUMER||this.ctx.props?.protocol!==PROTOCOL)return json({ok:false,reason:'binding-not-authorized'},403);
  if(request.method!=='POST')return json({ok:false,reason:'method-not-allowed'},405);
  try{
   const reader=request.body?.getReader();if(!reader)return json({ok:false,reason:'body-required'},400);const chunks:Uint8Array[]=[];let size=0;
   for(;;){const r=await reader.read();if(r.done)break;size+=r.value.length;if(size>300*1024){void reader.cancel().catch(()=>{});return json({ok:false,reason:'request-too-large'},413)}chunks.push(r.value)}
   const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}const input=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
   const path=new URL(request.url).pathname;
   if(path==='/ready'){
    if(input.model!==CODING_MODEL||Object.keys(input).length!==1)return json({allowed:false,reason:'invalid-model'},400);
    // Metadata refresh only: no provider-message request, claim, alarm or wake.
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    try{const result=await Promise.race([(async()=>{const r=await runner(this.env,abort.signal);return r.refreshAdmission()})(),new Promise<never>((_,reject)=>{timer=setTimeout(()=>{abort.abort();reject(Error('readiness-timeout'))},20000)})]);return json({allowed:result.decision.allowed,reason:result.decision.reason,nextCheckAtMs:result.decision.nextCheckAtMs,model:CODING_MODEL,provider:'minimax',route:'minimax-subscription',meteredFallback:false})}
    finally{if(timer)clearTimeout(timer)}
   }
   if(path==='/open'){
    if(!input.permit||Object.keys(input).length!==1||!identity(input.permit.attemptId))return json({ok:false,reason:'invalid-open'},400);
    return json(await this.env.CODING_MODEL_BROKER.getByName(input.permit.attemptId).open(input.permit));
   }
   if(!identity(input.attemptId))return json({ok:false,reason:'invalid-attempt'},400);
   const stub=this.env.CODING_MODEL_BROKER.getByName(input.attemptId),status=await stub.status();
   if(path==='/invoke'){
    if(Object.keys(input).sort().join(',')!=='attemptId,turn'||!input.turn||input.turn.attemptId!==input.attemptId||!status||input.turn.inputSha256!==status.inputSha256)return json({ok:false,reason:'invalid-invoke'},400);
    return json(JSON.parse(await stub.invoke(JSON.stringify(input.turn))));
   }
   if(path==='/close'&&Object.keys(input).sort().join(',')==='attemptId,inputSha256'&&sha(input.inputSha256)&&(!status||status.inputSha256===input.inputSha256))return json(await stub.close({attemptId:input.attemptId,inputSha256:input.inputSha256}));
   if(path==='/status'&&Object.keys(input).sort().join(',')==='attemptId,inputSha256'&&status?.inputSha256===input.inputSha256)return json(status);
   return json({ok:false,reason:'unknown-operation-or-identity'},404);
  }catch(e){return json({ok:false,reason:e instanceof BrokerError?e.reason:'broker-operation-unavailable'},409)}
 }
}
