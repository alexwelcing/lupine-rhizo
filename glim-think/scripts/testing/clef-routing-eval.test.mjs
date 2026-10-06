import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { boundedCommand, cfEnvironment, expectedAnswers, main, MODEL, readDataset, scoreResponse, summarize } from "./clef-routing-eval.mjs";

const request = { model: "clef-flash", state: { user_request: "Synthetic request." }, questions: {
  route: { type: "choice", criteria: { fast: "", deep: "", code: "", research: "" } },
  evidence: { type: "choice", criteria: { none: "", research_runs: "", ledger: "", both: "" } },
  workflow: { type: "choice", criteria: { answer: "", literature: "", hypothesis: "", critique: "", analysis: "" } },
} };
function answer(choice, choices, confidence = .8) {
  return { type: "choice", choice, confidence,
    probabilities: Object.fromEntries(choices.map(key => [key, key === choice ? .7 : .3 / (choices.length - 1)])) };
}
function response() {
  return { model: "clef-flash", request_id: "synthetic-provider-id", usage: { input_tokens: 25, output_tokens: 3 },
    answers: Object.fromEntries(Object.entries({ route: "research", evidence: "both", workflow: "analysis" })
      .map(([key, choice]) => [key, answer(choice, Object.keys(request.questions[key].criteria))])) };
}

test("scores each axis separately and preserves provider confidence rather than top probability", () => {
  const result = scoreResponse(response(), request, { route: "research", evidence: "ledger" });
  assert.equal(result.answers.route.confidence, .8);
  assert.equal(result.answers.route.margin, .6);
  assert.equal(result.answers.route.correct, true);
  assert.equal(result.answers.evidence.correct, false);
  assert.equal(result.answers.workflow.correct, null);
  assert.equal(result.provider_request_id, "synthetic-provider-id");
});

test("low confidence and ties abstain even when a provisional expected label agrees", () => {
  const value = response();
  value.answers.route.confidence = .6;
  value.answers.evidence.probabilities = { none: 0, research_runs: 0, ledger: .5, both: .5 };
  const result = scoreResponse(value, request, { route: "research", evidence: "both" }, { confidence: .7, margin: 0 });
  assert.equal(result.answers.route.correct, true);
  assert.equal(result.answers.route.accepted, false);
  assert.equal(result.answers.route.fallback_reason, "low-confidence");
  assert.equal(result.answers.evidence.accepted, false);
  assert.equal(result.answers.evidence.fallback_reason, "ambiguous-task");
});

test("rejects malformed distribution, missing axis, unsupported model and invalid usage", () => {
  const variants = [value => { value.answers.route.probabilities.fast = true; },
    value => { value.answers.route.probabilities.fast = .9; },
    value => { value.answers.route.choice = "fast"; }, value => { delete value.answers.evidence; },
    value => { value.answers.extra = value.answers.route; }, value => { value.usage.input_tokens = -1; },
    value => { value.usage.output_tokens = 1.5; }, value => { value.model = "generation-model"; }];
  for (const change of variants) { const value = response(); change(value); assert.throws(() => scoreResponse(value, request, {})); }
});

test("summary separates coverage, labeled accuracy and accepted accuracy without counting errors as votes", () => {
  const good = scoreResponse(response(), request, { route: "research" });
  const weak = response(); weak.answers.route.confidence = .1;
  const weakResult = scoreResponse(weak, request, { route: "fast" });
  const result = summarize([{ status: "completed", attempted: true, latency_ms: 10, ...good },
    { status: "completed", attempted: true, latency_ms: 20, ...weakResult },
    { status: "timeout", attempted: true }, { status: "not_started", attempted: false }]);
  assert.deepEqual([result.selected, result.attempted, result.completed, result.failed, result.not_started], [4, 3, 2, 1, 1]);
  assert.equal(result.by_question.route.accuracy, .5);
  assert.equal(result.by_question.route.coverage, .5);
  assert.equal(result.by_question.route.accepted_accuracy, 1);
  assert.equal(result.by_question.evidence.accuracy, null);
  assert.deepEqual(result.usage, { input_tokens: 50, output_tokens: 6 });
});

test("dataset selection rejects duplicates and invalid labels, and permits independently labeled planning cases", () => {
  const data = { schemaVersion: 1, name: "fixture", cases: [{ id: "one", prompt: "Synthetic text.", expectedTask: "fast",
    expectedEvidence: "none", expectedWorkflow: "answer" }] };
  const parsed = readDataset(JSON.stringify(data), ["one"]);
  assert.deepEqual(expectedAnswers(parsed.cases[0]), { route: "fast", evidence: "none", workflow: "answer" });
  assert.throws(() => readDataset(JSON.stringify(data), ["unknown"]));
  assert.throws(() => readDataset(JSON.stringify(data), ["one", "one"]));
  assert.throws(() => readDataset(JSON.stringify({ ...data, cases: [...data.cases, ...data.cases] })));
});

