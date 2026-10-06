import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { CATALOG } from '../scripts/library-content-catalog.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const INDEX_SOURCE = 'docs/research-index.md';
const INDEX = fs.readFileSync(path.join(ROOT, INDEX_SOURCE), 'utf8');
const ENTRIES = new Map(CATALOG.entries.map((entry) => [entry.id, entry]));
const SOURCES = new Set(CATALOG.entries.map((entry) => entry.source));

// The reader rewrites links only when their targets are in this same bundle.
// A file existing in Rhizo is insufficient to make it readable in the Library.
test('research index links all resolve to exported Library articles', () => {
  const links = [...INDEX.matchAll(/\]\(([^\s)]+\.md)(?:#[^\s)]*)?\)/g)].map((match) => match[1]);
  assert.ok(links.length > 0);
  for (const link of links) {
    assert.ok(!/^[a-z]+:/i.test(link), 'Use bundle links for research articles');
    const source = path.posix.normalize(path.posix.join(path.posix.dirname(INDEX_SOURCE), link));
    assert.ok(SOURCES.has(source), `Not in the public catalog: ${source}`);
    assert.ok(fs.existsSync(path.join(ROOT, source)), `Missing source: ${source}`);
  }
});

test('research journey opens the index and retains evidence and correction routes', () => {
  const journey = CATALOG.journeys.find((item) => item.id === 'research-progress');
  assert.ok(journey);
  assert.equal(journey.path[0], 'research-index');
  for (const id of journey.path) assert.ok(ENTRIES.has(id), `Unknown journey article: ${id}`);
  for (const id of ['conjecture-ledger', 'born-screening-re-audit', 'formal-proof-ledger', 'reproduce']) {
    assert.ok(journey.path.includes(id), `Missing evidence route: ${id}`);
  }
});

test('dated report statuses and dates match their public catalog sources', () => {
  const datedRows = [...INDEX.matchAll(/^\| (\d{4}-\d{2}-\d{2}) \| \[[^\]]+\]\(([^)]+)\) \| ([^|]+) \|/gm)];
  assert.ok(datedRows.length > 0);
  for (const [, date, relative, status] of datedRows) {
    const source = path.posix.normalize(path.posix.join('docs', relative));
    const entry = CATALOG.entries.find((item) => item.source === source);
    assert.ok(entry, source);
    assert.equal(status.trim(), CATALOG.statuses[entry.status]?.label?.en, source);
    assert.ok(fs.readFileSync(path.join(ROOT, source), 'utf8').slice(0, 1500).includes(date), `Date not in report header: ${source}`);
  }
  for (const entry of CATALOG.entries) {
    if (entry.status) assert.ok(CATALOG.statuses[entry.status], `Unknown public status: ${entry.status}`);
  }
});

test('latest exported research index and catalog match source with valid receipts', () => {
  const bundle = path.join(ROOT, 'exports/library-content/latest');
  const manifest = JSON.parse(fs.readFileSync(path.join(bundle, 'manifest.json'), 'utf8'));
  assert.equal(manifest.schemaVersion, 'library-content.v1');
  assert.deepEqual(manifest.catalog.journeys, CATALOG.journeys);
  const entry = manifest.catalog.entries.find((item) => item.id === 'research-index');
  assert.ok(entry);
  const bytes = fs.readFileSync(path.join(bundle, entry.source));
  assert.equal(bytes.toString(), INDEX);
  const receipt = manifest.files.find((item) => item.bundleSource === entry.source);
  assert.equal(receipt.bytes, bytes.length);
  assert.equal(receipt.sha256, crypto.createHash('sha256').update(bytes).digest('hex'));
});
