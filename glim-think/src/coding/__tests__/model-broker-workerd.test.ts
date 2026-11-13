import {it,expect} from 'vitest';
import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {resolve} from 'node:path';
it('actual workerd fetch preserves exact request and rejects redirects with only local outbound fixtures',async()=>{
 const result=await build({stdin:{contents:`import {workerMiniMaxFetch} from './integrations/research-coding-broker/worker-fetch'; export default {async fetch(req){const ac=new AbortController();try{const r=await workerMiniMaxFetch(ac.signal)('https://api.minimax.io/anthropic/v1/messages',{method:'POST',body:'fixture-only',headers:{'x-fixture':'no-credential'},redirect:'error',timeout:false});return new Response(await r.text(),{status:r.status})}catch(e){return new Response(e.message,{status:409})}}}`,resolveDir:resolve('.')},bundle:true,write:false,format:'esm',platform:'browser',target:'es2022'});
 // Retained local workerd supports through 2026-05-01; deployment-date compatibility remains separate.
 let requests=0,redirect=false;
 const mf=new Miniflare({modules:true,script:result.outputFiles[0].text,compatibilityDate:'2026-05-01',compatibilityFlags:['nodejs_compat'],outboundService:async req=>{requests++;expect(req.url).toBe('https://api.minimax.io/anthropic/v1/messages');expect(await req.text()).toBe('fixture-only');expect(req.headers.get('authorization')).toBeNull();return redirect?new Response('',{status:302,headers:{location:'https://never-follow.invalid/'}}):new Response('{"fixture":true}')}});
 try{const normal=await mf.dispatchFetch('https://broker.test');expect(normal.status).toBe(200);expect(await normal.json()).toEqual({fixture:true});redirect=true;const blocked=await mf.dispatchFetch('https://broker.test');expect(blocked.status).toBe(409);expect(await blocked.text()).toBe('broker-redirect-denied');expect(requests).toBe(2)}finally{await mf.dispose()}
},20000);
