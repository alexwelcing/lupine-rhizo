// Explicit snapshot host bridges over REAL installed Harness sessions/agents/loop.
// Deterministic LLM transport, no actual inference; no credentials, network, pollers.
import {pathToFileURL} from 'node:url';
import {mkdtemp,writeFile,readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const deps=process.env.LUPINE_DSH_DEPS;
const bundle=process.env.LUPINE_DSH_BUNDLE;
const output=process.env.LUPINE_DSH_OUTPUT;
const scratch=process.env.LUPINE_DSH_SCRATCH;
const snapshotPath=process.env.LUPINE_DSH_SNAPSHOT;
assert(deps&&bundle&&output&&scratch&&snapshotPath,'Explicit qualification paths required');
const base=path.join(deps,'node_modules','@deepseek-ai')+path.sep;
const load=name=>import(pathToFileURL(base+name+'/lib/index.js'));
const {Context}=await load('cordis');const llm=await load('dsh-llm');
const {Runtime,Store,SettingsSchema}=await import(pathToFileURL(bundle));
const {z}=await import(pathToFileURL(path.join(deps,'node_modules/zod/index.js')));
const out=output;const home=await mkdtemp(path.join(scratch,'joined-isolated-home-'));
const root=new Context();const handles=new Map();
const evidence={version:'joined-harness-v1',harness:'0.2.1-rc.3',prototype:'6337fc823ce20251c8de8085948165c81aaa701e',runtime_source:'pinned prototype with explicit SnapshotSetupPort patch and recorded portable build',actual_inference:false,simulated_transport:true,private_reasoning_emitted:false,actualServices:[],bridges:['SnapshotSessionControllerBridge delegates actual AgentRegistry create/resolve; titles metadata only','SnapshotWorkspaceBridge maps local cwd to ID','SnapshotPermissionBridge records requested preset, grants no OS permission','SnapshotBoundedSubprocessBridge allows only exact local Git credential-config metadata query in disposable home; global/system config disabled','SnapshotNoListenHttpBridge captures handler, opens no socket','SnapshotSource and local idempotent channel'],transportCalls:[],transportCallCeiling:16,transportLimitRefusal:null,toolResults:[],permissionRequests:[],channelAttempts:[],channelReceipts:[],networkAttempts:[],root_disposed:false,home};
const counts=new Map();let runtime;
class Scripted extends llm.LlmAdapter {
 async *stream(options){
  options.signal?.throwIfAborted();
  if(evidence.transportCalls.length>=evidence.transportCallCeiling){
   evidence.transportLimitRefusal??={firstRefusedOrdinal:evidence.transportCallCeiling+1,sessionId:options.sessionId,admittedCalls:evidence.transportCalls.length,meaning:'Refused before any scripted output; subsequent refusals are not counted'};
   throw Error('Scripted transport lifetime request ceiling exhausted');
  }
  const sid=options.sessionId;const n=(counts.get(sid)||0)+1;counts.set(sid,n);
  let block;
  if(String(sid).startsWith('worker-')) {
   if(n===1)block={type:'tool-call',id:`${sid}-${n}`,name:'read',arguments:JSON.stringify({path:path.join(home,'pinned-snapshot.json')})};
   else if(n===2)block={type:'tool-call',id:`${sid}-${n}`,name:'bash',arguments:JSON.stringify({command:'snapshot-sum',timeoutMs:2000})};
   else if(n===3){const failed=options.messages.some(m=>m.role==='tool'&&m.isError===true);block={type:'tool-call',id:`${sid}-${n}`,name:'orchestrator_report',arguments:JSON.stringify({state:failed?'failed':'ready',summary:failed?'Actual bounded fixture tool failed; no measurement result is claimed.':'SIMULATED transport selected actual bounded fixture measurement: sum 7. No physical validation or real model inference.'})};}
  } else {
   const candidates=options.messages.filter(m=>m.role==='user').flatMap(m=>m.content.filter(b=>b.type==='text').flatMap(b=>{try{const v=JSON.parse(b.text);return v.kind==='candidate'?[v]:[]}catch{return []}}));
   const pending=candidates.find(v=>!evidence.transportCalls.some(c=>c.tool==='orchestrator_route'&&c.trigger_id===v.trigger_id));
   if(pending) block={type:'tool-call',id:`master-${n}`,name:'orchestrator_route',arguments:JSON.stringify({decisions:[{kind:'accept',trigger_id:pending.trigger_id,title:'Bounded pinned snapshot evaluation',worktree_name:'snapshot-check',acknowledgement:'Checking the pinned snapshot locally.'}]})};
  }
  block??={type:'text',text:'SIMULATED transport turn ended; actual Harness owns this Session and durable tool results.'};
  evidence.transportCalls.push({sessionId:sid,request:n,provider:options.provider,model:options.model,tool:block.type==='tool-call'?block.name:null,...block.name==='orchestrator_route'?{trigger_id:JSON.parse(block.arguments).decisions[0].trigger_id}:{},input_bytes:Buffer.byteLength(JSON.stringify(options.messages)),output_bytes:Buffer.byteLength(JSON.stringify(block))});
  yield {type:'block-start',index:0,blockType:block.type};
  if(block.type==='tool-call')yield {type:'tool-call-delta',index:0,id:block.id,name:block.name,argumentsDelta:block.arguments};else yield {type:'text-delta',index:0,text:block.text};
  yield {type:'block-end',index:0,block};yield {type:'usage',usage:{inputTokens:0,outputTokens:0}};yield {type:'finish',reason:{kind:block.type==='tool-call'?'tool-calls':'stop'}};
 }
}
const variable=value=>({get:()=>value});
const wait=async(predicate,label)=>{const end=Date.now()+15000;while(!predicate()){if(Date.now()>end)throw Error('Deadline waiting for '+label);await new Promise(r=>setTimeout(r,15));}};
try {
 for(const name of ['dsh-session-projection','dsh-llm','dsh-session','dsh-system-prompt','dsh-tools','dsh-agent','dsh-skill']) {await root.plugin((await load(name)).default);evidence.actualServices.push(name)}
 await root.plugin(await load('dsh-session-persistence-jsonl'),{root:path.join(home,'sessions'),compression:'none'});evidence.actualServices.push('dsh-session-persistence-jsonl');
 root.llm.registerAdapter(['evaluation-deterministic'],new Scripted());
 const tools=await load('dsh-tools');
 const register=(name,parameters,execute)=>root.tools.register({name,description:'Sandbox snapshot fixture '+name,parameters,output:{schema:{type:'object',additionalProperties:true},render:(_args,v)=>[{type:'text',text:JSON.stringify(v)}]},execute});
 register('read',{type:'object',properties:{path:{type:'string'}},required:['path'],additionalProperties:false},async args=>{if(args.path!==path.join(home,'pinned-snapshot.json'))throw Error('Only pinned snapshot allowed');return {text:await readFile(args.path,'utf8')}});
 register('bash',{type:'object',properties:{command:{type:'string'},timeoutMs:{type:'number'}},required:['command'],additionalProperties:false},async args=>{if(args.command!=='snapshot-sum')throw Error('Only bounded snapshot-sum allowed');const body=await readFile(path.join(home,'pinned-snapshot.json'),'utf8');return JSON.parse(execFileSync(process.execPath,['-e','const v=JSON.parse(process.argv[1]);console.log(JSON.stringify({sum:v.fixture.measurements.reduce((a,b)=>a+b,0),revision:v.revision}))',body],{encoding:'utf8',timeout:2000,env:{PATH:process.env.PATH}}))});
 for(const name of ['skill','read_image','job_output','job_list','job_kill'])register(name,{type:'object',additionalProperties:true},async()=>{throw Error('Not available in bounded snapshot composition')});
 root.on('tools/result',(execution,result)=>{evidence.toolResults.push({name:execution.name,sessionId:execution.agent?.id,isError:result.isError??false,value:result.value??null,content:result.content?.filter(b=>b.type==='text').map(b=>b.text)??[]})});
 await root.plugin((await load('dsh-agent-loop')).default,{agents:[],maxParallelToolCalls:1});evidence.actualServices.push('dsh-agent-loop');
 const controller={async resolveAgent(id){const agent=root.agents.get(id);return agent?{agent}:{error:{code:'session/not-found'}}},async create({sessionId,workspaceId}){if(root.agents.get(sessionId))return;const h=await root.agents.create({sessionId,meta:{cwd:workspaceId},agentOptions:{provider:'evaluation-deterministic',model:'scripted-runtime-v1',maxTokens:1000}});handles.set(sessionId,h)},async rename({sessionId,title}){evidence.titles??={};evidence.titles[sessionId]=title},async selectModel(){throw Error('manual model changes disabled')},modelCatalog:async()=>({providers:[]})};
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
    const result=spawnSync(argv[0],argv.slice(1),{cwd:spec.cwd,encoding:'utf8',timeout:2000,maxBuffer:128*1024,env:{PATH:process.env.PATH,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_CEILING_DIRECTORIES:home}});
    output=String(result.stdout??'');stderr=String(result.stderr??'');
    if(result.error)throw result.error;
    return {exitCode:result.status,signal:result.signal??null};
   });
   return {done,collected:{stdout:{readFrom:()=>({text:output,nextOffset:output.length,lossy:false})},stderr:{readFrom:()=>({text:stderr,nextOffset:stderr.length,lossy:false})}}};
  }
 });

 const snapshot=JSON.parse(await readFile(snapshotPath,'utf8'));assert.equal(snapshot.schema,'lupine.dsh-pinned-snapshot.v1');assert.match(snapshot.revision,/^[0-9a-f]{40}$/);assert.deepEqual(snapshot.fixture.measurements,[1,2,4]);await writeFile(path.join(home,'pinned-snapshot.json'),JSON.stringify(snapshot));
 const store=new Store(path.join(home,'orchestrator.sqlite'));store.saveSettings(SettingsSchema.parse({...store.settings(),sources:{snapshot:{enabled:true,config:{}}},policy:{rules:[{id:'bounded',name:'Bounded snapshot',enabled:true,instruction:'Only local pinned fixture'}],sources:{snapshot:{allowed:[{id:'operator'}]}}},eval:{mode:'observe',model:null},executor:{maxWorkers:1,prepare:'',model:null}}));store.close();
 const port={mode:'snapshot-local-only',async resolve(machine,settings){if(Object.entries(settings.sources).some(([id,v])=>id!=='snapshot'&&v.enabled))throw Error('No external sources');return {...machine,repository:snapshot.repository,github:{cli:'/bin/false',login:'snapshot-disabled',noreply:'snapshot@invalid'}}}};
 runtime=new Runtime(root,{stateDir:home,promptMaxChars:variable(100000),admissionContextMaxPages:variable(10),admissionContextTimeoutMs:variable(15000)},()=>{throw Error('No persistent supervisor/restart')},port);await runtime.ready;
 runtime.sources.register({kind:'snapshot',title:{en:'Snapshot',zh:'Snapshot'},description:{en:'Local fixture',zh:'Local fixture'},schema:z.object({}),fields:[],health:['snapshot'],scope:()=>({listened:true,observed:true}),policy:{schema:z.object({allowed:z.array(z.object({id:z.string()}))}),fields:[],explicit:{en:'Explicit local fixture',zh:'Local'}},channel:{allowed:address=>address.local==='true',link:()=>({url:'',label:{en:'Local sink',zh:'Local'}}),send:async(_host,message)=>{evidence.channelAttempts.push(message.id);if(!evidence.channelReceipts.some(m=>m.id===message.id)){evidence.channelReceipts.push({id:message.id,text:message.text});await writeFile(path.join(home,'local-channel-receipts.json'),JSON.stringify(evidence.channelReceipts));}return 'sent'}},threadContext:{messageId:t=>t.id,read:async(_cmd,t)=>({messages:[{id:t.id,from:t.actor.id,at:t.at,text:t.text}],body:{snapshot}})}});
 const trigger={id:'snapshot:joined',source:'snapshot',threads:[{source:'snapshot',id:'joined'}],actor:{source:'snapshot',id:'operator'},human:true,addressed:'direct',at:new Date().toISOString(),text:'Evaluate the committed local fixture only using bounded read and snapshot-sum; report result.',meta:{},channel:{source:'snapshot',thread:'joined',address:{local:'true'}}};runtime.receive(trigger);
 await wait(()=>runtime.store.tickets.list().length===1,'ticket intake');
 await wait(()=>!!runtime.store.tickets.list()[0]?.ended,'worker report and durable ticket completion');
 await runtime.idle();for(const h of handles.values())await h.agent.whenIdle();await root.sessionPersistence.flush();
 evidence.tickets=runtime.store.tickets.list();evidence.actualClasses=[runtime.constructor.name,runtime.assessor.constructor.name,runtime.executor.constructor.name,runtime.sessions.constructor.name,...[...handles.values()].map(h=>h.agent.constructor.name)];
 evidence.sessions=[...handles.values()].map(h=>({id:h.agent.id,status:h.agent.status,event_count:h.agent.session.seq,roles:h.agent.session.deriveMessages().map(m=>m.role)}));
 assert.equal(evidence.toolResults.filter(r=>r.name==='bash').length,1);assert(evidence.toolResults.some(r=>r.name==='bash'&&!r.isError&&r.value?.sum===7&&r.value?.revision===snapshot.revision));assert.equal(evidence.toolResults.filter(r=>r.name==='orchestrator_report'&&!r.isError).length,1);assert.equal(evidence.networkAttempts.length,0);assert.equal(evidence.tickets.length,1);assert.equal(evidence.tickets[0].ended?.outcome,'completed');assert.equal(evidence.tickets[0].assignments[0].report?.state,'ready');assert(evidence.transportCalls.length<=16);assert.equal(evidence.transportLimitRefusal,null);evidence.outcome='passed';
}catch(error){evidence.outcome='failed';evidence.error={name:error.name,message:error.message,stack:error.stack};process.exitCode=1;}
finally{
 const cleanupErrors=[];
 try{if(runtime)await runtime.stop();}catch(error){cleanupErrors.push(String(error.message??error));}
 for(const h of handles.values()){try{await h.dispose();}catch(error){cleanupErrors.push(String(error.message??error));}}
 try{await root.fiber.dispose();evidence.root_disposed=true;}catch(error){cleanupErrors.push(String(error.message??error));}
 evidence.cleanupErrors=cleanupErrors;evidence.cleanupConfirmed=cleanupErrors.length===0&&evidence.root_disposed;
 if(!evidence.cleanupConfirmed){evidence.outcome='failed';process.exitCode=1;}
 evidence.launcher_used=false;evidence.installed_session_controller_used=false;evidence.prototype_dependency_graph='explicit rc.3 remapping';
 evidence.reported_tokens=null;evidence.synthetic_usage={inputTokens:0,outputTokens:0,meaning:'scripted placeholders, not measured provider usage'};
 evidence.credential_account_schedule_plugins_mounted=false;evidence.active_external_source_kinds=[];
 evidence.final_report_channel_delivery_qualified=false;evidence.joined_crash_recovery_qualified=false;
 evidence.networkObservability='networkAttempts covers denied bridge subprocesses only, not total HTTP or kernel egress';
 const serialized=JSON.stringify(evidence,null,2)+'\n';assert(Buffer.byteLength(serialized)<=2*1024*1024,'Result artifact exceeds 2 MiB');
 await writeFile(path.join(out,'joined-runtime-result.json'),serialized,{flag:'wx'});
 console.log(JSON.stringify({outcome:evidence.outcome,transport_calls:evidence.transportCalls.length,tools:evidence.toolResults.map(r=>r.name),tickets:evidence.tickets?.length,disposed:evidence.root_disposed,cleanupConfirmed:evidence.cleanupConfirmed}));
}
