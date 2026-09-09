/**
 * Minimal herdr socket client.
 *
 * Protocol (herdr 0.9.0, protocol 22, `herdr api schema --json`):
 *   - Unix socket, newline-delimited JSON.
 *   - Request: {id, method, params}. Response: {id, result} | {id, error:{code,message}}.
 *   - The server serves ONE request per connection and closes it after the
 *     reply (observed empirically; a second request on the same socket is
 *     reset). `events.subscribe` is the exception: the connection stays open
 *     and streams {event, data} envelopes after a {result:{type:"subscription_started"}}.
 *
 * Only the methods the bridge needs are typed. Everything else is reachable
 * through `call()`.
 */
import { createConnection, type Socket } from "node:net";

export type AgentStatus = "idle" | "working" | "blocked" | "done" | "unknown";

export interface HerdrError extends Error {
  code: string;
}

export function isHerdrError(e: unknown, code?: string): e is HerdrError {
  return e instanceof Error && typeof (e as HerdrError).code === "string" && (code === undefined || (e as HerdrError).code === code);
}

function herdrError(code: string, message: string): HerdrError {
  const err = new Error(message) as HerdrError;
  err.name = "HerdrError";
  err.code = code;
  return err;
}

export interface PaneRef {
  pane_id: string;
  workspace_id: string;
  tab_id: string;
}

export interface WorkspaceCreateResult {
  type: "workspace_created";
  workspace: { workspace_id: string; label: string };
  tab: { tab_id: string };
  root_pane: PaneRef & { agent_status: AgentStatus };
}

export interface AgentInfo extends PaneRef {
  name?: string | null;
  agent?: string | null;
  agent_status: AgentStatus;
  interactive_ready?: boolean;
  launch_pending?: boolean;
}

export interface AgentReadResult {
  type: "pane_read";
  read: PaneRef & { text: string; revision: number; truncated: boolean };
}

export interface AgentStatusChangedEvent {
  pane_id: string;
  workspace_id: string;
  agent_status: AgentStatus;
  agent?: string | null;
  display_agent?: string | null;
  title?: string | null;
}

export type Subscription =
  | { type: "pane.agent_status_changed"; pane_id: string; agent_status?: AgentStatus | null }
  | { type: "pane.agent_detected" }
  | { type: "pane.created" }
  | { type: "pane.exited" }
  | { type: "pane.closed" }
  | { type: "workspace.created" }
  | { type: "workspace.closed" };

export interface EventEnvelope {
  event: string;
  data: Record<string, unknown>;
}

export interface HerdrClientOptions {
  socketPath: string;
  /** Default per-request timeout when the caller does not pass one. */
  requestTimeoutMs?: number;
  connectTimeoutMs?: number;
}

let requestSeq = 0;

export class HerdrClient {
  readonly socketPath: string;
  private readonly requestTimeoutMs: number;
  private readonly connectTimeoutMs: number;

  constructor(options: HerdrClientOptions) {
    this.socketPath = options.socketPath;
    this.requestTimeoutMs = options.requestTimeoutMs ?? 30_000;
    this.connectTimeoutMs = options.connectTimeoutMs ?? 5_000;
  }

  private connect(): Promise<Socket> {
    return new Promise((resolve, reject) => {
      const socket = createConnection({ path: this.socketPath });
      const timer = setTimeout(() => {
        socket.destroy();
        reject(herdrError("connect_timeout", `herdr socket connect timed out (${this.socketPath})`));
      }, this.connectTimeoutMs);
      socket.once("connect", () => {
        clearTimeout(timer);
        resolve(socket);
      });
      socket.once("error", (e: NodeJS.ErrnoException) => {
        clearTimeout(timer);
        reject(herdrError(e.code === "ENOENT" || e.code === "ECONNREFUSED" ? "server_not_running" : "socket_error",
          `herdr socket ${this.socketPath}: ${e.message}`));
      });
    });
  }

