/**
 * Dispatch flow: poll worker → herdr workspace → agent → prompt → result.
 *
 * One job at a time per bridge (herdr agents are interactive; parallelism is
 * a deliberate later step once workspaces-per-job is proven). Each job:
 *   1. workspace.create (label bridge-<job_id prefix>)
 *   2. agent.start(kind) → agent.wait(idle) → settle grace
 *   3. agent.prompt(text, wait) — explicit timeout, always
 *   4. agent.read(recent_unwrapped) → excerpt
 *   5. POST /bridge/jobs/:id/result with a closing beat
 *   6. workspace.close per BRIDGE_KEEP_WORKSPACES
 */
import type { BridgeConfig } from "./config.ts";
import { isHerdrError, type AgentStatus, type HerdrClient } from "./herdr.ts";
import { backoffMs, errorFields, sleep, type Logger } from "./log.ts";
import { WorkerHttpError, type BridgeJob, type JobOutcomeStatus, type JobResult, type WorkerClient } from "./worker.ts";

export interface DispatchOptions {
  config: BridgeConfig;
  herdr: HerdrClient;
  worker: WorkerClient;
  log: Logger;
  now?: () => number;
  /** Called with the pane owning a job so telemetry can annotate beats. */
  onJobPane?: (paneId: string, job: BridgeJob | null) => void;
}

export interface DispatchStats {
  polled: number;
  claimed: number;
  completed: number;
  failed: number;
  resultPostFailures: number;
}

export interface JobOutcome {
  status: JobOutcomeStatus;
  output_excerpt: string;
  agent_status: AgentStatus | "unknown";
  workspace_id: string | null;
  pane_id: string | null;
  duration_ms: number;
  error?: string;
}

const EXCERPT_MAX = 4_000;

export function agentNameFor(job: BridgeJob): string {
  // herdr names: [a-z][a-z0-9_-]{0,31}, unique among live agents.
  const tail = job.job_id.toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 20) || "job";
  return `bridge-${tail}`.slice(0, 32);
}

/** Strip terminal furniture so the excerpt is mostly the agent's words. */
export function cleanExcerpt(text: string, max = EXCERPT_MAX): string {
  const lines = text
    .split("\n")
    .map((l) => l.replace(/[\u2500-\u257f]+/g, "").trimEnd())
    .filter((l) => l.trim().length > 0);
  const joined = lines.join("\n");
  return joined.length > max ? joined.slice(joined.length - max) : joined;
}

export function outcomeFromAgentStatus(status: AgentStatus | undefined): JobOutcomeStatus {
  if (status === "blocked") return "blocked";
  if (status === "done" || status === "idle") return "done";
  return "failed";
}

/**
 * Both reads are tails of the same scrollback. Find the longest run of
 * lines ending the snapshot (`before`) that also starts `after`, allowing
 * up to `maxRewritten` trailing snapshot lines to have been redrawn (the
 * `❯` input line is overwritten by the echoed prompt), and return only the
 * lines after that run. No usable overlap → return `after` unchanged.
 */
export function newOutputSince(before: string, after: string, maxRewritten = 3): string {
  const b = before.split("\n").map((l) => l.trimEnd());
  const a = after.split("\n").map((l) => l.trimEnd());
  if (!before.trim() || !after.trim()) return after;
  let best = 0;
  for (let skip = 0; skip <= maxRewritten && skip < b.length; skip++) {
    const tail = b.slice(0, b.length - skip);
    for (let overlap = Math.min(a.length, tail.length); overlap > best; overlap--) {
      let ok = false;
      for (let i = 0; i < overlap; i++) {
        if (a[i] !== tail[tail.length - overlap + i]) { ok = false; break; }
        ok = ok || a[i].length > 0;
      }
      if (ok) { best = overlap; break; }
    }
  }
  return best > 0 ? a.slice(best).join("\n") : after;
}

export class Dispatcher {
  private readonly stats: DispatchStats = { polled: 0, claimed: 0, completed: 0, failed: 0, resultPostFailures: 0 };

  private readonly options: DispatchOptions;

  constructor(options: DispatchOptions) {
    this.options = options;
  }

  get snapshot(): DispatchStats {
    return { ...this.stats };
  }

