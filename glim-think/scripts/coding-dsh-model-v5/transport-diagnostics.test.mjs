import test from 'node:test';
import assert from 'node:assert/strict';
import {createBrokerTransport,brokerDenialDiagnostic,bodyDigest,MODEL,PROVIDER} from './transport.mjs';
const now=1900000000000;
const config={endpoint:'https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/attempt-05/model',capability:'x'.repeat(48),taskId:'task-5',attemptId:'attempt-05',inputSha256:'a'.repeat(64),maxRequests:16,deadlineAtMs:now+600000,model:MODEL,maxOutputTokens:4096};
const request=(sessionId='worker')=>({provider:PROVIDER,model:MODEL,maxTokens:4096,sessionId,tools:[],toolHistory:{tools:[],updates:[]},messages:[{id:'user-1',role:'user',source:{kind:'user'},content:[{type:'text',text:'Private fixture request text.'}]}]});
const denial=(q,extra={})=>({schema:'lupine.coding-model-result.v1',ok:false,state:'unknown',reason:'provider-unknown',ordinal:q.ordinal,requestId:'coding:'+ 'a'.repeat(64)+':'+q.ordinal,...extra});
const response=v=>new Response(JSON.stringify(v),{headers:{'content-type':'application/json'}});
async function collect(t,q){const chunks=[];for await(const c of t.stream(q))chunks.push(c);return chunks}
test('first broker-withheld cause survives later stopped master preflight without releasing or replaying',async()=>{
 let calls=0;const t=createBrokerTransport(config,{now:()=>now,fetch:async(_url,opt)=>{calls++;return response(denial(JSON.parse(opt.body)))}});
 await assert.rejects(collect(t,request()));const first=t.status().firstFailure;
 assert.equal(first.code,'DSH_BROKER_RESULT_WITHHELD');assert.equal(first.stage,'broker-response');assert.equal(first.brokerReason,'provider-unknown');assert.equal(first.brokerState,'unknown');assert.equal(first.ordinal,1);assert.equal(first.providerTerminalEstablished,false);
 await assert.rejects(collect(t,request('master')));
 assert.deepEqual(t.status().firstFailure,first);assert.equal(t.status().secondaryRefusals.length,1);assert.equal(t.status().secondaryRefusals[0].stage,'pre-dispatch');assert.match(t.status().secondaryRefusals[0].message,/stopped or exhausted/);
 assert.equal(calls,1);const record=t.records()[0];assert.equal(record.status,'unknown');assert.equal(record.deliveredToHarness,false);assert.equal(record.usage,null);assert.equal(record.receiptSha256,null);assert.equal(record.archiveSha256,null);assert.deepEqual(record.failure,first);
});
test('unknown or identity-unqualified broker denial never echoes arbitrary text',async()=>{
 for(const extra of [{reason:'PRIVATE PROVIDER TEXT'},{ordinal:2},{requestId:'PRIVATE REQUEST IDENTIFIER'},{schema:'wrong-schema'}]){
  const t=createBrokerTransport(config,{now:()=>now,fetch:async(_url,opt)=>response(denial(JSON.parse(opt.body),extra))});await assert.rejects(collect(t,request()));const d=t.status().firstFailure;
  assert.equal(d.brokerReason,'unqualified-or-unrecognized-denial');assert(!JSON.stringify(t.status()).includes('PRIVATE'));assert.equal(t.records()[0].status,'unknown');
 }
});
test('diagnostic extraction never invokes broker-object accessors',()=>{
 let calls=0;const value=denial({ordinal:1});Object.defineProperty(value,'reason',{get(){calls++;throw Error('private')}});const d=brokerDenialDiagnostic(value,{ordinal:1});assert.equal(calls,0);assert.equal(d.brokerReason,'unqualified-or-unrecognized-denial');
});
test('a claimed not-dispatched denial is diagnostic only and never clears an unknown record',async()=>{
 const t=createBrokerTransport(config,{now:()=>now,fetch:async(_url,opt)=>response(denial(JSON.parse(opt.body),{state:'not-dispatched',reason:'provider-not-ready'}))});await assert.rejects(collect(t,request()));assert.equal(t.status().firstFailure.brokerState,'not-dispatched');assert.equal(t.records()[0].status,'unknown');assert.equal(t.status().firstFailure.providerTerminalEstablished,false);
});
test('HTTP/JSON failure retains a fixed initial boundary cause rather than parser excerpts',async()=>{
 for(const reply of [()=>new Response('PRIVATE ERROR', {status:503}),()=>new Response('{PRIVATE MALFORMED JSON',{headers:{'content-type':'application/json'}})]){
  let calls=0;const t=createBrokerTransport(config,{now:()=>now,fetch:async()=>{calls++;return reply()}});await assert.rejects(collect(t,request()));assert.equal(t.status().firstFailure.code,'DSH_BROKER_RESULT_UNQUALIFIED');await assert.rejects(collect(t,request('master')));assert.equal(t.status().firstFailure.code,'DSH_BROKER_RESULT_UNQUALIFIED');assert(!JSON.stringify(t.status()).includes('PRIVATE'));assert.equal(calls,1);
 }
});
test('repeated secondary refusals are bounded and returned diagnostics are detached',async()=>{
 let calls=0;const t=createBrokerTransport(config,{now:()=>now,fetch:async(_url,opt)=>{calls++;return response(denial(JSON.parse(opt.body)))}});await assert.rejects(collect(t,request()));for(let i=0;i<8;i++)await assert.rejects(collect(t,request('master')));const s=t.status();assert.equal(s.secondaryRefusals.length,4);s.firstFailure.brokerReason='modified';s.secondaryRefusals[0].message='modified';assert.equal(t.status().firstFailure.brokerReason,'provider-unknown');assert.notEqual(t.status().secondaryRefusals[0].message,'modified');assert.equal(calls,1);
});
test('consumer return after a yielded chunk records possibly partial delivery, never zero release or replay',async()=>{
 let calls=0;const t=createBrokerTransport(config,{now:()=>now,fetch:async(_url,opt)=>{calls++;const q=JSON.parse(opt.body);return response({schema:'lupine.coding-model-result.v1',ok:true,state:'completed',taskId:q.taskId,attemptId:q.attemptId,inputSha256:q.inputSha256,ordinal:q.ordinal,sessionId:q.sessionId,bodySha256:bodyDigest(q.body),requestId:'coding:'+'a'.repeat(64)+':'+q.ordinal,model:MODEL,content:[{type:'text',text:'Synthetic output.'}],stop_reason:'end_turn',usage:{input_tokens:1,output_tokens:2,cache_creation_input_tokens:0,cache_read_input_tokens:0},receiptSha256:'b'.repeat(64),archiveSha256:'c'.repeat(64),settlementConfirmed:true})}});
 const iterator=t.stream(request());assert.equal((await iterator.next()).value.type,'block-start');assert.equal((await iterator.next()).value.type,'text-delta');await iterator.return();
 const d=t.status().firstFailure;assert.equal(d.code,'DSH_BROKER_OUTPUT_DELIVERY_INCOMPLETE');assert.equal(d.resultReleased,null);assert.equal(d.deliveryComplete,false);assert.equal(d.outputMayHaveBeenReleased,true);assert.equal(t.records()[0].status,'completed');assert.equal(t.records()[0].deliveredToHarness,false);await assert.rejects(collect(t,request('master')));assert.deepEqual(t.status().firstFailure,d);assert.equal(calls,1);
});
