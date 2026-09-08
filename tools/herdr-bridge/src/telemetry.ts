/**
 * Telemetry flow: herdr events.subscribe → beat per agent-status transition
 * → POST /feed/beats.
 *
 * Beats are buffered in memory and flushed by a single sender so a worker
 * outage never blocks the herdr event loop. On flush failure the beat is
 * retried with backoff; the buffer is bounded (oldest dropped, counted) so a
 * long outage cannot grow without limit. beat_id is deterministic per
 * (machine, pane, state_change) so a retried POST is idempotent server-side
 * (lab_beats ON CONFLICT DO NOTHING).
 */
import type { AgentStatus, AgentStatusChangedEvent, EventEnvelope, HerdrClient } from "./herdr.ts";
import { backoffMs, errorFields, sleep, type Logger } from "./log.ts";
import { WorkerHttpError, type Beat, type WorkerClient } from "./worker.ts";

export interface TelemetryOptions {
  machineId: string;
  herdr: HerdrClient;
  worker: WorkerClient;
  log: Logger;
  maxBuffered?: number;
  maxBackoffMs?: number;
  /** Optional hook so the dispatcher can annotate beats with job ids. */
  jobForPane?: (paneId: string) => { job_id: string; campaign_id: string | null } | undefined;
  now?: () => number;
}

export interface TelemetryStats {
  received: number;
  sent: number;
  dropped: number;
  failed: number;
  buffered: number;
  reconnects: number;
}

export function transitionBeat(
  machineId: string,
  data: AgentStatusChangedEvent,
  previous: AgentStatus | undefined,
  seq: number,
  nowSeconds: number,
  job?: { job_id: string; campaign_id: string | null },
): Beat {
  const from = previous ?? "unknown";
  const agentKind = data.agent ?? data.display_agent ?? "unknown";
  return {
    beat_id: `herdr:${machineId}:${data.pane_id}:${seq}:${nowSeconds}`,
    agent: `herdr-bridge/${machineId}`,
    summary: `${agentKind} ${data.pane_id} ${from} -> ${data.agent_status}`,
    ts: nowSeconds,
    metrics: {
      source: "herdr-bridge",
      machine_id: machineId,
      pane_id: data.pane_id,
      workspace_id: data.workspace_id,
      agent_kind: agentKind,
      from_status: from,
      to_status: data.agent_status,
      transition: `${from}->${data.agent_status}`,
      ...(job ? { job_id: job.job_id, ...(job.campaign_id ? { campaign_id: job.campaign_id } : {}) } : {}),
    },
  };
}

export class TelemetryLoop {
  private readonly buffer: Beat[] = [];
  private readonly lastStatus = new Map<string, AgentStatus>();
  private readonly stats: TelemetryStats = { received: 0, sent: 0, dropped: 0, failed: 0, buffered: 0, reconnects: 0 };
  private seq = 0;
  private wake: (() => void) | null = null;
  private stopped = false;
  private subscription: { close(): void } | null = null;

  private readonly options: TelemetryOptions;

  constructor(options: TelemetryOptions) {
    this.options = options;
  }

  get snapshot(): TelemetryStats {
    return { ...this.stats, buffered: this.buffer.length };
  }

  /** Feed one herdr envelope (public for tests and for the dispatcher). */
  ingest(envelope: EventEnvelope): void {
    if (envelope.event !== "pane.agent_status_changed") return;
    const data = envelope.data as unknown as AgentStatusChangedEvent;
    if (typeof data.pane_id !== "string" || typeof data.agent_status !== "string") return;
    const previous = this.lastStatus.get(data.pane_id);
    if (previous === data.agent_status) return;
    this.lastStatus.set(data.pane_id, data.agent_status);
    this.stats.received += 1;
    const now = this.options.now ?? (() => Math.floor(Date.now() / 1000));
    const beat = transitionBeat(this.options.machineId, data, previous, ++this.seq, now(), this.options.jobForPane?.(data.pane_id));
    const max = this.options.maxBuffered ?? 1_000;
    if (this.buffer.length >= max) {
      this.buffer.shift();
      this.stats.dropped += 1;
      this.options.log.warn("beat_dropped_buffer_full", { max });
    }
    this.buffer.push(beat);
    this.wake?.();
  }

