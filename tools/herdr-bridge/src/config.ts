/**
 * Bridge configuration — everything comes from the environment so one
 * daemon binary serves N machines with N env files.
 */
import { hostname } from "node:os";
import { join } from "node:path";

export interface BridgeConfig {
  workerUrl: string;
  bridgeToken: string;
  herdrSocketPath: string;
  machineId: string;
  pollIntervalSeconds: number;
  /** Long-poll hint passed to the worker (bounded server-side at 20s). */
  pollWaitSeconds: number;
  /** Max wall time for one job prompt (agent.prompt wait). */
  jobTimeoutMs: number;
  agentStartTimeoutMs: number;
  /** Grace after the agent reports idle before the prompt is submitted. */
  agentSettleMs: number;
  readLines: number;
  keepWorkspaces: "always" | "failed" | "never";
  workspaceCwd: string;
  /** Prefix for herdr workspace labels (`<prefix>-<job id prefix>`). */
  workspaceLabelPrefix: string;
  telemetryEnabled: boolean;
  dispatchEnabled: boolean;
  maxBackoffMs: number;
}

function intEnv(env: NodeJS.ProcessEnv, key: string, fallback: number, min = 0): number {
  const raw = env[key];
  if (raw === undefined || raw.trim() === "") return fallback;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < min) {
    throw new Error(`${key} must be an integer >= ${min} (got ${JSON.stringify(raw)})`);
  }
  return parsed;
}

function boolEnv(env: NodeJS.ProcessEnv, key: string, fallback: boolean): boolean {
  const raw = env[key]?.trim().toLowerCase();
  if (raw === undefined || raw === "") return fallback;
  return !["0", "false", "no", "off"].includes(raw);
}

export function defaultHerdrSocketPath(env: NodeJS.ProcessEnv = process.env): string {
  const home = env.HOME ?? env.USERPROFILE ?? "";
  const configHome = env.XDG_CONFIG_HOME ?? join(home, ".config");
  return join(configHome, "herdr", "herdr.sock");
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): BridgeConfig {
  const workerUrl = (env.GLIM_WORKER_URL ?? "").trim().replace(/\/+$/, "");
  if (!workerUrl) throw new Error("GLIM_WORKER_URL is required");
  const bridgeToken = (env.GLIM_BRIDGE_TOKEN ?? "").trim();
  if (!bridgeToken) throw new Error("GLIM_BRIDGE_TOKEN is required");
  const machineId = (env.MACHINE_ID ?? hostname()).trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(machineId)) {
    throw new Error("MACHINE_ID must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
  }
  const keep = (env.BRIDGE_KEEP_WORKSPACES ?? "failed").trim().toLowerCase();
  if (keep !== "always" && keep !== "failed" && keep !== "never") {
    throw new Error("BRIDGE_KEEP_WORKSPACES must be always, failed, or never");
  }
  return {
    workerUrl,
    bridgeToken,
    herdrSocketPath: (env.HERDR_SOCKET_PATH ?? "").trim() || defaultHerdrSocketPath(env),
    machineId,
    pollIntervalSeconds: intEnv(env, "POLL_INTERVAL_SECONDS", 15, 1),
    pollWaitSeconds: intEnv(env, "BRIDGE_POLL_WAIT_SECONDS", 15, 0),
    jobTimeoutMs: intEnv(env, "BRIDGE_JOB_TIMEOUT_MS", 30 * 60 * 1000, 5_000),
    agentStartTimeoutMs: intEnv(env, "BRIDGE_AGENT_START_TIMEOUT_MS", 60_000, 3_001),
    agentSettleMs: intEnv(env, "BRIDGE_AGENT_SETTLE_MS", 3_000, 0),
    readLines: intEnv(env, "BRIDGE_READ_LINES", 80, 1),
    keepWorkspaces: keep,
    workspaceCwd: (env.BRIDGE_WORKSPACE_CWD ?? "").trim() || process.cwd(),
    workspaceLabelPrefix: (env.BRIDGE_WORKSPACE_LABEL ?? "").trim() || "bridge",
    telemetryEnabled: boolEnv(env, "BRIDGE_TELEMETRY", true),
    dispatchEnabled: boolEnv(env, "BRIDGE_DISPATCH", true),
    maxBackoffMs: intEnv(env, "BRIDGE_MAX_BACKOFF_MS", 5 * 60 * 1000, 1_000),
  };
}

/** Redacted view for the startup log line. */
export function describeConfig(cfg: BridgeConfig): Record<string, unknown> {
  return { ...cfg, bridgeToken: `<${cfg.bridgeToken.length} chars>` };
}
