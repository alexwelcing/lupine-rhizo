// CI-only, bounded diagnostic for the worker test typecheck. No tests are disabled.
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

if (process.platform !== "linux") throw new Error("Run this bounded diagnostic on the Linux CI runner");
const traceDir = mkdtempSync(join(tmpdir(), "glim-worker-typecheck-"));
const started = performance.now();
const child = spawnSync("bash", [
  "-c", 'ulimit -f 16384; exec "$@"', "bounded-worker-types",
  process.execPath, "node_modules/typescript/bin/tsc",
  "--noEmit", "--pretty", "false", "-p", "tsconfig.test.json",
  "--generateTrace", traceDir,
], { stdio: "inherit", timeout: 180_000, killSignal: "SIGKILL" });

const summary = {
  duration_ms: Math.round(performance.now() - started),
  status: child.status, signal: child.signal,
  error: child.error?.message ?? null,
  timed_out: child.error?.code === "ETIMEDOUT",
  trace_read_limit_bytes: 16 * 1024 * 1024,
  per_file_limit_kib: 16384,
  trace_bytes: null,
  pending_files: [],
  longest_checks: [],
  trace_error: null,
};
try {
  const path = join(traceDir, "trace.json");
  summary.trace_bytes = statSync(path).size;
  if (summary.trace_bytes > summary.trace_read_limit_bytes) throw new Error("trace exceeds read bound");
  const events = [];
  for (const line of readFileSync(path, "utf8").split("\n")) {
    try {
      const event = JSON.parse(line.trim().replace(/,$/, ""));
      if (event && typeof event === "object" && !Array.isArray(event)) events.push(event);
    } catch { /* The killed compiler can leave an incomplete final event. */ }
  }
  const pending = [];
  for (const event of events) {
    if (event.name !== "checkSourceFile") continue;
    if (event.ph === "B" && typeof event.args?.path === "string") pending.push(event.args.path);
    if (event.ph === "E") pending.pop();
  }
  summary.pending_files = pending.slice(-8);
  summary.longest_checks = events
    .filter(e => e.ph === "X" && typeof e.dur === "number" && e.cat === "check")
    .sort((a, b) => b.dur - a.dur).slice(0,8)
    .map(e => ({ name: e.name, duration_us: e.dur, path: e.args?.path ?? null, pos: e.args?.pos ?? null }));
} catch (error) {
  summary.trace_error = error instanceof Error ? error.message : String(error);
}
console.log("WORKER_TYPECHECK_DIAGNOSTIC " + JSON.stringify(summary));
process.exit(child.error ? (summary.timed_out ? 124 : 1) : (child.status ?? 1));
