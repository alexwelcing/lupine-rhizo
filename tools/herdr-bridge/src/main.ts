#!/usr/bin/env node
/**
 * herdr-bridge daemon entrypoint. Run with `node src/main.ts` (Node ≥ 22.18
 * strips types natively). See README.md for env vars.
 */
import { describeConfig, loadConfig } from "./config.ts";
import { Dispatcher } from "./dispatch.ts";
import { HerdrClient } from "./herdr.ts";
import { createLogger, errorFields } from "./log.ts";
import { TelemetryLoop } from "./telemetry.ts";
import { WorkerClient, type BridgeJob } from "./worker.ts";

async function main(): Promise<number> {
  const log = createLogger("herdr-bridge");
  let config;
  try {
    config = loadConfig();
  } catch (e) {
    log.error("config_invalid", errorFields(e));
    return 2;
  }
  log.info("starting", describeConfig(config));

  const herdr = new HerdrClient({ socketPath: config.herdrSocketPath });
  const worker = new WorkerClient({ baseUrl: config.workerUrl, token: config.bridgeToken });

  // Neither side is required at boot — the loops reconnect with backoff —
  // but log the initial state so a misconfigured socket path is obvious.
  try {
    const pong = await herdr.ping();
    log.info("herdr_reachable", { version: pong.version, protocol: pong.protocol });
  } catch (e) {
    log.warn("herdr_unreachable_at_start", errorFields(e));
  }

  const controller = new AbortController();
  const jobPanes = new Map<string, { job_id: string; campaign_id: string | null }>();

  const telemetry = new TelemetryLoop({
    machineId: config.machineId,
    herdr,
    worker,
    log: log.child("telemetry"),
    maxBackoffMs: config.maxBackoffMs,
    jobForPane: (paneId) => jobPanes.get(paneId),
  });
  const dispatcher = new Dispatcher({
    config,
    herdr,
    worker,
    log: log.child("dispatch"),
    onJobPane: (paneId: string, job: BridgeJob | null) => {
      if (job) jobPanes.set(paneId, { job_id: job.job_id, campaign_id: job.campaign_id });
      else {
        jobPanes.delete(paneId);
        telemetry.forget(paneId);
      }
    },
  });

  const shutdown = (signal: string) => {
    if (controller.signal.aborted) return;
    log.info("shutdown_requested", { signal });
    controller.abort();
  };
  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  const statsTimer = setInterval(() => {
    log.info("stats", { telemetry: telemetry.snapshot, dispatch: dispatcher.snapshot });
  }, 60_000);
  statsTimer.unref();

  const loops: Promise<void>[] = [];
  if (config.telemetryEnabled) loops.push(telemetry.run(controller.signal));
  else log.warn("telemetry_disabled");
  if (config.dispatchEnabled) loops.push(dispatcher.run(controller.signal));
  else log.warn("dispatch_disabled");
  await Promise.all(loops);
  clearInterval(statsTimer);
  log.info("stopped", { telemetry: telemetry.snapshot, dispatch: dispatcher.snapshot });
  return 0;
}

main().then(
  (code) => process.exit(code),
  (e) => {
    process.stderr.write(`${JSON.stringify({ level: "error", event: "fatal", ...errorFields(e) })}\n`);
    process.exit(1);
  },
);
