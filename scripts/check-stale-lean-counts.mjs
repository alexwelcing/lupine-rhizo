#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SELF = path.relative(ROOT, fileURLToPath(import.meta.url)).split(path.sep).join('/');
const ACTIVE_EXPORT_ROOT = path.join(ROOT, 'exports', 'library-content', 'latest');
const SKIP_ACTIVE_EXPORT = process.env.STALE_LEAN_SCAN_SKIP_ACTIVE_EXPORT === '1';
const STALE_NUMBER = /(?<![\d.])(?:77|190|262)(?![\d.])/;
const COUNT_CONTEXT = /theorems?|lemmas?|declarations?|build[- ]locked|proof layer|Lean 4 corpus|theorem[- ]inventory/i;
const TEXT_EXTENSIONS = new Set(['.html', '.json', '.js', '.md', '.mjs', '.txt', '.vtt']);
// atlas.v1.json is digest-locked by tools/check_ontology_links.py; preserving it
// is mandatory historical provenance rather than permission to reuse its count.
const HISTORICAL_PATH = /(?:^|\/)(?:CHANGELOG\.md|archive|exports|reviews)(?:\/|$)|ZENODO_DEPOSIT\.md$|\.zenodo\.json$|^registry\/ontology\/atlas\.v1\.json$/i;
const CODE_OR_TEST_PATH = /(?:^|\/)(?:tests?|testdata)(?:\/|$)|(?:^|\/)python\/tests\/|\.(?:lean|svg)$/i;

function trackedFiles() {
  return execFileSync('git', ['ls-files', '-z'], { cwd: ROOT })
    .toString('utf8')
    .split('\0')
    .filter(Boolean);
}

function activeExportFiles(directory = ACTIVE_EXPORT_ROOT) {
  if (!fs.existsSync(directory)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...activeExportFiles(absolute));
    } else if (entry.isFile()) {
      files.push(path.relative(ROOT, absolute).split(path.sep).join('/'));
    }
  }
  return files;
}

const failures = [];
for (const relative of new Set([...trackedFiles(), ...activeExportFiles()])) {
  const activeLatestExport = relative.startsWith('exports/library-content/latest/');
  const historicalCandidate = activeLatestExport
    ? relative.slice('exports/library-content/latest/'.length)
    : relative;
  if (relative === SELF || (activeLatestExport && SKIP_ACTIVE_EXPORT) || HISTORICAL_PATH.test(historicalCandidate) || CODE_OR_TEST_PATH.test(relative)) continue;
  if (!TEXT_EXTENSIONS.has(path.extname(relative).toLowerCase())) continue;
  const lines = fs.readFileSync(path.join(ROOT, relative), 'utf8').split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const localContext = lines.slice(Math.max(0, index - 1), index + 2).join('\n');
    if (!STALE_NUMBER.test(line) || !COUNT_CONTEXT.test(localContext)) continue;
    const context = lines.slice(Math.max(0, index - 10), index + 1).join('\n');
    if (/frozen (?:PP-2|historical) snapshot/i.test(context)) continue;
    failures.push(`${relative}:${index + 1}: ${line.trim()}`);
  }
}

if (failures.length > 0) {
  console.error('Refusing stale hand-typed Lean theorem totals outside labeled historical snapshots:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('check-stale-lean-counts: no active hand-typed 77/190/262 theorem totals');
