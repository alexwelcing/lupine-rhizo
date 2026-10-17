import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

const migration = readFileSync(new URL('../migrations/0023_public_activity_archive.sql', import.meta.url), 'utf8');
test('archive migration preserves ingestion snapshot across rerun and backdated imports', () => {
  const db = new DatabaseSync(':memory:');
  try {
    db.exec(`PRAGMA foreign_keys=ON;
      CREATE TABLE public_research_activity(id TEXT PRIMARY KEY, imported_at TEXT NOT NULL);
      INSERT INTO public_research_activity VALUES ('b','2026-10-02'),('a','2026-10-01'),('c','2026-10-02');`);
    db.exec(migration);
    const rows = () => db.prepare('SELECT sequence,record_id FROM public_activity_archive_sequence ORDER BY sequence').all().map(row => ({ ...row }));
    const original = rows();
    assert.deepEqual(original, [{ sequence:1,record_id:'a' }, { sequence:2,record_id:'b' }, { sequence:3,record_id:'c' }]);
    db.exec(migration);
    assert.deepEqual(rows(), original);
    db.exec("INSERT INTO public_research_activity VALUES ('late','2000-01-01')");
    assert.deepEqual(rows().slice(0,3), original);
    assert.deepEqual(rows()[3], { sequence:4,record_id:'late' });
    assert.throws(() => db.exec("UPDATE public_activity_archive_sequence SET record_id='late' WHERE sequence=1"), /immutable/);
    assert.throws(() => db.exec('DELETE FROM public_activity_archive_sequence WHERE sequence=1'), /immutable/);
    assert.equal(db.prepare('SELECT count(*) n FROM public_research_activity a LEFT JOIN public_activity_archive_sequence s ON s.record_id=a.id WHERE s.record_id IS NULL').get().n, 0);
  } finally { db.close(); }
});

test('release applies archive migration and runs its regression before worker deploy', () => {
  const workflow = readFileSync(new URL('../../.github/workflows/deploy-glim-think.yml', import.meta.url), 'utf8');
  assert.ok(workflow.includes('node --test scripts/prepare-public-activity-import.test.mjs scripts/public-activity-archive-migration.test.mjs'));
  const apply = workflow.indexOf('command: d1 execute glim-ledger --remote --file migrations/0023_public_activity_archive.sql');
  assert.ok(apply > 0 && apply < workflow.indexOf('command: deploy'));
});

test('remote metrics verifier accepts actual SQL and rejects every violated invariant', async () => {
  const { verifyArchiveMetrics } = await import('./verify-public-activity-archive.mjs');
  const sql = readFileSync(new URL('./verify-public-activity-archive.sql', import.meta.url),'utf8');
  const db = new DatabaseSync(':memory:');
  try {
    db.exec("CREATE TABLE public_research_activity(id TEXT PRIMARY KEY, imported_at TEXT NOT NULL); INSERT INTO public_research_activity VALUES ('a','2026-10-01');");
    db.exec(migration);
    const metrics = { ...db.prepare(sql).get() };
    const wrap = row => [{ success:true,results:[row] }];
    assert.equal(verifyArchiveMetrics(wrap(metrics)).public_count,1);
    for (const [key,value] of Object.entries({ archive_count:2,missing_sequence:1,orphan_sequence:1,duplicate_records:1,duplicate_sequences:1,invalid_sequences:1,append_trigger:0,immutable_triggers:1 })) {
      assert.throws(() => verifyArchiveMetrics(wrap({ ...metrics,[key]:value })), /invariants failed/);
    }
    for (const bad of [[],[{success:false,results:[metrics]}],wrap({...metrics,public_count:'1'}),wrap({...metrics,public_count:-1})]) assert.throws(() => verifyArchiveMetrics(bad));
    const workflow = readFileSync(new URL('../../.github/workflows/deploy-glim-think.yml', import.meta.url),'utf8');
    assert.ok(workflow.indexOf('Verify public activity archive before deployment') < workflow.indexOf('command: deploy'));
    assert.ok(workflow.includes('set -o pipefail'));
    assert.ok(workflow.includes('node scripts/query-public-activity-archive.mjs | node scripts/verify-public-activity-archive.mjs'));
  } finally { db.close(); }
});

test('workflow query runner passes SQL as one --command argument without shell/import mode', async () => {
  const { queryArchive, archiveQueryArguments } = await import('./query-public-activity-archive.mjs');
  const sql = readFileSync(new URL('./verify-public-activity-archive.sql',import.meta.url),'utf8');
  let called=false;
  queryArchive((executable,args,options) => {
    called=true;
    assert.equal(executable,process.execPath);
    assert.deepEqual(args.slice(0,-1), ['node_modules/wrangler/bin/wrangler.js','d1','execute','glim-ledger','--remote','--json','--command']);
    assert.equal(args.at(-1),sql);
    assert.equal(options.shell,false);
    assert.equal(options.env.WRANGLER_SEND_METRICS,'false');
    return {status:0,stdout:'[]'};
  });
  assert(called);
  assert.equal(archiveQueryArguments("SELECT '$(never-run)';").at(-1),"SELECT '$(never-run)';");
});

test('verifier CLI rejects import summaries/malformed JSON without echoing untrusted data', () => {
  const script = new URL('./verify-public-activity-archive.mjs',import.meta.url);
  for (const [input,category] of [
    ['not-json SECRET', 'invalid_json'],
    [JSON.stringify([{success:true,results:[{'Total queries executed':1,'Rows read':4,secret:'SECRET'}]}]),'invalid_metrics'],
    [JSON.stringify({secret:'SECRET'}),'invalid_result_shape'],
    [JSON.stringify([{success:true,results:[] }]),'invalid_result_shape'],
  ]) {
    const result=spawnSync(process.execPath,[script.pathname],{input,encoding:'utf8'});
    assert.equal(result.status,1);
    assert.equal(JSON.parse(result.stderr).category,category);
    assert(!result.stderr.includes('SECRET'));
  }
});

test('verifier CLI exposes only allowlisted counts on invariant failure', () => {
  const row={public_count:2,archive_count:1,missing_sequence:1,orphan_sequence:0,
    duplicate_records:0,duplicate_sequences:0,invalid_sequences:0,append_trigger:1,immutable_triggers:2,
    privatePayload:'SECRET'};
  const result=spawnSync(process.execPath,[new URL('./verify-public-activity-archive.mjs',import.meta.url).pathname],
    {input:JSON.stringify([{success:true,results:[row]}]),encoding:'utf8'});
  assert.equal(result.status,1);
  const diagnostic=JSON.parse(result.stderr);
  assert.equal(diagnostic.category,'invariant_failure');
  assert.equal(diagnostic.metrics.missing_sequence,1);
  assert(!result.stderr.includes('SECRET'));
  assert(!Object.hasOwn(diagnostic.metrics,'privatePayload'));
});
