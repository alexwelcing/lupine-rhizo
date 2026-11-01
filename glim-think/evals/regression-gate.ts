/**
 * Eval regression gate + Evolver auto-revert backstop.
 *
 * The Evolver (evals/evolver.ts) auto-merges prompt/criteria variants on
 * green. This is the safety net: it compares the two most recent
 * ModelScorecard claims and signals a regression if any model's mean pass-rate dropped
 * more than the threshold. With AUTO_REVERT=1, a detected regression also
 * reverts the most recent `evolver:auto` commit — but only if that commit
 * is confined to the Evolver's allowlist (glim-think/src/registry/), never
 * touching logic/infra. Fails closed.
 *
 * Usage:
 *   npx tsx evals/regression-gate.ts [--threshold 0.10] [--dry-run]
 *                                    [--seed-regression] [--min-samples 20]
 *
 * Exit 0 = comparable evidence passed; 1 = measured quality regression;
 * 2 = insufficient/invalid/unavailable evidence (never auto-reverted). The
 * caller keeps its advisory continue-on-error policy separately. A minimum
 * sample count defaults to 1 (nonempty measured evidence), preserving the
 * emitter's variable per-model sample sizes. Configure a higher policy floor
 * with --min-samples or EVAL_REGRESSION_MIN_SAMPLES; this is not a statistical
 * significance test. Unequal sample counts above the floor are allowed.
 *
 * Sources scorecards from the worker's public /feed/recent-claims (no new
 * endpoint, no secrets needed for the read).
 */
import { execSync } from "node:child_process";

const WORKER_URL =
  process.env.WORKER_URL ?? "https://glim-think-v1.aw-ab5.workers.dev";
function numericOption(flag: string, variable: string, fallback: number): number {
  const index = process.argv.indexOf(flag);
  return Number(index >= 0 ? process.argv[index + 1] : process.env[variable] ?? fallback);
}
const THRESHOLD = numericOption("--threshold", "EVAL_REGRESSION_THRESHOLD", 0.1);
const MIN_SAMPLES = numericOption("--min-samples", "EVAL_REGRESSION_MIN_SAMPLES", 1);
const DRY_RUN = process.argv.includes("--dry-run");
const SEED_REGRESSION = process.argv.includes("--seed-regression");
const AUTO_REVERT = process.env.AUTO_REVERT === "1";
const ALLOWLIST_PREFIX = "glim-think/src/registry/";

type Cell = { n: number; pass_rate: number };
type Scorecard = Record<string, Record<string, Cell>>;

function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

/** Preserve historical model-level scope: agent attributions, workers-ai and
 * unknown are optional diagnostics, not independent comparison populations. */
function optionalBucket(bucket: string): boolean {
  return bucket.includes("|") || bucket === "workers-ai" || bucket === "unknown";
}

function modelMeans(value: unknown, label: string): {
  means: Record<string, number>; evaluators: Record<string, string[]>; excluded: string[];
} {
  if (!object(value)) throw new Error(`${label}: malformed scorecard`);
  const means: Record<string, number> = Object.create(null);
  const evaluators: Record<string, string[]> = Object.create(null);
  const excluded: string[] = [];
  for (const [model, row] of Object.entries(value)) {
    if (optionalBucket(model)) { excluded.push(model); continue; }
    if (!model.trim() || !object(row) || Object.keys(row).length === 0)
      throw new Error(`${label}: empty/malformed model row ${model}`);
    const cells: Cell[] = [];
    for (const [name, cell] of Object.entries(row)) {
      if (!name.trim() || !object(cell) || typeof cell.n !== "number" || !Number.isSafeInteger(cell.n)
          || cell.n < MIN_SAMPLES || typeof cell.pass_rate !== "number" || !Number.isFinite(cell.pass_rate)
          || cell.pass_rate < 0 || cell.pass_rate > 1)
        throw new Error(`${label}: invalid or insufficient samples for ${model}/${name} (minimum ${MIN_SAMPLES})`);
      cells.push({ n: cell.n, pass_rate: cell.pass_rate });
    }
    means[model] = cells.reduce((sum, cell) => sum + cell.pass_rate, 0) / cells.length;
    evaluators[model] = Object.keys(row).sort();
  }
  if (Object.keys(means).length === 0) throw new Error(`${label}: no eligible model measurements`);
  return { means, evaluators, excluded };
}