test("CLI environment retains normal home authentication while dropping tokens, redirects and debug configuration", () => {
  const result = cfEnvironment("0".repeat(32), { HOME: "/fixture/home", PATH: "/fixture/bin", CLOUDFLARE_API_TOKEN: "secret",
    NODE_OPTIONS: "--inspect", DEBUG: "1", CLOUDFLARE_API_BASE_URL: "https://example.invalid", CF_API_BASE_URL: "https://example.invalid" });
  assert.equal(result.HOME, "/fixture/home");
  assert.equal(result.DO_NOT_TRACK, "1");
  for (const key of ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_API_BASE_URL", "CF_API_BASE_URL", "NODE_OPTIONS", "DEBUG"])
    assert.equal(result[key], undefined);
});

test("bounded child terminates on deadline and does not echo stderr", async () => {
  const result = await boundedCommand(process.execPath, ["-e", "process.stderr.write('private-fixture'); setInterval(()=>{},1000)"],
    { cwd: tmpdir(), env: process.env, timeoutMs: 150 });
  assert.equal(result.stop_reason, "timeout");
  assert.ok(result.latency_ms < 2000);
  assert.equal(result.stderr, undefined);
  assert.equal(result.stderr_bytes, 15);
});

test("bounded child stops excessive output", async () => {
  const result = await boundedCommand(process.execPath, ["-e", "process.stdout.write('x'.repeat(20000));setInterval(()=>{},1000)"],
    { cwd: tmpdir(), env: process.env, timeoutMs: 1000, outputLimit: 1000 });
  assert.equal(result.stop_reason, "output_limit");
  assert.ok(result.stdout.length <= 1000);
});

test("dry run loads real shared builder without executing even a missing CLI", async () => {
  const logged = [], original = console.log;
  try {
    console.log = value => logged.push(value);
    assert.equal(await main(["--case", "fast-greeting", "--cf", "/does/not/exist"]), 0);
  } finally { console.log = original; }
  const plan = JSON.parse(logged[0]);
  assert.equal(plan.mode, "dry_run");
  assert.equal(plan.classifier_calls, 0);
  assert.equal(plan.maximum_classifier_calls, 1);
  assert.equal(plan.generation_calls, 0);
  assert.equal(plan.cases[0].prompt, undefined);
});

test("fake official CLI protocol is invoked once per case and an existing run cannot be replayed", async () => {
  const directory = await mkdtemp(resolve(tmpdir(), "clef-eval-test-"));
  const original = console.log;
  try {
    const bin = resolve(directory, "cli/bin"), runDir = resolve(directory, "receipts");
    await mkdir(bin, { recursive: true });
    await writeFile(resolve(directory, "cli/package.json"), JSON.stringify({ name: "cf", version: "1.0.0-beta.12" }));
    await writeFile(resolve(bin, "cf"), `const fs=require('node:fs');
      const a=process.argv.slice(2);if(a[0]!=='ai'||a[1]!=='run'||a[2]!==${JSON.stringify(MODEL)})process.exit(4);
      const body=JSON.parse(fs.readFileSync(a[a.indexOf('--body')+1].slice(1),'utf8'));
      fs.appendFileSync(${JSON.stringify(resolve(directory, "count"))},'call\\n');
      const choices={route:'fast',evidence:'none',workflow:'answer'};
      const answers=Object.fromEntries(Object.entries(body.questions).map(([key,q])=>{const ids=Object.keys(q.criteria);return [key,{type:'choice',choice:choices[key],confidence:.9,probabilities:Object.fromEntries(ids.map(id=>[id,id===choices[key]?.7:.3/(ids.length-1)]))}]}));
      console.log(JSON.stringify({model:'clef-flash',answers,usage:{input_tokens:20,output_tokens:3}}));`);
    console.log = () => {};
    const args = ["--live", "--case", "fast-greeting", "--account-id", "0".repeat(32), "--run-dir", runDir, "--cf", resolve(bin, "cf")];
    assert.equal(await main(args), 0);
    const report = JSON.parse(await readFile(resolve(runDir, "report.json"), "utf8"));
    assert.equal(report.summary.completed, 1);
    assert.equal(report.cases[0].answers.route.correct, true);
    assert.equal(report.cases[0].provider_request_id, null);
    await assert.rejects(main(args));
    assert.equal(await readFile(resolve(directory, "count"), "utf8"), "call\n");
    assert.ok(!(await readFile(resolve(runDir, "report.json"), "utf8")).includes("Give me a one-line"));
  } finally { console.log = original; await rm(directory, { recursive: true, force: true }); }
});

test("a failed classification stops the remaining batch and provider error text stays out of receipts", async () => {
  const directory = await mkdtemp(resolve(tmpdir(), "clef-eval-stop-test-"));
  const original = console.log;
  try {
    const bin = resolve(directory, "cli/bin"), runDir = resolve(directory, "receipts");
    await mkdir(bin, { recursive: true });
    await writeFile(resolve(directory, "cli/package.json"), JSON.stringify({ name: "cf", version: "1.0.0-beta.12" }));
    await writeFile(resolve(bin, "cf"), `require('node:fs').appendFileSync(${JSON.stringify(resolve(directory, "count"))},'call\\n');
      process.stderr.write('PRIVATE-SYNTHETIC-ERROR');process.exit(1);`);
    console.log = () => {};
    assert.equal(await main(["--live", "--case", "fast-greeting", "--case", "fast-rewrite", "--account-id", "0".repeat(32),
      "--run-dir", runDir, "--cf", resolve(bin, "cf")]), 1);
    const raw = await readFile(resolve(runDir, "report.json"), "utf8"), report = JSON.parse(raw);
    assert.equal(report.status, "stopped");
    assert.equal(report.summary.attempted, 1);
    assert.equal(report.summary.not_started, 1);
    assert.equal(report.cases[0].completion_unknown, true);
    assert.equal(await readFile(resolve(directory, "count"), "utf8"), "call\n");
    assert.ok(!raw.includes("PRIVATE-SYNTHETIC-ERROR"));
  } finally { console.log = original; await rm(directory, { recursive: true, force: true }); }
});
