// A guest-side DSH adapter. Its only credential is a one-attempt broker capability.
// Provider credentials, raw thinking and provider HTTP are owned by the broker.
import { createHash } from 'node:crypto';

export const PROVIDER = 'lupine-minimax-subscription';
export const MODEL = 'MiniMax-M3.1-Flash';
export const LIMITS = Object.freeze({ requests: 16, providerBody: 256 * 1024, request: 300 * 1024,
  response: 128 * 1024, messages: 256, tools: 16, blocks: 128, timeoutMs: 180000 });
const sha = value => createHash('sha256').update(value).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const id = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value)
  && !value.startsWith('sk-') && !['constructor','prototype','__proto__'].includes(value);
const callId = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$/.test(value);
const toolName = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const integer = value => Number.isSafeInteger(value) && value >= 0;
function must(value, message) { if (!value) throw new Error(message); }
function keys(value, allowed, message) { must(object(value) && Object.keys(value).every(k => allowed.includes(k)), message); }

// Reject accessors, exotic objects, sparse arrays and non-JSON values without
// evaluating them. This snapshot is made before any asynchronous transport.
export function snapshot(value, depth = 0, budget = { nodes: 0 }) {
  must(depth <= 48 && ++budget.nodes <= 30000, 'JSON structure exceeds bound');
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return value;
  if (typeof value === 'number') { must(Number.isFinite(value) && !Object.is(value, -0), 'Invalid JSON number'); return value; }
  must(typeof value === 'object', 'Non-JSON value');
  const proto = Object.getPrototypeOf(value);
  must(Array.isArray(value) ? proto === Array.prototype : proto === Object.prototype || proto === null, 'Exotic JSON object');
  const descriptors = Object.getOwnPropertyDescriptors(value);
  must(Reflect.ownKeys(descriptors).every(k => typeof k === 'string'), 'Symbol JSON field');
  if (Array.isArray(value)) {
    must(Object.keys(descriptors).length === value.length + 1, 'Sparse or decorated JSON array');
    return Array.from({ length: value.length }, (_, i) => {
      const d = descriptors[String(i)]; must(d && Object.hasOwn(d, 'value') && d.enumerable, 'JSON array accessor');
      return snapshot(d.value, depth + 1, budget);
    });
  }
  const out = Object.create(null);
  for (const [key, d] of Object.entries(descriptors)) {
    must(!['constructor','prototype','__proto__'].includes(key), 'Unsupported reserved JSON field');
    must(Object.hasOwn(d, 'value') && d.enumerable, 'JSON accessor or hidden field');
    out[key] = snapshot(d.value, depth + 1, budget);
  }
  return out;
}
export function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
}
export const bodyDigest = body => sha(canonical(body));

export function parseConfig(raw, now = Date.now()) {
  must(typeof raw === 'string' && Buffer.byteLength(raw) <= 8192, 'Missing or oversized scoped broker configuration');
  const c = snapshot(JSON.parse(raw));
  keys(c, ['endpoint','capability','taskId','attemptId','inputSha256','maxRequests','deadlineAtMs','model','maxOutputTokens'], 'Unknown broker configuration field');
  must(id(c.taskId) && id(c.attemptId) && hash(c.inputSha256), 'Invalid task identity');
  const expected = `https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/${c.attemptId}/model`;
  must(c.endpoint === expected, 'Only the exact coding runner broker endpoint is allowed');
  must(typeof c.capability === 'string' && /^[A-Za-z0-9_-]{32,256}$/.test(c.capability), 'Invalid one-attempt capability');
  must(c.model === MODEL && integer(c.maxRequests) && c.maxRequests > 0 && c.maxRequests <= LIMITS.requests, 'Invalid fixed model or turn ceiling');
  must(integer(c.maxOutputTokens) && c.maxOutputTokens > 0 && c.maxOutputTokens <= 4096, 'Invalid output-token bound');
  must(integer(c.deadlineAtMs) && c.deadlineAtMs > now && c.deadlineAtMs <= now + 900000, 'Invalid original task deadline');
  return Object.freeze(c);
}
function textBlocks(content) {
  must(Array.isArray(content) && content.length <= LIMITS.blocks, 'Invalid text blocks');
  return content.map(b => { keys(b, ['type','text'], 'Unsupported text block field'); must(b.type === 'text' && typeof b.text === 'string', 'Only text content is supported'); return { type: 'text', text: b.text }; });
}

