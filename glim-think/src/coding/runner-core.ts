import { createHash } from 'node:crypto';
import { RUNNER_LIMITS as L, RunnerError, assertRunner, canonical, parseCodingTask, sha256, type CodingState, type CodingTask, type EvidenceRef } from './runner-contract';

export interface RunnerStore { get<T>(key:string):Promise<T|undefined>; put<T>(key:string,value:T):Promise<void>; setAlarm(at:number):Promise<void>; deleteAlarm():Promise<void>; transaction<T>(fn:(tx:RunnerStore)=>Promise<T>):Promise<T> }
export interface RunnerProcess { stdout:ReadableStream<Uint8Array>|null|undefined; stderr:ReadableStream<Uint8Array>|null|undefined; exitCode:Promise<number> }
export interface RunnerContainer { running:boolean; start(options:{image:string;entrypoint:string[];enableInternet:boolean;instance:string;env:Record<string,string>}):void; exec(args:string[],options:{cwd:string;user:string;env:Record<string,string>;stdin?:ReadableStream<Uint8Array>;stdout:'pipe';stderr:'pipe'}):Promise<RunnerProcess>; destroy(reason?:string):Promise<void>; setInactivityTimeout(ms:number):Promise<void> }
export interface RunnerBlobs { get(key:string):Promise<{body:ReadableStream<Uint8Array>;size:number}|null>; put(key:string,bytes:Uint8Array,options?:unknown):Promise<unknown> }
export interface RunnerDependencies { store:RunnerStore; blobs:RunnerBlobs; container:RunnerContainer; now?:()=>number;
  cleanupTimeoutMs?:number;
  commandEnvironment?(state:CodingState):Promise<Record<string,string>>;
  modelTerminal?(state:CodingState):Promise<{confirmed:boolean;metadata:Record<string,unknown>}>;
  admit(input:{taskId:string;attemptId:string;ownerId:string;inputSha256:string;manifestJson:string}):Promise<{admission:'created'|'replay'}>;
  terminal(input:{taskId:string;attemptId:string;ownerId:string;inputSha256:string;outcome:'succeeded'|'failed'|'unknown';receiptJson:string;receiptSha256:string;executionExitCode:number|null;evidence:EvidenceRef|null;evidenceVerified:boolean;cleanupConfirmed:boolean}):Promise<unknown>;
}
const KEY='attempt';
const ACTIVE=new Set(['claimed','preparing','executing','collecting']);
const ENV={PATH:'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',HOME:'/run/lupine-coding/home',LANG:'C.UTF-8',LC_ALL:'C.UTF-8',GIT_CONFIG_GLOBAL:'/dev/null',GIT_CONFIG_NOSYSTEM:'1',DEBIAN_FRONTEND:'noninteractive',PIP_DISABLE_PIP_VERSION_CHECK:'1'};
const BOOTSTRAP=`set -eu
mkdir -p /run/lupine-coding/home /workspace
if ! command -v git >/dev/null || ! command -v python3 >/dev/null || ! command -v bash >/dev/null; then
  if [ "$1" != true ]; then exit 78; fi
  apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update -qq >&2
  apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 install -y -qq --no-install-recommends bash git python3 ca-certificates >&2
fi
python3 -I -c 'import json,subprocess;print(json.dumps({"osRelease":open("/etc/os-release").read(),"versions":"\\n".join(subprocess.check_output(c,stderr=subprocess.STDOUT,text=True).strip() for c in (["git","--version"],["python3","--version"],["bash","--version"]))}))'
`;
export const RECEIVE_BUNDLE=`import sys,hashlib,os
expected,size=sys.argv[1],int(sys.argv[2]);h=hashlib.sha256();n=0
with open('/run/lupine-coding/source.bundle','xb') as f:
 while True:
  b=sys.stdin.buffer.read(65536)
  if not b:break
  n+=len(b)
  if n>size:raise RuntimeError('source size rejected')
  h.update(b);f.write(b)
 f.flush();os.fsync(f.fileno())
if n!=size or h.hexdigest()!=expected:raise RuntimeError('source identity rejected')
print('source-verified')
`;
/** Only the explicit v1 shallow source selects this path. No remote fetch or history inference. */
export const SHALLOW_CHECKOUT=`set -eu
test "$1" = "$2"
test ! -e "$4"
git -c core.hooksPath=/dev/null init --quiet "$4"
printf '%s\\n' "$2" > "$4/.git/shallow"
git -C "$4" -c core.hooksPath=/dev/null bundle unbundle "$3" >&2
git -C "$4" -c core.hooksPath=/dev/null checkout --quiet --detach "$1"
test "$(git -C "$4" rev-parse --is-shallow-repository)" = true
test "$(cat "$4/.git/shallow")" = "$2"
test "$(git -C "$4" rev-list --count HEAD)" = 1
git -C "$4" fsck --strict --no-reflogs >&2
git -C "$4" rev-parse HEAD
`;
export const READ_ARTIFACT=`import os,sys,stat
parts=sys.argv[1].split('/');limit=int(sys.argv[2]);fd=os.open('/workspace/repo',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:
 for part in parts[:-1]:
  nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
 leaf=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
 try:
  st=os.fstat(leaf)
  if not stat.S_ISREG(st.st_mode) or st.st_size>limit:raise RuntimeError('artifact rejected')
  n=0
  while True:
   b=os.read(leaf,65536)
   if not b:break
   n+=len(b)
   if n>limit:raise RuntimeError('artifact grew beyond bound')
   sys.stdout.buffer.write(b)
  if n!=st.st_size:raise RuntimeError('artifact changed size')
 finally:os.close(leaf)
finally:os.close(fd)
`;
const joined=(chunks:Uint8Array[],size:number)=>{const out=new Uint8Array(size);let offset=0;for(const b of chunks){out.set(b,offset);offset+=b.length;}return out;};
const safeExit=(n:unknown):number|null=>Number.isSafeInteger(n)&&Number(n)>=0&&Number(n)<=255?Number(n):null;

