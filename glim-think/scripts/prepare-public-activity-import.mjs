#!/usr/bin/env node
/** Offline only: validate a reviewed public export and prepare D1 inserts. */
import { build } from "esbuild";
import { createHash } from "node:crypto";
import { readFile, stat, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

let contract;
async function runtimeContract() {
  if (!contract) {
    const bundle = await build({ entryPoints: [fileURLToPath(new URL("../src/workspace/researchActivityContracts.ts", import.meta.url))],
      bundle: true, write: false, format: "esm", platform: "node", target: "node22", logLevel: "silent" });
    contract = import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].contents).toString("base64")}`);
  }
  return contract;
}

const INSERT = "INSERT INTO public_research_activity (id, activity_id, observed_at, reviewed_at, supersedes_id, payload_sha256, payload) VALUES (?, ?, ?, ?, ?, ?, ?)";
const sha = value => createHash("sha256").update(value).digest("hex");
// Hex UTF-8 literals cannot terminate or inject a SQL statement. D1 API callers
// can instead submit the original sql/params pairs in the JSON preparation.
const literal = value => value === null ? "NULL" : `CAST(X'${Buffer.from(value, "utf8").toString("hex")}' AS TEXT)`;

export async function preparePublicActivityImport(input) {
  const { decodePublicResearchActivity, PUBLIC_ACTIVITY_FEED_SCHEMA, PUBLIC_ACTIVITY_MAX_LIMIT } = await runtimeContract();
  if (!input || typeof input !== "object" || Array.isArray(input) ||
      Object.keys(input).sort().join(",") !== "items,schema,truncated" ||
      input.schema !== PUBLIC_ACTIVITY_FEED_SCHEMA || input.truncated !== false ||
      !Array.isArray(input.items) || input.items.length < 1 || input.items.length > PUBLIC_ACTIVITY_MAX_LIMIT) throw new Error("Invalid complete public feed");
  const records = input.items.map(item => decodePublicResearchActivity(item));
  if (new Set(records.map(item => item.id)).size !== records.length) throw new Error("Duplicate record IDs");
  const byId = new Map(records.map(item => [item.id, item]));
  // Validate any history carried within this batch before producing output.
  const predecessors = new Set();
  for (const item of records) {
    if (item.supersedes === null) continue;
    if (predecessors.has(item.supersedes)) throw new Error("Forked public history");
    predecessors.add(item.supersedes);
    const previous = byId.get(item.supersedes);
    if (!previous) continue; // Existing ancestry is verified by database triggers.
    if (item.activityId !== previous.activityId || item.evidenceKind !== previous.evidenceKind ||
        item.observedAt < previous.observedAt || item.reviewedAt <= previous.reviewedAt) throw new Error("Invalid public ancestry");
    if (["completed", "failed"].includes(previous.state)) {
      if (item.state !== previous.state || item.correctionReason === null) throw new Error("Invalid terminal correction");
    } else if (previous.state !== "planned" && item.state === "planned") throw new Error("Invalid state rewind");
  }
  const roots = records.filter(item => item.supersedes === null).map(item => item.activityId);
  if (new Set(roots).size !== roots.length) throw new Error("Duplicate activity roots");
  records.sort((a, b) => a.reviewedAt.localeCompare(b.reviewedAt) || a.id.localeCompare(b.id));
  const statements = records.map(record => {
    const payload = JSON.stringify(record);
    return { sql: INSERT, params: [record.id, record.activityId, record.observedAt, record.reviewedAt, record.supersedes, sha(payload), payload] };
  });
  const sql = ["-- Reviewed public activity only. Apply migration 0021_public_research_activity.sql first.",
    "-- Immutable and ancestry guards run in D1; identical IDs are idempotent.",
    ...statements.map(({ sql, params }) => { let i = 0; return sql.replace(/\?/g, () => literal(params[i++])) + ";"; }), ""].join("\n");
  return { schema: "lupine.public_activity_import_preparation.v1", records: records.length,
    migration: "glim-think/migrations/0021_public_research_activity.sql", statements, sql };
}

async function main() {
  const args = process.argv.slice(2);
  const inputPath = args.shift();
  const options = {};
  while (args.length) {
    const option = args.shift();
    if (option === "--check") { options.check = true; continue; }
    if (!["--sql", "--json"].includes(option) || !args.length || options[option]) throw new Error("Invalid arguments");
    options[option] = args.shift();
  }
  if (!inputPath || (!options.check && !options["--sql"] && !options["--json"])) throw new Error("Use INPUT --check or INPUT --sql OUTPUT [--json OUTPUT]");
  if ((await stat(inputPath)).size > 1_048_576) throw new Error("Export too large");
  const inputBytes = await readFile(inputPath);
  const input = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(inputBytes));
  const prepared = await preparePublicActivityImport(input);
  for (const key of ["--sql", "--json"]) if (options[key]) {
    if (resolve(options[key]) === resolve(inputPath)) throw new Error("Do not overwrite reviewed input");
    const value = key === "--sql" ? prepared.sql : JSON.stringify({ ...prepared, sql: undefined, inputSha256: sha(inputBytes) }, null, 2) + "\n";
    await writeFile(options[key], value, { encoding: "utf8", mode: 0o600, flag: "wx" });
  }
  console.log(JSON.stringify({ status: "validated_reviewed_public_export", records: prepared.records,
    inputSha256: sha(inputBytes), migration: prepared.migration, cloudWrites: 0 }));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(() => { console.error("Public activity preparation failed: check the strict reviewed export, arguments, and unused output paths. No cloud write was attempted."); process.exitCode = 1; });
}
