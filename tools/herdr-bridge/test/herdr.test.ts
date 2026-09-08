import test from "node:test";
import assert from "node:assert/strict";
import { HerdrClient, isHerdrError } from "../src/herdr.ts";
import { startFakeHerdr, RpcError, until } from "./helpers.ts";

test("herdr client: one request per connection, typed results", async () => {
  const fake = await startFakeHerdr();
  try {
    fake.on("workspace.create", (params) => ({
      type: "workspace_created",
      workspace: { workspace_id: "w1", label: params.label },
      tab: { tab_id: "w1:t1" },
      root_pane: { pane_id: "w1:p1", workspace_id: "w1", tab_id: "w1:t1", agent_status: "unknown" },
    }));
    const client = new HerdrClient({ socketPath: fake.socketPath });
    const pong = await client.ping();
    assert.equal(pong.version, "0.9.0");
    const ws = await client.workspaceCreate({ cwd: "/tmp", label: "bridge-test" });
    assert.equal(ws.root_pane.pane_id, "w1:p1");
    assert.deepEqual(fake.calls.map((c) => c.method), ["ping", "workspace.create"]);
    assert.equal(fake.calls[1].params.focus, false);
  } finally {
    await fake.close();
  }
});

test("herdr client: surfaces server error codes and socket absence", async () => {
  const fake = await startFakeHerdr();
  try {
    fake.on("agent.prompt", () => {
      throw new RpcError("agent_prompt_stalled", "no activity");
    });
    const client = new HerdrClient({ socketPath: fake.socketPath });
    await assert.rejects(client.agentPrompt("x", "hi", 1000), (e: unknown) => isHerdrError(e, "agent_prompt_stalled"));
  } finally {
    await fake.close();
  }
  const missing = new HerdrClient({ socketPath: "/nonexistent/herdr.sock" });
  await assert.rejects(missing.ping(), (e: unknown) => isHerdrError(e, "server_not_running"));
});

test("herdr client: request timeout fires when the server never replies", async () => {
  const fake = await startFakeHerdr();
  try {
    fake.on("agent.wait", () => new Promise(() => undefined));
    const client = new HerdrClient({ socketPath: fake.socketPath, requestTimeoutMs: 50 });
    await assert.rejects(client.call("agent.wait", { target: "x" }, 50), (e: unknown) => isHerdrError(e, "timeout"));
  } finally {
    await fake.close();
  }
});

test("herdr client: subscription streams events and reports server drop", async () => {
  const fake = await startFakeHerdr();
  const client = new HerdrClient({ socketPath: fake.socketPath });
  const events: string[] = [];
  let closedReason: Error | null | undefined;
  const sub = await client.subscribe(
    [{ type: "pane.agent_status_changed", pane_id: "w1:p1" }],
    (envelope) => events.push(`${envelope.event}:${envelope.data.agent_status}`),
    (reason) => { closedReason = reason; },
  );
  assert.equal(fake.subscribers.length, 1);
  fake.emit("pane.agent_status_changed", { pane_id: "w1:p1", workspace_id: "w1", agent_status: "working" });
  await until(() => events.length === 1);
  assert.deepEqual(events, ["pane.agent_status_changed:working"]);
  await fake.close();
  await until(() => closedReason !== undefined);
  sub.close();
});
