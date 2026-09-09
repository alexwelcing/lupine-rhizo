import test from "node:test";
import assert from "node:assert/strict";
import { agentNameFor, cleanExcerpt, Dispatcher, newOutputSince, outcomeFromAgentStatus } from "../src/dispatch.ts";
import { HerdrClient } from "../src/herdr.ts";
import { WorkerClient, type BridgeJob } from "../src/worker.ts";
import { captureLogger, fakeWorker, RpcError, startFakeHerdr, testConfig, until, type FakeHerdr } from "./helpers.ts";

const job: BridgeJob = {
  job_id: "0f3c2a1b-1111-4222-8333-444455556666",
  machine_id: "test-machine",
  agent_kind: "hermes",
  prompt: "Reply with PONG.",
  campaign_id: "github:9",
  status: "claimed",
  attempts: 1,
  created_at: 1_700_000_000,
  claimed_at: 1_700_000_010,
};

function happyHerdr(fake: FakeHerdr, opts: { finalStatus?: string; promptError?: RpcError } = {}) {
  fake.on("workspace.create", (params) => ({
    type: "workspace_created",
    workspace: { workspace_id: "w9", label: params.label },
    tab: { tab_id: "w9:t1" },
    root_pane: { pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", agent_status: "unknown" },
  }));
  let startAttempts = 0;
  fake.on("agent.start", (params) => {
    // First attempt lands before the shell prompt is up (observed live).
    if (startAttempts++ === 0) throw new RpcError("agent_pane_busy", `agent target pane ${params.pane_id} is not an available shell`);
    return { type: "agent_started", agent: { pane_id: params.pane_id, workspace_id: "w9", tab_id: "w9:t1", agent_status: "unknown", launch_pending: true } };
  });
  fake.on("agent.wait", () => ({ type: "agent_info", agent: { pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", agent_status: opts.finalStatus ?? "idle" } }));
  fake.on("agent.prompt", () => {
    if (opts.promptError) throw opts.promptError;
    return { type: "agent_prompted", agent: { pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", agent_status: opts.finalStatus ?? "done" } };
  });
  fake.on("agent.send_keys", () => ({ type: "ok" }));
  let reads = 0;
  fake.on("agent.read", () => ({
    type: "pane_read",
    read: {
      pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", revision: 3, truncated: false,
      // First read (pre-prompt snapshot) is the banner; later reads have scrolled and carry the answer.
      text: reads++ === 0
        ? "Welcome to\nHermes Agent!\n❯ \n"
        : "Hermes Agent!\n● Reply with PONG.\n╭─ Hermes ─╮\nPONG\n╰──────────╯\n ⚕ glm ·...\n",
    },
  }));
  fake.on("workspace.close", () => ({ type: "ok" }));
}

function build(fake: FakeHerdr, overrides = {}) {
  const worker = fakeWorker();
  const { log, lines } = captureLogger();
  const panes: Array<[string, BridgeJob | null]> = [];
  const dispatcher = new Dispatcher({
    config: testConfig({ herdrSocketPath: fake.socketPath, ...overrides }),
    herdr: new HerdrClient({ socketPath: fake.socketPath }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    now: () => 1_700_000_100,
    onJobPane: (pane, j) => panes.push([pane, j]),
  });
  return { worker, log, lines, dispatcher, panes };
}

test("helpers: agent naming, excerpt cleaning, status mapping", () => {
  assert.equal(agentNameFor(job), "bridge-0f3c2a1b-1111-4222-8");
  assert.match(agentNameFor(job), /^[a-z][a-z0-9_-]{0,31}$/);
  assert.equal(cleanExcerpt("╭─ x ─╮\n  hello  \n\n╰──╯\n"), " x\n  hello");
  assert.equal(cleanExcerpt("a".repeat(10), 4), "aaaa");
  assert.equal(outcomeFromAgentStatus("done"), "done");
  assert.equal(outcomeFromAgentStatus("idle"), "done");
  assert.equal(outcomeFromAgentStatus("blocked"), "blocked");
  assert.equal(outcomeFromAgentStatus("unknown"), "failed");
});

test("newOutputSince: keeps only lines appended after the snapshot", () => {
  assert.equal(newOutputSince("a\nb\nc", "b\nc\nd\ne"), "d\ne");
  assert.equal(newOutputSince("a\nb\nc", "a\nb\nc"), "");
  assert.equal(newOutputSince("a\nb\nc", "x\ny\nz"), "x\ny\nz");
  assert.equal(newOutputSince("a\nb  ", "b\nnew"), "new");
  assert.equal(newOutputSince("", "only"), "only");
  // The input line (`❯`) is overwritten by the echoed prompt after submission.
  assert.equal(newOutputSince("banner\nHermes Agent!\n❯ \n", "Hermes Agent!\n● do it\nPONG\n"), "● do it\nPONG\n");
  // Blank-only overlaps are not evidence.
  assert.equal(newOutputSince("x\n\n", "\nfresh"), "\nfresh");
});

test("runJob: full herdr sequence, result beat carries provenance, workspace closed", async () => {
  const fake = await startFakeHerdr();
  try {
    happyHerdr(fake);
    const { dispatcher, panes } = build(fake);
    const outcome = await dispatcher.runJob(job);
    assert.equal(outcome.status, "done");
    assert.equal(outcome.workspace_id, "w9");
    assert.equal(outcome.output_excerpt, "● Reply with PONG.\n Hermes\nPONG\n ⚕ glm ·...");
    assert.deepEqual(
      fake.calls.map((c) => c.method),
      ["workspace.create", "agent.start", "agent.start", "agent.wait", "agent.read", "agent.prompt", "agent.read", "workspace.close"],
    );
    const start = fake.calls[2].params;
    assert.equal(start.kind, "hermes");
    assert.equal(start.pane_id, "w9:p1");
    assert.equal(start.timeout_ms, 3_001);
    const prompt = fake.calls[5].params as { text: string; wait: { timeout_ms: number } };
    assert.equal(prompt.text, "Reply with PONG.");
    assert.equal(prompt.wait.timeout_ms, 5_000);
    assert.deepEqual(panes, [["w9:p1", job], ["w9:p1", null]]);

    const result = dispatcher.buildResult(job, outcome);
    assert.equal(result.status, "done");
    assert.equal(result.beat?.beat_id, `herdr-job:${job.job_id}:1:done`);
    assert.equal(result.beat?.metrics?.source, "herdr-bridge");
    assert.equal(result.beat?.metrics?.machine_id, "test-machine");
    assert.equal(result.beat?.metrics?.job_id, job.job_id);
    assert.equal(result.beat?.metrics?.status, "completed");
  } finally {
    await fake.close();
  }
});

test("runJob: blocked agent keeps the workspace and reports blocked", async () => {
  const fake = await startFakeHerdr();
  try {
    happyHerdr(fake, { finalStatus: "blocked" });
    const { dispatcher, lines } = build(fake, { keepWorkspaces: "failed" });
    // agent.wait must still report idle for readiness; only the prompt settles blocked.
    fake.on("agent.wait", () => ({ type: "agent_info", agent: { pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", agent_status: "idle" } }));
    const outcome = await dispatcher.runJob(job);
    assert.equal(outcome.status, "blocked");
    assert.ok(!fake.calls.some((c) => c.method === "workspace.close"));
    assert.ok(lines.some((l) => l.event === "workspace_kept"));
  } finally {
    await fake.close();
  }
});

test("runJob: prompt stall is nudged with Enter, then waited", async () => {
  const fake = await startFakeHerdr();
  try {
    happyHerdr(fake, { promptError: new RpcError("agent_prompt_stalled", "no activity") });
    fake.on("agent.wait", (params) => ({
      type: "agent_info",
      agent: { pane_id: "w9:p1", workspace_id: "w9", tab_id: "w9:t1", agent_status: params.until ? "idle" : "done" },
    }));
    const { dispatcher } = build(fake);
    const outcome = await dispatcher.runJob(job);
    assert.equal(outcome.status, "done");
    assert.deepEqual(
      fake.calls.map((c) => c.method),
      ["workspace.create", "agent.start", "agent.start", "agent.wait", "agent.read", "agent.prompt", "agent.send_keys", "agent.wait", "agent.read", "workspace.close"],
    );
  } finally {
    await fake.close();
  }
});

test("runJob: herdr timeout maps to timeout status with excerpt salvage", async () => {
  const fake = await startFakeHerdr();
  try {
    happyHerdr(fake, { promptError: new RpcError("timeout", "agent wait timed out") });
    const { dispatcher } = build(fake, { keepWorkspaces: "never" });
    const outcome = await dispatcher.runJob(job);
    assert.equal(outcome.status, "timeout");
    assert.equal(outcome.output_excerpt, "Hermes Agent!\n● Reply with PONG.\n Hermes\nPONG\n ⚕ glm ·...");
    assert.ok(fake.calls.some((c) => c.method === "workspace.close"));
  } finally {
    await fake.close();
  }
});

test("runJob: herdr down → failed outcome, nothing else attempted", async () => {
  const { dispatcher } = build({ socketPath: "/nonexistent/herdr.sock", calls: [] } as unknown as FakeHerdr);
  const outcome = await dispatcher.runJob(job);
  assert.equal(outcome.status, "failed");
  assert.match(outcome.error ?? "", /herdr socket/);
  assert.equal(outcome.workspace_id, null);
});

test("report: retries transient failures, gives up on 4xx", async () => {
  const fake = await startFakeHerdr();
  try {
    const { dispatcher, worker, lines } = build(fake);
    const outcome = { status: "done" as const, output_excerpt: "x", agent_status: "done" as const, workspace_id: "w9", pane_id: "w9:p1", duration_ms: 10 };
    worker.fail(2);
    assert.equal(await dispatcher.report(job, outcome), true);
    assert.equal(worker.calls.length, 3);
    assert.equal(worker.calls[2].path, `/bridge/jobs/${job.job_id}/result`);
    assert.equal((worker.calls[2].body as { beat: { beat_id: string } }).beat.beat_id, `herdr-job:${job.job_id}:1:done`);

    worker.respond(/\/result$/, () => Response.json({ error: "job already done" }, { status: 409 }));
    assert.equal(await dispatcher.report(job, outcome), false);
    assert.ok(lines.some((l) => l.event === "job_report_rejected"));
  } finally {
    await fake.close();
  }
});

test("run loop: polls, claims, executes, reports, and backs off on poll failure", async () => {
  const fake = await startFakeHerdr();
  try {
    happyHerdr(fake);
    const { dispatcher, worker, lines } = build(fake);
    let served = false;
    worker.respond("/bridge/jobs/next", () => {
      if (served) return new Response(null, { status: 204 });
      served = true;
      return Response.json({ ok: true, job });
    });
    worker.fail(1);
    const controller = new AbortController();
    const running = dispatcher.run(controller.signal);
    await until(() => worker.calls.some((c) => c.path.endsWith("/result")), 5_000);
    await until(() => dispatcher.snapshot.completed === 1);
    controller.abort();
    await running;
    assert.ok(lines.some((l) => l.event === "poll_failed"));
    assert.equal(worker.calls[0].path, "/bridge/jobs/next?machine_id=test-machine&wait_seconds=0");
    assert.equal(worker.calls[0].headers.authorization, "Bearer tok");
    assert.ok(dispatcher.snapshot.polled >= 2);
  } finally {
    await fake.close();
  }
});