/** One immutable command attempt. Alarms clean up; they never launch or replay work. */
export class CodingRunnerCore {
  private halted=false;
  private finalizing:Promise<void>|null=null;
  private pendingHandles=0;
  constructor(private readonly deps:RunnerDependencies){}
  private now(){return (this.deps.now??Date.now)();}
  private iso(){return new Date(this.now()).toISOString();}
  async status(){return (await this.deps.store.get<CodingState>(KEY))??null;}
  async submit(raw:unknown,ownerId:string):Promise<{created:boolean;state:CodingState}>{
    const task=parseCodingTask(raw);assertRunner(/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$/.test(ownerId),'Invalid runner owner');
    const inputSha256=await sha256(canonical(task));
    return this.deps.store.transaction(async tx=>{
      const old=await tx.get<CodingState>(KEY);
      if(old){assertRunner(old.inputSha256===inputSha256&&old.ownerId===ownerId,'Attempt identity conflict',409);return {created:false,state:old};}
      const state:CodingState={schema:'lupine.coding-attempt.v1',task,inputSha256,ownerId,status:'claimed',claimedAt:this.iso(),deadlineAtMs:this.now()+(task.timeoutSeconds+L.setupSeconds+L.captureSeconds)*1000,
        updatedAt:this.iso(),executionStarted:false,executionExitCode:null,reason:null,cleanupConfirmed:false,evidence:[],receipt:null,ledgerRecorded:false,pendingExec:false,cleanupAttempts:0,terminalIntent:null,environment:null};
      await tx.put(KEY,state);await tx.setAlarm(state.deadlineAtMs);return {created:true,state};
    });
  }
  private async change(fn:(state:CodingState)=>void){return this.deps.store.transaction(async tx=>{const s=await tx.get<CodingState>(KEY);assertRunner(s,'Attempt unavailable',404);fn(s);s.updatedAt=this.iso();await tx.put(KEY,s);return s;});}
  private async changeCapture(fn:(state:CodingState)=>void){return this.change(s=>{assertRunner(ACTIVE.has(s.status)&&!s.terminalIntent,'Captured evidence fenced after terminal snapshot',409);fn(s);});}
  private async active(){const s=await this.status();if(this.halted||!s||!ACTIVE.has(s.status)||this.now()>=s.deadlineAtMs)throw new RunnerError(409,'Attempt no longer active');return s;}
  private async changeActive(fn:(state:CodingState)=>void){return this.change(s=>{assertRunner(!this.halted&&ACTIVE.has(s.status)&&this.now()<s.deadlineAtMs,'Attempt mutation fenced after stop',409);fn(s);});}
  private async bounded<T>(promise:Promise<T>,ms:number):Promise<T|null>{let timer:ReturnType<typeof setTimeout>|undefined;void promise.catch(()=>{});try{return await Promise.race([promise,new Promise<null>(resolve=>{timer=setTimeout(()=>resolve(null),ms);})]);}catch{return null;}finally{if(timer!==undefined)clearTimeout(timer);}}
  private async destroy():Promise<boolean>{
    const current=await this.status();
    // A pending exec acknowledgement cannot be proven absent by an earlier destroy response.
    const pending=current?.pendingExec===true||this.pendingHandles>0;
    const confirmed=await this.bounded(this.deps.container.destroy('coding-attempt-cleanup').then(()=>true),this.deps.cleanupTimeoutMs??5000);
    return confirmed===true&&!pending;
  }
  private async capture(stream:ReadableStream<Uint8Array>|null|undefined,limit:number){
    if(!stream)return {bytes:new Uint8Array(),incomplete:true};
    const reader=stream.getReader(),chunks:Uint8Array[]=[];let size=0,incomplete=false;
    try {for(;;){const result=await reader.read();if(result.done)break;const chunk=result.value;
      if(size+chunk.byteLength>limit){const retained=chunk.subarray(0,Math.max(0,limit-size));chunks.push(retained);size+=retained.length;incomplete=true;this.halted=true;void this.destroy();await reader.cancel().catch(()=>{});break;}
      chunks.push(chunk);size+=chunk.byteLength;
    }}catch{incomplete=true;this.halted=true;void this.destroy();}finally{reader.releaseLock();}
    return {bytes:joined(chunks,size),incomplete};
  }
  private async execute(args:string[],cwd='/run/lupine-coding',stdin?:ReadableStream<Uint8Array>,limit=L.logBytes,extraEnv:Record<string,string>={}){
    await this.active();
    await this.changeActive(s=>{s.pendingExec=true;});
    this.pendingHandles++;
    const promise=this.deps.container.exec(args,{cwd,user:'0:0',env:{...ENV,...extraEnv},stdout:'pipe',stderr:'pipe',...(stdin?{stdin}: {})});
    // A start acknowledgement arriving after timeout must not leave a live guest.
    void promise.then(()=>{this.pendingHandles--;if(this.halted)void this.bounded(this.deps.container.destroy('late-coding-exec'),this.deps.cleanupTimeoutMs??5000);},()=>{this.pendingHandles--;});
    const process=await promise;
    await this.changeActive(s=>{s.pendingExec=false;});
    if(this.halted){void this.destroy();throw new RunnerError(409,'Late execution acknowledgement');}
    const [stdout,stderr,exit]=await Promise.all([this.capture(process.stdout,limit),this.capture(process.stderr,limit),process.exitCode.then(safeExit,()=>null)]);
    return {stdout:stdout.bytes,stderr:stderr.bytes,exitCode:exit,incomplete:stdout.incomplete||stderr.incomplete||exit===null};
  }
  private async verifyStored(ref:EvidenceRef){
    const object=await this.deps.blobs.get(ref.artifactKey);assertRunner(object&&object.size===ref.bytes,'Archived evidence unavailable',503);
    const reader=object.body.getReader(),hash=createHash('sha256');let size=0;
    try{for(;;){const next=await reader.read();if(next.done)break;size+=next.value.length;assertRunner(size<=ref.bytes,'Archived evidence exceeds bound',503);hash.update(next.value);}
      assertRunner(size===ref.bytes&&hash.digest('hex')===ref.sha256,'Archived evidence identity mismatch',503);
    }catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
  }
  private async save(kind:EvidenceRef['kind'],bytes:Uint8Array,path?:string){
    const s=await this.status();assertRunner(s,'Attempt unavailable',404);const hash=await sha256(bytes);
    const ref:EvidenceRef={artifactKey:`runs/${s.task.attemptId}/${kind}/${hash}`,sha256:hash,bytes:bytes.byteLength,kind,...(path?{path}:{})};
    await this.deps.blobs.put(ref.artifactKey,bytes,{onlyIf:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/octet-stream'}});
    await this.verifyStored(ref);return ref;
  }
  private async saveSetup(stage:'source-receive'|'checkout',result:{stdout:Uint8Array;stderr:Uint8Array;exitCode:number|null;incomplete:boolean}){
    // Preserve exact bounded raw bytes before a validation failure can discard diagnostics.
    const stdout=await this.save(`${stage}-stdout`,result.stdout);
    await this.changeCapture(s=>{s.evidence.push(stdout);});
    const stderr=await this.save(`${stage}-stderr`,result.stderr);
    await this.changeCapture(s=>{s.evidence.push(stderr);});
    const detail=await this.save(stage,new TextEncoder().encode(canonical({schema:'lupine.coding-setup-stage.v1',stage,exitCode:result.exitCode,incomplete:result.incomplete,stdout,stderr,streamByteLimit:L.logBytes})));
    await this.changeCapture(s=>{s.evidence.push(detail);});
  }
  private sourceStream(body:ReadableStream<Uint8Array>,task:CodingTask):ReadableStream<Uint8Array>{
    const hash=createHash('sha256');let bytes=0;const reader=body.getReader();
    return new ReadableStream<Uint8Array>({pull:async controller=>{
      try{const next=await reader.read();if(next.done){assertRunner(bytes===task.source.bytes&&hash.digest('hex')===task.source.sha256,'Source stream identity mismatch');controller.close();reader.releaseLock();return;}
        bytes+=next.value.length;assertRunner(bytes<=task.source.bytes&&bytes<=L.sourceBytes,'Source stream exceeds bound');hash.update(next.value);controller.enqueue(next.value);
      }catch(error){controller.error(error);await reader.cancel().catch(()=>{});}},cancel:reason=>reader.cancel(reason)});
  }
  async run():Promise<void>{
    const claimed=await this.deps.store.transaction(async tx=>{const s=await tx.get<CodingState>(KEY);if(!s||s.status!=='claimed')return null;s.status='preparing';s.updatedAt=this.iso();await tx.put(KEY,s);return s;});
    if(!claimed)return;
    let outcome:'succeeded'|'failed'|'unknown'='unknown',reason='execution-outcome-unconfirmed';let timer:ReturnType<typeof setTimeout>|undefined;
    const timeout=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{this.halted=true;void this.destroy();reject(new RunnerError(504,'Attempt deadline reached'));},Math.max(1,claimed.deadlineAtMs-this.now()));});
    const work=async()=>{
      const admission=await this.deps.admit({taskId:claimed.task.taskId,attemptId:claimed.task.attemptId,ownerId:claimed.ownerId,inputSha256:claimed.inputSha256,manifestJson:canonical(claimed.task)});
      assertRunner(admission.admission==='created','Ledger admission replay cannot authorize execution',409);
      await this.active();
      const source=await this.deps.blobs.get(claimed.task.source.artifactKey);assertRunner(source&&source.size===claimed.task.source.bytes,'Pinned source unavailable',409);
      await this.active();
      this.deps.container.start({image:'cloudflare/debian-trixie',entrypoint:['sleep','infinity'],instance:'standard-1',enableInternet:claimed.task.enableInternet,env:{PATH:ENV.PATH}});
      await this.deps.container.setInactivityTimeout((claimed.task.timeoutSeconds+L.setupSeconds+L.captureSeconds)*1000);
      await this.changeActive(s=>{s.setupStage='bootstrap';});
      const bootstrap=await this.execute(['/bin/sh','-c',BOOTSTRAP,'bootstrap',String(claimed.task.enableInternet)],'/');
      const bootLog=await this.save('bootstrap',new TextEncoder().encode(canonical({stdout:new TextDecoder().decode(bootstrap.stdout),stderr:new TextDecoder().decode(bootstrap.stderr),exitCode:bootstrap.exitCode})));
      await this.changeCapture(s=>{s.evidence.push(bootLog);});
      assertRunner(!bootstrap.incomplete&&bootstrap.exitCode===0,'Bootstrap failed or exceeded its output bound',409);
      let environment:{osRelease:string;versions:string};try{environment=JSON.parse(new TextDecoder().decode(bootstrap.stdout));}catch{throw new RunnerError(409,'Bootstrap metadata unavailable');}
      assertRunner(typeof environment.osRelease==='string'&&environment.osRelease.length<=4096&&typeof environment.versions==='string'&&environment.versions.length<=8192,'Invalid bootstrap metadata');
      await this.changeActive(s=>{s.environment={image:'cloudflare/debian-trixie',...environment};});
      await this.changeActive(s=>{s.setupStage='source-receive';});
      const received=await this.execute(['python3','-I','-c',RECEIVE_BUNDLE,claimed.task.source.sha256,String(claimed.task.source.bytes)],'/run/lupine-coding',this.sourceStream(source.body,claimed.task));
      await this.saveSetup('source-receive',received);
      assertRunner(!received.incomplete&&received.exitCode===0&&new TextDecoder().decode(received.stdout).trim()==='source-verified','Source integrity check failed',409);
      await this.changeActive(s=>{s.setupStage='checkout';});
      const checkout=await this.execute(claimed.task.source.kind==='git-shallow-bundle-v1'
        ?['/bin/sh','-c',SHALLOW_CHECKOUT,'checkout',claimed.task.repository.commit,claimed.task.source.boundaryCommit,'/run/lupine-coding/source.bundle','/workspace/repo']
        :['/bin/sh','-c','set -eu; git -c core.hooksPath=/dev/null clone --quiet --no-checkout /run/lupine-coding/source.bundle /workspace/repo; git -C /workspace/repo -c core.hooksPath=/dev/null checkout --quiet --detach "$1"; git -C /workspace/repo rev-parse HEAD','checkout',claimed.task.repository.commit],'/workspace');
      await this.saveSetup('checkout',checkout);
      assertRunner(!checkout.incomplete&&checkout.exitCode===0&&new TextDecoder().decode(checkout.stdout).trim()===claimed.task.repository.commit,'Pinned commit checkout failed',409);
      const commandEnv=claimed.task.model?await this.deps.commandEnvironment?.(await this.active()):{};
      assertRunner(!claimed.task.model||commandEnv,'Included model broker unavailable',503);
      await this.active();await this.changeActive(s=>{s.status='executing';s.executionStarted=true;});
      const command=await this.execute(['/usr/bin/timeout','--signal=TERM','--kill-after=5',String(claimed.task.timeoutSeconds),'/bin/bash','--noprofile','--norc','-c',claimed.task.command],'/workspace/repo',undefined,L.logBytes,commandEnv??{});
      const stdout=await this.save('stdout',command.stdout),stderr=await this.save('stderr',command.stderr);
      await this.changeCapture(s=>{s.executionExitCode=command.exitCode;s.evidence.push(stdout,stderr);if(ACTIVE.has(s.status))s.status='collecting';});
      assertRunner(!command.incomplete,'Command output or terminal evidence incomplete',409);
      await this.active();let artifactBytes=0;
      for(const path of claimed.task.artifactPaths){const output=await this.execute(['python3','-I','-c',READ_ARTIFACT,path,String(L.artifactBytes)],'/workspace/repo',undefined,L.artifactBytes);
        assertRunner(!output.incomplete&&output.exitCode===0,'Requested artifact unavailable or invalid',409);artifactBytes+=output.stdout.length;assertRunner(artifactBytes<=L.artifactTotalBytes,'Artifact aggregate exceeds bound',409);
        const artifact=await this.save('artifact',output.stdout,path);await this.changeActive(s=>{s.evidence.push(artifact);});}
      outcome=command.exitCode===0?'succeeded':'failed';reason=command.exitCode===0?'command-exited-zero':'command-exited-nonzero';
    };
    // Consume rejection even if deadline wins. No deferred stage can run after active() refuses it.
    const running=work();void running.catch(()=>{});
    try{await Promise.race([running,timeout]);}catch(error){const current=await this.status();
      outcome=current?.executionStarted?'unknown':'failed';reason=error instanceof RunnerError?(error.code===504?'attempt-deadline-reached':current?.executionStarted?'command-evidence-incomplete':current?.setupStage?`${current.setupStage}-failed`:'pre-execution-failed'):current?.setupStage&&!current.executionStarted?`${current.setupStage}-outcome-unconfirmed`:'transport-or-storage-outcome-unconfirmed';
      if(!(error instanceof RunnerError))outcome='unknown';
    }finally{if(timer!==undefined)clearTimeout(timer);this.halted=true;}
    await this.finish(outcome,reason);
  }
  private async finish(outcome:'succeeded'|'failed'|'unknown',reason:string){
    if(this.finalizing)return this.finalizing;
    this.finalizing=this.finalize(outcome,reason).catch(error=>{this.finalizing=null;throw error;});return this.finalizing;
  }
  private async finalize(outcome:'succeeded'|'failed'|'unknown',reason:string){
    this.halted=true;
    const locked=await this.deps.store.transaction(async tx=>{const s=await tx.get<CodingState>(KEY);if(!s||(!ACTIVE.has(s.status)&&s.status!=='finalizing'))return null;
      s.status='finalizing';s.updatedAt=this.iso();await tx.put(KEY,s);return s;});
    if(!locked)return;
    const cleaned=await this.destroy();if(!cleaned){outcome='unknown';reason='container-cleanup-unconfirmed';}
    const current=await this.status();if(!current||current.terminalIntent)return;
    let modelEvidence:Record<string,unknown>|null=null;
    if(current.task.model){
      const model=await this.bounded(this.deps.modelTerminal?.(current)??Promise.reject(Error('broker unavailable')),15000);
      modelEvidence=model?.metadata??{state:'unavailable'};
      if(!model?.confirmed){outcome='unknown';reason='model-terminal-unconfirmed';}
    }
    const payload={schema:'lupine.coding-terminal.v1',taskId:current.task.taskId,attemptId:current.task.attemptId,inputSha256:current.inputSha256,ownerId:current.ownerId,
      repository:current.task.repository,source:current.task.source,mode:current.task.mode,outcome,reason,executionStarted:current.executionStarted,executionExitCode:current.executionExitCode,
      claimedAt:current.claimedAt,finishedAt:this.iso(),cleanupConfirmed:cleaned,evidence:current.evidence,environment:current.environment,
      setupStage:current.setupStage??null,sourceCommitChecked:current.executionStarted,providerCredentialsSupplied:false,modelExecutionQualified:!!modelEvidence&&Number(modelEvidence.completedRequests)>0&&outcome==='succeeded',modelEvidence,guestPrivilege:'root-within-dedicated-container',
      artifactScope:'Guest-produced bytes observed after command exit; not a semantic verdict or atomic filesystem snapshot.',acceptance:'separate-review-required',automaticReplay:false};
    const receiptJson=canonical(payload),receiptSha256=await sha256(receiptJson);
    await this.change(s=>{assertRunner(s.status==='finalizing'&&!s.terminalIntent,'Terminal intent already fixed',409);s.cleanupConfirmed=cleaned;s.cleanupAttempts++;s.terminalIntent={outcome,reason,receiptJson,receiptSha256,cleanupConfirmed:cleaned};});
    await this.reconcileTerminal();
    if(cleaned)await this.deps.store.deleteAlarm();else await this.deps.store.setAlarm(this.now()+60000);
  }
  /** Retries only the exact frozen evidence/ledger commit. Never starts or execs a guest. */
  async reconcileTerminal(){
    const s=await this.status();assertRunner(s?.terminalIntent,'No frozen terminal intent to reconcile',409);
    const intent=s.terminalIntent;if(s.ledgerRecorded)return;
    let receipt:EvidenceRef|null=null,valid=true;
    const commit=async()=>{
      assertRunner(await sha256(intent.receiptJson)===intent.receiptSha256,'Terminal intent integrity failed',409);
      const payload=JSON.parse(intent.receiptJson);assertRunner(payload.taskId===s.task.taskId&&payload.attemptId===s.task.attemptId&&payload.inputSha256===s.inputSha256,'Terminal identity failed',409);
      for(const ref of s.evidence){await this.verifyStored(ref);assertRunner(valid,'Metadata reconciliation deadline reached',504);}
      receipt=await this.save('receipt',new TextEncoder().encode(intent.receiptJson));assertRunner(valid,'Metadata reconciliation deadline reached',504);
      await this.deps.terminal({taskId:s.task.taskId,attemptId:s.task.attemptId,ownerId:s.ownerId,inputSha256:s.inputSha256,outcome:intent.outcome,receiptJson:intent.receiptJson,receiptSha256:intent.receiptSha256,executionExitCode:s.executionExitCode,evidence:receipt,evidenceVerified:true,cleanupConfirmed:intent.cleanupConfirmed});
      assertRunner(valid,'Metadata reconciliation deadline reached',504);
      await this.change(state=>{assertRunner(valid&&state.terminalIntent?.receiptSha256===intent.receiptSha256,'Terminal intent changed',409);state.status=intent.outcome;state.reason=intent.reason;state.receipt=receipt;state.ledgerRecorded=true;});return true;
    };
    const committed=await this.bounded(commit(),(this.deps.cleanupTimeoutMs??5000)*3);valid=false;
    if(committed!==true)await this.change(state=>{if(state.ledgerRecorded)return;state.status='unknown';state.reason='terminal-persistence-unconfirmed';state.receipt=receipt;});
  }
  async alarm(){
    const state=await this.status();if(!state)return;
    if(ACTIVE.has(state.status)&&this.now()<state.deadlineAtMs){await this.deps.store.setAlarm(state.deadlineAtMs);return;}
    this.halted=true;
    if(ACTIVE.has(state.status)||(state.status==='finalizing'&&!state.terminalIntent))await this.finish('unknown','watchdog-expired-no-replay');
    else if(!state.cleanupConfirmed&&state.cleanupAttempts<3){const cleaned=await this.destroy();await this.change(s=>{s.cleanupAttempts++;if(cleaned)s.cleanupConfirmed=true;});
      if(cleaned||state.cleanupAttempts+1>=3)await this.deps.store.deleteAlarm();else await this.deps.store.setAlarm(this.now()+60000);
    }else await this.deps.store.deleteAlarm();
  }
}
