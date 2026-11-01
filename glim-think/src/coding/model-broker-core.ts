/** Included-subscription coding authority. The caller is a trusted service binding,
 * never the guest. Provider credentials and private thinking stay outside guests.
 * Every admitted ordinal is consumed before asynchronous provider work; ambiguity
 * closes future admission rather than replaying an inference. */
export const CODING_MODEL = 'MiniMax-M3.1-Flash' as const;
export type Json = null | boolean | number | string | Json[] | {[key:string]:Json};
export type Message = {role:'user'|'assistant';content:Json};
export type BrokerPermit = {
  schema:'lupine.coding-model-permit.v1';consumerService:string;taskId:string;attemptId:string;inputSha256:string;
  repositoryCommit:string;sourceSha256:string;adapterSha256:string;model:typeof CODING_MODEL;
  maxRequests:number;maxOutputTokens:number;maxInputBytes:number;createdAtMs:number;expiresAtMs:number;runnerDeadlineAtMs:number;
};
export type BrokerTurn = {schema:'lupine.coding-model-turn.v1';taskId:string;attemptId:string;inputSha256:string;ordinal:number;sessionId:string;
  body:{model:typeof CODING_MODEL;max_tokens:number;stream:false;system?:Json;messages:Message[];tools?:Json[]}};
export type PrivateProviderResult = {state:'completed';model:typeof CODING_MODEL;content:Json[];stop_reason:'end_turn'|'tool_use';usage:Json;receiptSha256:string;settlementConfirmed:true}
  | {state:'not-dispatched'|'unknown'|'failed';reason:string};
