import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const fields = ['public_count','archive_count','missing_sequence','orphan_sequence','duplicate_records',
  'duplicate_sequences','invalid_sequences','append_trigger','immutable_triggers'];
function failure(category, message, metrics) {
  return Object.assign(new Error(message), { category, metrics });
}

/** Wrangler --json result only; diagnostics never include public/private payloads. */
export function verifyArchiveMetrics(value) {
  if (!Array.isArray(value) || value.length !== 1 || value[0]?.success !== true ||
      !Array.isArray(value[0].results) || value[0].results.length !== 1) throw failure('invalid_result_shape','Invalid archive verification result');
  const row = value[0].results[0];
  if (!row || fields.some(key => !Number.isSafeInteger(row[key]) || row[key] < 0)) throw failure('invalid_metrics','Invalid archive verification metrics');
  if (row.public_count !== row.archive_count || row.missing_sequence || row.orphan_sequence ||
      row.duplicate_records || row.duplicate_sequences || row.invalid_sequences ||
      row.append_trigger !== 1 || row.immutable_triggers !== 2) throw failure('invariant_failure','Archive sequence invariants failed', Object.fromEntries(fields.map(key => [key,row[key]])));
  return Object.fromEntries(fields.map(key => [key,row[key]]));
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { console.log(JSON.stringify({ verified: true, metrics: verifyArchiveMetrics(JSON.parse(readFileSync(0,'utf8'))) })); }
  catch (error) {
    console.error(JSON.stringify({ verified:false, category:error instanceof SyntaxError ? 'invalid_json' : error.category || 'verification_failure', ...(error.metrics ? { metrics:error.metrics } : {}) }));
    process.exitCode=1;
  }
}
