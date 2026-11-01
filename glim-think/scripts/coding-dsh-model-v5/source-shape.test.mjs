import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { convertHarnessRequest, createBrokerTransport, MODEL, PROVIDER, bodyDigest } from './transport.mjs';
import { UNAVAILABLE_TOOLS, restrictUnavailableTools } from './tool-surface.mjs';

const fixture = JSON.parse(readFileSync(new URL('./source-shape-fixture.json', import.meta.url)));
for (const [name, code] of Object.entries(fixture.snippets))
  assert.equal(createHash('sha256').update(code).digest('hex'), fixture.snippetSha256[name]);
const deepFreeze = value => {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(deepFreeze); Object.freeze(value);
  }
  return value;
};
// Exact source methods; surrounding registry, schemas, text and clock are
// deterministic fixture inputs. This does not boot the complete Harness.
const method = name => Function('snapshotJsonValue', 'RUN_CODE_NAME', `return ({${fixture.snippets[name]}}).${name}`)(structuredClone, 'run_code');
const helpers = Function('deepFreeze','randomUUID','brandString',
  Object.entries(fixture.snippets).filter(([n]) => n.startsWith('create')).map(([,c])=>c).join('\n') +
  ';return {createMessage,createUserMessage,createSystemMessage,createAssistantMessage,createToolResultMessage};')(deepFreeze, randomUUID, v=>v);
const History = Function('deepFreeze', fixture.snippets.ToolHistoryProjection+';return ToolHistoryProjection;')(deepFreeze);
const definition = name => ({ name, description: 'Synthetic source-shape tool '+name,
  parameters: { type: 'object', properties: { path: { type: 'string' } }, additionalProperties: false } });
function registry(names, bounded) {
  const restrictions = [{ allow: new Set(fixture.inheritedTools) }];
  const own = { tools: new Map(names.map(n=>[n,definition(n)])),
    admits: name => restrictions.every(r=>(!r.allow||r.allow.has(name))&&(!r.deny||!r.deny.has(name))) };
  const service = { layers: { global: { tools: new Map(fixture.inheritedTools.map(n=>[n,definition(n)])) },
    chainLayers: () => [own], peek: () => own }, modeFor: () => 'native', view: method('view'), schemaOf: method('schemaOf') };
  const agent = { ctx: { tools: { restrict(filter) {
    const known=service.view(agent).restrictableNames;
    for(const n of filter.deny)assert(known.has(n));
    const row={deny:new Set(filter.deny)}; restrictions.push(row);
    return ()=>restrictions.splice(restrictions.indexOf(row),1);
  } } } };
  if(bounded){own.tools.set('assessment_write',definition('assessment_write'));restrictUnavailableTools(agent);}
  const view=service.view(agent);
  return { tools:[...view.visible.values()].map(d=>service.schemaOf(d,true)), view };
}
const now=1900000000000;
const config={endpoint:'https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/attempt-02/model',capability:'x'.repeat(48),
  taskId:'coding-task',attemptId:'attempt-02',inputSha256:'a'.repeat(64),maxRequests:16,deadlineAtMs:now+600000,model:MODEL,maxOutputTokens:4096};
function first(tools) {
  const history = new History(); history.apply({type:'request/header',seq:0,data:{header:{tools},reason:'initial'}});
  return {provider:PROVIDER,model:MODEL,maxTokens:4096,sessionId:'orchestrator-1234',tools,toolHistory:history.snapshot(),
    messages:[helpers.createSystemMessage('Synthetic system'),helpers.createUserMessage({source:{kind:'runtime-context',form:'snapshot',sections:[{name:'synthetic',text:'Synthetic state'}]},content:[{type:'text',text:'Synthetic state'}]}),
      helpers.createUserMessage({source:{kind:'user'},content:[{type:'text',text:'Synthetic task'}]})]};
}
test('pinned registry logic reproduces original 21-tool rejection before history and messages', async()=>{
  const old=registry(fixture.mainTools,false); assert.equal(old.tools.length,21);
  const q=first(old.tools); q.messages=undefined;
  let calls=0;const t=createBrokerTransport(config,{now:()=>now,fetch:()=>{calls++;throw Error('no network')}});
  await assert.rejects(async()=>{for await(const unused of t.stream(q))void unused},/Too many tools/);
  assert.equal(calls,0);assert.equal(t.status().firstFailure.code,'DSH_TOOL_COUNT_EXCEEDED');
  assert.equal(t.status().firstFailure.shape.toolCount,21);
});
test('deny six inherited tools and add one own writer preserves own tools and Runtime allow validation',()=>{
  const master=registry(fixture.mainTools,true),worker=registry(fixture.workerTools,true);
  assert.equal(master.tools.length,16);assert.equal(worker.tools.length,8);
  for(const n of UNAVAILABLE_TOOLS){assert(!master.view.visible.has(n));assert(master.view.restrictableNames.has(n));}
  for(const n of fixture.mainTools)assert(master.view.visible.has(n));
  for(const n of ['assessment_write','bash'])assert(master.view.visible.has(n)&&worker.view.visible.has(n));
  for(const t of master.tools)assert.deepEqual(Object.keys(t),['name','description','parameters']);
});
test('actual message constructors and initial history convert at16 tools; next tool turn preserves exact prefix',()=>{
  const q=first(registry(fixture.mainTools,true).tools),body=convertHarnessRequest(q,config);
  assert.equal(q.toolHistory.updates.length,0);assert.equal(body.tools.length,16);assert.equal(body.messages.length,1);
  const before=structuredClone(body);
  q.messages.push(helpers.createAssistantMessage({source:{provider:PROVIDER,model:MODEL},content:[{type:'tool-call',id:'call-1',name:'bash',arguments:'{"command":"cat README.md"}'}]}),
    helpers.createToolResultMessage({callId:'call-1',content:[{type:'text',text:'Synthetic file content'}],isError:false}));
  const after=convertHarnessRequest(q,config);
  assert.deepEqual(after.messages[0],before.messages[0]);assert.equal(after.messages.length,3);
  assert.equal(after.messages[2].content[0].type,'tool_result');
  assert.equal(bodyDigest({system:before.system,tools:before.tools}),bodyDigest({system:after.system,tools:after.tools}));
});
test('dynamic history remains unsupported; source-shape coverage does not loosen admission',()=>{
  const q=first(registry(fixture.mainTools,true).tools);
  q.toolHistory={tools:q.tools,updates:[{messageId:'fixed',additions:[]}]};
  assert.throws(()=>convertHarnessRequest(q,config),/Dynamic tool history/);
});
test('budget feedback is serialized once in the actual source message helper and never rewrites history',()=>{
  const q=first(registry(fixture.workerTools,true).tools);q.sessionId='worker-1234';
  const feedback={used:8,phase:'explore'};
  q.messages.push(helpers.createAssistantMessage({source:{provider:PROVIDER,model:MODEL},content:[{type:'tool-call',id:'call-budget',name:'bash',arguments:'{"command":"cat README.md"}'}]}),helpers.createToolResultMessage({callId:'call-budget',content:[{type:'text',text:'Synthetic bounded output'},{type:'text',text:JSON.stringify({codingBudget:feedback})}],isError:false}));
  const before=convertHarnessRequest(q,config),frozen=JSON.stringify(before.messages);
  feedback.used=9;feedback.phase='finalize';
  assert.equal(JSON.stringify(convertHarnessRequest(q,config).messages),frozen);
  assert.equal(q.toolHistory.updates.length,0);
});
