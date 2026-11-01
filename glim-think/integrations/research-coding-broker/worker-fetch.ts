/** Exact included-subscription transport surface. No redirect, count, generic
 * API or alternate origin is exposed by this Worker-specific shim. */
const QUOTA='https://api.minimax.io/v1/token_plan/remains';
const MESSAGES='https://api.minimax.io/anthropic/v1/messages';
export function workerMiniMaxFetch(outer:AbortSignal,base:typeof fetch=fetch):typeof fetch {
 return (async(input:RequestInfo|URL,init?:RequestInit)=>{
  const url=typeof input==='string'?input:input instanceof URL?input.href:input.url;
  const method=(init?.method??(input instanceof Request?input.method:'GET')).toUpperCase();
  if(!((url===QUOTA&&method==='GET')||(url===MESSAGES&&method==='POST')))throw Error('broker-endpoint-denied');
  if(outer.aborted)throw Error('broker-aborted');
  const clean={...init} as RequestInit&{timeout?:unknown};delete clean.timeout;
  clean.redirect='manual';clean.signal=init?.signal?AbortSignal.any([outer,init.signal]):outer;
  const response=await base(input,clean);
  if(response.status>=300&&response.status<400){void response.body?.cancel().catch(()=>{});throw Error('broker-redirect-denied')}
  return response;
 }) as typeof fetch;
}
