#!/usr/bin/env node
/** Bounded, opt-in Clef classification only; official cf CLI owns authentication. */
import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

export const MODEL = "@cf/cloudflare/clef-flash";
const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const DATASET = resolve(ROOT, "evals/__datasets__/clef-routing.json");
const MAX_DATASET_BYTES = 131072;
const MAX_RESPONSE_BYTES = 131072;
const hash = value => createHash("sha256").update(value).digest("hex");
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const probability = value => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
const safeId = value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$/.test(value);
const now = () => new Date().toISOString();

export function readDataset(raw, selected = []) {
  if (Buffer.byteLength(raw) > MAX_DATASET_BYTES) throw new Error("dataset_exceeds_limit");
  const data = JSON.parse(raw);
  if (!object(data) || data.schemaVersion !== 1 || !safeId(data.name)
      || !Array.isArray(data.cases) || !data.cases.length || data.cases.length > 24)
    throw new Error("invalid_dataset");
  const seen = new Set();
  for (const entry of data.cases) {
    if (!object(entry) || !safeId(entry.id) || seen.has(entry.id)
        || typeof entry.prompt !== "string" || !entry.prompt.trim() || entry.prompt.length > 2000
        || !["fast", "deep", "code", "research"].includes(entry.expectedTask))
      throw new Error("invalid_case");
    seen.add(entry.id);
    for (const key of ["expectedEvidence", "expectedWorkflow"])
      if (entry[key] !== undefined && !safeId(entry[key])) throw new Error("invalid_expected_answer");
  }
  if (new Set(selected).size !== selected.length || selected.some(id => !seen.has(id)))
    throw new Error("invalid_case_selection");
  return { ...data, cases: data.cases.filter(entry => !selected.length || selected.includes(entry.id)) };
}

export function expectedAnswers(entry) {
  return { route: entry.expectedTask,
    ...(entry.expectedEvidence === undefined ? {} : { evidence: entry.expectedEvidence }),
    ...(entry.expectedWorkflow === undefined ? {} : { workflow: entry.expectedWorkflow }) };
}

export function scoreResponse(response, request, expected, thresholds = { confidence: 0.7, margin: 0.15 }) {
  if (object(response) && response.success === true && object(response.result)) response = response.result;
  if (!object(response) || ![MODEL, "clef-flash"].includes(response.model)
      || !object(response.answers) || !object(response.usage)) throw new Error("invalid_response");
  const questionIds = Object.keys(request.questions);
  if (Object.keys(response.answers).length !== questionIds.length) throw new Error("invalid_answers");
  const answers = {};
  for (const id of questionIds) {
    const question = request.questions[id], answer = response.answers[id];
    const options = Object.keys(question.criteria);
    if (question.type !== "choice" || !object(answer) || answer.type !== "choice"
        || !options.includes(answer.choice) || !probability(answer.confidence)
        || !object(answer.probabilities) || Object.keys(answer.probabilities).length !== options.length
        || options.some(option => !probability(answer.probabilities[option]))) throw new Error("invalid_choice");
    const values = options.map(option => answer.probabilities[option]);
    if (Math.abs(values.reduce((sum, value) => sum + value, 0) - 1) > 0.001) throw new Error("invalid_distribution");
    const margin = answer.probabilities[answer.choice]
      - Math.max(...options.filter(option => option !== answer.choice).map(option => answer.probabilities[option]));
    if (margin < 0) throw new Error("choice_not_maximum");
    const accepted = answer.confidence >= thresholds.confidence && margin >= thresholds.margin && margin > 0;
    answers[id] = { choice: answer.choice, confidence: answer.confidence, margin,
      accepted, fallback_reason: answer.confidence < thresholds.confidence ? "low-confidence"
        : !accepted ? "ambiguous-task" : null,
      expected: expected[id] ?? null, correct: expected[id] === undefined ? null : answer.choice === expected[id] };
  }
  for (const key of ["input_tokens", "output_tokens"])
    if (!Number.isSafeInteger(response.usage[key]) || response.usage[key] < 0) throw new Error("invalid_usage");
  return { classifier_model: response.model,
    provider_request_id: [response.request_id, response.id].find(safeId) ?? null,
    answers, usage: { input_tokens: response.usage.input_tokens, output_tokens: response.usage.output_tokens } };
}

