import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { build } from '../node_modules/esbuild/lib/main.js';

// Every service response is synthetic; no network, model calls or Git effects.
const directory = await mkdtemp(path.join(tmpdir(), 'rhizo-regression-contract-'));
after(() => rm(directory, { recursive: true, force: true }));
const gate = path.join(directory, 'gate.mjs');
await build({ entryPoints: [process.env.REGRESSION_GATE_TEST_SOURCE ?? new URL('./regression-gate.ts', import.meta.url).pathname], outfile: gate, bundle: true, platform: 'node', format: 'esm' });
const cell = (pass_rate = .9, n = 20) => ({ n, pass_rate });
const scorecard = () => ({ modelA: { completeness: cell(), hallucination: cell() }, modelB: { completeness: cell() } });
const claim = (scorecard, created_at) => ({ claim_type: 'ModelScorecard', claim_data: JSON.stringify({ scorecard }), created_at });
const rows = (current = scorecard(), previous = scorecard()) => [claim(current, '2026-01-02T00:00:00Z'), claim(previous, '2026-01-01T00:00:00Z')];
let sequence = 0;
async function run(value, { args = [], failure = false, env = {} } = {}) {
  const stub = path.join(directory, `response-${sequence++}.mjs`);
  await writeFile(stub, failure ? 'globalThis.fetch=async()=>{throw Error("synthetic unavailable")};' : `globalThis.fetch=async()=>Response.json(${JSON.stringify(value)});`);
  const result = spawnSync(process.execPath, ['--import', stub, gate, ...args], { encoding: 'utf8', timeout: 15000,
    env: { ...process.env, AUTO_REVERT: '0', EVAL_REGRESSION_THRESHOLD: '0.1', EVAL_REGRESSION_MIN_SAMPLES: '20', ...env } });
  assert.ifError(result.error);
  return { exit: result.status, output: result.stdout + result.stderr };
}
async function insufficient(value, options) {
  const result = await run(value, options);
  assert.equal(result.exit, 2, result.output);
  assert.match(result.output, /INSUFFICIENT/);
  assert.doesNotMatch(result.output, /— PASS/);
  return result;
}
test('comparable complete scorecards pass and a measured regression fails', async () => {
  const good = await run(rows()); assert.equal(good.exit, 0, good.output); assert.match(good.output, /— PASS/);
  const current = scorecard(); current.modelA.completeness = cell(.1);
  const bad = await run(rows(current)); assert.equal(bad.exit, 1, bad.output); assert.match(bad.output, /— FAIL/);
});
test('a missing model, empty scorecard or missing evaluator cannot pass', async () => {
  const missing = scorecard(); delete missing.modelB; await insufficient(rows(missing));
  await insufficient(rows({}));
  const evaluator = scorecard(); delete evaluator.modelA.hallucination; await insufficient(rows(evaluator));
});
test('new models and new evaluators are unbaselined, not silently passed', async () => {
  const current = scorecard(); current.modelC = { completeness: cell() }; await insufficient(rows(current));
  const evaluator = scorecard(); evaluator.modelB.reasoning = cell(); await insufficient(rows(evaluator));
});
test('missing, zero, fractional or below-policy sample counts cannot pass', async () => {
  for (const n of [undefined, 0, -1, 1.5, 19, '20']) {
    const current = scorecard(); current.modelA.completeness = { n, pass_rate: .9 }; await insufficient(rows(current));
  }
  const previous = scorecard(); previous.modelA.completeness.n = 0; await insufficient(rows(scorecard(), previous));
});
test('sample policy is explicit and configurable without changing workflow authorization', async () => {
  const current = scorecard(); current.modelA.completeness.n = 1;
  const result = await run(rows(current), { args: ['--min-samples', '1'] }); assert.equal(result.exit, 0, result.output);
});
test('missing, out-of-range or nonnumeric pass rates cannot pass', async () => {
  for (const pass_rate of [undefined, null, -1, 2, '0.9']) {
    const current = scorecard(); current.modelA.completeness = { n: 20, pass_rate }; await insufficient(rows(current));
  }
});
test('malformed latest claim is not skipped in favor of older good evidence', async () => {
  await insufficient([{ claim_type: 'ModelScorecard', claim_data: '{', created_at: '2026-01-03T00:00:00Z' }, ...rows()]);
  await insufficient([claim(null, '2026-01-03T00:00:00Z'), ...rows()]);
  await insufficient({ claims: 'malformed' });
});
test('missing cards, unavailable service and invalid dates yield insufficient evidence', async () => {
  await insufficient([]); await insufficient([rows()[0]]); await insufficient(null, { failure: true });
  const invalid = rows(); invalid[0].created_at = ''; await insufficient(invalid);
  const duplicateDate = rows(); duplicateDate[0].created_at = duplicateDate[1].created_at; await insufficient(duplicateDate);
});
test('optional attribution buckets are deliberately excluded but cannot be the only evidence', async () => {
  const current = scorecard(); Object.assign(current, { 'modelA|agent': null, 'workers-ai': {}, unknown: {} });
  const result = await run(rows(current)); assert.equal(result.exit, 0, result.output); assert.match(result.output, /Excluded optional buckets/);
  await insufficient(rows({ 'modelA|agent': { completeness: cell() }, unknown: {} }));
});
test('invalid thresholds/minimums cannot turn regressions or absence into pass', async () => {
  for (const args of [['--threshold', 'NaN'], ['--threshold', '-1'], ['--threshold', '2'], ['--min-samples', '0'], ['--min-samples', '1.5'], ['--threshold']]) await insufficient(rows(), { args });
});
test('unchanged seeded local dry-run remains usable', async () => {
  const good = await run(null, { args: ['--dry-run'] }); assert.equal(good.exit, 0, good.output);
  const bad = await run(null, { args: ['--dry-run', '--seed-regression'] }); assert.equal(bad.exit, 1, bad.output);
});

