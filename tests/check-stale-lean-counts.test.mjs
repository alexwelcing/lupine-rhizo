import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCANNER = path.join(REPO_ROOT, 'scripts', 'check-stale-lean-counts.mjs');
const EXPORTER = path.join(REPO_ROOT, 'scripts', 'export_library_content.mjs');

function createFixtureRepo(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'rhizo-stale-lean-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'scripts'), { recursive: true });
  fs.copyFileSync(SCANNER, path.join(root, 'scripts', 'check-stale-lean-counts.mjs'));
  fs.copyFileSync(EXPORTER, path.join(root, 'scripts', 'export_library_content.mjs'));
  execFileSync('git', ['init', '--quiet'], { cwd: root });
  return root;
}

test('rejects a stale theorem total in an active latest-export article', (t) => {
  const root = createFixtureRepo(t);
  const relative = 'exports/library-content/latest/articles/docs/formal-vision.md';
  const absolute = path.join(root, relative);
  fs.mkdirSync(path.dirname(absolute), { recursive: true });
  fs.writeFileSync(absolute, 'Current proof layer: 77 build-locked theorems.\n');
  execFileSync('git', ['add', 'scripts/check-stale-lean-counts.mjs', relative], { cwd: root });

  const result = spawnSync(process.execPath, ['scripts/check-stale-lean-counts.mjs'], {
    cwd: root,
    encoding: 'utf8',
  });

  assert.equal(result.status, 1, result.stdout || result.stderr);
  assert.match(result.stderr, /exports\/library-content\/latest\/articles\/docs\/formal-vision\.md:1/);
});

test('exporter post-scan cannot inherit the pre-scan bypass', (t) => {
  const root = createFixtureRepo(t);
  const source = 'registry/ontology/atlas.v1.json';
  const exported = `exports/library-content/latest/articles/${source}`;
  fs.mkdirSync(path.join(root, 'scripts'), { recursive: true });
  fs.writeFileSync(path.join(root, 'package.json'), '{"type":"module"}\n');
  fs.writeFileSync(
    path.join(root, 'scripts', 'library-content-catalog.js'),
    `export const CATALOG = { statuses: {}, categories: [], journeys: [], entries: [{ source: '${source}' }], languages: {} };\n`,
  );
  fs.mkdirSync(path.dirname(path.join(root, source)), { recursive: true });
  fs.writeFileSync(path.join(root, source), 'Current proof layer: 77 build-locked theorems.\n');
  execFileSync('git', ['add', '.'], { cwd: root });

  const result = spawnSync(process.execPath, ['scripts/export_library_content.mjs'], {
    cwd: root,
    encoding: 'utf8',
    env: { ...process.env, STALE_LEAN_SCAN_SKIP_ACTIVE_EXPORT: '1' },
  });

  assert.equal(result.status, 1, result.stdout || result.stderr);
  assert.match(result.stderr, /exports\/library-content\/latest\/articles\/registry\/ontology\/atlas\.v1\.json:1/);
});