export function summarize(cases) {
  const completed = cases.filter(entry => entry.status === "completed");
  const byQuestion = {};
  for (const entry of completed) for (const [id, answer] of Object.entries(entry.answers)) {
    const stats = byQuestion[id] ??= { observed: 0, labeled: 0, correct: 0, accepted: 0,
      accepted_labeled: 0, accepted_correct: 0, confusion: {} };
    stats.observed++;
    if (answer.accepted) stats.accepted++;
    if (answer.expected !== null) {
      stats.labeled++;
      if (answer.correct) stats.correct++;
      if (answer.accepted) {
        stats.accepted_labeled++;
        if (answer.correct) stats.accepted_correct++;
      }
      const row = stats.confusion[answer.expected] ??= {};
      row[answer.choice] = (row[answer.choice] ?? 0) + 1;
    }
  }
  for (const stats of Object.values(byQuestion)) {
    stats.accuracy = stats.labeled ? stats.correct / stats.labeled : null;
    stats.coverage = stats.observed ? stats.accepted / stats.observed : null;
    stats.accepted_accuracy = stats.accepted_labeled ? stats.accepted_correct / stats.accepted_labeled : null;
  }
  const latency = completed.map(entry => entry.latency_ms).sort((a, b) => a - b);
  return { selected: cases.length, attempted: cases.filter(entry => entry.attempted).length,
    completed: completed.length, failed: cases.filter(entry => entry.attempted && entry.status !== "completed").length,
    not_started: cases.filter(entry => !entry.attempted).length, by_question: byQuestion,
    end_to_end_latency_ms: { p50: latency.length ? latency[Math.ceil(latency.length * .5) - 1] : null,
      p95: latency.length ? latency[Math.ceil(latency.length * .95) - 1] : null },
    usage: completed.reduce((sum, entry) => ({ input_tokens: sum.input_tokens + entry.usage.input_tokens,
      output_tokens: sum.output_tokens + entry.usage.output_tokens }), { input_tokens: 0, output_tokens: 0 }) };
}

