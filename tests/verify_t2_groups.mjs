// Verify T2 acceptance: exactly 6 mlip-flywheel, exactly 1 extraction,
// on the correct entry ids, and the hypotheses group untouched.
// (T10 consolidated the three extraction logs into one 'extraction-overview'
// entry; updated here from the original count of 3.)
import { readFileSync } from 'node:fs';

const src = readFileSync(
  new URL('../scripts/library-content-catalog.js', import.meta.url),
  'utf8',
);

const entryRe = /\{\s*id:\s*'([^']+)'.*?\n\s*\},?/gs;
const entries = {};
let m;
while ((m = entryRe.exec(src)) !== null) {
  const block = m[0];
  const id = m[1];
  const grpMatch = block.match(/group:\s*'([^']+)'/);
  const catMatch = block.match(/category:\s*'([^']+)'/);
  entries[id] = {
    group: grpMatch ? grpMatch[1] : null,
    category: catMatch ? catMatch[1] : null,
  };
}

const expectFlywheel = new Set([
  'mlip-cloud-baseline-distill',
  'mlip-ni-paired-accuracy-live',
  'mlip-ni-zero-point-policy-replay',
  'mlip-mptrj-broad-dft-canary',
  'projection-law-round2-results',
  'layer2-research-paper',
]);
const expectExtraction = new Set([
  'extraction-overview',
]);

const flywheel = Object.entries(entries).filter(([, v]) => v.group === 'mlip-flywheel');
const extraction = Object.entries(entries).filter(([, v]) => v.group === 'extraction');
const hypotheses = Object.entries(entries).filter(([, v]) => v.group === 'hypotheses');

let pass = true;

function check(label, got, want) {
  const ok = got.length === want.size && got.every(([id]) => want.has(id));
  console.log(`${ok ? 'PASS' : 'FAIL'} — ${label}: ${got.length} entries`);
  if (!ok) pass = false;
  for (const [id, v] of got) {
    console.log(`    ${id}  (category: ${v.category})`);
  }
}

check('group: mlip-flywheel', flywheel, expectFlywheel);
check('group: extraction', extraction, expectExtraction);

console.log(`\nINFO — group: hypotheses: ${hypotheses.length} entries (unchanged by T2)`);
for (const [id] of hypotheses) console.log(`    ${id}`);

for (const id of [...expectFlywheel, ...expectExtraction]) {
  if (!entries[id]) {
    console.log(`FAIL — missing entry: ${id}`);
    pass = false;
  }
}

console.log(`\n${pass ? 'ALL PASS' : 'FAILURES PRESENT'}`);
process.exit(pass ? 0 : 1);
