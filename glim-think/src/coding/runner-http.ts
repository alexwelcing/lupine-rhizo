import { checkAccess } from '../middleware/access';
import type { Env } from '../types';
import type { CodingRunnerEnv } from './runner-worker';
import { RUNNER_LIMITS, RunnerError, assertRunner, parseCodingTask, validId } from './runner-contract';
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
const json=(value:unknown,status=200)=>Response.json(value,{status,headers});
function sameSecret(a:string,b:string){if(a.length!==b.length)return false;let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;}
export async function authorizeCodingRequest(request:Request,env:CodingRunnerEnv):Promise<Response|null>{
  const origin=request.headers.get('Origin');if(origin&&origin!==new URL(request.url).origin)return json({error:'Same-origin operator request required'},403);
  const token=env.RUNNER_OPERATOR_TOKEN,authorization=request.headers.get('Authorization');
  if(token&&token.length>=32&&authorization?.startsWith('Bearer ')&&sameSecret(token,authorization.slice(7)))return null;
  if(!env.CF_ACCESS_TEAM_DOMAIN||!env.CF_ACCESS_AUD||!env.ADMIN_EMAIL?.trim())return json({error:'Verified operator authentication required'},403);
  // Deliberately omit DEV_MODE and every legacy service token: only genuine Access is accepted here.
  const denial=await checkAccess(request,{CF_ACCESS_TEAM_DOMAIN:env.CF_ACCESS_TEAM_DOMAIN,CF_ACCESS_AUD:env.CF_ACCESS_AUD} as Env,[env.ADMIN_EMAIL]);
  if(denial)return json({error:'Verified operator authentication required'},403);
  try {const token=request.headers.get('Cf-Access-Jwt-Assertion')!;const part=token.split('.')[1];const payload=JSON.parse(atob(part.replace(/-/g,'+').replace(/_/g,'/')));
    if(!Number.isSafeInteger(payload.exp)||payload.exp<=Date.now()/1000||payload.iss!==`https://${env.CF_ACCESS_TEAM_DOMAIN}.cloudflareaccess.com`)throw Error();
  }catch{return json({error:'Verified operator authentication required'},403);}
  return null;
}
async function boundedJson(request:Request):Promise<unknown>{
  assertRunner(request.headers.get('Content-Type')?.split(';')[0].trim()==='application/json','Use application/json',415);
  assertRunner(!request.headers.has('Content-Encoding')&&request.body,'A bounded uncompressed JSON body is required');
  const reader=request.body.getReader();let count=0;const chunks:Uint8Array[]=[];
  try{for(;;){const next=await reader.read();if(next.done)break;count+=next.value.length;assertRunner(count<=RUNNER_LIMITS.manifestBytes,'Coding manifest too large',413);chunks.push(next.value);}}
  catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
  const bytes=new Uint8Array(count);let offset=0;for(const b of chunks){bytes.set(b,offset);offset+=b.length;}
  try{return JSON.parse(new TextDecoder('utf-8',{fatal:true,ignoreBOM:false}).decode(bytes));}catch{throw new RunnerError(400,'Invalid coding JSON');}
}
export async function codingFetch(request:Request,env:CodingRunnerEnv):Promise<Response>{
    try{
      const denial=await authorizeCodingRequest(request,env);if(denial)return denial;
      const path=new URL(request.url).pathname;
      if(path==='/coding/capabilities'&&request.method==='GET')return json({schema:'lupine.coding-runner-capabilities.v1',mode:'code-execution',image:'cloudflare/debian-trixie',imageDigestPinned:false,modelExecution:'unqualified',providerCredentialsSupplied:false,metadataDoesNotStartContainer:true,automaticReplay:false,limits:RUNNER_LIMITS});
      if(path==='/coding/tasks'&&request.method==='POST'){
        const task=parseCodingTask(await boundedJson(request));const result=await env.CODING_RUNNER.getByName(task.attemptId).submit(task);
        return json(result,result.created?202:200);
      }
      const reconciliation=/^\/coding\/tasks\/([^/]+)\/reconcile$/.exec(path);
      if(reconciliation&&request.method==='POST'&&validId(reconciliation[1]))return json({attempt:await env.CODING_RUNNER.getByName(reconciliation[1]).reconcile()});
      const match=/^\/coding\/tasks\/([^/]+)(?:\/evidence\/([0-9a-f]{64}))?$/.exec(path);
      if(match&&request.method==='GET'&&validId(match[1])){
        const stub=env.CODING_RUNNER.getByName(match[1]);if(match[2])return stub.evidence(match[2]);
        const state=await stub.status();return state?json({attempt:state}):json({error:'Attempt not found'},404);
      }
      return json({error:'Coding route not found'},404);
    }catch(error){return error instanceof RunnerError?json({error:error.message},error.code):json({error:'Coding runner operation unavailable; inspect the existing attempt before any new action'},503);}
}
