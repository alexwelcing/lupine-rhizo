// Actual pinned prototype Runtime plus Harness with a scoped subscription broker.
// Running this composition can request model inference; it requires a separately admitted coding attempt.
import {pathToFileURL,fileURLToPath} from 'node:url';
import {mkdtemp,writeFile,readFile,open} from 'node:fs/promises';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {realpath} from 'node:fs/promises';
import {parseConfig,createHarnessAdapter,PROVIDER,MODEL} from './transport.mjs';
const digest=value=>createHash('sha256').update(value).digest('hex');
const config=parseConfig(process.env.LUPINE_CODING_MODEL_CONFIG_JSON);
// The capability is retained only in the transport closure. Subprocesses receive
// a separate explicit environment; no provider or operator credential is read.
delete process.env.LUPINE_CODING_MODEL_CONFIG_JSON;
const targetRoot=await realpath(process.cwd());
const output=path.join(targetRoot,'.lupine-coding-evidence');
const prepared=JSON.parse(await readFile(path.join(output,'model-prepared.json'),'utf8'));
assert.equal(prepared.schema,'lupine.dsh-model-prepared.v1');
assert.equal(prepared.targetRoot,targetRoot);assert.equal(prepared.nodeVersion,process.version);
assert.equal(prepared.nodeExecutable,process.execPath);
const recipeDir=path.dirname(fileURLToPath(import.meta.url));
const sourceLockBytes=await readFile(path.join(recipeDir,'source-lock.json'));
assert.equal(digest(sourceLockBytes),prepared.modelRecipeSha256);
for(const [name,hash] of Object.entries(JSON.parse(sourceLockBytes).files))assert.equal(digest(await readFile(path.join(recipeDir,name))),hash,`Model source mismatch: ${name}`);
const revision=execFileSync('git',['rev-parse','HEAD'],{cwd:targetRoot,encoding:'utf8',timeout:5000,env:{PATH:process.env.PATH,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null'}}).trim();
assert.equal(revision,prepared.targetRevision);
const deadline=Math.min(config.deadlineAtMs,prepared.deadlineAtMs);
assert(deadline>Date.now()+20000,'No task budget remains');
const task=JSON.parse(await readFile(path.join(targetRoot,'.lupine-coding-task.json'),'utf8'));
assert.equal(task.schema,'lupine.dsh-coding-instruction.v1');assert.equal(task.taskId,config.taskId);
assert(typeof task.instruction==='string'&&Buffer.byteLength(task.instruction)<=16384&&task.instruction.length>0);
const deps=prepared.dependencies,bundle=prepared.bundle,scratch=prepared.scratch;
const snapshotPath=path.join(output,'dsh-pinned-snapshot.json');
const buildIdentity=JSON.parse(await readFile(path.join(output,'dsh-build-identity.json'),'utf8'));
assert.equal(digest(await readFile(bundle)),buildIdentity.bundleSha256,'Prepared Runtime bundle differs');
const parentLock=JSON.parse(await readFile(path.join(recipeDir,'../coding-dsh-qualification/source-lock.json'),'utf8'));
for(const source of parentLock.harness.serviceFiles)assert.equal(digest(await readFile(path.join(deps,'node_modules',source.path))),source.sha256,`Installed Harness changed: ${source.path}`);
const base=path.join(deps,'node_modules','@deepseek-ai')+path.sep;
const load=name=>import(pathToFileURL(base+name+'/lib/index.js'));
const {Context}=await load('cordis');const llm=await load('dsh-llm');
const {Runtime,Store,SettingsSchema}=await import(pathToFileURL(bundle));
const {z}=await import(pathToFileURL(path.join(deps,'node_modules/zod/index.js')));
const out=output;const home=await mkdtemp(path.join(scratch,'joined-isolated-home-'));
const root=new Context();const handles=new Map();
const evidence={schema:'lupine.dsh-model-runtime.v1',harness:'0.2.1-rc.3',prototype:'6337fc823ce20251c8de8085948165c81aaa701e',
 taskId:config.taskId,attemptId:config.attemptId,inputSha256:config.inputSha256,targetRevision:revision,
 modelRecipeSha256:prepared.modelRecipeSha256,instructionSha256:digest(task.instruction),
 actualServices:[],toolResults:[],permissionRequests:[],channelAttempts:[],channelReceipts:[],networkAttempts:[],
 bridges:['SnapshotSetupPort prevents external sources and GitHub authorization claims','SessionController delegates actual Harness AgentRegistry','Workspace mapping is metadata, not a filesystem sandbox','Explicit credential-free native read/bash tools in dedicated coding guest','No listening web server; local result channel only'],
 configuredProvider:PROVIDER,configuredModel:MODEL,rawReasoningExported:false,providerCredentialsInGuest:false,
 root_disposed:false,modelTurns:[],finalReportChannelDeliveryQualified:false,joinedCrashRecoveryQualified:false};
let runtime;
const modelTransport=createHarnessAdapter(llm,config);
const safeText=value=>String(value).split(config.capability).join('[scoped-capability-redacted]');
const subprocessEnv={PATH:process.env.PATH,HOME:home,TMPDIR:scratch,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'};
const variable=value=>({get:()=>value});
const wait=async(predicate,label)=>{const end=deadline-15000;while(!predicate()){if(modelTransport.status().stopped)throw Error('Model transport stopped; no automatic replay');if(Date.now()>end)throw Error('Deadline waiting for '+label);await new Promise(r=>setTimeout(r,15));}};
try {
 for(const name of ['dsh-session-projection','dsh-llm','dsh-session','dsh-system-prompt','dsh-tools','dsh-agent','dsh-skill']) {await root.plugin((await load(name)).default);evidence.actualServices.push(name)}
 await root.plugin(await load('dsh-session-persistence-jsonl'),{root:path.join(home,'sessions'),compression:'none'});evidence.actualServices.push('dsh-session-persistence-jsonl');
 root.llm.registerAdapter([PROVIDER],modelTransport.adapter);
 const register=(name,parameters,execute)=>root.tools.register({name,description:'Authorized coding guest '+name,parameters,output:{schema:{type:'object',additionalProperties:true},render:(_args,v)=>[{type:'text',text:JSON.stringify(v)}]},execute});
 register('read',{type:'object',properties:{path:{type:'string'}},required:['path'],additionalProperties:false},async args=>{
  assert(typeof args.path==='string');const file=await realpath(path.resolve(targetRoot,args.path));
  assert(file.startsWith(targetRoot+path.sep),'Read outside pinned repository refused');
  const handle=await open(file,'r');
  try {
   const info=await handle.stat();assert(info.isFile()&&info.size<=65536,'Read exceeds 64 KiB');
   const buffer=Buffer.alloc(65537);const {bytesRead}=await handle.read(buffer,0,buffer.length,0);
   assert(bytesRead<=65536,'Read grew beyond 64 KiB');
   return {path:path.relative(targetRoot,file),text:safeText(buffer.subarray(0,bytesRead).toString('utf8'))};
  }finally{await handle.close();}
 });
 register('bash',{type:'object',properties:{command:{type:'string'},timeoutMs:{type:'number'}},required:['command'],additionalProperties:false},async args=>{
  assert(typeof args.command==='string'&&Buffer.byteLength(args.command)<=16384,'Command exceeds 16 KiB');
  const timeout=Math.min(args.timeoutMs??30000,30000,deadline-Date.now()-15000);
  assert(Number.isSafeInteger(timeout)&&timeout>0,'Command deadline exhausted');
  const r=spawnSync('/bin/bash',['--noprofile','--norc','-c',args.command],{cwd:targetRoot,env:subprocessEnv,timeout,maxBuffer:65536,killSignal:'SIGKILL'});
  assert(!r.error&&Number.isInteger(r.status),'Native command incomplete; outer container destruction required');
  return {exitCode:r.status,stdout:safeText(Buffer.from(r.stdout??'').toString('utf8')),stderr:safeText(Buffer.from(r.stderr??'').toString('utf8'))};
 });
 for(const name of ['skill','read_image','job_output','job_list','job_kill'])register(name,{type:'object',additionalProperties:true},async()=>{throw Error('Not available in bounded snapshot composition')});
 root.on('tools/result',(execution,result)=>{
  const rendered=JSON.stringify({value:result.value??null,content:result.content??[]});
  evidence.toolResults.push({name:execution.name,sessionId:execution.agent?.id,isError:result.isError??false,bytes:Buffer.byteLength(rendered),sha256:digest(rendered)});
 });
 await root.plugin((await load('dsh-agent-loop')).default,{agents:[],maxParallelToolCalls:1});evidence.actualServices.push('dsh-agent-loop');
 const controller={async resolveAgent(id){const agent=root.agents.get(id);return agent?{agent}:{error:{code:'session/not-found'}}},async create({sessionId,workspaceId}){if(root.agents.get(sessionId))return;const h=await root.agents.create({sessionId,meta:{cwd:workspaceId},agentOptions:{provider:PROVIDER,model:MODEL,maxTokens:config.maxOutputTokens}});handles.set(sessionId,h)},async rename({sessionId,title}){evidence.titles??={};evidence.titles[sessionId]=title},async selectModel(){throw Error('manual model changes disabled')},modelCatalog:async()=>({providers:[]})};
 root.reflect.provide('sessionController',controller);
 root.reflect.provide('workspaceRegistry',{create:async cwd=>({id:cwd})});
 root.reflect.provide('permissionPresets',{set:(session,preset)=>{evidence.permissionRequests.push({sessionId:session.id,preset,os_access_changed:false})}});
 root.reflect.provide('webServer',{host:'127.0.0.1',port:0,register:()=>()=>{}});
 root.reflect.provide('subprocess', {
  spawn(spec) {
   const argv=[...spec.argv];
   const allowed=argv[0]==='git' && JSON.stringify(argv.slice(1))===JSON.stringify(['config','-z','--show-scope','--get-regexp','^(credential\\..*|http\\..*extraheader)$']);
   if(!allowed) {evidence.networkAttempts.push({denied_subprocess_argv:argv,cwd:spec.cwd,network_attempt_established:false});throw Error('Snapshot subprocess denied');}
   if(!String(spec.cwd).startsWith(home+path.sep))throw Error('Git config read outside disposable home denied');
   evidence.localConfigChecks??=[];evidence.localConfigChecks.push({argv,cwd:spec.cwd,global_and_system_config_disabled:true});
   let output='',stderr='';
   const done=Promise.resolve().then(()=>{
    const result=spawnSync(argv[0],argv.slice(1),{cwd:spec.cwd,encoding:'utf8',timeout:2000,maxBuffer:128*1024,env:{...subprocessEnv,GIT_CEILING_DIRECTORIES:home}});
    output=String(result.stdout??'');stderr=String(result.stderr??'');
    if(result.error)throw result.error;
    return {exitCode:result.status,signal:result.signal??null};
   });
   return {done,collected:{stdout:{readFrom:()=>({text:output,nextOffset:output.length,lossy:false})},stderr:{readFrom:()=>({text:stderr,nextOffset:stderr.length,lossy:false})}}};
  }
 });

 const snapshot=JSON.parse(await readFile(snapshotPath,'utf8'));assert.equal(snapshot.schema,'lupine.dsh-pinned-snapshot.v1');assert.equal(snapshot.revision,revision);
 const store=new Store(path.join(home,'orchestrator.sqlite'));store.saveSettings(SettingsSchema.parse({...store.settings(),sources:{snapshot:{enabled:true,config:{}}},policy:{rules:[{id:'bounded',name:'Bounded snapshot',enabled:true,instruction:'Perform only the explicit authorized coding instruction in the pinned local repository. Do not publish, deploy, message people, start schedules, use credentials, make model calls outside the scoped adapter, or run scientific simulations.'}],sources:{snapshot:{allowed:[{id:'operator'}]}}},eval:{mode:'observe',model:null},executor:{maxWorkers:1,prepare:'',model:null}}));store.close();
 const port={mode:'snapshot-local-only',async resolve(machine,settings){if(Object.entries(settings.sources).some(([id,v])=>id!=='snapshot'&&v.enabled))throw Error('No external sources');return {...machine,repository:targetRoot,github:{cli:'/bin/false',login:'snapshot-disabled',noreply:'snapshot@invalid'}}}};
 runtime=new Runtime(root,{stateDir:home,promptMaxChars:variable(100000),admissionContextMaxPages:variable(10),admissionContextTimeoutMs:variable(15000)},()=>{throw Error('No persistent supervisor/restart')},port);await runtime.ready;
 runtime.sources.register({kind:'snapshot',title:{en:'Snapshot',zh:'Snapshot'},description:{en:'Local fixture',zh:'Local fixture'},schema:z.object({}),fields:[],health:['snapshot'],scope:()=>({listened:true,observed:true}),policy:{schema:z.object({allowed:z.array(z.object({id:z.string()}))}),fields:[],explicit:{en:'Explicit local fixture',zh:'Local'}},channel:{allowed:address=>address.local==='true',link:()=>({url:'',label:{en:'Local sink',zh:'Local'}}),send:async(_host,message)=>{evidence.channelAttempts.push(message.id);if(!evidence.channelReceipts.some(m=>m.id===message.id)){evidence.channelReceipts.push({id:message.id,textSha256:digest(message.text),bytes:Buffer.byteLength(message.text)});await writeFile(path.join(home,'local-channel-receipts.json'),JSON.stringify(evidence.channelReceipts));}return 'sent'}},threadContext:{messageId:t=>t.id,read:async(_cmd,t)=>({messages:[{id:t.id,from:t.actor.id,at:t.at,text:t.text}],body:{repository:snapshot.repository,revision:snapshot.revision,instructionSha256:evidence.instructionSha256}})}});
 const trigger={id:'snapshot:joined',source:'snapshot',threads:[{source:'snapshot',id:'joined'}],actor:{source:'snapshot',id:'operator'},human:true,addressed:'direct',at:new Date().toISOString(),text:task.instruction,meta:{},channel:{source:'snapshot',thread:'joined',address:{local:'true'}}};runtime.receive(trigger);
 await wait(()=>runtime.store.tickets.list().length===1,'ticket intake');
 await wait(()=>!!runtime.store.tickets.list()[0]?.ended,'worker report and durable ticket completion');
 await runtime.idle();for(const h of handles.values())await h.agent.whenIdle();await root.sessionPersistence.flush();
 evidence.tickets=runtime.store.tickets.list().map(t=>({id:t.id,ended:t.ended,assignments:t.assignments.map(a=>({id:a.id,report:a.report?{state:a.report.state,summarySha256:digest(a.report.summary??''),summaryBytes:Buffer.byteLength(a.report.summary??'')}:null}))}));evidence.actualClasses=[runtime.constructor.name,runtime.assessor.constructor.name,runtime.executor.constructor.name,runtime.sessions.constructor.name,...[...handles.values()].map(h=>h.agent.constructor.name)];
 evidence.sessions=[...handles.values()].map(h=>({id:h.agent.id,status:h.agent.status,event_count:h.agent.session.seq,roles:h.agent.session.deriveMessages().map(m=>m.role)}));
 evidence.modelTurns=modelTransport.records();
 assert(evidence.modelTurns.length>0&&evidence.modelTurns.length<=config.maxRequests);
 assert(evidence.modelTurns.every(r=>r.status==='completed'&&r.deliveredToHarness));
 assert.equal(evidence.networkAttempts.length,0);assert.equal(evidence.tickets.length,1);
 assert.equal(evidence.tickets[0].ended?.outcome,'completed');
 assert.equal(evidence.tickets[0].assignments.at(-1)?.report?.state,'ready');evidence.outcome='completed-model-coding-task';
}catch(error){evidence.outcome='failed';evidence.error={name:error.name,message:safeText(error.message).slice(0,2048)};process.exitCode=1;}
finally{
 const cleanupErrors=[];
 try{if(runtime)await runtime.stop();}catch(error){cleanupErrors.push(String(error.message??error));}
 for(const h of handles.values()){try{await h.dispose();}catch(error){cleanupErrors.push(String(error.message??error));}}
 try{await root.fiber.dispose();evidence.root_disposed=true;}catch(error){cleanupErrors.push(String(error.message??error));}
 evidence.cleanupErrors=cleanupErrors;evidence.cleanupConfirmed=cleanupErrors.length===0&&evidence.root_disposed;
 if(!evidence.cleanupConfirmed){evidence.outcome='failed';process.exitCode=1;}
 evidence.launcher_used=false;evidence.installed_session_controller_used=false;evidence.prototype_dependency_graph='explicit rc.3 remapping';
 evidence.modelTurns=modelTransport.records();evidence.providerReportedTokens=evidence.modelTurns.map(t=>({ordinal:t.ordinal,usage:t.usage}));evidence.actualModelInferenceObserved=evidence.modelTurns.some(t=>t.status==='completed');evidence.providerHttpRequestCount=null;evidence.billedUsd=null;
 evidence.credential_account_schedule_plugins_mounted=false;evidence.active_external_source_kinds=[];
 // Preserve a bounded tracked-source diff even when the model task fails.
 // Untracked deliverables require explicit runner artifact paths of their own.
 try{
  const result=spawnSync('git',['-c','core.hooksPath=/dev/null','diff','--binary','--no-ext-diff','--no-textconv','HEAD','--','.'],{cwd:targetRoot,env:subprocessEnv,timeout:5000,maxBuffer:2*1024*1024});
  assert(!result.error&&result.status===0,'Tracked diff capture incomplete');
  const bytes=Buffer.from(result.stdout??'');assert(!bytes.includes(Buffer.from(config.capability)),'Scoped capability in diff');
  await writeFile(path.join(out,'model-worktree.patch'),bytes,{flag:'wx'});
  evidence.trackedDiff={bytes:bytes.length,sha256:digest(bytes),includesUntrackedFiles:false};
 }catch{evidence.trackedDiff={available:false,reason:'bounded-diff-capture-unavailable'};evidence.outcome='failed';process.exitCode=1;}
 evidence.networkObservability='networkAttempts covers denied bridge subprocesses only, not total HTTP or kernel egress';
 const serialized=JSON.stringify(evidence,null,2)+'\n';assert(!serialized.includes(config.capability),'Scoped capability must never enter artifacts');assert(Buffer.byteLength(serialized)<=2*1024*1024,'Result artifact exceeds 2 MiB');
 await writeFile(path.join(out,'model-runtime-result.json'),serialized,{flag:'wx'});
 console.log(JSON.stringify({outcome:evidence.outcome,model_turns:evidence.modelTurns.length,tools:evidence.toolResults.map(r=>r.name),tickets:evidence.tickets?.length,disposed:evidence.root_disposed,cleanupConfirmed:evidence.cleanupConfirmed}));
}
