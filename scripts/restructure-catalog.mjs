#!/usr/bin/env node
// Restructure the library catalog per docs/plans/library-restructure-2026-06-26.md
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const target = path.join(__dirname, 'library-content-catalog.js');

// Import current catalog (we'll rewrite the file, but read the old object in memory)
const { CATALOG } = await import(target + '?cachebust=' + Date.now());

const categoryMap = {
  // changelog stays
  // conjectures stays
  // formalization stays
  // validation stays
  theory: 'methods',
  uq: 'methods',
  meta: 'operations',
  decisions: 'operations',
  partnerships: 'operations',
  ecosystem: 'references',
  reviews: 'references',
  references: 'references',
  foundations: 'foundations',
  changelog: 'changelog',
};

const articleCategoryOverrides = {
  // orientation overlap fixes
  'public-approach': 'foundations',
  // methods migration
  methodology: 'methods',
};

const groups = {
  hypotheses: [
    'conjecture-ledger',
    'hyp-hyper-ribbon-universality',
    'hyp-hyper-ribbon-mlip-transfer',
    'hyp-cross-mlip-orthogonal-errors',
    'hyp-au-mlip-escape',
    'hyp-fe-persistent-outlier',
    'hyp-dband-correlation',
    'hyp-meam-intrinsic-2d',
    'hyp-bccfcc-causal-shield',
    'formal-proof-ledger',
  ],
  'mlip-flywheel': [
    'mlip-cloud-baseline-distill',
    'mlip-ni-paired-accuracy-live',
    'mlip-ni-zero-point-policy-replay',
    'mlip-mptrj-broad-dft-canary',
    'projection-law-round2-results',
    'layer2-research-paper',
  ],
  extraction: [
    'extraction-complete',
    'extraction-report',
    'extraction-notes',
  ],
};

const groupForArticle = Object.fromEntries(
  Object.entries(groups).flatMap(([group, ids]) => ids.map((id) => [id, group])),
);

const featuredPlan = {
  'projection-law-round2-results': 'anchor',
  'layer2-research-paper': 'newest',
  'born-screening-re-audit': 'counter',
  'working-papers': 'replication',
};

const titleUpdates = {
  'operating-system': {
    title: 'Lupine Operating System',
    subtitle: 'How the research loop fits together: agenda, ledger, evidence, and correction.',
  },
  'resource-fabric': {
    title: 'Infrastructure Fabric',
    subtitle: 'The compute and storage fabric that reproduces every Lupine result.',
  },
};

const newCategories = [
  {
    id: 'foundations',
    label: { en: 'Foundations & Vision', zh: '基础与愿景' },
    blurb: { en: 'Orientation, shared vocabulary, data provenance, and the research agenda. Start here if you are new.', zh: '方向、共享词汇、数据来源与研究议程。如果你是新来的，从这里开始。' },
  },
  {
    id: 'conjectures',
    label: { en: 'Conjectures & Proofs', zh: '猜想与证明' },
    blurb: { en: 'Every claim we have tested, its lifecycle status, and the evidence behind it. The hypothesis ledger.', zh: '我们测试过的每个声明、其生命周期状态及其背后的证据。假设台账。' },
  },
  {
    id: 'methods',
    label: { en: 'Methods & Theory', zh: '方法与理论' },
    blurb: { en: 'How we measure, bound, and reason about potential error — from sloppy-model geometry to Bayesian active learning.', zh: '我们如何测量、界定和推理势函数误差 — 从 sloppy-model 几何到贝叶斯主动学习。' },
  },
  {
    id: 'validation',
    label: { en: 'Validation & Evidence', zh: '验证与证据' },
    blurb: { en: 'Benchmarks, live-lab results, and the MLIP flywheel evidence chain.', zh: '基准测试、实时实验室结果以及 MLIP 飞轮证据链。' },
  },
  {
    id: 'formalization',
    label: { en: 'Formalization', zh: '形式化' },
    blurb: { en: 'Lean-backed theorem proofs, build-locking contracts, and the formal proof ledger.', zh: 'Lean 支持的定理证明、构建锁定契约以及形式化证明台账。' },
  },
  {
    id: 'changelog',
    label: { en: 'Progress Log', zh: '进展日志' },
    blurb: { en: 'What changed, why, and what is next. The narrative spine of the project.', zh: '改变了什么、为什么以及下一步是什么。项目的叙事主线。' },
  },
  {
    id: 'references',
    label: { en: 'Reviews & References', zh: '评议与参考文献' },
    blurb: { en: 'The literature we build on, the funding context, and the adversarial reviews our claims passed before going public.', zh: '我们所依据的文献、资金背景以及我们的声明在公开前通过的对抗性评议。' },
  },
  {
    id: 'operations',
    label: { en: 'Build & Operations', zh: '构建与运营' },
    blurb: { en: 'How this library was built and how to reproduce every result. Extraction logs, ADRs, and operational fabric.', zh: '该图书馆是如何构建的，以及如何复现每个结果。提取日志、架构决策记录和运营结构。' },
  },
];