  /** Runs until aborted. Never throws. */
  async run(signal: AbortSignal): Promise<void> {
    const { config, log } = this.options;
    let pollFailures = 0;
    while (!signal.aborted) {
      let job: BridgeJob | null = null;
      try {
        this.stats.polled += 1;
        job = await this.options.worker.nextJob(config.machineId, config.pollWaitSeconds);
        pollFailures = 0;
      } catch (e) {
        const wait = backoffMs(pollFailures++, 1_000, config.maxBackoffMs);
        log.warn("poll_failed", { ...errorFields(e), retry_in_ms: wait, attempt: pollFailures });
        await sleep(wait, signal);
        continue;
      }
      if (!job) {
        await sleep(config.pollIntervalSeconds * 1000, signal);
        continue;
      }
      this.stats.claimed += 1;
      log.info("job_claimed", { job_id: job.job_id, agent_kind: job.agent_kind, campaign_id: job.campaign_id, attempts: job.attempts });
      const outcome = await this.runJob(job, signal);
      await this.report(job, outcome, signal);
    }
  }

  /**
   * A freshly created workspace's shell may not be at its prompt when we
   * ask herdr to start the agent (`agent_pane_busy`, observed in the
   * live smoke test 100–300ms after workspace.create). Retry within the agent
   * start budget; any other error propagates.
   */
  private async startAgentWithRetry(name: string, kind: string, paneId: string, signal?: AbortSignal): Promise<void> {
    const { config, herdr, log } = this.options;
    const deadline = Date.now() + config.agentStartTimeoutMs;
    for (let attempt = 0; ; attempt++) {
      try {
        await herdr.agentStart({ name, kind, pane_id: paneId, timeout_ms: config.agentStartTimeoutMs });
        if (attempt > 0) log.info("agent_start_retry_succeeded", { pane_id: paneId, attempt });
        return;
      } catch (e) {
        if (!isHerdrError(e, "agent_pane_busy") || Date.now() + 250 > deadline || signal?.aborted) throw e;
        if (attempt === 0) log.debug("agent_start_waiting_for_shell", { pane_id: paneId });
        await sleep(250, signal);
      }
    }
  }

