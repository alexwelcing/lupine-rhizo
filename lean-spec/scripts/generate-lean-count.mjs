#!/usr/bin/env node
// Generates lean-spec/theorem-count.json from the active Lean source tree.
// This is the canonical inventory for README and downstream public surfaces.

import fs from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const LEAN_SPEC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TARGET = path.join(LEAN_SPEC, 'OpenDistillationFactory');
const OUT = path.join(LEAN_SPEC, 'theorem-count.json');
const PACKAGE_OUT = path.resolve(LEAN_SPEC, '..', 'python', 'lupine_distill', 'odf', 'theorem-count.json');
const DECL_RE = /^[ \t]*(?:@\[[^\n]*\][ \t]*)*(?:(?:private|protected|noncomputable|unsafe)[ \t]+)*(?:theorem|lemma)\b/gm;

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

function stripLeanTrivia(source) {
  let out = '';
  let blockDepth = 0;
  let inString = false;
  let inInterpolatedString = false;
  let interpolationDepth = 0;
  let inInterpolationString = false;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    const next = source[i + 1];
    if (blockDepth > 0) {
      if (ch === '/' && next === '-') { blockDepth += 1; out += '  '; i += 1; }
      else if (ch === '-' && next === '/') { blockDepth -= 1; out += '  '; i += 1; }
      else out += ch === '\n' ? '\n' : ' ';
    } else if (inInterpolatedString) {
      if (interpolationDepth === 0) {
        if (ch === '\\') { out += '  '; i += 1; }
        else if (ch === '"') { inInterpolatedString = false; out += ' '; }
        else if (ch === '{') { interpolationDepth = 1; out += ' '; }
        else out += ch === '\n' ? '\n' : ' ';
      } else if (inInterpolationString) {
        if (ch === '\\') { out += '  '; i += 1; }
        else if (ch === '"') { inInterpolationString = false; out += ' '; }
        else out += ch === '\n' ? '\n' : ' ';
      } else if (ch === '-' && next === '-') {
        const end = source.indexOf('\n', i);
        if (end === -1) { out += ' '.repeat(source.length - i); break; }
        out += ' '.repeat(end - i); i = end - 1;
      } else if (ch === '/' && next === '-') { blockDepth = 1; out += '  '; i += 1; }
      else if (ch === '"') { inInterpolationString = true; out += ' '; }
      else if (ch === '{') { interpolationDepth += 1; out += ' '; }
      else if (ch === '}') { interpolationDepth -= 1; out += ' '; }
      else out += ch;
    } else if (inString) {
      if (ch === '\\') { out += '  '; i += 1; }
      else if (ch === '"') { inString = false; out += ' '; }
      else out += ch === '\n' ? '\n' : ' ';
    } else if (ch === '-' && next === '-') {
      const end = source.indexOf('\n', i);
      if (end === -1) { out += ' '.repeat(source.length - i); break; }
      out += ' '.repeat(end - i);
      i = end - 1;
    } else if (ch === '/' && next === '-') {
      blockDepth = 1; out += '  '; i += 1;
    } else if (ch === '"') {
      if (source.slice(i - 2, i) === 's!') inInterpolatedString = true;
      else inString = true;
      out += ' ';
    } else out += ch;
  }
  if (blockDepth !== 0 || inString || inInterpolatedString || inInterpolationString) {
    throw new Error('unterminated Lean comment or string');
  }
  return out;
}

const parserProbe = stripLeanTrivia(`
theorem plain : True := by trivial
@[simp] theorem attributed : True := by trivial
private theorem hidden : True := by trivial
  protected lemma indented : True := by trivial
-- theorem commented : True := by sorry
/- lemma blocked : True := by sorry -/
def quoted := "sorry"
def interpolated := s!"{(sorry : Nat)}"
`);
if ([...parserProbe.matchAll(DECL_RE)].length !== 4 || [...parserProbe.matchAll(/\bsorry\b/g)].length !== 1) {
  throw new Error('Lean inventory parser self-check failed');
}

const files = leanFiles(TARGET);
if (!files.length) throw new Error(`no .lean files found under ${TARGET}`);

let count = 0;
let sorryCount = 0;
const sourceHash = createHash('sha256');
for (const file of files) {
  const source = fs.readFileSync(file, 'utf8');
  const relative = path.relative(LEAN_SPEC, file).split(path.sep).join('/');
  sourceHash.update(relative).update('\0').update(source).update('\0');
  const code = stripLeanTrivia(source);
  count += [...code.matchAll(DECL_RE)].length;
  sorryCount += [...code.matchAll(/\bsorry\b/g)].length;
}

const sourceSha256 = sourceHash.digest('hex');
let countedAt = '';
try {
  countedAt = execSync(
    'git log -1 --format=%cs -- OpenDistillationFactory OpenDistillationFactory.lean',
    { cwd: LEAN_SPEC, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] },
  ).trim();
} catch {
  const prior = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : {};
  if (prior.source_sha256 === sourceSha256) countedAt = prior.counted_at;
  else if (process.env.SOURCE_DATE_EPOCH) {
    countedAt = new Date(Number(process.env.SOURCE_DATE_EPOCH) * 1000).toISOString().slice(0, 10);
  }
}
if (!/^\d{4}-\d{2}-\d{2}$/.test(countedAt)) throw new Error('could not derive Lean source as-of date');
const inventory = {
  count,
  modules: files.length,
  zero_sorry: sorryCount === 0,
  counted_at: countedAt,
  source: 'lean-spec/OpenDistillationFactory{,.lean} (vendored packages excluded)',
  source_sha256: sourceSha256,
  rule: 'theorem/lemma declarations after stripping nested comments and strings; supports attributes, whitespace, and declaration modifiers; every active sorry token fails; regenerate with lean-spec/scripts/generate-lean-count.mjs — never hand-edit',
};

const encoded = `${JSON.stringify(inventory, null, 2)}\n`;
fs.writeFileSync(OUT, encoded);
fs.writeFileSync(PACKAGE_OUT, encoded);
console.log(`generate-lean-count: ${count} declarations (sorry hits in proof code: ${sorryCount}) → ${path.relative(LEAN_SPEC, OUT)}`);
if (sorryCount > 0) process.exit(2);
