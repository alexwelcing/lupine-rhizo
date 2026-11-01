import {beforeAll,it,expect} from 'vitest';
import {build} from 'esbuild';
import {resolve} from 'node:path';
import {codingFetch} from '../runner-http';
import {CodingSchedulerError,type CodingSchedulerNoModelDispatchInput} from '../scheduler-state';
import type {CodingRunnerEnv} from '../runner-worker';

const token='operator-fixture-credential-48-bytes-not-a-task-capability';
const disposition:CodingSchedulerNoModelDispatchInput={kind:'release-confirmed-no-model-dispatch',authorizationId:'reviewed-release',expectedTerminalReceiptSha256:'a'.repeat(64),reviewEvidenceSha256:'b'.repeat(64)};
const url='https://runner.test/coding/scheduler/reconcile';
function request(body:unknown,authorization='Bearer '+token,origin?:string){return new Request(url,{method:'POST',headers:{'Content-Type':'application/json',...(authorization?{Authorization:authorization}:{}),...(origin?{Origin:origin}:{})},body:JSON.stringify(body)});}
function httpFixture(){
 const calls:unknown[][]=[];let accesses=0,modelCalls=0;
 const env={RUNNER_OPERATOR_TOKEN:token,
  CODING_SCHEDULER:{getByName(name:string){
   accesses++;expect(name).toBe('coding-scheduler-v1');
   return {reconcile:async(...args:unknown[])=>{calls.push(args);return {tasks:[{state:'unknown',releasedByDisposition:true,dispositionSha256:'c'.repeat(64)}]};}};
  }},
  CODING_RUNNER:{getByName(){return {model:async()=>{modelCalls++;return {ok:false,state:'refused'};}};}}
 } as unknown as CodingRunnerEnv;
 return {env,calls,get accesses(){return accesses;},get modelCalls(){return modelCalls;}};
}
it('operator-only reconcile forwards the exact disposition and preserves private response headers',async()=>{
 const f=httpFixture(),body={attemptId:'attempt-1',disposition};const response=await codingFetch(request(body),f.env);
 expect(response.status).toBe(200);expect(response.headers.get('Cache-Control')).toBe('private, no-store');expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff');expect(f.calls).toEqual([['attempt-1',disposition]]);expect(f.modelCalls).toBe(0);
 expect(await response.json()).toMatchObject({tasks:[{state:'unknown',releasedByDisposition:true}]});
});
it('a guest model capability, missing auth, or cross-origin operator cannot reach scheduler disposition',async()=>{
 const f=httpFixture(),body={attemptId:'attempt-1',disposition};for(const r of [request(body,''),request(body,'Bearer '+'d'.repeat(64)),request(body,'Bearer '+token,'https://foreign.test')])expect((await codingFetch(r,f.env)).status).toBe(403);
 expect(f.accesses).toBe(0);expect(f.calls).toEqual([]);
 // Its one permitted HTTP surface remains the model route; placing a
 // disposition in that body never routes it to the scheduling authority.
 const r=await codingFetch(new Request('https://runner.test/coding/tasks/attempt-1/model',{method:'POST',headers:{Authorization:'Bearer '+'d'.repeat(64),'Content-Type':'application/json'},body:JSON.stringify(body)}),f.env);
 expect(r.status).toBe(200);expect(f.modelCalls).toBe(1);expect(f.accesses).toBe(0);
});
it('legacy reconcile remains metadata-only and bounded malformed requests never call reconciliation',async()=>{
 const f=httpFixture();expect((await codingFetch(request({attemptId:'attempt-1'}),f.env)).status).toBe(200);expect(f.calls).toEqual([['attempt-1',undefined]]);
 for(const raw of ['{',JSON.stringify({attemptId:'attempt-1',padding:'x'.repeat(32768)})]){const r=await codingFetch(new Request(url,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:raw}),f.env);expect([400,413]).toContain(r.status);}
 expect(f.calls).toHaveLength(1);
});
it('disposition conflicts are rejected and unexpected private errors are not returned',async()=>{
 for(const error of [new CodingSchedulerError('conflict','Immutable disposition conflict'),Error('PRIVATE_TRANSPORT_DETAIL')]){const env={RUNNER_OPERATOR_TOKEN:token,CODING_SCHEDULER:{getByName(){return {reconcile:async()=>{throw error;}};}}} as unknown as CodingRunnerEnv;const r=await codingFetch(request({attemptId:'attempt-1',disposition}),env);expect(r.status).toBe(error instanceof CodingSchedulerError?409:503);expect(await r.text()).not.toContain('PRIVATE_TRANSPORT_DETAIL');}
});

