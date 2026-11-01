import test from 'node:test';
import assert from 'node:assert/strict';
import { createBrokerTransport, createHarnessAdapter, parseConfig, convertHarnessRequest, snapshot,
  canonical, bodyDigest, requestShape, MODEL, PROVIDER } from './transport.mjs';

const now = 1900000000000;
const config = () => ({ endpoint: 'https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/attempt-01/model',
  capability: 'x'.repeat(48), taskId: 'coding-task', attemptId: 'attempt-01', inputSha256: 'a'.repeat(64),
  maxRequests: 16, deadlineAtMs: now + 600000, model: MODEL, maxOutputTokens: 4096 });
const text = text => ({ type: 'text', text });
const user = textValue => ({ id: 'user-1', role: 'user', source: { kind: 'user' }, content: [text(textValue)] });
const tool = { name: 'read', description: 'Read one repository path', parameters: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'], additionalProperties: false } };
const request = () => structuredClone({ provider: PROVIDER, model: MODEL, maxTokens: 1000, sessionId: 'worker-01',
  messages: [{ id: 'system-1', role: 'system', source: { kind: 'system-prompt' }, content: [text('Inspect the pinned source.')] }, user('Read README.md')],
  tools: [tool], toolHistory: { tools: [tool], updates: [] } });
const completed = (q, changes = {}) => ({ schema: 'lupine.coding-model-result.v1', ok: true, state: 'completed',
  taskId: q.taskId, attemptId: q.attemptId, inputSha256: q.inputSha256, ordinal: q.ordinal, sessionId: q.sessionId,
  bodySha256: bodyDigest(q.body), requestId: `coding:attempt-01:${q.ordinal}`, model: MODEL,
  content: [text('The source is available.')], stop_reason: 'end_turn',
  usage: { input_tokens: 17, output_tokens: 6, cache_creation_input_tokens: null, cache_read_input_tokens: 11 },
  receiptSha256: 'b'.repeat(64), archiveSha256: 'c'.repeat(64), settlementConfirmed: true, ...changes });
const response = value => new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
const collect = async stream => { const events = []; for await (const e of stream) events.push(e); return events; };
const fixture = mutate => {
  const calls = []; const transport = createBrokerTransport(config(), { now: () => now, fetch: async (url, init) => {
    const q = JSON.parse(init.body); calls.push({ url, init, q }); return response(mutate ? mutate(completed(q), q) : completed(q));
  } }); return { calls, transport };
};

test('exact scoped configuration; canonical hash is key-order independent', () => {
  assert.equal(parseConfig(JSON.stringify(config()), now).model, MODEL);
  assert.equal(bodyDigest({ b: 2, a: { d: 4, c: 3 } }), bodyDigest({ a: { c: 3, d: 4 }, b: 2 }));
  for (const change of [{ endpoint: 'https://evil.invalid/model' }, { deadlineAtMs: now }, { deadlineAtMs: now + 900001 },
    { maxRequests: 17 }, { maxOutputTokens: 4097 }, { model: 'other' }, { capability: 'short' }, { providerKey: 'forbidden' }])
    assert.throws(() => parseConfig(JSON.stringify({ ...config(), ...change }), now));
});
test('snapshot never evaluates accessors and refuses non-JSON shape', () => {
  let accessed = 0; const value = { get secret() { accessed++; return 'x'; } };
  assert.throws(() => snapshot(value)); assert.equal(accessed, 0);
  for (const v of [undefined, NaN, -0, new Date(), [1, , 3]]) assert.throws(() => snapshot(v));
});
test('first preflight diagnostic is fixed-code structural metadata and is immutable across repeats', async () => {
  const f=fixture(),q=request();q.tools=Array.from({length:21},(_,i)=>({...tool,name:'tool'+i}));
  q.messages[1].content[0].text='PRIVATE_PROMPT_SENTINEL';
  q.PRIVATE_UNKNOWN_KEY='SECRET_VALUE';
  await assert.rejects(collect(f.transport.stream(q)),/Too many tools/);
  const first=f.transport.status().firstFailure;
  assert.equal(first.code,'DSH_TOOL_COUNT_EXCEEDED');assert.equal(first.shape.toolCount,21);
  assert.equal(first.admittedRequests,0);assert.equal(first.shape.unknownFieldCount,1);
  assert(!JSON.stringify(first).includes('PRIVATE'));assert(!JSON.stringify(first).includes('SECRET'));
  first.code='tampered';assert.equal(f.transport.status().firstFailure.code,'DSH_TOOL_COUNT_EXCEEDED');
  await assert.rejects(collect(f.transport.stream(request())));
  assert.equal(f.transport.status().firstFailure.code,'DSH_TOOL_COUNT_EXCEEDED');assert.equal(f.calls.length,0);
});
test('request shape does not evaluate accessors or export arbitrary key/role strings', () => {
  let accesses=0;const q={get tools(){accesses++;throw Error('private')},PRIVATE_KEY:'private',
    messages:[{role:'PRIVATE_ROLE',content:[text('PRIVATE_PROMPT')]}]};
  const shape=requestShape(q);assert.equal(accesses,0);assert.equal(shape.toolCount,null);
  assert.equal(shape.roles.other,1);assert(!JSON.stringify(shape).includes('PRIVATE'));
});
test('invalid argument JSON diagnostic never retains native parser prompt excerpts', async()=>{
  const f=fixture(),q=request();q.messages.push({id:'a1',role:'assistant',source:{kind:'model',provider:PROVIDER,model:MODEL},
    content:[{type:'tool-call',id:'c1',name:'read',arguments:'PRIVATE_INVALID_JSON'}]});
  await assert.rejects(collect(f.transport.stream(q)));
  const d=f.transport.status().firstFailure;assert.equal(d.code,'DSH_INVALID_JSON');
  assert(!JSON.stringify(d).includes('PRIVATE_INVALID_JSON'));assert.equal(f.calls.length,0);
});
test('projects leading system and native tools without silently changing control', () => {
  const q = request(); const body = convertHarnessRequest(q, config());
  assert.deepEqual(body.system, [text('Inspect the pinned source.')]);
  assert.equal(body.tools[0].input_schema.type, 'object'); assert.equal(body.stream, false);
  assert.equal(body.max_tokens, 1000); assert.equal(body.model, MODEL);
  assert.equal(q.messages.length, 2);
});
test('round trips tool call and ordered parallel results as one Anthropic user message', () => {
  const q = request(); q.messages.push({ id: 'assistant-1', role: 'assistant', source: { kind: 'model', provider: PROVIDER, model: MODEL },
    content: [{ type: 'tool-call', id: 'call-1', name: 'read', arguments: '{"path":"README.md"}' },
      { type: 'tool-call', id: 'call-2', name: 'read', arguments: '{"path":"AGENTS.md"}' }] },
  { id: 'result-1', role: 'tool', toolCallId: 'call-1', source: { kind: 'tool', callId: 'call-1' }, content: [text('readme')] },
  { id: 'result-2', role: 'tool', toolCallId: 'call-2', source: { kind: 'tool', callId: 'call-2' }, isError: true, content: [text('missing')] });
  const body = convertHarnessRequest(q, config()); assert.equal(body.messages.length, 3);
  assert.equal(body.messages[2].content.length, 2); assert.equal(body.messages[2].content[1].is_error, true);
  const bad = structuredClone(q); bad.messages[3].source.callId = 'wrong'; assert.throws(() => convertHarnessRequest(bad, config()));
  const duplicate = structuredClone(q); duplicate.messages[4].toolCallId = 'call-1'; assert.throws(() => convertHarnessRequest(duplicate, config()));
  const missing = structuredClone(q); missing.messages.pop(); assert.throws(() => convertHarnessRequest(missing, config()));
});
for (const [name, mutate] of [
  ['reasoning', q => q.messages[1].content.push({ type: 'reasoning', text: 'private' })],
  ['image', q => q.messages[1].content.push({ type: 'image', attachment: {} })],
  ['developer', q => { q.messages[1].role = 'developer'; }],
  ['late system', q => q.messages.push(q.messages[0])],
  ['tool history update', q => q.toolHistory.updates.push({ messageId: 'x', additions: [] })],
  ['sampling control', q => { q.temperature = 0.2; }],
  ['provider switching', q => { q.provider = 'other'; }],
  ['output enlargement', q => { q.maxTokens = 5000; }],
  ['deferred tool', q => { q.tools[0] = { ...tool, deferLoading: true }; }],
  ['oversized prompt', q => { q.messages[1].content[0].text = 'x'.repeat(256 * 1024); }],
  ['oversized session ID', q => { q.sessionId = 'x'.repeat(129); }],
  ['reserved schema field', q => { q.tools[0].parameters.properties.constructor = { type: 'string' }; }],
]) test(`rejects unsupported ${name} before HTTP`, async () => {
  const f = fixture(); const q = request(); mutate(q); await assert.rejects(collect(f.transport.stream(q))); assert.equal(f.calls.length, 0);
  assert.equal(f.transport.status().stopped, true); await assert.rejects(collect(f.transport.stream(request()))); assert.equal(f.calls.length, 0);
});
test('releases only settled complete output, preserves missing usage and excludes capability from records', async () => {
  const f = fixture(); const chunks = await collect(f.transport.stream(request()));
  assert.equal(f.calls.length, 1); assert.equal(f.calls[0].init.redirect, 'manual');
  assert.equal(f.calls[0].init.headers.authorization, `Bearer ${config().capability}`);
  assert.deepEqual(chunks.find(v => v.type === 'usage').usage, { inputTokens: 17, outputTokens: 6, cacheReadTokens: 11 });
  assert.equal(chunks.at(-1).reason.kind, 'stop');
  const records = f.transport.records(); assert.equal(records[0].deliveredToHarness, true);
  assert.equal(records[0].usage.cache_creation_input_tokens, null); assert(!JSON.stringify(records).includes(config().capability));
  records[0].status = 'tampered'; assert.equal(f.transport.records()[0].status, 'completed');
});
test('tool output produces the exact Harness block sequence and canonical argument string', async () => {
  const f = fixture(r => ({ ...r, content: [{ type: 'tool_use', id: 'tool-1', name: 'read', input: { path: 'README.md' } }], stop_reason: 'tool_use' }));
  const chunks = await collect(f.transport.stream(request()));
  assert.deepEqual(chunks.map(v => v.type), ['block-start','tool-call-delta','block-end','usage','finish']);
  assert.equal(chunks[1].argumentsDelta, '{"path":"README.md"}'); assert.equal(chunks.at(-1).reason.kind, 'tool-calls');
});
for (const [name, mutate] of [
  ['wrong attempt', r => ({ ...r, attemptId: 'other' })],
  ['wrong request hash', r => ({ ...r, bodySha256: 'd'.repeat(64) })],
  ['wrong model', r => ({ ...r, model: 'other' })],
  ['unsettled receipt', r => ({ ...r, settlementConfirmed: false })],
  ['archive absent', r => ({ ...r, archiveSha256: null })],
  ['reasoning leak', r => ({ ...r, content: [{ type: 'thinking', thinking: 'private' }] })],
  ['unknown response field', r => ({ ...r, rawResponse: 'private' })],
  ['missing usage', r => ({ ...r, usage: { ...r.usage, input_tokens: null } })],
  ['missing cache field', r => { const out = structuredClone(r); delete out.usage.cache_read_input_tokens; return out; }],
  ['unknown tool', r => ({ ...r, content: [{ type: 'tool_use', id: 'bad', name: 'external_network', input: {} }], stop_reason: 'tool_use' })],
  ['incomplete tool output', r => ({ ...r, content: [{ type: 'tool_use', id: 'bad', name: 'read', input: {} }], stop_reason: 'max_tokens' })],
  ['refusal', r => ({ ...r, stop_reason: 'refusal' })],
  ['scoped capability in result', r => ({ ...r, content: [text(config().capability)] })],
]) test(`withholds ${name}, emits no partial result, and does not replay`, async () => {
  const f = fixture(mutate), chunks = [];
  await assert.rejects(async () => { for await (const c of f.transport.stream(request())) chunks.push(c); });
  assert.equal(chunks.length, 0); assert.equal(f.calls.length, 1);
  await assert.rejects(collect(f.transport.stream(request()))); assert.equal(f.calls.length, 1);
  assert.equal(f.transport.records()[0].status, 'unknown');
});
test('absolute deadline and call ceiling do not reset between sessions', async () => {
  let calls = 0; const c = { ...config(), maxRequests: 2 };
  const t = createBrokerTransport(c, { now: () => now, fetch: async (_u, init) => { calls++; return response(completed(JSON.parse(init.body))); } });
  await collect(t.stream(request())); await collect(t.stream({ ...request(), sessionId: 'worker-02' }));
  await assert.rejects(collect(t.stream({ ...request(), sessionId: 'worker-03' }))); assert.equal(calls, 2);
});
test('distinct concurrent sessions serialize without replay or mutation after queue admission', async () => {
  let release, calls = 0; const seen = [];
  const t = createBrokerTransport(config(), { now: () => now, fetch: async (_url, init) => {
    calls++; seen.push(JSON.parse(init.body)); if (calls === 1) await new Promise(r => { release = r; }); return response(completed(JSON.parse(init.body)));
  } });
  const first = collect(t.stream(request())); await Promise.resolve();
  const secondInput = { ...request(), sessionId: 'other' }; const second = collect(t.stream(secondInput));
  secondInput.messages[1].content[0].text = 'changed after admission';
  assert.equal(calls, 1); release(); await Promise.all([first, second]); assert.equal(calls, 2);
  assert.equal(seen[1].body.messages[0].content[0].text, 'Read README.md'); assert.equal(seen[1].ordinal, 2);
});
test('unknown HTTP outcome is unreplayable even when a later call would succeed', async () => {
  let calls = 0; const t = createBrokerTransport(config(), { now: () => now, fetch: async () => { calls++; throw Error('unknown network outcome'); } });
  await assert.rejects(collect(t.stream(request()))); await assert.rejects(collect(t.stream(request())));
  assert.equal(calls, 1); assert.equal(t.records()[0].status, 'unknown');
});
test('redirect and oversized response are withheld', async () => {
  for (const returned of [new Response('', { status: 302 }), new Response('{}', { headers: { 'content-type': 'application/json', 'content-length': String(128 * 1024 + 1) } })]) {
    const t = createBrokerTransport(config(), { now: () => now, fetch: async () => returned });
    await assert.rejects(collect(t.stream(request())));
  }
});
test('late response, caller abort and abandoned output cannot authorize another turn', async () => {
  let clock = now; const t = createBrokerTransport(config(), { now: () => clock, fetch: async (_u, init) => { clock += 600001; return response(completed(JSON.parse(init.body))); } });
  await assert.rejects(collect(t.stream(request())));
  const f = fixture(); const stream = f.transport.stream(request()); await stream.next(); await stream.return();
  await assert.rejects(collect(f.transport.stream(request()))); assert.equal(f.calls.length, 1);
  const aborted = fixture(), abort = new AbortController(); abort.abort();
  await assert.rejects(collect(aborted.transport.stream({ ...request(), signal: abort.signal }))); assert.equal(aborted.calls.length, 0);
});
test('system/tools cannot drift inside a session and retry policy is explicitly disabled', async () => {
  const f = fixture(); await collect(f.transport.stream(request())); const q = request(); q.messages[0].content[0].text = 'changed';
  await assert.rejects(collect(f.transport.stream(q))); assert.equal(f.calls.length, 1);
  const { adapter } = createHarnessAdapter({ LlmAdapter: class {} }, config(), { now: () => now });
  assert.equal(adapter.providerRetryPolicy().maxRetries, 0); assert.deepEqual(adapter.providerRetryPolicy().retryableCodes, []);
  const info = await adapter.resolveModel(PROVIDER, MODEL); assert.equal(info.defaultMaxTokens, 4096);
  assert.equal(info.systemPromptUpdate, undefined); assert.equal(info.context, undefined);
});