function summary(lines: string[]): void {
  const text = lines.join("\n") + "\n";
  process.stdout.write(text);
  const f = process.env.GITHUB_STEP_SUMMARY;
  if (f) {
    try {
      // Append, don't clobber other steps' summaries.
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      require("node:fs").appendFileSync(f, text);
    } catch {
      /* non-fatal */
    }
  }
}

async function fetchScorecards(): Promise<
  { scorecard: unknown; created_at: string }[]
> {
  if (DRY_RUN) {
    const base: Scorecard = {
      "MiniMax-M2.7": { completeness: { n: 20, pass_rate: 0.82 } },
      "glm-5.1": { completeness: { n: 20, pass_rate: 0.79 } },
    };
    const newer: Scorecard = SEED_REGRESSION
      ? {
          "MiniMax-M2.7": { completeness: { n: 20, pass_rate: 0.6 } }, // -0.22
          "glm-5.1": { completeness: { n: 20, pass_rate: 0.8 } },
        }
      : {
          "MiniMax-M2.7": { completeness: { n: 20, pass_rate: 0.85 } },
          "glm-5.1": { completeness: { n: 20, pass_rate: 0.81 } },
        };
    return [
      { scorecard: newer, created_at: "2026-01-02T00:00:00Z" },
      { scorecard: base, created_at: "2026-01-01T00:00:00Z" },
    ];
  }
  const res = await fetch(`${WORKER_URL}/feed/recent-claims`, { signal: AbortSignal.timeout(15_000) });
  if (!res.ok) throw new Error(`/feed/recent-claims ${res.status}`);
  // Bound the read before JSON parsing, including chunked responses.
  const limit = 1024 * 1024;
  if (!res.body || Number(res.headers.get("content-length")) > limit) throw new Error("Scorecard response exceeds read limit");
  const reader = res.body.getReader(); const chunks: Uint8Array[] = []; let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > limit) { await reader.cancel(); throw new Error("Scorecard response exceeds read limit"); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  const body: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  const rows = Array.isArray(body) ? body : object(body) && Array.isArray(body.claims) ? body.claims : null;
  if (!rows || rows.length > 2000) throw new Error("Malformed or oversized claims response");
  const cards = rows.filter((row): row is Record<string, unknown> => object(row) && row.claim_type === "ModelScorecard");
  // Unknown dates cannot safely be ordered; do not silently select older evidence.
  for (const card of cards) {
    if (typeof card.created_at !== "string" || !Number.isFinite(Date.parse(card.created_at)))
      throw new Error("ModelScorecard missing a valid recorded date");
  }
  cards.sort((a, b) => Date.parse(b.created_at as string) - Date.parse(a.created_at as string));
  return cards.slice(0, 2).map((card) => {
    if (typeof card.claim_data !== "string") throw new Error("ModelScorecard missing claim data");
    const data: unknown = JSON.parse(card.claim_data);
    if (!object(data) || !("scorecard" in data)) throw new Error("ModelScorecard missing scorecard");
    return { scorecard: data.scorecard, created_at: card.created_at as string };
  });
}