  async runJob(job: BridgeJob, signal?: AbortSignal): Promise<JobOutcome> {
    const { config, herdr, log } = this.options;
    const started = Date.now();
    const name = agentNameFor(job);
    let workspaceId: string | null = null;
    let paneId: string | null = null;
    let agentStatus: AgentStatus | "unknown" = "unknown";
    let excerpt = "";
    let status: JobOutcomeStatus = "failed";
    let error: string | undefined;

    try {
      const ws = await herdr.workspaceCreate({
        cwd: config.workspaceCwd,
        label: `${config.workspaceLabelPrefix}-${job.job_id.slice(0, 8)}`,
        focus: false,
        env: { GLIM_BRIDGE_JOB_ID: job.job_id, GLIM_BRIDGE_MACHINE_ID: config.machineId },
      });
      workspaceId = ws.workspace.workspace_id;
      paneId = ws.root_pane.pane_id;
      this.options.onJobPane?.(paneId, job);
      log.info("workspace_created", { job_id: job.job_id, workspace_id: workspaceId, pane_id: paneId });

      await this.startAgentWithRetry(name, job.agent_kind, paneId, signal);
      const ready = await herdr.agentWait(name, ["idle"], config.agentStartTimeoutMs);
      agentStatus = ready.agent.agent_status;
      log.info("agent_ready", { job_id: job.job_id, agent: name, kind: job.agent_kind, status: agentStatus });
      // Some agents redraw right after first idle; a short grace avoids a
      // swallowed first keystroke (observed with hermes: prompt sent at t+0
      // stalled, at t+3s worked).
      if (config.agentSettleMs > 0) await sleep(config.agentSettleMs, signal);

      // Snapshot the pane so the excerpt is the agent's answer, not its
      // startup banner.
      let before = "";
      try {
        before = (await herdr.agentRead(name, config.readLines)).read.text;
      } catch {
        // best effort — fall back to the full tail
      }

      let prompted;
      try {
        prompted = await herdr.agentPrompt(name, job.prompt, config.jobTimeoutMs);
      } catch (e) {
        if (isHerdrError(e, "agent_prompt_stalled")) {
          // The text was submitted but no activity was observed. Nudge with
          // Enter once and wait for a settled state instead of failing.
          log.warn("prompt_stalled_retrying_enter", { job_id: job.job_id });
          await herdr.agentSendKeys(name, ["enter"]);
          prompted = await herdr.agentWait(name, undefined, config.jobTimeoutMs);
        } else {
          throw e;
        }
      }
      agentStatus = prompted.agent.agent_status;
      status = outcomeFromAgentStatus(agentStatus);

      const read = await herdr.agentRead(name, config.readLines);
      excerpt = cleanExcerpt(newOutputSince(before, read.read.text));
      if (status === "blocked") {
        error = "agent is waiting on an approval/question dialog; left running for a human";
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      if (isHerdrError(e, "timeout")) status = "timeout";
      else if (isHerdrError(e, "agent_blocked")) status = "blocked";
      else status = "failed";
      log.error("job_failed", { job_id: job.job_id, status, ...errorFields(e) });
      if (paneId && !excerpt) {
        try {
          const read = await herdr.agentRead(name, config.readLines);
          excerpt = cleanExcerpt(read.read.text);
        } catch {
          // best effort
        }
      }
    }

    const keep = config.keepWorkspaces === "always" || (config.keepWorkspaces === "failed" && status !== "done");
    if (workspaceId && !keep) {
      try {
        await herdr.workspaceClose(workspaceId);
        log.info("workspace_closed", { job_id: job.job_id, workspace_id: workspaceId });
      } catch (e) {
        log.warn("workspace_close_failed", { job_id: job.job_id, workspace_id: workspaceId, ...errorFields(e) });
      }
    } else if (workspaceId) {
      log.info("workspace_kept", { job_id: job.job_id, workspace_id: workspaceId, status });
    }
    if (paneId) this.options.onJobPane?.(paneId, null);

    if (status === "done") this.stats.completed += 1;
    else this.stats.failed += 1;
    return { status, output_excerpt: excerpt, agent_status: agentStatus, workspace_id: workspaceId, pane_id: paneId, duration_ms: Date.now() - started, error };
  }

  buildResult(job: BridgeJob, outcome: JobOutcome): JobResult {
    const now = this.options.now ?? (() => Math.floor(Date.now() / 1000));
    const ts = now();
    return {
      status: outcome.status,
      output_excerpt: outcome.output_excerpt,
      beat: {
        beat_id: `herdr-job:${job.job_id}:${job.attempts}:${outcome.status}`,
        agent: `herdr-bridge/${this.options.config.machineId}`,
        summary: `job ${job.job_id.slice(0, 8)} ${outcome.status} (${job.agent_kind}, ${Math.round(outcome.duration_ms / 1000)}s)`,
        ts,
        metrics: {
          source: "herdr-bridge",
          machine_id: this.options.config.machineId,
          job_id: job.job_id,
          agent_kind: job.agent_kind,
          status: outcome.status === "done" ? "completed" : "failed",
          job_status: outcome.status,
          agent_status: outcome.agent_status,
          duration_ms: outcome.duration_ms,
          attempt: job.attempts,
          ...(outcome.workspace_id ? { workspace_id: outcome.workspace_id } : {}),
          ...(outcome.pane_id ? { pane_id: outcome.pane_id } : {}),
          ...(outcome.error ? { error: outcome.error.slice(0, 500) } : {}),
        },
      },
    };
  }

  /** Post the result with retries; gives up only on a non-retryable 4xx. */
  async report(job: BridgeJob, outcome: JobOutcome, signal?: AbortSignal): Promise<boolean> {
    const { log, config } = this.options;
    const result = this.buildResult(job, outcome);
    for (let attempt = 0; ; attempt++) {
      try {
        const response = await this.options.worker.postResult(job.job_id, result);
        log.info("job_reported", { job_id: job.job_id, status: outcome.status, beat_id: response.beat_id, duration_ms: outcome.duration_ms });
        return true;
      } catch (e) {
        if (e instanceof WorkerHttpError && !e.retryable) {
          this.stats.resultPostFailures += 1;
          log.error("job_report_rejected", { job_id: job.job_id, status: e.status, body: e.body.slice(0, 300) });
          return false;
        }
        if (signal?.aborted) {
          this.stats.resultPostFailures += 1;
          log.error("job_report_abandoned_on_shutdown", { job_id: job.job_id, ...errorFields(e) });
          return false;
        }
        const wait = backoffMs(attempt, 1_000, config.maxBackoffMs);
        log.warn("job_report_failed", { job_id: job.job_id, ...errorFields(e), retry_in_ms: wait, attempt });
        await sleep(wait, signal);
      }
    }
  }
}
