import {ASSESSMENT_SCHEMA} from './assessment-writer.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { projectPinnedZodSchema } from './zod-schema.mjs';
import { convertHarnessRequest, snapshot, MODEL, PROVIDER } from './transport.mjs';

// Explicit source archives, not a package install or an unpinned node_modules
// fallback. The author receipt joins these files to exact registry integrity.
const zodRoot=process.env.CODING_DSH_ZOD_PACKAGE_PATH, valuesFile=process.env.CODING_DSH_UTIL_VALUES_FILE;
assert(zodRoot&&path.isAbsolute(zodRoot)&&valuesFile&&path.isAbsolute(valuesFile),'Provide exact retained Zod and util-values source paths');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const pins=JSON.parse(readFileSync(new URL('./projection-runtime-pins.json',import.meta.url)));
for(const pin of pins){const file=pin.path.startsWith('zod/')?path.join(zodRoot,pin.path.slice(4)):valuesFile;assert.equal(sha(readFileSync(file)),pin.sha256);}
assert.equal(JSON.parse(readFileSync(path.join(zodRoot,'package.json'))).version,'4.4.3');
const {z}=await import(pathToFileURL(path.join(zodRoot,'index.js')));
const {snapshotJsonValue}=await import(pathToFileURL(valuesFile));
const families=JSON.parse(readFileSync(new URL('./schema-families.json',import.meta.url)));
assert.equal(sha(families.javascript),families.javascriptSha256);
const {mainTools,executorTools}=Function('z',families.javascript+';return {mainTools,executorTools};')(z);
const host={resources:{},sessions:{},settings:{},github:{deployment:{github:{login:'snapshot-disabled'}}}};
const master=mainTools(host,{id:'orchestrator-source-fixture'}),worker=executorTools(host,{id:'ticket-source-fixture'});
assert.equal(master.length,14);assert.equal(worker.length,6);
const schemaOfCode=JSON.parse(readFileSync(new URL('./source-shape-fixture.json',import.meta.url))).snippets.schemaOf;
const schemaOf=Function('snapshotJsonValue',`return ({${schemaOfCode}}).schemaOf`)(snapshotJsonValue);
const native=[{name:'bash',description:'Synthetic native tool',parameters:{type:'object',additionalProperties:true}},{name:'assessment_write',description:'Fixed source assessment writer',parameters:ASSESSMENT_SCHEMA}];
const config={maxOutputTokens:4096};
const request=tools=>({provider:PROVIDER,model:MODEL,maxTokens:4096,sessionId:'source-fixture',tools,toolHistory:{tools,updates:[]},
 messages:[{id:'s1',role:'system',source:{kind:'system-prompt'},content:[{type:'text',text:'Synthetic system'}]},
 {id:'u1',role:'user',source:{kind:'user'},content:[{type:'text',text:'Synthetic task'}]}]});
