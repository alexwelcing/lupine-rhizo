import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export function archiveQueryArguments(sql) {
  // --file uses D1 import mode and returns import statistics, not SELECT rows.
  return ['node_modules/wrangler/bin/wrangler.js','d1','execute','glim-ledger','--remote','--json','--command',sql];
}
export function queryArchive(spawn = spawnSync) {
  const sql = readFileSync(new URL('./verify-public-activity-archive.sql', import.meta.url),'utf8');
  return spawn(process.execPath, archiveQueryArguments(sql), {
    encoding:'utf8', shell:false, maxBuffer:1024*1024,
    env:{ ...process.env, WRANGLER_SEND_METRICS:'false' },
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = queryArchive();
  if (result.error || result.status !== 0) {
    // Do not echo Wrangler stderr, credentials, SQL or arbitrary database output.
    console.error(JSON.stringify({ verified:false,category:'archive_query_failed',exitCode:result.status ?? null }));
    process.exitCode=1;
  } else process.stdout.write(result.stdout);
}