  /** One request, one connection, one reply. */
  async call<T = unknown>(method: string, params: Record<string, unknown> = {}, timeoutMs?: number): Promise<T> {
    const id = `herdr-bridge:${method}:${++requestSeq}`;
    const socket = await this.connect();
    const budget = timeoutMs ?? this.requestTimeoutMs;
    return new Promise<T>((resolve, reject) => {
      let buffer = "";
      let settled = false;
      const finish = (fn: () => void) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        socket.destroy();
        fn();
      };
      const timer = setTimeout(
        () => finish(() => reject(herdrError("timeout", `herdr ${method} timed out after ${budget}ms`))),
        budget,
      );
      socket.setEncoding("utf8");
      socket.on("data", (chunk: string) => {
        buffer += chunk;
        const nl = buffer.indexOf("\n");
        if (nl < 0) return;
        const line = buffer.slice(0, nl);
        let parsed: { id?: string; result?: T; error?: { code: string; message: string } };
        try {
          parsed = JSON.parse(line);
        } catch (e) {
          return finish(() => reject(herdrError("bad_response", `unparseable herdr reply: ${String(e)}`)));
        }
        if (parsed.error) {
          return finish(() => reject(herdrError(parsed.error!.code, parsed.error!.message)));
        }
        finish(() => resolve(parsed.result as T));
      });
      socket.on("error", (e) => finish(() => reject(herdrError("socket_error", e.message))));
      socket.on("close", () => finish(() => reject(herdrError("closed", `herdr closed the connection before replying to ${method}`))));
      socket.write(`${JSON.stringify({ id, method, params })}\n`);
    });
  }

  ping(): Promise<{ type: "pong"; version: string; protocol: number }> {
    return this.call("ping", {}, 5_000);
  }

  workspaceCreate(params: { cwd: string; label: string; focus?: boolean; env?: Record<string, string> }): Promise<WorkspaceCreateResult> {
    return this.call("workspace.create", { focus: false, ...params });
  }

  workspaceClose(workspaceId: string): Promise<{ type: "ok" }> {
    return this.call("workspace.close", { workspace_id: workspaceId });
  }

  /**
   * agent.start returns immediately with launch_pending=true over the socket
   * (unlike the CLI, which blocks on readiness). Follow with agentWait(idle).
   * Right after workspace.create the shell may not be at its prompt yet and
   * herdr answers `agent_pane_busy`; callers should retry briefly.
   */
  agentStart(params: { name: string; kind: string; pane_id: string; args?: string[]; timeout_ms?: number }): Promise<{ type: "agent_started"; agent: AgentInfo }> {
    return this.call("agent.start", params);
  }

  paneList(workspaceId?: string): Promise<{ type: "pane_list"; panes: Array<PaneRef & { agent?: string | null; agent_status: AgentStatus }> }> {
    return this.call("pane.list", workspaceId ? { workspace_id: workspaceId } : {});
  }

  agentWait(target: string, until: AgentStatus[] | undefined, timeoutMs: number): Promise<{ type: "agent_info"; agent: AgentInfo }> {
    const params: Record<string, unknown> = { target, timeout_ms: timeoutMs };
    if (until) params.until = until;
    return this.call("agent.wait", params, timeoutMs + 5_000);
  }

  /** Submit a prompt and wait for the first settled idle/done/blocked state. */
  agentPrompt(target: string, text: string, timeoutMs: number): Promise<{ type: "agent_prompted"; agent: AgentInfo }> {
    return this.call("agent.prompt", { target, text, wait: { timeout_ms: timeoutMs } }, timeoutMs + 5_000);
  }

  agentRead(target: string, lines: number): Promise<AgentReadResult> {
    return this.call("agent.read", { target, source: "recent_unwrapped", lines, strip_ansi: true });
  }

  agentGet(target: string): Promise<{ type: "agent_info"; agent: AgentInfo }> {
    return this.call("agent.get", { target });
  }

  agentSendKeys(target: string, keys: string[]): Promise<{ type: "ok" }> {
    return this.call("agent.send_keys", { target, keys });
  }

  /**
   * Long-lived subscription. Resolves once the server acknowledges; the
   * returned handle emits envelopes via `onEvent` until `close()` or the
   * server drops the socket (then `onClose` fires with the reason).
   */
  subscribe(
    subscriptions: Subscription[],
    onEvent: (envelope: EventEnvelope) => void,
    onClose: (reason: Error | null) => void,
  ): Promise<{ close(): void }> {
    return new Promise((resolve, reject) => {
      const id = `herdr-bridge:events.subscribe:${++requestSeq}`;
      this.connect().then((socket) => {
        let buffer = "";
        let started = false;
        let closed = false;
        const startTimer = setTimeout(() => {
          if (!started) {
            socket.destroy();
            reject(herdrError("timeout", "events.subscribe was not acknowledged"));
          }
        }, this.connectTimeoutMs);
        socket.setEncoding("utf8");
        socket.on("data", (chunk: string) => {
          buffer += chunk;
          let nl: number;
          while ((nl = buffer.indexOf("\n")) >= 0) {
            const line = buffer.slice(0, nl);
            buffer = buffer.slice(nl + 1);
            if (!line.trim()) continue;
            let parsed: { id?: string; result?: { type?: string }; error?: { code: string; message: string }; event?: string; data?: Record<string, unknown> };
            try {
              parsed = JSON.parse(line);
            } catch {
              continue;
            }
            if (!started) {
              clearTimeout(startTimer);
              if (parsed.error) {
                socket.destroy();
                return reject(herdrError(parsed.error.code, parsed.error.message));
              }
              started = true;
              resolve({ close: () => { closed = true; socket.destroy(); } });
              continue;
            }
            if (parsed.event && parsed.data) onEvent({ event: parsed.event, data: parsed.data });
          }
        });
        socket.on("error", (e) => { if (started && !closed) onClose(e); });
        socket.on("close", () => { if (started && !closed) onClose(null); });
        socket.write(`${JSON.stringify({ id, method: "events.subscribe", params: { subscriptions } })}\n`);
      }, reject);
    });
  }
}