const rows=[];
for(const [role,tools]of [['master',master],['worker',worker]])for(const tool of tools){
 test(`actual pinned Zod + util-values preserve ${role} ${tool.name} JSON schema`,()=>{
  const raw=z.toJSONSchema(tool.schema),standard=tool.schema['~standard'];
  assert.equal(snapshotJsonValue(raw),undefined);
  assert.throws(()=>schemaOf({name:tool.name,description:tool.description,parameters:raw},true),/lossless JSON/);
  assert.throws(()=>snapshot(raw),/hidden field/);
  const projected=projectPinnedZodSchema(raw,standard);
  assert.equal(JSON.stringify(raw),JSON.stringify(projected));assert(snapshotJsonValue(projected));assert(snapshot(projected));
  const wire=schemaOf({name:tool.name,description:tool.description,parameters:projected},true);
  assert(convertHarnessRequest(request([wire]),config));
  assert(Object.hasOwn(raw,'~standard'));assert(!Object.hasOwn(projected,'~standard'));
  rows.push({role,name:tool.name,rawHiddenRejected:true,jsonBytes:Buffer.byteLength(JSON.stringify(projected)),jsonSha256:sha(JSON.stringify(projected))});
 });
}
test('all real schema families fit unchanged16/8 complete tool surface and stable history',()=>{
 for(const [tools,count]of [[master,16],[worker,8]]){
  const wire=[...native,...tools.map(t=>schemaOf({name:t.name,description:t.description,parameters:projectPinnedZodSchema(z.toJSONSchema(t.schema),t.schema['~standard'])},true))];
  const first=request(wire),body=convertHarnessRequest(first,config);assert.equal(body.tools.length,count);
  first.messages.push({id:'a1',role:'assistant',source:{kind:'model',provider:PROVIDER,model:MODEL},content:[{type:'tool-call',id:'c1',name:'bash',arguments:'{}'}]},
   {id:'t1',role:'tool',source:{kind:'tool',callId:'c1'},toolCallId:'c1',isError:false,content:[{type:'text',text:'Synthetic result'}]});
  const next=convertHarnessRequest(first,config);assert.deepEqual(next.tools,body.tools);assert.deepEqual(next.messages[0],body.messages[0]);
 }
});
test('projection leaves original Zod argument validation and default semantics intact',()=>{
 const schema=master.find(t=>t.name==='orchestrator_read').schema;
 projectPinnedZodSchema(z.toJSONSchema(schema),schema['~standard']);
 assert.deepEqual(schema.parse({resource:'tickets'}),{resource:'tickets',offset:0});
 assert.equal(schema.safeParse({resource:'',limit:9001}).success,false);
});
function rawFixture(){const schema=z.object({value:z.string()}).strict();return {schema,raw:z.toJSONSchema(schema)};}
for(const [label,mutate]of [
 ['extra hidden root',raw=>Object.defineProperty(raw,'hidden',{value:1})],
 ['root symbol',raw=>{raw[Symbol('hidden')]=1}],
 ['root accessor',raw=>Object.defineProperty(raw,'value',{enumerable:true,get(){throw Error('MUST_NOT_EVALUATE')}})],
 ['nested hidden',raw=>Object.defineProperty(raw.properties.value,'hidden',{value:1})],
 ['nested symbol',raw=>{raw.properties.value[Symbol('hidden')]=1}],
 ['nested accessor',raw=>Object.defineProperty(raw.properties.value,'surprise',{enumerable:true,get(){throw Error('MUST_NOT_EVALUATE')}})],
 ['nested metadata',raw=>Object.defineProperty(raw.properties.value,'~standard',Object.getOwnPropertyDescriptor(raw,'~standard'))],
 ['undefined field',raw=>{raw.properties.value.bad=undefined}],
 ['nonfinite number',raw=>{raw.properties.value.bad=Infinity}],
 ['exotic prototype',raw=>{raw.properties.value.bad=new Date(0)}],
 ['reserved field',raw=>{raw.properties.value.constructor={type:'string'}}],
 ['cyclic schema',raw=>{raw.properties.value.cycle=raw}],
])test(`rejects ${label} without silently losing data or invoking accessors`,()=>{
 const {schema,raw}=rawFixture();mutate(raw);
 assert.throws(()=>projectPinnedZodSchema(raw,schema['~standard']),e=>e.message.startsWith('ZOD_SCHEMA_')&&!e.message.includes('MUST_NOT_EVALUATE'));
});
test('metadata descriptor and origin are exact, not a generic hidden-field exemption',()=>{
 const {schema,raw}=rawFixture(),d=Object.getOwnPropertyDescriptor(raw,'~standard');
 for(const changed of [{...d,enumerable:true},{...d,writable:true},{...d,configurable:true},
  {...d,value:{...d.value,vendor:'other'}},{...d,value:{...d.value,extra:true}},
  {...d,value:{...d.value,jsonSchema:{input:()=>{},output:()=>{},extra:1}}}]){
  const copy={...raw};Object.defineProperty(copy,'~standard',changed);
  assert.throws(()=>projectPinnedZodSchema(copy,schema['~standard']));
 }
 assert.throws(()=>projectPinnedZodSchema(raw,z.object({other:z.boolean()})['~standard']));
});
test('all20 family checks completed with no tool executor or provider invocation',()=>{
 assert.equal(rows.length,20);
 console.log(JSON.stringify({schema:'lupine.dsh-zod-family-reproduction.v1',families:rows,fullHarnessBoot:false,providerInvocations:0,toolExecutorsInvoked:0}));
});
