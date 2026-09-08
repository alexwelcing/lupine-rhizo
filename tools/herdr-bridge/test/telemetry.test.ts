import test from "node:test";
import assert from "node:assert/strict";
import { HerdrClient } from "../src/herdr.ts";
import { TelemetryLoop, transitionBeat } from "../src/telemetry.ts";
import { WorkerClient } from "../src/worker.ts";
import { captureLogger, fakeWorker, startFakeHerdr, until } from "./helpers.ts";

test("transitionBeat: shape, provenance tags, and job annotation", () => {
  const beat = transitionBeat(
    "aledev",
    { pane_id: "w1:p1", workspace_id: "w1", agent_status: "working", agent: "hermes" },
    "idle",
    3,
    1_788_000_000,
    { job_id: "job-1", campaign_id: "github:1" },
  );
  assert.equal(beat.beat_id, "herdr:aledev:w1:p1:3:1788000000");
  assert.equal(beat.agent, "herdr-bridge/aledev");
  assert.equal(beat.summary, "hermes w1:p1 idle -> working");
  assert.deepEqual(beat.metrics, {
    source: "herdr-bridge",
    machine_id: "aledev",
    pane_id: "w1:p1",
    workspace_id: "w1",
    agent_kind: "hermes",
    from_status: "idle",
    to_status: "working",
    transition: "idle->working",
    job_id: "job-1",
    campaign_id: "github:1",
  });
});

test("telemetry loop: forwards transitions as beats, dedupes repeats, ignores other events", async () => {
  const fake = await startFakeHerdr();
  const worker = fakeWorker();
  const { log } = captureLogger();
  const loop = new TelemetryLoop({
    machineId: "m1",
    herdr: new HerdrClient({ socketPath: fake.socketPath }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    maxBackoffMs: 20,
    now: () => 1_700_000_000,
  });
  const controller = new AbortController();
  const running = loop.run(controller.signal);
  try {
    await until(() => fake.subscribers.length === 1);
    const subscribe = fake.calls.find((c) => c.method === "events.subscribe")!;
    assert.deepEqual(subscribe.params.subscriptions, [
      { type: "pane.created" },
      { type: "pane.closed" },
      { type: "pane.agent_status_changed", pane_id: "w1:p1" },
      { type: "pane.agent_status_changed", pane_id: "w1:p2" },
    ]);
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "idle", agent: "hermes" });
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "idle", agent: "hermes" });
    fake.emit("pane.updated", { pane: { pane_id: "w1:p1" } });
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "working", agent: "hermes" });
    await until(() => worker.calls.length === 2);
    assert.deepEqual(worker.calls.map((c) => c.path), ["/feed/beats", "/feed/beats"]);
    assert.equal(worker.calls[0].headers.authorization, "Bearer tok");
    assert.equal((worker.calls[0].body as { metrics: { transition: string } }).metrics.transition, "unknown->idle");
    assert.equal((worker.calls[1].body as { metrics: { transition: string } }).metrics.transition, "idle->working");
    assert.equal(loop.snapshot.sent, 2);
    assert.equal(loop.snapshot.received, 2);
  } finally {
    controller.abort();
    await running;
    await fake.close();
  }
});

test("telemetry loop: retries transient worker failures and drops non-retryable ones", async () => {
  const fake = await startFakeHerdr();
  const worker = fakeWorker();
  const { log, lines } = captureLogger();
  const loop = new TelemetryLoop({
    machineId: "m1",
    herdr: new HerdrClient({ socketPath: fake.socketPath }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    maxBackoffMs: 20,
  });
  const controller = new AbortController();
  const running = loop.run(controller.signal);
  try {
    await until(() => fake.subscribers.length === 1);
    worker.fail(2);
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "working" });
    await until(() => loop.snapshot.sent === 1, 5_000);
    assert.equal(worker.calls.length, 3);
    assert.ok(lines.some((l) => l.event === "beat_send_failed"));

    worker.respond("/feed/beats", () => Response.json({ error: "bad" }, { status: 400 }));
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "done" });
    await until(() => loop.snapshot.failed === 1, 5_000);
    assert.equal(loop.snapshot.buffered, 0);
    assert.ok(lines.some((l) => l.event === "beat_rejected"));
  } finally {
    controller.abort();
    await running;
    await fake.close();
  }
});