test('insufficient coverage never invokes AUTO_REVERT even when explicitly enabled', async () => {
  const bin = path.join(directory, 'bin');
  const { mkdir, access } = await import('node:fs/promises'); await mkdir(bin);
  const marker = path.join(directory, 'git-was-invoked');
  await writeFile(path.join(bin, 'git'), `#!/bin/sh\nprintf invoked > ${JSON.stringify(marker)}\nexit 99\n`, { mode: 0o755 });
  await insufficient(rows({}), { env: { AUTO_REVERT: '1', PATH: `${bin}:${process.env.PATH}` } });
  await insufficient(null, { failure: true, env: { AUTO_REVERT: '1', PATH: `${bin}:${process.env.PATH}` } });
  await assert.rejects(access(marker));
});
test('claims envelope/order is supported while excessive response bytes are rejected', async () => {
  const result = await run({ claims: [...rows()].reverse() }); assert.equal(result.exit, 0, result.output);
  await insufficient([{ ...rows()[0], ignoredPadding: 'x'.repeat(1024 * 1024) }, rows()[1]]);
});
test('JSON overflow rates remain invalid after actual claim-data parsing', async () => {
  const latest = rows()[0]; latest.claim_data = '{"scorecard":{"modelA":{"completeness":{"n":20,"pass_rate":1e999}}}}';
  await insufficient([latest, rows()[1]]);
});

test('default sample floor accepts nonempty emitter cells without imposing a new sample policy', async () => {
  const current = scorecard(); const previous = scorecard();
  current.modelA.completeness.n = 1; previous.modelA.completeness.n = 2;
  const result = await run(rows(current, previous), { env: { EVAL_REGRESSION_MIN_SAMPLES: undefined } });
  assert.equal(result.exit, 0, result.output); assert.match(result.output, /minimum samples per model\/evaluator: 1/);
});

// Producer shape from ab-oracle.ts persistScorecard: same claim type but
// window=experiment and n/mean_score cells, deliberately not pass-rate data.
function oracleClaim(created_at) {
  return { claim_type: 'ModelScorecard', created_at,
    claim_data: JSON.stringify({ window: 'experiment', dataset: 'synthetic-only', generated_at: created_at,
      scorecard: { modelA: { completeness: { n: 20, mean_score: .9 } } },
      ab: { agent: 'synthetic-agent', axis: 'model', baseline: 'synthetic-baseline', candidate: 'modelA', n: 20, deltas: {}, regression: false, verdict: 'synthetic-only' } }) };
}
test('actual A/B oracle mean_score producer shape is insufficient and never coerced to pass_rate', async () => {
  await insufficient([oracleClaim('2026-01-02T00:00:00Z'), oracleClaim('2026-01-01T00:00:00Z')]);
});
test('a recent incompatible A/B oracle scorecard is not bypassed for older pass-rate claims', async () => {
  await insufficient([oracleClaim('2026-01-03T00:00:00Z'), ...rows()]);
  await insufficient([claim(scorecard(), '2026-01-04T00:00:00Z'), oracleClaim('2026-01-03T00:00:00Z'), ...rows()]);
});
