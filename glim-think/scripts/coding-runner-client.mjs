#!/usr/bin/env node
// Operator-only client. The credential is never part of a task or guest env.
import { readFile, writeFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';

const [action, input, output] = process.argv.slice(2);
const scheduledActions=['configure','enqueue','tick','stop','reconcile'];
const schedulerAction=action?.startsWith('schedule-')?action.slice(9):null;
if (!['submit', 'status', 'schedule-status', ...scheduledActions.map(x=>'schedule-'+x)].includes(action) || !input || !output) {
  console.error('Usage: coding-runner-client.mjs submit manifest.json receipt.json | status attempt-id receipt.json | schedule-status - receipt.json | schedule-{configure,enqueue,tick,stop,reconcile} request.json receipt.json');
  process.exit(2);
}
try {
  const origin = new URL(process.env.LUPINE_CODING_ORIGIN ?? '');
  if (origin.protocol !== 'https:' || origin.username || origin.password || origin.search || origin.hash || origin.pathname !== '/') {
    throw new Error('LUPINE_CODING_ORIGIN must be an HTTPS origin without credentials, path, query or fragment');
  }
  const tokenPath = process.env.LUPINE_CODING_TOKEN_FILE;
  if (!tokenPath) throw new Error('Set LUPINE_CODING_TOKEN_FILE to the private operator credential file');
  const tokenStat = await stat(tokenPath);
  if ((tokenStat.mode & 0o077) !== 0) throw new Error('Operator credential file must not be group/world accessible');
  const token = (await readFile(tokenPath, 'utf8')).trim();
  if (!/^[A-Za-z0-9_-]{43,128}$/.test(token)) throw new Error('Invalid operator credential format');
  const headers = new Headers({ Authorization: `Bearer ${token}`, Accept: 'application/json' });
  let body;
  let path;
  if (action === 'submit' || scheduledActions.includes(schedulerAction)) {
    body = await readFile(input, 'utf8');
    if (Buffer.byteLength(body) > (schedulerAction?32768:65536)) throw new Error('Request exceeds its byte bound');
    JSON.parse(body);
    path = schedulerAction?'/coding/scheduler/'+schedulerAction:'/coding/tasks';
    headers.set('Content-Type', 'application/json');
  } else if(action==='schedule-status') {
    if(input!=='-')throw new Error('Schedule status takes - as its input');
    path='/coding/scheduler';
  } else {
    if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$/.test(input)) throw new Error('Invalid attempt id');
    path = `/coding/tasks/${encodeURIComponent(input)}`;
  }
  const response = await fetch(new URL(path, origin), {
    method: body!==undefined ? 'POST' : 'GET', headers, body,
    redirect: 'manual', signal: AbortSignal.timeout(30000),
  });
  const reader = response.body?.getReader();
  const chunks = [];
  let bytes = 0;
  if (reader) while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    bytes += chunk.value.byteLength;
    if (bytes > 1024 * 1024) {
      await reader.cancel();
      throw new Error('Response exceeds 1 MiB');
    }
    chunks.push(Buffer.from(chunk.value));
  }
  const text = Buffer.concat(chunks).toString('utf8');
  let result;
  try { result = JSON.parse(text); } catch { result = { nonJsonResponse: true }; }
  const receipt = { observedAt: new Date().toISOString(), origin: origin.origin, action,
    httpStatus: response.status, responseBytes: bytes, result };
  // Exclusive output prevents an observation from replacing an earlier receipt.
  await writeFile(resolve(output), JSON.stringify(receipt, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  console.log(JSON.stringify({ httpStatus: response.status, receipt: resolve(output) }));
  if (!response.ok) process.exitCode = 1;
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Operator request failed');
  // A transport timeout is unknown, never a reason to invent another attempt.
  process.exitCode = 1;
}