/** Keep OAuth ownership in cf. Do not inherit tokens, API redirects, debug hooks or project .env. */
export function cfEnvironment(accountId, original = process.env) {
  const env = {};
  for (const key of ["HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "USER", "LOGNAME", "XDG_CONFIG_HOME", "APPDATA"])
    if (original[key] !== undefined) env[key] = original[key];
  return { ...env, CLOUDFLARE_ACCOUNT_ID: accountId, CF_QUIET: "1", CF_SEND_TELEMETRY: "false",
    WRANGLER_SEND_METRICS: "false", DO_NOT_TRACK: "1", NO_COLOR: "1", CF_NO_OSC_PROGRESS: "1", CI: "1" };
}

/** One process, no retries; bytes remain in memory and never reach the receipts. */
export function boundedCommand(executable, args, { cwd, env, timeoutMs, outputLimit = MAX_RESPONSE_BYTES }) {
  return new Promise(resolveResult => {
    const started = performance.now();
    let child, stopReason = null, timer, killTimer, stdoutBytes = 0, stderrBytes = 0;
    const stdout = [];
    const signalGroup = signal => {
      if (!child?.pid) return;
      try { process.kill(-child.pid, signal); } catch { /* Already exited. */ }
    };
    const stop = reason => {
      if (stopReason) return;
      stopReason = reason;
      signalGroup("SIGTERM");
      killTimer = setTimeout(() => signalGroup("SIGKILL"), 500);
    };
    const interrupt = () => stop("interrupted");
    const finish = (code, signal) => {
      clearTimeout(timer); clearTimeout(killTimer);
      signalGroup("SIGKILL");
      process.off("SIGINT", interrupt); process.off("SIGTERM", interrupt);
      resolveResult({ stdout: Buffer.concat(stdout), stdout_bytes: stdoutBytes, stderr_bytes: stderrBytes,
        returncode: code, signal, stop_reason: stopReason, latency_ms: Math.round(performance.now() - started) });
    };
    try {
      child = spawn(executable, args, { cwd, env, detached: true, stdio: ["ignore", "pipe", "pipe"] });
    } catch { finish(null, null); return; }
    process.once("SIGINT", interrupt); process.once("SIGTERM", interrupt);
    child.once("error", () => { stopReason = "spawn_failed"; });
    child.stdout.on("data", chunk => {
      stdoutBytes += chunk.length;
      if (stdoutBytes + stderrBytes <= outputLimit) stdout.push(chunk);
      else stop("output_limit");
    });
    child.stderr.on("data", chunk => {
      stderrBytes += chunk.length;
      if (stdoutBytes + stderrBytes > outputLimit) stop("output_limit");
    });
    child.once("close", finish);
    timer = setTimeout(() => stop("timeout"), timeoutMs);
  });
}

async function loadBuilder() {
  const { build } = await import("esbuild");
  const compiled = await build({ entryPoints: [resolve(ROOT, "src/agents/clefRouter.ts")], bundle: true,
    write: false, platform: "node", format: "esm", target: "node22", logLevel: "silent" });
  const bytes = compiled.outputFiles[0].contents;
  const router = await import(`data:text/javascript;base64,${Buffer.from(bytes).toString("base64")}`);
  if (typeof router.buildClefRequest !== "function") throw new Error("shared_clef_request_builder_unavailable");
  return { builder: router.buildClefRequest, router_sha256: hash(bytes) };
}

function checkedRequest(builder, entry) {
  const request = builder(entry.prompt);
  if (!object(request) || request.model !== "clef-flash" || !object(request.questions)
      || !object(request.state) || request.state.user_request !== entry.prompt.trim()
      || Object.keys(request).sort().join() !== "model,questions,state"
      || Object.keys(request.state).join() !== "user_request"
      || !request.questions.route || Object.keys(request.questions).length > 3)
    throw new Error("unexpected_classifier_request");
  for (const [id, question] of Object.entries(request.questions)) {
    if (!["route", "evidence", "workflow"].includes(id) || question.type !== "choice"
        || !object(question.criteria) || Object.keys(question.criteria).length < 2)
      throw new Error("unexpected_classifier_question");
  }
  for (const [id, label] of Object.entries(expectedAnswers(entry)))
    if (!request.questions[id] || !Object.hasOwn(request.questions[id].criteria, label))
      throw new Error("expected_label_missing_from_schema");
  return request;
}

async function exclusiveJson(path, value) {
  await writeFile(path, JSON.stringify(value, null, 2) + "\n", { flag: "wx", mode: 0o600 });
}

export async function main(argv = process.argv.slice(2)) {
  const { values } = parseArgs({ args: argv, options: {
    live: { type: "boolean", default: false }, help: { type: "boolean", default: false },
    dataset: { type: "string", default: DATASET }, case: { type: "string", multiple: true, default: [] },
    "run-dir": { type: "string" }, "account-id": { type: "string" }, profile: { type: "string" },
    cf: { type: "string", default: resolve(ROOT, "hosted-preview/node_modules/cf/bin/cf") },
    "timeout-ms": { type: "string", default: "20000" }, "total-ms": { type: "string", default: "300000" },
    "min-confidence": { type: "string", default: "0.7" }, "min-margin": { type: "string", default: "0.15" },
  } });
  if (values.help) {
    console.log("Clef routing eval (dry run by default)\n  --live --account-id ID --run-dir NEW_PRIVATE_DIR\n  [--case ID ...] [--dataset FILE] [--cf CLI] [--profile NAME]\n  [--timeout-ms 20000] [--total-ms 300000] [--min-confidence 0.7] [--min-margin 0.15]");
    return 0;
  }
  const timeoutMs = Number(values["timeout-ms"]), totalMs = Number(values["total-ms"]);
  const thresholds = { confidence: Number(values["min-confidence"]), margin: Number(values["min-margin"]) };
  if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 60000
      || !Number.isInteger(totalMs) || totalMs < timeoutMs || totalMs > 600000
      || !probability(thresholds.confidence) || !probability(thresholds.margin)) throw new Error("invalid_limits");
  const raw = await readFile(resolve(values.dataset), "utf8"), dataset = readDataset(raw, values.case);
  const { builder, router_sha256 } = await loadBuilder();
  const prepared = dataset.cases.map(entry => ({ entry, request: checkedRequest(builder, entry) }));
  const runId = randomUUID();
  const cases = prepared.map(({ entry, request }) => ({ case_id: entry.id, request_id: randomUUID(),
    request_sha256: hash(JSON.stringify(request)), prompt_sha256: hash(entry.prompt), expected: expectedAnswers(entry),
    status: "not_started", attempted: false }));
  const manifest = { schema_version: 1, run_id: runId, created_at: now(), model: MODEL,
    dataset: dataset.name, dataset_sha256: hash(raw), router_sha256, thresholds,
    timeout_ms: timeoutMs, total_ms: totalMs, maximum_classifier_calls: cases.length,
    automatic_retry: false, generation_calls: 0, raw_prompts_recorded: false, cases };
  if (!values.live) { console.log(JSON.stringify({ ...manifest, mode: "dry_run", classifier_calls: 0 }, null, 2)); return 0; }
  if (!/^[a-f0-9]{32}$/i.test(values["account-id"] ?? "") || !values["run-dir"])
    throw new Error("live_requires_account_id_and_new_run_dir");
  if (values.profile !== undefined && !/^[A-Za-z0-9_.-]{1,80}$/.test(values.profile)) throw new Error("invalid_profile");
  const cf = resolve(values.cf), runDir = resolve(values["run-dir"]);
  const packageJson = JSON.parse(await readFile(resolve(dirname(cf), "../package.json"), "utf8"));
  if (packageJson.name !== "cf" || packageJson.version !== "1.0.0-beta.12")
    throw new Error("unreviewed_cf_version_review_retry_and_body_protocol_first");
  await mkdir(runDir, { mode: 0o700 }); // Exclusive: an existing run is never resumed or replayed.
  await chmod(runDir, 0o700);
  await exclusiveJson(resolve(runDir, "manifest.json"), { ...manifest, mode: "live", cf_version: packageJson.version });
  const temporary = await mkdtemp(resolve(tmpdir(), "lupine-clef-eval-"));
  await chmod(temporary, 0o700);
  const env = cfEnvironment(values["account-id"]);
  const deadline = performance.now() + totalMs;
  let stopped = null;
  try {
    for (let index = 0; index < prepared.length; index++) {
      if (performance.now() + timeoutMs > deadline) { stopped = "batch_deadline"; break; }
      const bodyPath = resolve(temporary, "request.json"), receipt = cases[index];
      await exclusiveJson(bodyPath, prepared[index].request);
      await exclusiveJson(resolve(runDir, `${receipt.case_id}.intent.json`), { ...receipt, created_at: now(), automatic_retry: false });
      receipt.attempted = true;
      receipt.started_at = now();
      const result = await boundedCommand(process.execPath, [cf, "ai", "run", MODEL, "--body", `@${bodyPath}`, "--quiet",
        ...(values.profile ? ["--profile", values.profile] : [])], { cwd: temporary, env, timeoutMs });
      await rm(bodyPath);
      Object.assign(receipt, { finished_at: now(), latency_ms: result.latency_ms,
        stdout_bytes: result.stdout_bytes, stderr_bytes: result.stderr_bytes, returncode: result.returncode,
        status: result.stop_reason ?? (result.returncode === 0 ? "completed" : "cli_failed") });
      if (receipt.status === "completed") {
        try { Object.assign(receipt, scoreResponse(JSON.parse(result.stdout.toString("utf8")), prepared[index].request, receipt.expected, thresholds)); }
        catch { receipt.status = "invalid_response"; }
      }
      receipt.error = receipt.status === "completed" ? null : receipt.status;
      receipt.completion_unknown = receipt.status !== "completed";
      receipt.automatic_retry = false;
      await exclusiveJson(resolve(runDir, `${receipt.case_id}.receipt.json`), receipt);
      console.log(JSON.stringify({ case_id: receipt.case_id, request_id: receipt.request_id, status: receipt.status,
        route: receipt.answers?.route?.choice ?? null, correct: receipt.answers?.route?.correct ?? null }));
      if (receipt.status !== "completed") { stopped = receipt.status; break; }
    }
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
  const report = { schema_version: 1, run_id: runId, finished_at: now(), status: stopped ? "stopped" : "completed",
    stop_reason: stopped, automatic_retry: false, generation_calls: 0,
    latency_scope: "CLI startup, OAuth handling and API request; not Worker binding latency",
    interpretation: "Small synthetic routing evaluation with provisional labels; not a research-quality or model-quality benchmark.",
    summary: summarize(cases), cases };
  await exclusiveJson(resolve(runDir, "report.json"), report);
  console.log(JSON.stringify({ run_id: runId, status: report.status, summary: report.summary }));
  return stopped ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().then(code => { process.exitCode = code; }).catch(error => {
    // Never echo provider errors, request bodies, command arguments, or credentials.
    const known = /^[a-z][a-z0-9_]{0,100}$/.test(error?.message ?? "") ? error.message : "evaluation_setup_failed";
    console.error(JSON.stringify({ error: known, automatic_retry: false }));
    process.exitCode = 1;
  });
}
