import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export function archiveQueryArguments(sql) {
  // --file uses D1 import mode and returns import statistics, not SELECT rows.
  return ['node_modules/wrangler/bin/wrangler.js','d1','execute','glim-ledger','--remote','--json',`--command=${sql}`];
}
export function queryFailureCategory(result) {
  const stderr = `${result.stderr || ''}\n${result.stdout || ''}`.replace(/\x1b\[[0-9;]*m/g,'');
  if (result.error?.code === 'ENOBUFS') return 'query_output_limit';
  if (result.error) return 'query_process_error';
  if (/Unknown argument|Not enough non-option arguments/.test(stderr)) return 'query_argument_parse_error';
  if (/CLOUDFLARE_API_TOKEN|Authentication error|authenticate|not logged in/i.test(stderr)) return 'query_authentication_error';
  return 'archive_query_failed';
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
    console.error(JSON.stringify({ verified:false,category:queryFailureCategory(result),exitCode:result.status ?? null }));
    process.exitCode=1;
  } else process.stdout.write(result.stdout);
}