export interface BrokerTransaction {get<T>(key:string):Promise<T|undefined>;put<T>(key:string,value:T):Promise<void>}
export interface BrokerStore {transaction<T>(fn:(tx:BrokerTransaction)=>Promise<T>):Promise<T>}
export interface BrokerArchive {put(key:string,bytes:Uint8Array):Promise<void>;get(key:string):Promise<Uint8Array|null>}
export interface BrokerProvider {
  /** These identities are deployment supplied, not selected by a guest/permit. */
  policySha256:string;credentialGenerationSha256:string;
  ready(signal:AbortSignal):Promise<{allowed:boolean;reason:string}>;
  invoke(input:{requestId:string;jobId:string;seatId:string;body:BrokerTurn['body'];signal:AbortSignal}):Promise<PrivateProviderResult>;
}
type Ref={key:string;sha256:string;bytes:number};
type Operation={ordinal:number;sessionId:string;bodySha256:string;requestId:string;state:'intent'|'completed'|'not-dispatched'|'failed'|'unknown';reason:string|null;archive:Ref|null;receiptSha256:string|null};
type State={permit:BrokerPermit;permitSha256:string;policySha256:string;credentialGenerationSha256:string;status:'open'|'closed'|'attention';lastAtMs:number;nextOrdinal:number;activeOrdinal:number|null;operations:Operation[];sessions:Record<string,Ref>};
type Transcript={context:Json;sanitized:Message[];private:Message[]};
export type BrokerDenied={ok:false;schema:'lupine.coding-model-result.v1';state:string;reason:string;ordinal?:number;requestId?:string};
export type BrokerCompleted={ok:true;schema:'lupine.coding-model-result.v1';state:'completed';taskId:string;attemptId:string;inputSha256:string;ordinal:number;sessionId:string;bodySha256:string;requestId:string;model:typeof CODING_MODEL;content:Json[];stop_reason:'end_turn'|'tool_use';usage:Json;receiptSha256:string;archiveSha256:string;settlementConfirmed:true};
export class BrokerError extends Error {constructor(readonly reason:string){super(reason)}}
function fail(reason:string):never {throw new BrokerError(reason)}
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const id=(v:unknown):v is string=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(v)&&!v.startsWith('sk-')&&!['constructor','prototype','__proto__'].includes(v);
const integer=(v:unknown,min:number,max:number):v is number=>Number.isSafeInteger(v)&&Number(v)>=min&&Number(v)<=max;
const enc=new TextEncoder();
export function brokerCanonical(v:unknown):string {
  if(v===null||typeof v==='string'||typeof v==='boolean')return JSON.stringify(v);
  if(typeof v==='number'&&Number.isFinite(v))return JSON.stringify(v);
  if(Array.isArray(v))return '['+v.map(brokerCanonical).join(',')+']';
  if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+brokerCanonical((v as Record<string,unknown>)[k])).join(',')+'}';
  return fail('non-json-value');
}
export async function brokerHash(v:string|Uint8Array):Promise<string>{const bytes=typeof v==='string'?enc.encode(v):v;return [...new Uint8Array(await crypto.subtle.digest('SHA-256',Uint8Array.from(bytes).buffer as ArrayBuffer))].map(n=>n.toString(16).padStart(2,'0')).join('')}
/** Snapshot plain data without evaluating accessors or user toJSON methods. */
function snapshot(value:unknown,maxBytes:number):any {
  const seen=new Set<object>();let nodes=0;
  const copy=(v:unknown,depth:number):Json=>{
    if(++nodes>32768||depth>48)fail('input-complexity-limit');
    if(v===null||typeof v==='boolean'||typeof v==='string'||typeof v==='number'&&Number.isFinite(v))return v as Json;
    if(!v||typeof v!=='object'||seen.has(v))return fail('invalid-plain-json');
    const proto=Object.getPrototypeOf(v);if(proto!==Object.prototype&&proto!==null&&!Array.isArray(v))fail('invalid-json-prototype');
    seen.add(v);const out:any=Array.isArray(v)?[]:{};
    for(const k of Reflect.ownKeys(v)){
      if(Array.isArray(v)&&k==='length')continue;
      if(typeof k!=='string'||k==='__proto__'||k==='constructor'||k==='prototype')fail('invalid-json-key');
      const d=Object.getOwnPropertyDescriptor(v,k)!;if(!('value'in d)||!d.enumerable)fail('invalid-json-descriptor');
      if(Array.isArray(v)&&!/^\d+$/.test(k))fail('invalid-json-array');
      out[k]=copy(d.value,depth+1);
    }
    seen.delete(v);if(Array.isArray(v)&&(out.length!==v.length||Array.from({length:v.length},(_,i)=>i).some(i=>!Object.hasOwn(out,i))))fail('sparse-json-array');return out;
  };
  const out=copy(value,0);if(enc.encode(brokerCanonical(out)).length>maxBytes)fail('input-byte-limit');return out;
}
function exact(v:any,required:string[],optional:string[]=[]):boolean{return !!v&&typeof v==='object'&&!Array.isArray(v)&&required.every(k=>Object.hasOwn(v,k))&&Object.keys(v).every(k=>required.includes(k)||optional.includes(k))}
export function parseBrokerPermit(raw:unknown,consumerService:string):BrokerPermit {
  const p=snapshot(raw,8192);
  if(!exact(p,['schema','consumerService','taskId','attemptId','inputSha256','repositoryCommit','sourceSha256','adapterSha256','model','maxRequests','maxOutputTokens','maxInputBytes','createdAtMs','expiresAtMs','runnerDeadlineAtMs'])
    ||p.schema!=='lupine.coding-model-permit.v1'||p.consumerService!==consumerService||!id(p.taskId)||!id(p.attemptId)||!hash(p.inputSha256)||!hash(p.sourceSha256)||!hash(p.adapterSha256)
    ||typeof p.repositoryCommit!=='string'||!/^[a-f0-9]{40}$/.test(p.repositoryCommit)||p.model!==CODING_MODEL
    ||!integer(p.maxRequests,1,16)||!integer(p.maxOutputTokens,1,4096)||!integer(p.maxInputBytes,1,262144)
    ||!integer(p.createdAtMs,0,Number.MAX_SAFE_INTEGER)||!integer(p.expiresAtMs,p.createdAtMs+1,Number.MAX_SAFE_INTEGER)||!integer(p.runnerDeadlineAtMs,p.expiresAtMs,Number.MAX_SAFE_INTEGER))fail('invalid-permit');
  return p;
}
function parseTurn(raw:unknown,p:BrokerPermit):BrokerTurn {
  const t=snapshot(raw,p.maxInputBytes+2048), b=t.body;
  if(!exact(t,['schema','taskId','attemptId','inputSha256','ordinal','sessionId','body'])||t.schema!=='lupine.coding-model-turn.v1'||t.taskId!==p.taskId||t.attemptId!==p.attemptId||t.inputSha256!==p.inputSha256||!integer(t.ordinal,1,p.maxRequests)||!id(t.sessionId)
    ||!exact(b,['model','max_tokens','stream','messages'],['system','tools'])||b.model!==CODING_MODEL||b.stream!==false||!integer(b.max_tokens,1,p.maxOutputTokens)||!Array.isArray(b.messages)||b.messages.length<1||b.messages.length>256)fail('invalid-turn');
  if(enc.encode(brokerCanonical(b)).length>p.maxInputBytes)fail('input-byte-limit');
  const text=(v:any)=>exact(v,['type','text'])&&v.type==='text'&&typeof v.text==='string';
  const names=new Set<string>();
  if(b.tools!==undefined){if(!Array.isArray(b.tools)||b.tools.length>16)fail('invalid-tools');for(const tool of b.tools){if(!exact(tool,['name','description','input_schema'])||typeof tool.name!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(tool.name)||names.has(tool.name)||typeof tool.description!=='string'||!tool.input_schema||typeof tool.input_schema!=='object'||Array.isArray(tool.input_schema))fail('invalid-tools');names.add(tool.name)}}
  if(b.system!==undefined&&typeof b.system!=='string'&&!(Array.isArray(b.system)&&b.system.every(text)))fail('invalid-system');
  for(const m of b.messages){
    if(!exact(m,['role','content'])||!['user','assistant'].includes(m.role))fail('invalid-message');
    if(typeof m.content==='string')continue;
    if(!Array.isArray(m.content)||m.content.length>256)fail('invalid-message-content');
    for(const c of m.content){
      if(text(c))continue;
      if(m.role==='assistant'&&exact(c,['type','id','name','input'])&&c.type==='tool_use'&&typeof c.id==='string'&&c.id.length<=256&&names.has(c.name)&&c.input&&typeof c.input==='object'&&!Array.isArray(c.input))continue;
      if(m.role==='user'&&exact(c,['type','tool_use_id','content'],['is_error'])&&c.type==='tool_result'&&typeof c.tool_use_id==='string'&&c.tool_use_id.length<=256&&(c.is_error===undefined||typeof c.is_error==='boolean')&&(typeof c.content==='string'||Array.isArray(c.content)&&c.content.every(text)))continue;
      fail('unsupported-message-content');
    }
  }
  return t;
}
function cleanContent(content:Json[],tools:Json[]|undefined):Json[]{
  const names=new Set((tools??[]).map(t=>(t as any).name)),ids=new Set<string>();const out:Json[]=[];
  for(const raw of content){const c=raw as any;
    if(c?.type==='thinking'||c?.type==='redacted_thinking')continue;
    if(exact(c,['type','text'])&&c.type==='text'&&typeof c.text==='string'){out.push(c);continue}
    if(exact(c,['type','id','name','input'])&&c.type==='tool_use'&&id(c.id)&&!ids.has(c.id)&&names.has(c.name)&&c.input&&typeof c.input==='object'&&!Array.isArray(c.input)){ids.add(c.id);out.push(c);continue}
    fail('unsupported-provider-content');
  }
  if(!out.length)fail('empty-sanitized-response');return out;
}
/** Only the provider supplies assistant history. A guest contributes one merged
 * user message, including exactly the outstanding tool results if any. These
 * are guest-reported tool results, not proof of actual shell/tool execution. */