function revertLastEvolverCommit(): void {
  const sha = execSync(`git log --grep "evolver:auto" -n1 --format=%H`)
    .toString()
    .trim();
  if (!sha) {
    summary(["⚠️ regression detected but no `evolver:auto` commit to revert."]);
    return;
  }
  const stat = execSync(`git show --stat --format= --name-only ${sha}`)
    .toString()
    .trim()
    .split("\n")
    .filter(Boolean);
  const outside = stat.filter((p) => !p.startsWith(ALLOWLIST_PREFIX));
  if (outside.length > 0) {
    summary([
      `🛑 Refusing to auto-revert ${sha.slice(0, 9)} — it touches paths`,
      `outside ${ALLOWLIST_PREFIX}: ${outside.join(", ")}.`,
      "Manual intervention required (fails closed).",
    ]);
    process.exit(1);
  }
  if (DRY_RUN) {
    summary([`(dry-run) would revert ${sha.slice(0, 9)} (registry-only ✓).`]);
    return;
  }
  execSync(`git revert --no-edit ${sha}`);
  execSync(`git push`);
  summary([`↩️ Auto-reverted \`evolver:auto\` commit ${sha.slice(0, 9)}.`]);
}

async function main(): Promise<void> {
  if (!Number.isFinite(THRESHOLD) || THRESHOLD < 0 || THRESHOLD > 1
      || !Number.isSafeInteger(MIN_SAMPLES) || MIN_SAMPLES < 1)
    throw new Error("Threshold must be in [0,1] and minimum samples a positive integer");
  const cards = await fetchScorecards();
  if (cards.length < 2) throw new Error(`Only ${cards.length} ModelScorecard(s); need two comparable measurements`);
  if (Date.parse(cards[0].created_at) <= Date.parse(cards[1].created_at))
    throw new Error("Scorecards need distinct ordered recorded dates");
  const current = modelMeans(cards[0].scorecard, "current");
  const previous = modelMeans(cards[1].scorecard, "previous");
  const cur = current.means; const prev = previous.means;
  const models = Object.keys(cur).sort(); const previousModels = Object.keys(prev).sort();
  if (JSON.stringify(models) !== JSON.stringify(previousModels))
    throw new Error("Model coverage changed (removed or new unbaselined models); comparison unavailable");
  for (const model of models) {
    if (JSON.stringify(current.evaluators[model]) !== JSON.stringify(previous.evaluators[model]))
      throw new Error(`Evaluator coverage changed for ${model}; comparison unavailable`);
  }
  const excluded = [...new Set([...current.excluded, ...previous.excluded])].sort();
  if (excluded.length) summary([`Excluded optional buckets (not assessed): ${excluded.join(", ")}`]);

  const regressions: string[] = [];
  const rows: string[] = ["| model | prev | cur | Δ |", "|---|---|---|---|"];
  for (const [model, curScore] of Object.entries(cur)) {
    const prevScore = prev[model];
    if (prevScore === undefined) continue;
    const delta = curScore - prevScore;
    rows.push(
      `| ${model} | ${prevScore.toFixed(3)} | ${curScore.toFixed(3)} | ${
        delta >= 0 ? "+" : ""
      }${delta.toFixed(3)} |`,
    );
    if (delta < -THRESHOLD)
      regressions.push(
        `${model}: ${prevScore.toFixed(3)} → ${curScore.toFixed(3)} (${delta.toFixed(3)})`,
      );
  }

  if (regressions.length === 0) {
    summary([
      "## ✅ Eval regression gate — PASS",
      "",
      `Threshold: ${THRESHOLD}; minimum samples per model/evaluator: ${MIN_SAMPLES}`,
      ...rows,
    ]);
    return;
  }

  summary([
    "## ❌ Eval regression gate — FAIL",
    "",
    `Threshold: ${THRESHOLD}. Regressed:`,
    ...regressions.map((r) => `- ${r}`),
    "",
    ...rows,
  ]);
  if (AUTO_REVERT) revertLastEvolverCommit();
  process.exit(1);
}

main().catch((e) => {
  // Missing measurement is distinct from quality regression and never reaches
  // AUTO_REVERT. Workflow continue-on-error remains the caller's advisory policy.
  summary([`## ⚠️ Eval regression gate — INSUFFICIENT: ${String(e)}`]);
  process.exit(2);
});
