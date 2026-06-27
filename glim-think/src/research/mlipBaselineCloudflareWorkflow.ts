import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import type { Env } from "../types";
import {
  completeSmokeMlipBaselineRun,
  dispatchQueuedMlipBaselineCells,
  finalizeMlipBaselineRun,
  getMlipBaselineRun,
  markMlipBaselineRunStatus,
  preflightMlipBaselineRun,
  retireStaleMlipBaselineCells,
  type MlipBaselineGridWorkflowParams,
  type MlipBaselineSummary,
} from "./mlipBaselineGrid";

interface WaveState {
  wave: number;
  dispatched: number;
  skipped: number;
  active: number;
  capacity: number;
}

interface WorkflowDurableState {
  preflight_ok: boolean;
  profile: string;
  max_waves: number;
  waves_completed: number;
  last_summary: MlipBaselineSummary | null;
  wave_history: WaveState[];
  completed: boolean;
  error: string | null;
}

const DEFAULT_RETRY = {
  limit: 3,
  delay: "10 seconds",
  backoff: "exponential" as const,
};

const LIGHT_RETRY = {
  limit: 2,
  delay: "5 seconds",
  backoff: "exponential" as const,
};

const DISPATCH_RETRY = {
  limit: 5,
  delay: "15 seconds",
  backoff: "exponential" as const,
};

export class MlipBaselineGridWorkflow extends WorkflowEntrypoint<Env, MlipBaselineGridWorkflowParams> {
  async run(
    event: Readonly<WorkflowEvent<MlipBaselineGridWorkflowParams>>,
    step: WorkflowStep,
  ): Promise<unknown> {
    const runId = event.payload.run_id;

    // Initialize durable workflow state
    const durableState = await step.do(
      `init-state ${runId}`,
      { retries: LIGHT_RETRY, timeout: "15 seconds" },
      async (): Promise<WorkflowDurableState> => ({
        preflight_ok: false,
        profile: "unknown",
        max_waves: 72,
        waves_completed: 0,
        last_summary: null,
        wave_history: [],
        completed: false,
        error: null,
      }),
    );

    // Preflight step: validate configuration and fixture readiness
    const preflight = await step.do(
      `preflight ${runId}`,
      { retries: DEFAULT_RETRY, timeout: "30 seconds" },
      async () => preflightMlipBaselineRun(this.env, runId),
    );

    // Persist preflight result into durable state
    await step.do(
      `persist-preflight ${runId}`,
      { retries: LIGHT_RETRY, timeout: "15 seconds" },
      async () => {
        durableState.preflight_ok = preflight.ok;
        durableState.profile = preflight.profile;
        return { preflight_ok: preflight.ok, profile: preflight.profile };
      },
    );

    // Smoke profile: run deterministic synthetic completion without external compute
    if (preflight.profile === "smoke") {
      const smokeResult = await step.do(
        `complete-smoke ${runId}`,
        { retries: DEFAULT_RETRY, timeout: "30 seconds" },
        async () => completeSmokeMlipBaselineRun(this.env, runId),
      );

      const finalState = await step.do(
        `finalize-smoke ${runId}`,
        { retries: DEFAULT_RETRY, timeout: "30 seconds" },
        async () => finalizeMlipBaselineRun(this.env, runId),
      );

      return {
        run_id: runId,
        profile: "smoke",
        smoke_completed: smokeResult.completed,
        final_state: finalState,
        workflow_state: { ...durableState, completed: true },
      };
    }

    // Mark run as actively running in the ledger
    await step.do(
      `mark-running ${runId}`,
      { retries: LIGHT_RETRY, timeout: "15 seconds" },
      async () => {
        await markMlipBaselineRunStatus(this.env, runId, "running");
        return { ok: true };
      },
    );

    // Load the initial grid state (cells, summary, run record)
    const initialState = await step.do(
      `load-state ${runId}`,
      { retries: DEFAULT_RETRY, timeout: "15 seconds" },
      async () => {
        const state = await getMlipBaselineRun(this.env, runId);
        if (!state) throw new Error(`MLIP baseline run '${runId}' not found`);
        return state;
      },
    );

    const maxWaves = Math.max(1, Math.trunc(initialState.run.max_poll_waves ?? 72));
    durableState.max_waves = maxWaves;

    // Main dispatch-and-poll loop with durable state after each wave
    for (let wave = 0; wave < maxWaves; wave += 1) {
      // Dispatch queued cells up to active capacity
      const dispatch = await step.do(
        `dispatch-wave-${wave + 1} ${runId}`,
        { retries: DISPATCH_RETRY, timeout: "60 seconds" },
        async () => dispatchQueuedMlipBaselineCells(this.env, runId),
      );

      // Load current summary to decide whether to continue or break
      const currentSummary = await step.do(
        `inspect-wave-${wave + 1} ${runId}`,
        { retries: DEFAULT_RETRY, timeout: "15 seconds" },
        async () => {
          const current = await getMlipBaselineRun(this.env, runId);
          if (!current) throw new Error(`MLIP baseline run '${runId}' not found`);
          return current.summary;
        },
      );

      // Persist wave outcome into durable state so resume picks up correctly
      await step.do(
        `persist-wave-${wave + 1} ${runId}`,
        { retries: LIGHT_RETRY, timeout: "15 seconds" },
        async () => {
          durableState.waves_completed = wave + 1;
          durableState.last_summary = currentSummary;
          durableState.wave_history.push({
            wave: wave + 1,
            dispatched: dispatch.dispatched.length,
            skipped: dispatch.skipped.length,
            active: dispatch.active,
            capacity: dispatch.capacity,
          });
          return { wave: wave + 1, summary: currentSummary };
        },
      );

      // Break early if all cells are resolved (completed or failed)
      if (currentSummary.cells_completed + currentSummary.cells_failed >= currentSummary.cells_total) {
        durableState.completed = true;
        break;
      }

      // Sleep before next poll wave; resumed instances get priority per CF docs
      await step.sleep(`sleep-wave-${wave + 1} ${runId}`, "5 minutes");
    }

    // Finalize: write reports, update ledger status, emit evaluations
    const finalState = await step.do(
      `finalize ${runId}`,
      { retries: DEFAULT_RETRY, timeout: "30 seconds" },
      async () => finalizeMlipBaselineRun(this.env, runId),
    );

    // Retire any stale queued/enqueued cells older than 14 days as cleanup
    await step.do(
      `retire-stale ${runId}`,
      { retries: LIGHT_RETRY, timeout: "30 seconds" },
      async () => {
        await retireStaleMlipBaselineCells(this.env, runId, { olderThanHours: 336, dryRun: false });
        return { ok: true };
      },
    );

    return {
      run_id: runId,
      preflight,
      workflow_state: durableState,
      final_state: finalState,
    };
  }
}
