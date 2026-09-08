/**
 * glim-think control-plane client (outbound only).
 *
 * Auth: `Authorization: Bearer <GLIM_BRIDGE_TOKEN>` — the worker's
 * HERDR_BRIDGE_TOKEN, honoured on /bridge/* (middleware/access.ts) and on
 * POST /feed/beats (feed/beats.ts). Never the global INTERNAL_TASK_TOKEN.
 */
export interface BridgeJob {
  job_id: string;
  machine_id: string;
  agent_kind: string;
  prompt: string;
  campaign_id: string | null;
  status: string;
  attempts: number;
  created_at: number;
  claimed_at: number | null;
}

export type JobOutcomeStatus = "done" | "failed" | "blocked" | "timeout";

export interface Beat {
  beat_id: string;
  agent: string;
  summary: string;
  metrics?: Record<string, unknown>;
  ts?: number;
}

export interface JobResult {
  status: JobOutcomeStatus;
  output_excerpt?: string;
  beat?: Beat;
}

export class WorkerHttpError extends Error {
  readonly status: number;
  readonly path: string;
  readonly body: string;

  constructor(status: number, path: string, body: string) {
    super(`worker ${path} -> ${status}: ${body.slice(0, 200)}`);
    this.name = "WorkerHttpError";
    this.status = status;
    this.path = path;
    this.body = body;
  }
  /** 5xx and 429 are transient; 4xx otherwise means our request is wrong. */
  get retryable(): boolean {
    return this.status >= 500 || this.status === 429;
  }
}

export interface WorkerClientOptions {
  baseUrl: string;
  token: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export class WorkerClient {
  private readonly baseUrl: string;
  private readonly token: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(options: WorkerClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.token = options.token;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.timeoutMs = options.timeoutMs ?? 30_000;
  }

  private async request(method: string, path: string, body?: unknown, timeoutMs?: number): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs ?? this.timeoutMs);
    try {
      return await this.fetchImpl(`${this.baseUrl}${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${this.token}`,
          Accept: "application/json",
          ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timer);
    }
  }

  private async expectJson<T>(response: Response, path: string): Promise<T> {
    const text = await response.text();
    if (!response.ok) throw new WorkerHttpError(response.status, path, text);
    return JSON.parse(text || "{}") as T;
  }

  /** Poll for the oldest pending job; null on 204. */
  async nextJob(machineId: string, waitSeconds: number): Promise<BridgeJob | null> {
    const path = `/bridge/jobs/next?machine_id=${encodeURIComponent(machineId)}&wait_seconds=${waitSeconds}`;
    const response = await this.request("GET", path, undefined, (waitSeconds + 15) * 1000);
    if (response.status === 204) {
      await response.text().catch(() => undefined);
      return null;
    }
    const body = await this.expectJson<{ job: BridgeJob }>(response, path);
    return body.job;
  }

  async postResult(jobId: string, result: JobResult): Promise<{ ok: true; job_id: string; status: string; beat_id: string | null }> {
    const path = `/bridge/jobs/${encodeURIComponent(jobId)}/result`;
    return this.expectJson(await this.request("POST", path, result), path);
  }

  async postBeat(beat: Beat): Promise<{ ok: true; beat_id: string }> {
    return this.expectJson(await this.request("POST", "/feed/beats", beat), "/feed/beats");
  }
}