  forget(paneId: string): void {
    this.lastStatus.delete(paneId);
  }

  /** Runs until the signal aborts. Never throws. */
  async run(signal: AbortSignal): Promise<void> {
    const sender = this.sendLoop(signal);
    const subscriber = this.subscribeLoop(signal);
    await Promise.all([sender, subscriber]);
  }

  private async subscribeLoop(signal: AbortSignal): Promise<void> {
    let attempt = 0;
    const log = this.options.log.child("subscribe");
    while (!signal.aborted && !this.stopped) {
      try {
        // herdr 0.9.0 only accepts `pane.agent_status_changed` with an
        // explicit pane_id, so enumerate panes and subscribe each; a
        // `pane.created` event (any pane, no id filter) makes us rebuild
        // the subscription so new job panes are covered.
        const { panes } = await this.options.herdr.paneList();
        let resolveRebuild: () => void = () => undefined;
        const rebuild = new Promise<void>((r) => { resolveRebuild = r; });
        this.subscription = await this.options.herdr.subscribe(
          [
            { type: "pane.created" },
            { type: "pane.closed" },
            ...panes.map((p) => ({ type: "pane.agent_status_changed" as const, pane_id: p.pane_id })),
          ],
          (envelope) => {
            if (envelope.event === "pane_created" || envelope.event === "pane.created") return resolveRebuild();
            if (envelope.event === "pane_closed" || envelope.event === "pane.closed") {
              const pane = (envelope.data.pane as { pane_id?: string } | undefined)?.pane_id ?? envelope.data.pane_id;
              if (typeof pane === "string") this.lastStatus.delete(pane);
              return;
            }
            this.ingest(envelope);
          },
          (reason) => {
            log.warn("subscription_closed", reason ? errorFields(reason) : { reason: "server closed" });
            resolveRebuild();
          },
        );
        if (attempt > 0) this.stats.reconnects += 1;
        attempt = 0;
        log.info("subscribed", { socket: this.options.herdr.socketPath, panes: panes.length });
        await Promise.race([rebuild, abortPromise(signal)]);
        this.subscription?.close();
        this.subscription = null;
      } catch (e) {
        const wait = backoffMs(attempt++, 1_000, this.options.maxBackoffMs);
        log.warn("subscribe_failed", { ...errorFields(e), retry_in_ms: wait, attempt });
        await sleep(wait, signal);
      }
    }
    this.subscription?.close();
  }

  private async sendLoop(signal: AbortSignal): Promise<void> {
    const log = this.options.log.child("send");
    let attempt = 0;
    while (!signal.aborted) {
      if (this.buffer.length === 0) {
        await new Promise<void>((resolve) => {
          this.wake = resolve;
          signal.addEventListener("abort", () => resolve(), { once: true });
        });
        this.wake = null;
        continue;
      }
      const beat = this.buffer[0];
      try {
        await this.options.worker.postBeat(beat);
        this.buffer.shift();
        this.stats.sent += 1;
        attempt = 0;
        log.debug("beat_sent", { beat_id: beat.beat_id, summary: beat.summary });
      } catch (e) {
        if (e instanceof WorkerHttpError && !e.retryable) {
          // Our payload is wrong (or the token is) — retrying cannot help; drop and surface.
          this.buffer.shift();
          this.stats.failed += 1;
          log.error("beat_rejected", { beat_id: beat.beat_id, status: e.status, body: e.body.slice(0, 200) });
          continue;
        }
        const wait = backoffMs(attempt++, 1_000, this.options.maxBackoffMs);
        log.warn("beat_send_failed", { ...errorFields(e), retry_in_ms: wait, buffered: this.buffer.length });
        await sleep(wait, signal);
      }
    }
    // Best-effort drain on shutdown (one pass, no retry).
    while (this.buffer.length > 0) {
      const beat = this.buffer.shift()!;
      try {
        await this.options.worker.postBeat(beat);
        this.stats.sent += 1;
      } catch (e) {
        this.stats.failed += 1;
        log.warn("beat_lost_on_shutdown", { beat_id: beat.beat_id, ...errorFields(e) });
      }
    }
  }
}

function abortPromise(signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve();
    signal.addEventListener("abort", () => resolve(), { once: true });
  });
}
