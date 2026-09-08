/**
 * Test doubles: a fake herdr ndjson server on a temp Unix socket (mirrors
 * the one-request-per-connection behaviour of herdr 0.9.0) and a scripted
 * fetch for the worker side.
 */
import { createServer, type Server, type Socket } from "node:net";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { BridgeConfig } from "../src/config.ts";
import { createLogger, type Logger } from "../src/log.ts";

export type RpcHandler = (params: Record<string, unknown>, socket: Socket) => unknown | Promise<unknown>;

export interface FakeHerdr {
  socketPath: string;
  server: Server;
  calls: Array<{ method: string; params: Record<string, unknown> }>;
  subscribers: Socket[];
  handlers: Map<string, RpcHandler>;
  on(method: string, handler: RpcHandler): void;
  emit(event: string, data: Record<string, unknown>): void;
  close(): Promise<void>;
}

export class RpcError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export async function startFakeHerdr(): Promise<FakeHerdr> {
  const dir = mkdtempSync(join(tmpdir(), "herdr-bridge-test-"));
  const socketPath = join(dir, "herdr.sock");
  const calls: FakeHerdr["calls"] = [];
  const subscribers: Socket[] = [];
  const handlers = new Map<string, RpcHandler>();

  const server = createServer((socket) => {
    let buffer = "";
    socket.setEncoding("utf8");
    socket.on("data", async (chunk: string) => {
      buffer += chunk;
      const nl = buffer.indexOf("\n");
      if (nl < 0) return;
      const line = buffer.slice(0, nl);
      buffer = buffer.slice(nl + 1);
      const req = JSON.parse(line) as { id: string; method: string; params: Record<string, unknown> };
      calls.push({ method: req.method, params: req.params });
      if (req.method === "events.subscribe") {
        subscribers.push(socket);
        socket.write(`${JSON.stringify({ id: req.id, result: { type: "subscription_started" } })}\n`);
        socket.on("close", () => {
          const i = subscribers.indexOf(socket);
          if (i >= 0) subscribers.splice(i, 1);
        });
        return;
      }
      const handler = handlers.get(req.method);
      try {
        if (!handler) throw new RpcError("unknown_method", `no handler for ${req.method}`);
        const result = await handler(req.params, socket);
        socket.end(`${JSON.stringify({ id: req.id, result })}\n`);
      } catch (e) {
        const code = e instanceof RpcError ? e.code : "internal";
        socket.end(`${JSON.stringify({ id: req.id, error: { code, message: (e as Error).message } })}\n`);
      }
    });
    socket.on("error", () => undefined);
  });
  await new Promise<void>((resolve) => server.listen(socketPath, resolve));

  const fake: FakeHerdr = {
    socketPath,
    server,
    calls,
    subscribers,
    handlers,
    on: (method, handler) => handlers.set(method, handler),
    emit: (event, data) => {
      for (const s of subscribers) s.write(`${JSON.stringify({ event, data })}\n`);
    },
    close: () =>
      new Promise<void>((resolve) => {
        for (const s of subscribers) s.destroy();
        server.close(() => resolve());
      }),
  };
  fake.on("ping", () => ({ type: "pong", version: "0.9.0", protocol: 22 }));
  fake.on("pane.list", () => ({
    type: "pane_list",
    panes: [
      { pane_id: "w1:p1", workspace_id: "w1", tab_id: "w1:t1", agent_status: "unknown" },
      { pane_id: "w1:p2", workspace_id: "w1", tab_id: "w1:t1", agent_status: "idle" },
    ],
  }));
  return fake;
}

export interface FakeWorkerCall {
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
}

export interface FakeWorker {
  calls: FakeWorkerCall[];
  fetch: typeof fetch;
  /** Queue a response for the next matching request; default is 200 {ok:true}. */
  respond(path: string | RegExp, handler: (call: FakeWorkerCall) => Response | Promise<Response>): void;
  fail(times: number, error?: Error): void;
}

export function fakeWorker(): FakeWorker {
  const calls: FakeWorkerCall[] = [];
  const responders: Array<{ path: string | RegExp; handler: (call: FakeWorkerCall) => Response | Promise<Response> }> = [];
  let failures = 0;
  let failure: Error = new Error("ECONNREFUSED");
  const fetchImpl = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const path = new URL(url).pathname + new URL(url).search;
    const headers = Object.fromEntries(Object.entries(init?.headers ?? {}).map(([k, v]) => [k.toLowerCase(), String(v)]));
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const call = { method: init?.method ?? "GET", path, headers, body };
    calls.push(call);
    if (failures > 0) {
      failures -= 1;
      throw failure;
    }
    const responder = responders.find((r) => (typeof r.path === "string" ? path.startsWith(r.path) : r.path.test(path)));
    if (responder) return responder.handler(call);
    return Response.json({ ok: true });
  }) as typeof fetch;
  return {
    calls,
    fetch: fetchImpl,
    respond: (path, handler) => responders.unshift({ path, handler }),
    fail: (times, error) => {
      failures = times;
      if (error) failure = error;
    },
  };
}

export function testConfig(overrides: Partial<BridgeConfig> = {}): BridgeConfig {
  return {
    workerUrl: "https://worker.test",
    bridgeToken: "bridge-secret",
    herdrSocketPath: "/nonexistent.sock",
    machineId: "test-machine",
    pollIntervalSeconds: 1,
    pollWaitSeconds: 0,
    jobTimeoutMs: 5_000,
    agentStartTimeoutMs: 3_001,
    agentSettleMs: 0,
    readLines: 40,
    keepWorkspaces: "never",
    workspaceCwd: "/tmp",
    workspaceLabelPrefix: "bridge",
    telemetryEnabled: true,
    dispatchEnabled: true,
    maxBackoffMs: 20,
    ...overrides,
  };
}

export function captureLogger(): { log: Logger; lines: Array<Record<string, unknown>> } {
  const lines: Array<Record<string, unknown>> = [];
  const log = createLogger("test", { level: "debug", sink: (line) => lines.push(JSON.parse(line)) });
  return { log, lines };
}

export function until(predicate: () => boolean, timeoutMs = 3_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (predicate()) return resolve();
      if (Date.now() > deadline) return reject(new Error("until() timed out"));
      setTimeout(tick, 10);
    };
    tick();
  });
}
