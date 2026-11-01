// Two fixed local artifacts. This validates structure/provenance pointers, not
// scientific truth or source-reading causality; independent review is required.
import {readFileSync,writeFileSync,lstatSync,realpathSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {snapshot} from './transport.mjs';
export const DOMAIN_IDS=Object.freeze(['orchestration','discovery-knowledge','library-provenance','scientific-compute','formal-evidence','build-deploy','evaluation-measurement','researcher-experience']);
export const DOMAIN_LABELS=Object.freeze({'orchestration':'Durable agent orchestration','discovery-knowledge':'Discovery and knowledge graph','library-provenance':'Library publication and provenance','scientific-compute':'Scientific and numerical computation','formal-evidence':'Formal proofs and evidence gates','build-deploy':'Build, dependencies and deployment','evaluation-measurement':'Evaluation and operational measurement','researcher-experience':'Researcher experience and taxonomy'});
const string={type:'string'};
const array=item=>({type:'array',items:item});
const object=(properties,required=Object.keys(properties))=>({type:'object',properties,required,additionalProperties:false});
export const ASSESSMENT_SCHEMA=object({targetRevision:string,status:{enum:['complete-source-review','incomplete']},summary:string,
  inspectedPaths:array(string),domains:array(object({id:{enum:DOMAIN_IDS},status:{enum:['source-observed','uninspected']},finding:string,paths:array(string),limitation:string})),
  priorities:array(object({title:string,evidencePaths:array(string),proposal:string,failureTest:string,recoveryTest:string})),exclusions:array(string),limitations:array(string)});
const sha=x=>createHash('sha256').update(x).digest('hex');
function text(x,max=2400){assert(typeof x==='string'&&x.trim().length>0&&x.length<=max,'Assessment text missing or too long');return x}
function keys(x,n){assert(x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length===n.length&&Object.keys(x).every(k=>n.includes(k)),'Unexpected assessment fields')}
function paths(xs){assert(Array.isArray(xs)&&xs.length<=64,'Too many source paths');for(const p of xs)assert(typeof p==='string'&&p.length<=240&&/^[A-Za-z0-9_.\-/]+$/.test(p)&&!p.startsWith('/')&&!p.split('/').some(x=>x==='..'||x===''||x==='.'),'Invalid source path');assert(new Set(xs).size===xs.length,'Duplicate source path');return xs}
export function validateAssessment(input,{revision,pathExists}) {
  const v=snapshot(input);assert(Buffer.byteLength(JSON.stringify(v))<=65536,'Assessment exceeds 64 KiB');
  keys(v,['targetRevision','status','summary','inspectedPaths','domains','priorities','exclusions','limitations']);
  assert(v.targetRevision===revision,'Wrong assessment revision');assert(['complete-source-review','incomplete'].includes(v.status));text(v.summary);
  paths(v.inspectedPaths);const observed=new Set(v.inspectedPaths);for(const p of observed)assert(pathExists(p),'Source path absent from pinned commit');
  assert(Array.isArray(v.domains)&&v.domains.length===8,'Exactly eight domain entries required');const ids=new Set();
  for(const d of v.domains){keys(d,['id','status','finding','paths','limitation']);assert(DOMAIN_IDS.includes(d.id)&&!ids.has(d.id),'Unknown or duplicate domain');ids.add(d.id);assert(['source-observed','uninspected'].includes(d.status));text(d.finding);text(d.limitation);paths(d.paths);assert(d.paths.every(p=>observed.has(p)),'Domain path missing from inspectedPaths');if(d.status==='source-observed')assert(d.paths.length>0,'Observed domain requires a source path');else assert(d.paths.length===0,'Uninspected domain cannot claim a read path')}
  if(v.status==='complete-source-review')assert(v.domains.every(d=>d.status==='source-observed'),'Incomplete coverage cannot be ready');
  assert(Array.isArray(v.priorities)&&v.priorities.length===3,'Exactly three priorities required');
  for(const p of v.priorities){keys(p,['title','evidencePaths','proposal','failureTest','recoveryTest']);text(p.title,300);text(p.proposal);text(p.failureTest);text(p.recoveryTest);paths(p.evidencePaths);assert(p.evidencePaths.length>0&&p.evidencePaths.every(p=>observed.has(p)),'Priority needs inspected evidence paths')}
  for(const field of ['exclusions','limitations']){assert(Array.isArray(v[field])&&v[field].length>0&&v[field].length<=16);v[field].forEach(s=>text(s,1200))}
  const wire=JSON.stringify(v);assert(wire.split(/\s+/).length<=1600,'Keep the complete structured assessment concise');
  return v;
}
export function renderAssessment(v){
  const out=['# Repository assessment at '+v.targetRevision,'',v.summary,'','Status: '+v.status+'. This is a source review, pending independent review; it is not scientific acceptance or publication approval.',''];
  for(const d of v.domains)out.push('## '+DOMAIN_LABELS[d.id],'',d.finding,'','Source paths: '+(d.paths.join(', ')||'Not inspected')+'. Status: '+d.status+'.','', 'Limitation: '+d.limitation,'');
  out.push('## Priorities','');for(const p of v.priorities)out.push('### '+p.title,'',p.proposal,'','Evidence: '+p.evidencePaths.join(', '),'','Failure test: '+p.failureTest,'','Recovery test: '+p.recoveryTest,'');
  out.push('## Exclusions','',...v.exclusions.map(s=>'- '+s),'','## Limitations','',...v.limitations.map(s=>'- '+s),'');
  const md=out.join('\n');assert(Buffer.byteLength(md)<=65536&&md.split(/\s+/).length<=2000,'Rendered assessment exceeds bounds');return md;
}
export function createAssessmentWriter({root,output,revision,forbiddenText,deadlineAtMs,now=Date.now,pathExists}) {
  const directoryIdentity=realpathSync(output);
  const directoryValid=()=>{try{const s=lstatSync(output);return s.isDirectory()&&!s.isSymbolicLink()&&realpathSync(output)===directoryIdentity}catch{return false}};
  assert(directoryValid(),'Assessment directory is not an owned real directory');
  const files={json:path.join(output,'repository-assessment.json'),markdown:path.join(output,'repository-assessment.md')};
  const exists=pathExists??(p=>{const r=spawnSync('git',['cat-file','-t',revision+':'+p],{cwd:root,encoding:'utf8',timeout:1000,maxBuffer:1024,env:{PATH:process.env.PATH,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null'}});return !r.error&&r.status===0&&r.stdout.trim()==='blob'});
  let committed=null,attempted=false;
  function valid(){try{if(!committed||!directoryValid())return false;for(const [k,p]of Object.entries(files)){const s=lstatSync(p);if(!s.isFile()||s.isSymbolicLink()||s.size>65536||sha(readFileSync(p))!==committed.hashes[k])return false;}return true}catch{return false}}
  return {
    write(input){assert(directoryValid(),'Assessment directory identity changed');assert(now()<deadlineAtMs,'Original task deadline reached');const v=validateAssessment(input,{revision,pathExists:exists});const bytes={json:JSON.stringify(v,null,2)+'\n',markdown:renderAssessment(v)};for(const b of Object.values(bytes))assert(!b.includes(forbiddenText),'Scoped capability in assessment');
      if(committed){assert(valid()&&Object.entries(bytes).every(([k,b])=>sha(b)===committed.hashes[k]),'Assessment is immutable once written');return structuredClone(committed)}
      assert(!attempted,'Prior assessment write uncertain; no overwrite');attempted=true;
      for(const [k,p]of Object.entries(files)){assert(now()<deadlineAtMs);writeFileSync(p,bytes[k],{flag:'wx',mode:0o600})}
      committed={schema:'lupine.coding-assessment-commit.v1',status:v.status,hashes:Object.fromEntries(Object.entries(bytes).map(([k,b])=>[k,sha(b)])),bytes:Object.fromEntries(Object.entries(bytes).map(([k,b])=>[k,Buffer.byteLength(b)])),pathExistenceChecked:true,actualReadingIndependentlyProven:false,semanticAcceptance:false,publicationApproval:false};
      assert(valid()&&now()<deadlineAtMs,'Assessment readback/deadline failed');return structuredClone(committed);
    },ready:()=>valid()&&committed.status==='complete-source-review'&&now()<deadlineAtMs,
    status:()=>({attempted,committed:committed?structuredClone(committed):null,readbackValid:valid()})
  };
}
