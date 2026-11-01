import { canonical, sha256, assertRunner, type CodingState } from './runner-contract';
import type { CodingRunnerEnv } from './runner-worker';

/** Calls a deployment-bound service only. No arbitrary URL or provider credential. */
export async function codingBrokerCall(env:CodingRunnerEnv,path:'ready'|'open'|'invoke'|'close'|'status',body:unknown):Promise<any>{
  assertRunner(env.CODING_MODELS,'Included model service is unavailable',503);
  const response=await env.CODING_MODELS.fetch(new Request('https://coding-broker.internal/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),redirect:'manual'}));
  if(response.status>=300&&response.status<400){await response.body?.cancel();throw Error('Broker redirect rejected');}
  assertRunner(response.body,'Model broker response unavailable',503);
  const reader=response.body.getReader();const chunks:Uint8Array[]=[];let length=0;
  try{for(;;){const x=await reader.read();if(x.done)break;length+=x.value.length;assertRunner(length<=1024*1024,'Model broker response exceeds bound',503);chunks.push(x.value);}}
  catch(e){await reader.cancel().catch(()=>{});throw e;}finally{reader.releaseLock();}
  const joined=new Uint8Array(length);let off=0;for(const x of chunks){joined.set(x,off);off+=x.length;}
  const parsed=JSON.parse(new TextDecoder('utf-8',{fatal:true,ignoreBOM:false}).decode(joined));
  assertRunner(response.ok&&parsed&&typeof parsed==='object'&&!Array.isArray(parsed),'Included model request was not accepted',response.status===409?409:503);
  return parsed;
}
type ModelSession={schema:'lupine.coding-model-session.v1';inputSha256:string;tokenSha256:string;expiresAtMs:number;permitSha256:string|null;state:'opening'|'open'|'closed'};
const SESSION='model-session';
export async function openCodingModel(env:CodingRunnerEnv,storage:DurableObjectStorage,state:CodingState){
  state=structuredClone(state);
  const model=state.task.model;assertRunner(model,'No model authorized',409);
  assertRunner(state.status==='preparing'&&!state.terminalIntent&&Date.now()<state.deadlineAtMs,'Coding task cannot open a model session',409);
  const token=[...crypto.getRandomValues(new Uint8Array(32))].map(n=>n.toString(16).padStart(2,'0')).join('');
  const tokenSha256=await sha256(token),now=Date.now(),expiresAtMs=Math.min(state.deadlineAtMs,now+state.task.timeoutSeconds*1000);
  const permit={schema:'lupine.coding-model-permit.v1',consumerService:'lupine-coding-runner-v01',taskId:state.task.taskId,attemptId:state.task.attemptId,inputSha256:state.inputSha256,
    repositoryCommit:state.task.repository.commit,sourceSha256:state.task.source.sha256,adapterSha256:model.adapterSha256,model:model.model,maxRequests:model.maxRequests,maxOutputTokens:model.maxOutputTokens,
    maxInputBytes:256*1024,createdAtMs:now,expiresAtMs,runnerDeadlineAtMs:state.deadlineAtMs};
  const permitSha256=await sha256(canonical(permit));
  const session:ModelSession={schema:'lupine.coding-model-session.v1',inputSha256:state.inputSha256,tokenSha256,expiresAtMs,permitSha256,state:'opening'};
  const samePreparing=(latest:CodingState|undefined)=>latest?.status==='preparing'&&!latest.terminalIntent&&latest.inputSha256===state.inputSha256&&latest.task.taskId===state.task.taskId&&latest.task.attemptId===state.task.attemptId&&Date.now()<latest.deadlineAtMs&&Date.now()<expiresAtMs;
  await storage.transaction(async tx=>{assertRunner(samePreparing(await tx.get<CodingState>('attempt')),'Coding task no longer accepts model opening',409);assertRunner(!await tx.get(SESSION),'Model capability already consumed',409);await tx.put(SESSION,session);});
  const result=await codingBrokerCall(env,'open',{permit});
  assertRunner(result.permitSha256===permitSha256&&result.taskId===state.task.taskId&&result.attemptId===state.task.attemptId&&result.inputSha256===state.inputSha256&&result.status==='open'&&result.expiresAtMs===expiresAtMs,'Broker permit identity unavailable',503);
  await storage.transaction(async tx=>{const current=await tx.get<ModelSession>(SESSION);
    assertRunner(samePreparing(await tx.get<CodingState>('attempt'))&&current?.state==='opening'&&current.tokenSha256===tokenSha256&&current.permitSha256===permitSha256&&current.inputSha256===state.inputSha256,'Late model opening withheld',409);
    await tx.put(SESSION,{...session,state:'open'});
  });
  const config={endpoint:`https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/${state.task.attemptId}/model`,capability:token,
    taskId:state.task.taskId,attemptId:state.task.attemptId,inputSha256:state.inputSha256,maxRequests:model.maxRequests,deadlineAtMs:expiresAtMs,model:model.model,maxOutputTokens:model.maxOutputTokens};
  return {LUPINE_CODING_MODEL_CONFIG_JSON:JSON.stringify(config)};
}
export async function invokeCodingModel(env:CodingRunnerEnv,storage:DurableObjectStorage,state:CodingState|null,capability:string,turn:any){
  turn=structuredClone(turn);
  assertRunner(state?.task.model&&state.status==='executing'&&!state.terminalIntent&&Date.now()<state.deadlineAtMs,'Coding task is not accepting model turns',409);
  const session=await storage.get<ModelSession>(SESSION);
  assertRunner(session?.state==='open'&&Date.now()<session.expiresAtMs&&session.inputSha256===state.inputSha256,'Model session is unavailable',409);
  assertRunner(/^[a-f0-9]{64}$/.test(capability)&&await sha256(capability)===session.tokenSha256,'Task capability rejected',403);
  assertRunner(turn?.taskId===state.task.taskId&&turn.attemptId===state.task.attemptId&&turn.inputSha256===state.inputSha256,'Model turn task mismatch',409);
  const currentAllowed=async()=>storage.transaction(async tx=>{const latest=await tx.get<CodingState>('attempt'),current=await tx.get<ModelSession>(SESSION);
    assertRunner(latest?.status==='executing'&&!latest.terminalIntent&&latest.inputSha256===state.inputSha256&&latest.task.taskId===state.task.taskId&&latest.task.attemptId===state.task.attemptId&&Date.now()<latest.deadlineAtMs
      &&current?.state==='open'&&current.tokenSha256===session.tokenSha256&&current.permitSha256===session.permitSha256&&current.inputSha256===state.inputSha256&&Date.now()<current.expiresAtMs,'Model output or dispatch withheld after task closure',409);
  });
  await currentAllowed();
  const result=await codingBrokerCall(env,'invoke',{attemptId:state.task.attemptId,turn});
  await currentAllowed();
  return result;
}
export async function closeCodingModel(env:CodingRunnerEnv,storage:DurableObjectStorage,state:CodingState){
  const session=await storage.get<ModelSession>(SESSION);
  if(!session)return {confirmed:true,metadata:{state:'not-opened',completedRequests:0}};
  await storage.put(SESSION,{...session,state:'closed'});
  const result=await codingBrokerCall(env,'close',{attemptId:state.task.attemptId,inputSha256:state.inputSha256});
  const closed=result.status;
  const confirmed=result.confirmed===true&&result.pendingUnknown===false&&result.inputSha256===state.inputSha256
    &&closed?.status==='closed'&&closed.taskId===state.task.taskId&&closed.attemptId===state.task.attemptId&&closed.inputSha256===state.inputSha256&&closed.permitSha256===session.permitSha256
    &&Number.isSafeInteger(result.completedRequests)&&result.completedRequests>=0&&result.completedRequests<=(state.task.model?.maxRequests??0);
  return {confirmed,metadata:result};
}
