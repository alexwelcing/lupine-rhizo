import test from "node:test";
import assert from "node:assert/strict";
import { defaultHerdrSocketPath, describeConfig, loadConfig } from "../src/config.ts";
import { backoffMs, createLogger } from "../src/log.ts";

const base = { GLIM_WORKER_URL: "https://w.test/", GLIM_BRIDGE_TOKEN: "s3cret", HOME: "/home/u" };

test("config: defaults and normalisation", () => {
  const cfg = loadConfig({ ...base, MACHINE_ID: "box-1" });
  assert.equal(cfg.workerUrl, "https://w.test");
  assert.equal(cfg.machineId, "box-1");
  assert.equal(cfg.herdrSocketPath, "/home/u/.config/herdr/herdr.sock");
  assert.equal(cfg.pollIntervalSeconds, 15);
  assert.equal(cfg.keepWorkspaces, "failed");
  assert.equal(cfg.telemetryEnabled, true);
  assert.equal(describeConfig(cfg).bridgeToken, "<6 chars>");
});

test("config: env overrides and validation", () => {
  const cfg = loadConfig({
    ...base,
    MACHINE_ID: "m",
    HERDR_SOCKET_PATH: "/run/h.sock",
    POLL_INTERVAL_SECONDS: "3",
    BRIDGE_KEEP_WORKSPACES: "ALWAYS",
    BRIDGE_TELEMETRY: "off",
    XDG_CONFIG_HOME: "/xdg",
  });
  assert.equal(cfg.herdrSocketPath, "/run/h.sock");
  assert.equal(cfg.pollIntervalSeconds, 3);
  assert.equal(cfg.keepWorkspaces, "always");
  assert.equal(cfg.telemetryEnabled, false);
  assert.equal(defaultHerdrSocketPath({ XDG_CONFIG_HOME: "/xdg" }), "/xdg/herdr/herdr.sock");

  assert.throws(() => loadConfig({ GLIM_BRIDGE_TOKEN: "x" }), /GLIM_WORKER_URL/);
  assert.throws(() => loadConfig({ GLIM_WORKER_URL: "x" }), /GLIM_BRIDGE_TOKEN/);
  assert.throws(() => loadConfig({ ...base, MACHINE_ID: "bad id" }), /MACHINE_ID/);
  assert.throws(() => loadConfig({ ...base, MACHINE_ID: "m", POLL_INTERVAL_SECONDS: "0" }), /POLL_INTERVAL_SECONDS/);
  assert.throws(() => loadConfig({ ...base, MACHINE_ID: "m", BRIDGE_KEEP_WORKSPACES: "maybe" }), /BRIDGE_KEEP_WORKSPACES/);
});

test("log: structured lines with level threshold and child components", () => {
  const lines: string[] = [];
  const log = createLogger("root", { level: "info", sink: (l) => lines.push(l), base: { machine_id: "m" } });
  log.debug("hidden");
  log.child("sub").warn("shown", { n: 1 });
  assert.equal(lines.length, 1);
  const parsed = JSON.parse(lines[0]);
  assert.equal(parsed.component, "root.sub");
  assert.equal(parsed.level, "warn");
  assert.equal(parsed.event, "shown");
  assert.equal(parsed.machine_id, "m");
  assert.equal(parsed.n, 1);
  assert.match(parsed.ts, /^\d{4}-\d{2}-\d{2}T/);
});

test("backoff: capped and jittered", () => {
  for (let i = 0; i < 50; i++) {
    const v = backoffMs(i, 100, 1_000);
    assert.ok(v >= 0 && v < 1_000, `attempt ${i} -> ${v}`);
  }
  assert.ok(backoffMs(0, 100, 1_000) < 100);
});
