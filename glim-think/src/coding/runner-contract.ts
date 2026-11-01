/** Operator-authored code execution only. No provider entitlement is implied. */
export const RUNNER_LIMITS = { sourceBytes: 256 * 1024 * 1024, manifestBytes: 24 * 1024,
  commandBytes: 16 * 1024, logBytes: 512 * 1024, artifactBytes: 2 * 1024 * 1024,
  artifactTotalBytes: 8 * 1024 * 1024, artifactCount: 16, commandSeconds: 900, setupSeconds: 240, captureSeconds: 60 } as const;
export type CodingTask = {
  schema: 'lupine.coding-task.v1'; taskId: string; attemptId: string;
  repository: { owner: string; name: string; commit: string };
  source: { artifactKey: string; sha256: string; bytes: number } & ({kind:'git-bundle'}|{kind:'git-shallow-bundle-v1';boundaryCommit:string});
  mode: 'code-execution'; command: string; timeoutSeconds: number; enableInternet: boolean; artifactPaths: string[];
};
export type EvidenceRef = { artifactKey: string; sha256: string; bytes: number; kind: 'stdout'|'stderr'|'artifact'|'bootstrap'|'receipt'|'source-receive-stdout'|'source-receive-stderr'|'source-receive'|'checkout-stdout'|'checkout-stderr'|'checkout'; path?: string };
export type CodingState = {
  schema: 'lupine.coding-attempt.v1'; task: CodingTask; inputSha256: string; ownerId: string;
  status: 'claimed'|'preparing'|'executing'|'collecting'|'finalizing'|'succeeded'|'failed'|'unknown';
  claimedAt: string; deadlineAtMs: number; updatedAt: string; executionStarted: boolean;
  executionExitCode: number|null; reason: string|null; cleanupConfirmed: boolean;
  setupStage?: 'bootstrap'|'source-receive'|'checkout';
  evidence: EvidenceRef[]; receipt: EvidenceRef|null; ledgerRecorded: boolean;
  pendingExec: boolean; cleanupAttempts: number; terminalIntent: {outcome:'succeeded'|'failed'|'unknown';reason:string;receiptJson:string;receiptSha256:string;cleanupConfirmed:boolean}|null;
  environment: { image: string; osRelease: string; versions: string }|null;
};
export class RunnerError extends Error { constructor(public readonly code: number, message: string) { super(message); } }
export function assertRunner(ok: unknown, message: string, code=400): asserts ok { if (!ok) throw new RunnerError(code,message); }
export const canonical = (value: unknown): string => {
  if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  if (value!==null && typeof value==='object') return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical((value as Record<string,unknown>)[k])).join(',')+'}';
  const result=JSON.stringify(value); if(result===undefined) throw new RunnerError(400,'Unsupported canonical value'); return result;
};
export async function sha256(value: Uint8Array|string): Promise<string> {
  const bytes=typeof value==='string'?new TextEncoder().encode(value):value;
  const result=await crypto.subtle.digest('SHA-256',bytes as BufferSource);
  return [...new Uint8Array(result)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export const validId=(v:unknown):v is string=>typeof v==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$/.test(v);
const exact=(v:unknown,keys:string[]):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===[...keys].sort().join(',');
export function parseCodingTask(raw:unknown):CodingTask {
  assertRunner(exact(raw,['schema','taskId','attemptId','repository','source','mode','command','timeoutSeconds','enableInternet','artifactPaths']),'Invalid coding task fields');
  assertRunner(raw.schema==='lupine.coding-task.v1'&&validId(raw.taskId)&&validId(raw.attemptId),'Invalid coding identity');
  assertRunner(raw.mode==='code-execution','DSH/model execution is unqualified; use code-execution mode');
  assertRunner(exact(raw.repository,['owner','name','commit'])&&typeof raw.repository.owner==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$/.test(raw.repository.owner)&&typeof raw.repository.name==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$/.test(raw.repository.name)&&typeof raw.repository.commit==='string'&&/^[0-9a-f]{40}$/.test(raw.repository.commit),'Invalid pinned repository');
  const source=raw.source;
  const ordinary=exact(source,['kind','artifactKey','sha256','bytes'])&&source.kind==='git-bundle';
  const shallow=exact(source,['kind','artifactKey','sha256','bytes','boundaryCommit'])&&source.kind==='git-shallow-bundle-v1'&&source.boundaryCommit===raw.repository.commit;
  assertRunner((ordinary||shallow)&&typeof source.sha256==='string'&&/^[0-9a-f]{64}$/.test(source.sha256)&&source.artifactKey===`sources/${source.sha256}.bundle`&&Number.isSafeInteger(source.bytes)&&Number(source.bytes)>0&&Number(source.bytes)<=RUNNER_LIMITS.sourceBytes,'Invalid pinned source bundle');
  assertRunner(typeof raw.command==='string'&&raw.command.trim().length>0&&!raw.command.includes('\0')&&new TextEncoder().encode(raw.command).length<=RUNNER_LIMITS.commandBytes,'Invalid bounded command');
  assertRunner(Number.isSafeInteger(raw.timeoutSeconds)&&Number(raw.timeoutSeconds)>=1&&Number(raw.timeoutSeconds)<=RUNNER_LIMITS.commandSeconds&&typeof raw.enableInternet==='boolean','Invalid deadline/network policy');
  assertRunner(Array.isArray(raw.artifactPaths)&&raw.artifactPaths.length<=RUNNER_LIMITS.artifactCount&&new Set(raw.artifactPaths).size===raw.artifactPaths.length,'Invalid artifact list');
  for(const path of raw.artifactPaths) assertRunner(typeof path==='string'&&path.length<=240&&/^[a-zA-Z0-9_.\/-]+$/.test(path)&&!path.startsWith('/')&&path.split('/').every(p=>p!=='.'&&p!=='..'&&p.length>0)&&!path.startsWith('.git/'),'Invalid relative artifact path');
  return structuredClone(raw) as CodingTask;
}
export function publicCodingState(s:CodingState|null) {
  if(!s)return null;
  return {schema:s.schema,taskId:s.task.taskId,attemptId:s.task.attemptId,inputSha256:s.inputSha256,repository:s.task.repository,source:s.task.source,
    mode:s.task.mode,providerMode:'unqualified-no-provider-credentials',status:s.status,claimedAt:s.claimedAt,updatedAt:s.updatedAt,deadlineAtMs:s.deadlineAtMs,
    timeoutSeconds:s.task.timeoutSeconds,enableInternet:s.task.enableInternet,executionStarted:s.executionStarted,executionExitCode:s.executionExitCode,
    reason:s.reason,setupStage:s.setupStage??null,pendingExec:s.pendingExec,cleanupAttempts:s.cleanupAttempts,terminalReconciliationPending:!!s.terminalIntent&&!s.ledgerRecorded,cleanupConfirmed:s.cleanupConfirmed,evidence:s.evidence,receipt:s.receipt,ledgerRecorded:s.ledgerRecorded,environment:s.environment,
    acceptance:'separate-review-required',automaticReplay:false};
}