export function convertHarnessRequest(options, config) {
  must(options.provider === PROVIDER && options.model === MODEL, 'Pinned DSH model route differs');
  for (const k of ['reasoningEffort','temperature','stop']) must(options[k] === undefined, 'Unsupported request control');
  must(integer(options.maxTokens) && options.maxTokens > 0 && options.maxTokens <= config.maxOutputTokens, 'Unsupported output-token request');
  must(id(options.sessionId), 'Invalid DSH session identity');
  const tools = snapshot(options.tools ?? []);
  must(Array.isArray(tools) && tools.length <= LIMITS.tools, 'Too many tools');
  const names = new Set();
  const mappedTools = tools.map(t => {
    keys(t, ['name','description','parameters'], 'Unsupported dynamic or deferred tool declaration');
    must(toolName(t.name) && !names.has(t.name) && typeof t.description === 'string' && object(t.parameters), 'Invalid tool definition');
    names.add(t.name); return { name: t.name, description: t.description, input_schema: t.parameters };
  });
  if (options.toolHistory !== undefined) {
    const history = snapshot(options.toolHistory); keys(history, ['tools','updates'], 'Unsupported tool history');
    must(Array.isArray(history.updates) && history.updates.length === 0 && canonical(history.tools) === canonical(tools), 'Dynamic tool history is unsupported');
  }
  const input = snapshot(options.messages);
  must(Array.isArray(input) && input.length > 0 && input.length <= LIMITS.messages, 'Invalid message count');
  const messages = [], system = [], pending = new Map(), allCalls = new Set();
  let sawConversation = false;
  const append = (role, content) => {
    must(content.length > 0, 'Empty conversation message');
    const previous = messages.at(-1);
    // Anthropic carries tool results in user blocks. Preserve their ordering and
    // combine consecutive user/tool messages instead of inventing empty turns.
    if (role === 'user' && previous?.role === 'user') previous.content.push(...content);
    else { must(previous?.role !== role, 'Consecutive assistant messages unsupported'); messages.push({ role, content }); }
  };
  for (const m of input) {
    keys(m, ['id','role','content','source','toolCallId','isError'], 'Unsupported message field');
    must(id(m.id) && object(m.source), 'Missing DSH message provenance');
    if (m.role === 'system') {
      must(!sawConversation && system.length === 0 && m.source.kind === 'system-prompt', 'Only a leading system message is supported');
      system.push(...textBlocks(m.content)); continue;
    }
    sawConversation = true;
    if (m.role === 'user') {
      must(pending.size === 0, 'Missing tool results before user message'); append('user', textBlocks(m.content));
    } else if (m.role === 'assistant') {
      must(messages.length > 0 && pending.size === 0 && m.source.kind === 'model' && m.source.provider === PROVIDER && m.source.model === MODEL
        && m.source.replayState === undefined, 'Assistant provenance or pending tools differ');
      must(Array.isArray(m.content) && m.content.length > 0 && m.content.length <= LIMITS.blocks, 'Invalid assistant content');
      const content = m.content.map(b => {
        if (b.type === 'text') return textBlocks([b])[0];
        keys(b, ['type','id','name','arguments'], 'Unsupported assistant block');
        must(b.type === 'tool-call' && callId(b.id) && !allCalls.has(b.id) && names.has(b.name) && typeof b.arguments === 'string', 'Invalid assistant tool call');
        const args = snapshot(JSON.parse(b.arguments)); must(object(args), 'Tool arguments must be an object');
        // This adapter writes its own arguments with JSON.stringify. Refuse an
        // altered/noncanonical history (including duplicate JSON keys).
        must(JSON.stringify(args) === b.arguments, 'Tool arguments differ from canonical emitted history');
        allCalls.add(b.id); pending.set(b.id, b.name); return { type: 'tool_use', id: b.id, name: b.name, input: args };
      });
      append('assistant', content);
    } else if (m.role === 'tool') {
      must(callId(m.toolCallId) && pending.has(m.toolCallId) && m.source.kind === 'tool' && m.source.callId === m.toolCallId
        && (m.isError === undefined || typeof m.isError === 'boolean'), 'Unmatched or duplicate tool result');
      pending.delete(m.toolCallId);
      append('user', [{ type: 'tool_result', tool_use_id: m.toolCallId, content: textBlocks(m.content), ...(m.isError === undefined ? {} : { is_error: m.isError }) }]);
    } else throw new Error('Unsupported message role; developer updates require a separately qualified adapter');
  }
  must(messages.length > 0 && messages[0].role === 'user' && messages.at(-1).role === 'user' && pending.size === 0, 'Incomplete conversation turn');
  const body = { model: MODEL, max_tokens: options.maxTokens, stream: false,
    ...(system.length ? { system } : {}), messages, ...(mappedTools.length ? { tools: mappedTools } : {}) };
  must(Buffer.byteLength(canonical(body)) <= LIMITS.providerBody, 'Provider body exceeds 256 KiB');
  return body;
}