let loadWrapper:(fixture:any)=>any;
beforeAll(async()=>{
 const result=await build({entryPoints:[resolve('src/coding/scheduler-worker.ts')],bundle:true,write:false,format:'cjs',platform:'node',target:'es2022',plugins:[{name:'scheduler-ports',setup(b){
  b.onResolve({filter:/^cloudflare:workers$/},()=>({path:'workers',namespace:'fixture'}));
  b.onResolve({filter:/^\.\/scheduler-storage$/},()=>({path:'storage',namespace:'fixture'}));
  b.onLoad({filter:/.*/,namespace:'fixture'},a=>({contents:a.path==='workers'?'export class DurableObject { constructor(ctx,env){this.ctx=ctx;this.env=env;} }':'export function createDurableCodingScheduler(storage,deps){fixture.dependencies=deps;return fixture.scheduler;}',loader:'js'}));
 }}]});
 loadWrapper=(fixture:any)=>{const module={exports:{}};new Function('module','exports','fixture',result.outputFiles[0].text)(module,module.exports,fixture);return (module.exports as any).CodingSchedule;};
});
function wrapperFixture(){
 const identity={taskId:'task-1',attemptId:'attempt-1',inputSha256:'1'.repeat(64),ownerId:'runner'},calls:string[]=[],forwarded:unknown[][]=[];
 let runner:any={...identity,status:'unknown',ledgerRecorded:true,cleanupConfirmed:true,receipt:{sha256:'2'.repeat(64)}};
 let row:any={task_id:identity.taskId,attempt_id:identity.attemptId,owner_id:identity.ownerId,input_sha256:identity.inputSha256,manifest_json:'{}',admitted_at:'2026-11-01T00:00:00Z',terminal_json:JSON.stringify({receiptJson:'{"fixture":"D1"}',receiptSha256:'3'.repeat(64)}),acceptance_json:null};
 const fixture:any={scheduler:{reconcile:async(...args:unknown[])=>{forwarded.push(args);return {fixture:true};}}};
 const Wrapper=loadWrapper(fixture),env={
  CODING_RUNNER:{getByName(id:string){
   expect(id).toBe(identity.attemptId);return {status:async()=>{calls.push('runner-status');return runner;}};
  }},
  LEDGER:{prepare(query:string){
   expect(query).toContain('FROM coding_attempts');expect(query).toContain('coding_terminal_receipts');
   return {bind(id:string){expect(id).toBe(identity.attemptId);return {first:async()=>{calls.push('D1-terminal');return row;}};}};
  }}
 };
 const wrapper=new Wrapper({storage:{}},env);
 return {fixture,wrapper,identity,calls,forwarded,setRunner(v:any){runner=v;},setRow(v:any){row=v;}};
}
it('actual wrapper independently reads Runner receipt SHA and D1 terminal without normalizing a mismatch',async()=>{
 const f=wrapperFixture(),r=await f.fixture.dependencies.status(f.identity);expect(f.calls).toEqual(['runner-status','D1-terminal']);expect(r.runnerTerminalReceiptSha256).toBe('2'.repeat(64));expect(r.terminal).toEqual({receiptJson:'{"fixture":"D1"}',receiptSha256:'3'.repeat(64)});expect(r.ledgerRecorded).toBe(true);
 expect(r.runnerTerminalReceiptSha256).not.toBe(r.terminal.receiptSha256);
});
it('missing Runner or D1 state cannot fabricate committed terminal evidence',async()=>{
 const f=wrapperFixture();f.setRunner(null);expect(await f.fixture.dependencies.status(f.identity)).toBeNull();expect(f.calls).toEqual(['runner-status']);
 const g=wrapperFixture();g.setRow(null);const r=await g.fixture.dependencies.status(g.identity);expect(r.ledgerRecorded).toBe(false);expect(r.terminal).toBeNull();expect(r.runnerTerminalReceiptSha256).toBe('2'.repeat(64));
});
it('actual DO wrapper forwards explicit disposition unchanged and retains the legacy optional signature',async()=>{
 const f=wrapperFixture();await f.wrapper.reconcile('attempt-1',disposition);await f.wrapper.reconcile('attempt-1');expect(f.forwarded).toEqual([['attempt-1',disposition],['attempt-1',undefined]]);expect(f.calls).toEqual([]);
});