function userContribution(message:Message,previousAssistant:Json|null):void {
  if(message.role!=='user')fail('guest-assistant-history-forbidden');
  const expected=new Set<string>(Array.isArray(previousAssistant)?previousAssistant.filter((c:any)=>c?.type==='tool_use').map((c:any)=>c.id):[]);
  if(typeof message.content==='string'){if(expected.size)fail('missing-tool-results');return}
  if(!Array.isArray(message.content)||!message.content.length)fail('invalid-user-contribution');
  const seen=new Set<string>();
  for(const c of message.content as any[]){
    if(c.type==='text'){if(seen.size!==expected.size)fail('user-text-before-tool-results');continue}
    if(c.type!=='tool_result'||!expected.has(c.tool_use_id)||seen.has(c.tool_use_id))fail('orphan-or-duplicate-tool-result');
    seen.add(c.tool_use_id);
  }
  if(seen.size!==expected.size)fail('missing-tool-results');
}
const denied=(state:string,reason:string,op?:Operation):BrokerDenied=>({ok:false,schema:'lupine.coding-model-result.v1',state,reason,...(op?{ordinal:op.ordinal,requestId:op.requestId}:{})});
export class CodingModelBrokerCore {
  constructor(private readonly deps:{store:BrokerStore;archive:BrokerArchive;provider:BrokerProvider;consumerService:string;now?:()=>number}){
    if(!hash(deps.provider.policySha256)||!hash(deps.provider.credentialGenerationSha256))fail('invalid-provider-identity');
  }
  private now(){const n=(this.deps.now??Date.now)();if(!integer(n,0,Number.MAX_SAFE_INTEGER))fail('invalid-clock');return n}
  async open(raw:unknown){
    const p=parseBrokerPermit(raw,this.deps.consumerService), digest=await brokerHash(brokerCanonical(p)),at=this.now();
    if(at<p.createdAtMs||at>=p.expiresAtMs)fail('expired-permit');
    await this.deps.store.transaction(async tx=>{if(await tx.get('closed'))fail('permit-closed');const old=await tx.get<State>('state');if(old){if(old.permitSha256!==digest||old.policySha256!==this.deps.provider.policySha256||old.credentialGenerationSha256!==this.deps.provider.credentialGenerationSha256)fail('permit-conflict');if(old.status!=='open')fail('permit-not-admitting');return}
      await tx.put<State>('state',{permit:p,permitSha256:digest,policySha256:this.deps.provider.policySha256,credentialGenerationSha256:this.deps.provider.credentialGenerationSha256,status:'open',lastAtMs:at,nextOrdinal:1,activeOrdinal:null,operations:[],sessions:{}});
    });
    return this.status();
  }
  async status(){return this.deps.store.transaction(async tx=>{const s=await tx.get<State>('state');if(!s)return null;return {schema:'lupine.coding-model-status.v1',taskId:s.permit.taskId,attemptId:s.permit.attemptId,inputSha256:s.permit.inputSha256,permitSha256:s.permitSha256,model:CODING_MODEL,status:s.status,expiresAtMs:s.permit.expiresAtMs,consumedRequests:s.operations.length,maxRequests:s.permit.maxRequests,activeOrdinal:s.activeOrdinal,policySha256:s.policySha256,credentialGenerationSha256:s.credentialGenerationSha256,operations:s.operations.map(o=>({...o})),automaticReplay:false}})}
  async close(identity?:{attemptId:string;inputSha256:string}){
    const closed=await this.deps.store.transaction(async tx=>{
      const s=await tx.get<State>('state'),prior=await tx.get<{attemptId:string;inputSha256:string}>('closed');
      const wanted=identity??(s?{attemptId:s.permit.attemptId,inputSha256:s.permit.inputSha256}:null);
      if(!wanted||!id(wanted.attemptId)||!hash(wanted.inputSha256))fail('close-identity-required');
      if(s&&(s.permit.attemptId!==wanted.attemptId||s.permit.inputSha256!==wanted.inputSha256)||prior&&(prior.attemptId!==wanted.attemptId||prior.inputSha256!==wanted.inputSha256))fail('close-identity-conflict');
      await tx.put('closed',wanted);if(s){s.status='closed';await tx.put('state',s)}return wanted;
    });
    const s=await this.status(),pendingUnknown=s?.operations.some(o=>o.state==='intent'||o.state==='unknown')??false;
    return {confirmed:!pendingUnknown,closed:true,inputSha256:closed.inputSha256,completedRequests:s?.operations.filter(o=>o.state==='completed').length??0,pendingUnknown,status:s};
  }
  private async archive(value:unknown):Promise<Ref>{const bytes=enc.encode(brokerCanonical(value));if(bytes.length>2*1024*1024)fail('private-archive-byte-limit');const sha256=await brokerHash(bytes),key=`coding-model-private/${sha256}.json`;await this.deps.archive.put(key,bytes);const actual=await this.deps.archive.get(key);if(!actual||actual.length!==bytes.length||await brokerHash(actual)!==sha256)fail('private-archive-readback-failed');return {key,sha256,bytes:bytes.length}}
  private async read(ref:Ref):Promise<any>{const bytes=await this.deps.archive.get(ref.key);if(!bytes||bytes.length!==ref.bytes||await brokerHash(bytes)!==ref.sha256)fail('private-continuation-integrity-failed');return JSON.parse(new TextDecoder().decode(bytes))}
  async invoke(raw:unknown):Promise<BrokerCompleted|BrokerDenied>{
    const initial=await this.deps.store.transaction(tx=>tx.get<State>('state'));if(!initial)return denied('refused','permit-not-open');
    let turn:BrokerTurn;try{turn=parseTurn(raw,initial.permit)}catch(e){return denied('refused',e instanceof BrokerError?e.reason:'invalid-turn')}
    const bodySha256=await brokerHash(brokerCanonical(turn.body));
    const requestId=`coding:${initial.permitSha256}:${turn.ordinal}`;
    const claim=await this.deps.store.transaction(async tx=>{
      const s=await tx.get<State>('state');if(!s)fail('permit-not-open');const at=this.now();
      const prior=s.operations.find(o=>o.ordinal===turn.ordinal);
      if(prior)return {denial:denied(prior.state,prior.bodySha256===bodySha256&&prior.sessionId===turn.sessionId?'ordinal-already-consumed':'ordinal-identity-conflict',prior)};
      if(s.status!=='open'||s.activeOrdinal!==null||at<s.lastAtMs||at>=s.permit.expiresAtMs||s.policySha256!==this.deps.provider.policySha256||s.credentialGenerationSha256!==this.deps.provider.credentialGenerationSha256)return {denial:denied('refused','permit-not-admitting')};
      if(turn.ordinal!==s.nextOrdinal||turn.ordinal>s.permit.maxRequests)return {denial:denied('refused','ordinal-out-of-sequence')};
      const op:Operation={ordinal:turn.ordinal,sessionId:turn.sessionId,bodySha256,requestId,state:'intent',reason:null,archive:null,receiptSha256:null};
      s.operations.push(op);s.nextOrdinal++;s.activeOrdinal=turn.ordinal;s.lastAtMs=at;await tx.put('state',s);return {state:s,op};
    });
    if('denial'in claim)return claim.denial!;
    const {state,op}=claim as {state:State;op:Operation};const abort=new AbortController();const deadline=Math.min(state.permit.expiresAtMs,this.now()+120000);let timer:ReturnType<typeof setTimeout>|undefined,observedAt=state.lastAtMs;
    const check=()=>{const now=this.now();if(abort.signal.aborted||now<observedAt||now>=deadline)fail('turn-deadline-exceeded');observedAt=now};
    const work=async():Promise<BrokerCompleted|BrokerDenied>=>{
      check();const context=snapshot({system:turn.body.system??null,tools:turn.body.tools??[]},262144) as Json;
      let messages=turn.body.messages;
      const priorRef=state.sessions[turn.sessionId];
      if(priorRef){const prior=(await this.read(priorRef)).transcript as Transcript;check();if(brokerCanonical(prior.context)!==brokerCanonical(context)||turn.body.messages.length!==prior.sanitized.length+1||brokerCanonical(turn.body.messages.slice(0,prior.sanitized.length))!==brokerCanonical(prior.sanitized))fail('session-history-conflict');userContribution(turn.body.messages[prior.sanitized.length],prior.sanitized.at(-1)!.content);messages=[...prior.private,turn.body.messages[prior.sanitized.length]]}
      else {if(turn.body.messages.length!==1)fail('initial-history-forbidden');userContribution(turn.body.messages[0],null)}
      const body={...turn.body,messages};if(enc.encode(brokerCanonical(body)).length>state.permit.maxInputBytes)fail('private-input-byte-limit');
      const readiness=await this.deps.provider.ready(abort.signal);check();
      if(!readiness.allowed){await this.finish(op,'not-dispatched','provider-not-ready',null,null);return denied('not-dispatched','provider-not-ready',op)}
      const admitted=await this.deps.store.transaction(async tx=>{const s=await tx.get<State>('state');return !!s&&s.status==='open'&&s.activeOrdinal===op.ordinal&&s.operations[op.ordinal-1]?.state==='intent'&&this.now()>=s.lastAtMs&&this.now()<deadline});check();
      if(!admitted)fail('dispatch-fenced');
      const result=await this.deps.provider.invoke({requestId,jobId:`coding:${state.permitSha256}`,seatId:'coding',body,signal:abort.signal});check();
      if(result.state!=='completed'){await this.finish(op,result.state,'provider-'+result.state,null,null);return denied(result.state,'provider-'+result.state,op)}
      if(result.model!==CODING_MODEL||result.settlementConfirmed!==true||!hash(result.receiptSha256)||!['end_turn','tool_use'].includes(result.stop_reason))fail('provider-result-unqualified');
      const safe=snapshot(result,1024*1024) as Extract<PrivateProviderResult,{state:'completed'}>;
      const content=cleanContent(safe.content,turn.body.tools);
      if(enc.encode(brokerCanonical({content,usage:safe.usage})).length>120*1024)fail('sanitized-response-byte-limit');
      if((safe.stop_reason==='tool_use')!==content.some(c=>(c as any).type==='tool_use'))fail('provider-stop-content-conflict');
      const transcript:Transcript={context,sanitized:[...turn.body.messages,{role:'assistant',content}],private:[...messages,{role:'assistant',content:safe.content}]};
      const ref=await this.archive({schema:'lupine.coding-model-private.v1',permitSha256:state.permitSha256,ordinal:op.ordinal,bodySha256,requestId,result:safe,transcript});check();
      const committed=await this.finish(op,'completed',null,ref,safe.receiptSha256);check();if(!committed)return denied('unknown','completion-fenced',op);
      return {ok:true,schema:'lupine.coding-model-result.v1',state:'completed',taskId:turn.taskId,attemptId:turn.attemptId,inputSha256:turn.inputSha256,ordinal:turn.ordinal,sessionId:turn.sessionId,bodySha256,requestId,model:CODING_MODEL,content,stop_reason:safe.stop_reason,usage:safe.usage,receiptSha256:safe.receiptSha256,archiveSha256:ref.sha256,settlementConfirmed:true};
    };
    try{return await Promise.race([work(),new Promise<never>((_,reject)=>{timer=setTimeout(()=>{abort.abort();reject(new BrokerError('turn-deadline-exceeded'))},Math.max(1,deadline-this.now()))})])}
    catch{abort.abort();try{await this.finish(op,'unknown','turn-completion-unknown',null,null);await this.deps.store.transaction(async tx=>{const s=await tx.get<State>('state');if(s?.status==='open'){s.status='attention';await tx.put('state',s)}})}catch{/* Original durable intent or completed ordinal still prohibits replay. */}return denied('unknown','turn-completion-unknown',op)}
    finally{if(timer)clearTimeout(timer)}
  }
  private async finish(op:Operation,outcome:Operation['state'],reason:string|null,archive:Ref|null,receiptSha256:string|null):Promise<boolean>{return this.deps.store.transaction(async tx=>{
    const s=await tx.get<State>('state');if(!s)return false;const stored=s.operations.find(o=>o.ordinal===op.ordinal);if(!stored||stored.state!=='intent'||stored.requestId!==op.requestId)return false;
    const at=this.now();const allowed=s.status==='open'&&s.activeOrdinal===op.ordinal&&at>=s.lastAtMs&&at<s.permit.expiresAtMs;
    stored.state=allowed?outcome:'unknown';stored.reason=allowed?reason:'completion-fenced';stored.archive=archive;stored.receiptSha256=receiptSha256;s.activeOrdinal=null;s.lastAtMs=Math.max(at,s.lastAtMs);
    if(stored.state==='completed'&&archive)s.sessions[op.sessionId]=archive;else if(s.status!=='closed')s.status='attention';await tx.put('state',s);return allowed&&stored.state===outcome;
  })}
}