function validateCompleted(raw, request, config) {
  const r = snapshot(raw);
  keys(r, ['schema','ok','state','taskId','attemptId','inputSha256','ordinal','sessionId','bodySha256','requestId','model','content','stop_reason','usage','receiptSha256','archiveSha256','settlementConfirmed'], 'Unexpected broker result field');
  must(r.schema === 'lupine.coding-model-result.v1' && r.ok === true && r.state === 'completed', 'Broker did not return a completed result');
  for (const k of ['taskId','attemptId','inputSha256','ordinal','sessionId']) must(r[k] === request[k], 'Broker result identity mismatch');
  must(r.bodySha256 === bodyDigest(request.body) && id(r.requestId) && r.model === config.model, 'Broker result request or model mismatch');
  must(hash(r.receiptSha256) && hash(r.archiveSha256) && r.settlementConfirmed === true, 'Durable broker settlement is required');
  must(Array.isArray(r.content) && r.content.length > 0 && r.content.length <= LIMITS.blocks, 'Invalid sanitized broker content');
  const allowedTools = new Set((request.body.tools ?? []).map(t => t.name)), ids = new Set();
  r.content.forEach(b => {
    if (b.type === 'text') textBlocks([b]);
    else {
      keys(b, ['type','id','name','input'], 'Unexpected tool output field');
      must(b.type === 'tool_use' && callId(b.id) && !ids.has(b.id) && allowedTools.has(b.name) && object(b.input), 'Unsupported or duplicate returned tool call'); ids.add(b.id);
    }
  });
  must(['end_turn','tool_use','max_tokens','stop_sequence'].includes(r.stop_reason), 'Unsupported terminal stop reason');
  must((r.stop_reason === 'tool_use') === (ids.size > 0), 'Tool calls require a complete tool-use terminal');
  keys(r.usage, ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens'], 'Invalid usage fields');
  must(integer(r.usage.input_tokens) && integer(r.usage.output_tokens), 'Missing authoritative input/output token counts');
  for (const k of ['cache_creation_input_tokens','cache_read_input_tokens']) must(r.usage[k] === null || integer(r.usage[k]), 'Missing cache usage must be null, not fabricated zero');
  return r;
}
async function readBounded(response) {
  const declared = response.headers.get('content-length');
  must(declared === null || /^\d+$/.test(declared) && Number(declared) <= LIMITS.response, 'Oversized broker response');
  must(response.body, 'Missing broker response'); const reader = response.body.getReader(), parts = []; let size = 0;
  try {
    while (true) { const { done, value } = await reader.read(); if (done) break; size += value.length; must(size <= LIMITS.response, 'Oversized broker response'); parts.push(Buffer.from(value)); }
  } catch (error) { void reader.cancel().catch(() => {}); throw error; }
  return { bytes: size, value: JSON.parse(Buffer.concat(parts).toString('utf8')) };
}

export function createBrokerTransport(config, { fetch: fetcher = globalThis.fetch, now = Date.now } = {}) {
  // Validate even callers that construct config directly rather than use env.
  const c = parseConfig(JSON.stringify(config), now());
  let ordinal = 0, stopped = false, queued = 0, tail = Promise.resolve();
  const records = [], sessions = new Map();
  return {
    records: () => structuredClone(records),
    status: () => ({ stopped, admittedRequests: ordinal, queuedRequests: queued }),
    async *stream(options) {
      // Detach model-facing inputs before waiting for another distinct session.
      // Queueing is admission of new turns, never retrying a consumed ordinal.
      let body;
      try {
        must(!stopped && queued + ordinal < c.maxRequests, 'Attempt transport is stopped or exhausted; automatic replay is forbidden');
        body = convertHarnessRequest(options, c);
      } catch (error) { stopped = true; throw error; }
      const sessionId = options.sessionId, callerSignal = options.signal;
      let release; const previous = tail; tail = new Promise(resolve => { release = resolve; }); queued++;
      let record, completedEmission = false;
      try {
        await previous; queued--;
        must(!stopped, 'A prior turn stopped the attempt; automatic replay is forbidden');
        callerSignal?.throwIfAborted();
        must(now() < c.deadlineAtMs && ordinal < c.maxRequests, 'Original attempt deadline or turn ceiling exhausted');
        const contextSha = bodyDigest({ system: body.system ?? [], tools: body.tools ?? [] });
        const oldContext = sessions.get(sessionId);
        must(oldContext === undefined || oldContext === contextSha, 'Session system/tool configuration changed');
        sessions.set(sessionId, contextSha);
        const request = { schema: 'lupine.coding-model-turn.v1', taskId: c.taskId, attemptId: c.attemptId,
          inputSha256: c.inputSha256, ordinal: ++ordinal, sessionId, body };
        const encoded = canonical(request); must(Buffer.byteLength(encoded) <= LIMITS.request, 'Broker request exceeds 300 KiB');
        record = { ordinal, sessionId, bodySha256: bodyDigest(body), inputBytes: Buffer.byteLength(encoded),
          status: 'unknown', configuredProvider: PROVIDER, configuredModel: MODEL, modelReported: null,
          outputBytes: null, usage: null, receiptSha256: null, archiveSha256: null, deliveredToHarness: false };
        records.push(record);
        const timeout = AbortSignal.timeout(Math.max(1, Math.min(LIMITS.timeoutMs, c.deadlineAtMs - now())));
        const signal = callerSignal ? AbortSignal.any([timeout, callerSignal]) : timeout;
        let result;
        try {
          const response = await fetcher(c.endpoint, { method: 'POST', redirect: 'manual', signal,
            headers: { authorization: `Bearer ${c.capability}`, 'content-type': 'application/json' }, body: encoded });
          must(response.status === 200 && response.headers.get('content-type')?.split(';')[0] === 'application/json', 'Broker response unavailable; exact receipt reconciliation required');
          const read = await readBounded(response); record.outputBytes = read.bytes;
          must(read.value?.ok === true, 'Broker withheld result; no replay');
          result = validateCompleted(read.value, request, c);
          must(!canonical(result.content).includes(c.capability), 'Scoped capability cannot enter Harness output');
          signal.throwIfAborted(); must(now() < c.deadlineAtMs, 'Broker response completed after task deadline');
        } catch { throw new Error('Broker turn could not be released safely; automatic retry is forbidden'); }
        Object.assign(record, { status: 'completed', modelReported: result.model, usage: result.usage,
          receiptSha256: result.receiptSha256, archiveSha256: result.archiveSha256 });
        for (const [index, b] of result.content.entries()) {
          callerSignal?.throwIfAborted();
          const block = b.type === 'text' ? { type: 'text', text: b.text } : { type: 'tool-call', id: b.id, name: b.name, arguments: JSON.stringify(b.input) };
          yield { type: 'block-start', index, blockType: block.type };
          yield block.type === 'text' ? { type: 'text-delta', index, text: block.text }
            : { type: 'tool-call-delta', index, id: block.id, name: block.name, argumentsDelta: block.arguments };
          yield { type: 'block-end', index, block };
        }
        const u = result.usage;
        yield { type: 'usage', usage: { inputTokens: u.input_tokens, outputTokens: u.output_tokens,
          ...(u.cache_creation_input_tokens === null ? {} : { cacheWriteTokens: u.cache_creation_input_tokens }),
          ...(u.cache_read_input_tokens === null ? {} : { cacheReadTokens: u.cache_read_input_tokens }) } };
        yield { type: 'finish', reason: { kind: result.stop_reason === 'tool_use' ? 'tool-calls' : result.stop_reason === 'max_tokens' ? 'max-tokens' : 'stop' } };
        completedEmission = true; record.deliveredToHarness = true;
      } finally { if (!completedEmission) stopped = true; release(); }
    },
  };
}

export function createHarnessAdapter(llm, config, options) {
  const transport = createBrokerTransport(config, options);
  class ScopedSubscriptionAdapter extends llm.LlmAdapter {
    providerRetryPolicy() { return { mode: 'normal', maxRetries: 0, retryableCodes: [], initialDelayMs: 1, maxDelayMs: 1, jitterRatio: 0 }; }
    async resolveModel(provider, model, signal) {
      signal?.throwIfAborted(); must(provider === PROVIDER && model === MODEL, 'Unknown fixed model route');
      return { provider, id: model, name: model, inputModalities: ['text'], defaultMaxTokens: config.maxOutputTokens };
    }
    stream(options) { return transport.stream(options); }
  }
  return { adapter: new ScopedSubscriptionAdapter(), records: transport.records, status: transport.status };
}