const statusGloss = {
  proposed: { en: 'A conjecture we intend to test; no evidence yet.', zh: '我们打算测试的猜想；目前尚无证据。' },
  supported: { en: 'Evidence-backed but not formally proven.', zh: '有证据支持但尚未形式化证明。' },
  open: { en: 'Under active investigation; could go either way.', zh: '正在积极调查中；结果尚不确定。' },
  refuted: { en: 'We tested it and falsified it ourselves.', zh: '我们已测试并自行证伪。' },
  'self-corrected': { en: 'We published it, then found a confounder and retracted the strong form.', zh: '我们发表后发现了混淆因素，并撤回了较强形式。' },
  proven: { en: 'Backed by a machine-checked Lean proof.', zh: '由机器检查的 Lean 证明支持。' },
  live: { en: 'Continuously refreshed evidence (live-lab canary).', zh: '持续刷新的证据（实时实验室金丝雀）。' },
};

const journeys = [
  {
    id: 'new-here',
    label: { en: "I'm new here", zh: '初次访问' },
    description: { en: 'Start with the big picture.', zh: '从全局开始。' },
    path: ['what-is-an-interatomic-potential', 'readme', 'glossary', 'error-geometry-objects', 'conjecture-ledger', 'hyp-hyper-ribbon-universality', 'mlip-cloud-baseline-distill', 'research-evolution'],
  },
  {
    id: 'materials-scientist',
    label: { en: 'Show me the physics', zh: '展示物理' },
    description: { en: 'Evaluate the claims against the evidence.', zh: '根据证据评估声明。' },
    path: ['data-provenance', 'sloppy-models', 'error-geometry-objects', 'hyp-hyper-ribbon-universality', 'hyp-cross-mlip-orthogonal-errors', 'projection-law-round2-results', 'layer2-research-paper', 'academic-review-projection-law', 'references'],
  },
  {
    id: 'mlip-builder',
    label: { en: 'I build MLIPs', zh: '我构建 MLIP' },
    description: { en: 'Understand the flywheel, the operator, and how to reproduce results.', zh: '理解飞轮、算子以及如何复现结果。' },
    path: ['working-papers', 'mlip-cloud-baseline-distill', 'mlip-ni-paired-accuracy-live', 'mlip-mptrj-broad-dft-canary', 'projection-law-round2-preregistration', 'projection-law-round2-results', 'bayesian-active-learning', 'gnn-error-prediction', 'reproduce'],
  },
  {
    id: 'funder-reviewer',
    label: { en: 'Is this rigorous?', zh: '这是否严谨？' },
    description: { en: 'Assess epistemic discipline and formal backing.', zh: '评估认识论纪律和形式化支持。' },
    path: ['internal-science-program', 'methodology', 'conjecture-ledger', 'hyp-dband-correlation', 'hyp-bccfcc-causal-shield', 'formal-proof-ledger', 'formal-audit', 'funding-landscape', 'phoenix-observability'],
  },
];

const newEntries = [
  {
    id: 'what-is-an-interatomic-potential',
    source: 'docs/what-is-an-interatomic-potential.md',
    title: 'What Is an Interatomic Potential?',
    subtitle: 'A five-minute primer on the models that let computers simulate atoms, and why they are necessary but wrong in structured ways.',
    category: 'foundations',
    tags: ['primer', 'mlip', 'basics'],
  },
  {
    id: 'projection-law-in-plain-language',
    source: 'docs/projection-law-in-plain-language.md',
    title: 'The Projection Law in Plain Language',
    subtitle: 'A 300-word explanation of what the Lupine correction operator does for a materials scientist.',
    category: 'validation',
    tags: ['primer', 'projection-law', 'mlip'],
    group: 'mlip-flywheel',
  },
];

function migrateEntry(entry) {
  const next = { ...entry };
  const override = articleCategoryOverrides[entry.id];
  next.category = override || categoryMap[entry.category] || entry.category;

  // group assignment
  if (groupForArticle[entry.id]) {
    next.group = groupForArticle[entry.id];
  }

  // featured governance
  if (featuredPlan[entry.id]) {
    next.featured = true;
    next.featuredRole = featuredPlan[entry.id];
  } else if (entry.featured) {
    delete next.featured;
    delete next.featuredRole;
  }

  // title/subtitle updates
  if (titleUpdates[entry.id]) {
    next.title = titleUpdates[entry.id].title;
    next.subtitle = titleUpdates[entry.id].subtitle;
  }

  return next;
}

const migratedEntries = CATALOG.entries.map(migrateEntry);

const nextCatalog = {
  statuses: Object.fromEntries(
    Object.entries(CATALOG.statuses).map(([k, v]) => [k, { ...v, gloss: statusGloss[k] }]),
  ),
  categories: newCategories,
  languages: CATALOG.languages,
  journeys,
  entries: [...migratedEntries, ...newEntries],
};

const output = `// Curated catalog. Order here = order on the shelf.
// Restructured 2026-06-26 per docs/plans/library-restructure-2026-06-26.md
// 8 categories, ${nextCatalog.entries.length} entries, journeys, featured roles, and group ribbons.

export const CATALOG = ${JSON.stringify(nextCatalog, null, 2)};
`;

fs.writeFileSync(target, output);
console.log(`Wrote restructured catalog to ${target}`);
console.log(`Categories: ${nextCatalog.categories.length}, Entries: ${nextCatalog.entries.length}`);

// Print counts by category
const counts = {};
for (const e of nextCatalog.entries) {
  counts[e.category] = (counts[e.category] || 0) + 1;
}
for (const c of nextCatalog.categories) {
  console.log(`  ${c.id}: ${counts[c.id] || 0}`);
}
