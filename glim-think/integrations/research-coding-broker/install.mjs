import {readFile,writeFile,access} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

// Explicit local installation only; no deployment, credentials, or model IO.
const [rootArg,receiptArg]=process.argv.slice(2);
assert(rootArg&&receiptArg,'Usage: node install.mjs <research-package> <new-receipt.json>');
const root=resolve(rootArg),receipt=resolve(receiptArg),here=dirname(fileURLToPath(import.meta.url));
const hash=b=>createHash('sha256').update(b).digest('hex');
const baseline=JSON.parse(await readFile(resolve(here,'baseline.json'),'utf8'));
for(const row of baseline.files){const bytes=await readFile(resolve(root,row.path));assert.equal(hash(bytes),row.sha256,`Baseline changed: ${row.path}`);assert.equal(bytes.length,row.bytes);}
const exists=async p=>access(p).then(()=>true,()=>false);
assert(!await exists(receipt),'Receipt already exists');
const copies=[['research-entrypoint.ts','cloudflare/coding-model-broker.ts'],['worker-fetch.ts','cloudflare/coding-model-worker-fetch.ts'],['../../src/coding/model-broker-core.ts','cloudflare/model-broker-core.ts']];
const data=[];
for(const [source,target] of copies){assert(!await exists(resolve(root,target)),`Target already exists: ${target}`);data.push({target,bytes:await readFile(resolve(here,source))});}
const configPath=resolve(root,'cloudflare/wrangler.managed.jsonc'),workerPath=resolve(root,'cloudflare/worker.ts');
const oldConfig=await readFile(configPath,'utf8'),oldWorker=await readFile(workerPath,'utf8');
const config=JSON.parse(oldConfig);assert.equal(config.name,baseline.service);assert(!config.durable_objects.bindings.some(x=>x.name==='CODING_MODEL_BROKER'));
config.durable_objects.bindings.push({name:'CODING_MODEL_BROKER',class_name:'CodingModelBroker'});
config.exports.CodingModelBroker={type:'durable-object',storage:'sqlite'};
config.compatibility_flags=[...new Set([...(config.compatibility_flags??[]),'nodejs_compat'])];
config.main='coding-model-worker.ts';
const wrapper="// Additive service composition; the original public Worker remains byte-identical.\nexport { default } from './worker';\nexport * from './worker';\nexport { CodingModelBroker, CodingModelBrokerEntrypoint } from './coding-model-broker';\n";
assert(!await exists(resolve(root,'cloudflare/coding-model-worker.ts')),'Wrapper already exists');
// Save original bytes and intent before any edit, permitting exact review/recovery.
const finalConfig=JSON.stringify(config,null,2)+'\n';
await writeFile(receipt,JSON.stringify({schema:'lupine.coding-broker-install.v1',recordedAt:new Date().toISOString(),service:baseline.service,baselineVersion:baseline.workerVersion,baselineFiles:baseline.files.length,original:{worker:oldWorker,config:oldConfig},additions:[...data.map(x=>({path:x.target,sha256:hash(x.bytes),bytes:x.bytes.length})),{path:'cloudflare/coding-model-worker.ts',sha256:hash(wrapper),bytes:Buffer.byteLength(wrapper)}],changes:[{path:'cloudflare/wrangler.managed.jsonc',sha256:hash(finalConfig)}],deploymentPerformed:false},null,2)+'\n',{flag:'wx',mode:0o600});
for(const row of data)await writeFile(resolve(root,row.target),row.bytes,{flag:'wx'});
await writeFile(resolve(root,'cloudflare/coding-model-worker.ts'),wrapper,{flag:'wx'});await writeFile(configPath,finalConfig);
console.log(JSON.stringify({installed:true,service:baseline.service,baselineFilesVerified:baseline.files.length,newFiles:data.length+1,changedFiles:1,receipt}));