test("telemetry loop: resubscribes after herdr drops the connection", async () => {
  const fake = await startFakeHerdr();
  const worker = fakeWorker();
  const { log, lines } = captureLogger();
  const loop = new TelemetryLoop({
    machineId: "m1",
    herdr: new HerdrClient({ socketPath: fake.socketPath }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    maxBackoffMs: 20,
  });
  const controller = new AbortController();
  const running = loop.run(controller.signal);
  try {
    await until(() => fake.subscribers.length === 1);
    fake.subscribers[0].destroy();
    await until(() => lines.some((l) => l.event === "subscription_closed"));
    await until(() => fake.calls.filter((c) => c.method === "events.subscribe").length >= 2, 5_000);
    await until(() => fake.subscribers.length === 1, 5_000);
    fake.emit("pane.agent_status_changed", { pane_id: "w1:p2", workspace_id: "w1", agent_status: "idle" });
    await until(() => loop.snapshot.sent === 1, 5_000);
  } finally {
    controller.abort();
    await running;
    await fake.close();
  }
});

test("telemetry loop: rebuilds the per-pane subscription when a pane is created", async () => {
  const fake = await startFakeHerdr();
  const worker = fakeWorker();
  const { log } = captureLogger();
  const loop = new TelemetryLoop({
    machineId: "m1",
    herdr: new HerdrClient({ socketPath: fake.socketPath }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    maxBackoffMs: 20,
  });
  const controller = new AbortController();
  const running = loop.run(controller.signal);
  try {
    await until(() => fake.subscribers.length === 1);
    fake.on("pane.list", () => ({
      type: "pane_list",
      panes: [{ pane_id: "w1:p1", workspace_id: "w1", tab_id: "w1:t1", agent_status: "unknown" }, { pane_id: "w2:p1", workspace_id: "w2", tab_id: "w2:t1", agent_status: "unknown" }],
    }));
    fake.emit("pane_created", { pane: { pane_id: "w2:p1", workspace_id: "w2" } });
    await until(() => fake.calls.filter((c) => c.method === "events.subscribe").length === 2, 5_000);
    await until(() => fake.subscribers.length === 1, 5_000);
    const second = fake.calls.filter((c) => c.method === "events.subscribe")[1];
    assert.ok((second.params.subscriptions as Array<{ pane_id?: string }>).some((s) => s.pane_id === "w2:p1"));
    fake.emit("pane.agent_status_changed", { pane_id: "w2:p1", workspace_id: "w2", agent_status: "working" });
    await until(() => loop.snapshot.sent === 1, 5_000);
  } finally {
    controller.abort();
    await running;
    await fake.close();
  }
});

test("telemetry loop: bounded buffer drops oldest beats while the worker is down", async () => {
  const worker = fakeWorker();
  const { log } = captureLogger();
  const loop = new TelemetryLoop({
    machineId: "m1",
    herdr: new HerdrClient({ socketPath: "/nonexistent.sock" }),
    worker: new WorkerClient({ baseUrl: "https://worker.test", token: "tok", fetchImpl: worker.fetch }),
    log,
    maxBuffered: 2,
  });
  const statuses = ["idle", "working", "done", "idle"];
  for (const [i, status] of statuses.entries()) {
    loop.ingest({ event: "pane.agent_status_changed", data: { pane_id: `w1:p${i}`, workspace_id: "w1", agent_status: status } });
  }
  assert.equal(loop.snapshot.buffered, 2);
  assert.equal(loop.snapshot.dropped, 2);
});
