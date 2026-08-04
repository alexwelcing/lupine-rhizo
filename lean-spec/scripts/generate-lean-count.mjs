#!/usr/bin/env node
// Generates lean-spec/theorem-count.json from the active Lean source tree.
// This is the canonical inventory for README and downstream public surfaces.

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const LEAN_SPEC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TARGET = path.join(LEAN_SPEC, 'OpenDistillationFactory');
const OUT = path.join(LEAN_SPEC, 'theorem-count.json');
const DECL_RE = /^(theorem|lemma)\s/;
const SORRY_RE = /:=\s*sorry\b|\bby\s+sorry\b|^\s*sorry\s*$/;
const COMMENT_RE = /^\s*(--|\/-|\*)/;

function leanFiles(root) {
  const files = [];
  const rootFile = `${root}.lean`;
  if (fs.existsSync(rootFile)) files.push(rootFile);
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const entryPath = path.join(dir, entry.name);
      if (entryPath.includes(`${path.sep}packages${path.sep}`) || entryPath.includes(`${path.sep}.lake${path.sep}`)) continue;
      if (entry.isDirectory()) walk(entryPath);
      else if (entry.isFile() && entryPath.endsWith('.lean')) files.push(entryPath);
    }
  };
  if (fs.existsSync(root)) walk(root);
  return files.sort();
}

const files = leanFiles(TARGET);
if (!files.length) throw new Error(`no .lean files found under ${TARGET}`);

let count = 0;
let sorryCount = 0;
for (const file of files) {
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (DECL_RE.test(line)) count += 1;
    if (SORRY_RE.test(line) && !COMMENT_RE.test(line)) sorryCount += 1;
  }
}

const sourceCommit = execSync('git rev-parse --short HEAD', { cwd: LEAN_SPEC, encoding: 'utf8' }).trim();
const inventory = {
  count,
  modules: files.length,
  zero_sorry: sorryCount === 0,
  counted_at: new Date().toISOString().slice(0, 10),
  source: 'lean-spec/OpenDistillationFactory{,.lean} (vendored packages excluded)',
  source_commit: sourceCommit,
  rule: 'top-level declarations: lines matching /^(theorem|lemma)\\s/ in *.lean under OpenDistillationFactory{,.lean}, excluding /packages/ and /.lake/; regenerate with lean-spec/scripts/generate-lean-count.mjs — never hand-edit',
};

fs.writeFileSync(OUT, `${JSON.stringify(inventory, null, 2)}\n`);
console.log(`generate-lean-count: ${count} declarations (sorry hits in proof code: ${sorryCount}) → ${path.relative(LEAN_SPEC, OUT)}`);
if (sorryCount > 0) process.exit(2);
