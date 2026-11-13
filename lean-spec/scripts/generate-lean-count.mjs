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

// ── Breakdown ───────────────────────────────────────────────────────────────
// A declaration block runs from its theorem/lemma keyword to the line before the
// next non-blank line indented no deeper than the keyword (Lean convention:
// statements and proofs are indented under their declaration), and never past
// the start of the next counted declaration.
function declarationBlocks(code) {
  const blocks = [];
  const matches = [...code.matchAll(DECL_RE)];
  for (const [index, match] of matches.entries()) {
    const lineStart = code.lastIndexOf('\n', match.index) + 1;
    const indent = code.slice(lineStart).match(/^[ \t]*/)[0].length;
    const limit = index + 1 < matches.length ? matches[index + 1].index : code.length;
    let end = code.indexOf('\n', match.index);
    if (end === -1 || end > limit) end = limit;
    while (end < limit) {
      let next = code.indexOf('\n', end + 1);
      if (next === -1) next = code.length;
      const line = code.slice(end + 1, next);
      if (line.trim() && line.match(/^[ \t]*/)[0].length <= indent) break;
      end = next;
    }
    blocks.push(code.slice(match.index, Math.min(end, limit)).replace(/\s+/g, ' ').trim());
  }
  return blocks;
}

// The whole proof is exactly one argument-free tactic (`:= by decide`,
// `:= by native_decide`, `:= by rfl`, `:= by norm_num`) or the term `:= rfl`.
// The proof starts at the first `:= by`; a term proof counts only when the
// block has no `by`, `calc` or `where` (so a calc chain ending in
// `:= by norm_num` or `:= rfl` is not a single-tactic check).
const SINGLE_TACTICS = ['decide', 'native_decide', 'rfl', 'norm_num'];
function singleTactic(block) {
  const tactic = block.match(/^.*?:=\s*by\s+(.*)$/);
  if (tactic) return SINGLE_TACTICS.includes(tactic[1]) ? tactic[1] : null;
  if (/\b(?:by|calc|where)\b/.test(block)) return null;
  return /:=\s*rfl$/.test(block) ? 'rfl' : null;
}

// Grades assigned by hand in the correction-theory registry. Parsed from the
// trivia-stripped source; cross-checked against its `#guard` length lock.
const REGISTRY = path.join(TARGET, 'UniversalCorrection', 'Empirical', 'Registry.lean');
function registryGrades() {
  if (!fs.existsSync(REGISTRY)) return null;
  const code = stripLeanTrivia(fs.readFileSync(REGISTRY, 'utf8'));
  const gradeDecl = code.match(/inductive\s+EpistemicGrade\s+where([\s\S]*?)deriving/);
  const head = code.match(/def\s+theoremInventory\s*:\s*List\s+TheoremInventoryEntry\s*:=\s*\[/);
  if (!gradeDecl || !head) return null;
  const grades = [...gradeDecl[1].matchAll(/\|\s*([A-Za-z_][A-Za-z0-9_]*)/g)].map((m) => m[1]);
  let depth = 1;
  let i = head.index + head[0].length;
  const start = i;
  for (; i < code.length && depth > 0; i += 1) {
    if (code[i] === '[') depth += 1;
    else if (code[i] === ']') depth -= 1;
  }
  if (depth !== 0 || !grades.length) return null;
  const list = code.slice(start, i - 1);
  const entries = [...list.matchAll(/\{[^{}]*\}/g)].map((m) => m[0]);
  const byGrade = Object.fromEntries(grades.map((grade) => [grade, 0]));
  for (const entry of entries) {
    const assigned = [...entry.matchAll(/epistemicGrade\s*:=\s*\.([A-Za-z_][A-Za-z0-9_]*)/g)];
    if (assigned.length !== 1 || !(assigned[0][1] in byGrade)) {
      throw new Error(`Registry.lean: cannot read the epistemicGrade of entry ${entry.slice(0, 80)}`);
    }
    byGrade[assigned[0][1]] += 1;
  }
  const lock = code.match(/#guard\s+theoremInventory\.length\s*==\s*(\d+)/);
  if (lock && Number(lock[1]) !== entries.length) {
    throw new Error(`Registry.lean: parsed ${entries.length} inventory entries but its #guard locks ${lock[1]}`);
  }
  return {
    source: path.relative(path.resolve(LEAN_SPEC, '..'), REGISTRY).split(path.sep).join('/'),
    scope: 'EpistemicGrade labels assigned by hand in theoremInventory; covers the correction-theory surface listed there, not every counted declaration',
    entries: entries.length,
    by_grade: byGrade,
  };
}

const files = leanFiles(TARGET);
if (!files.length) throw new Error(`no .lean files found under ${TARGET}`);

let count = 0;
let sorryCount = 0;
let nativeDecideUses = 0;
let nativeDecideDeclarations = 0;
const singleTacticCounts = Object.fromEntries(SINGLE_TACTICS.map((tactic) => [tactic, 0]));
const sourceHash = createHash('sha256');
for (const file of files) {
  const source = fs.readFileSync(file, 'utf8');
  const relative = path.relative(LEAN_SPEC, file).split(path.sep).join('/');
  sourceHash.update(relative).update('\0').update(source).update('\0');
  const code = stripLeanTrivia(source);
  count += [...code.matchAll(DECL_RE)].length;
  sorryCount += [...code.matchAll(/\bsorry\b/g)].length;
  nativeDecideUses += [...code.matchAll(/\bnative_decide\b/g)].length;
  for (const block of declarationBlocks(code)) {
    if (/\bnative_decide\b/.test(block)) nativeDecideDeclarations += 1;
    const tactic = singleTactic(block);
    if (tactic) singleTacticCounts[tactic] += 1;
  }
}
const singleTacticTotal = Object.values(singleTacticCounts).reduce((sum, n) => sum + n, 0);

const tacticProbe = declarationBlocks(stripLeanTrivia(`
theorem a : 1 = 1 := by decide
theorem b : 1 = 1 := by
  native_decide
theorem c : 1 = 1 := rfl
theorem d : 1 = 1 := by simp [foo]
theorem e : 1 = 1 := by
  norm_num
  rfl
  protected lemma f : 1 = 1 := by norm_num -- trailing comment
def g := 0
theorem h : 1 = 1 := by
  calc 1 = 1 := by rfl
    _ = 1 := by norm_num
theorem i : 1 = 1 := calc 1 = 1 := rfl
`)).map(singleTactic);
if (JSON.stringify(tacticProbe) !== JSON.stringify(['decide', 'native_decide', 'rfl', null, null, 'norm_num', null, null])) {
  throw new Error(`Lean breakdown parser self-check failed: ${JSON.stringify(tacticProbe)}`);
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
  breakdown: {
    rule: 'computed from the same stripped source as count. single_tactic_checks: counted declarations whose whole proof is one argument-free decide, native_decide, rfl or norm_num tactic, or the term rfl. native_decide: active native_decide tokens, and counted declarations whose proof uses one (it trusts the compiled evaluator). registry_grades: hand-assigned labels parsed from Registry.lean, null when it cannot be parsed. Lean checks arithmetic and stated inequalities; none of these numbers measures physics.',
    single_tactic_checks: { total: singleTacticTotal, by_tactic: singleTacticCounts },
    native_decide: { uses: nativeDecideUses, declarations: nativeDecideDeclarations },
    registry_grades: registryGrades(),
  },
};

const encoded = `${JSON.stringify(inventory, null, 2)}\n`;
fs.writeFileSync(OUT, encoded);
fs.writeFileSync(PACKAGE_OUT, encoded);
console.log(`generate-lean-count: ${count} declarations (sorry hits in proof code: ${sorryCount}) → ${path.relative(LEAN_SPEC, OUT)}`);
if (sorryCount > 0) process.exit(2);
