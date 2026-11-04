// CI-only, bounded diagnostic for the worker test typecheck. No tests are disabled.
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

if (process.platform !== "linux") throw new Error("Run this bounded diagnostic on the Linux CI runner");
const traceDir = mkdtempSync(join(tmpdir(), "glim-worker-typecheck-"));
const profilePath = join(traceDir, "v8.log");
const started = performance.now();
const child = spawnSync("bash", [
  "-c", 'ulimit -f 16384; exec "$@"', "bounded-worker-types",
  process.execPath, "--prof", "--prof-sampling-interval=10000",
  "--no-logfile-per-isolate", `--logfile=${profilePath}`,
  "node_modules/typescript/bin/tsc",
  "--noEmit", "--pretty", "false", "-p", "tsconfig.test.json",
  "--generateTrace", traceDir,
], { stdio: "inherit", timeout: 165_000, killSignal: "SIGKILL" });

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
  profile: null,
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

if (child.error || child.status !== 0) {
  // Reserve the final 15 seconds of the same three-minute diagnostic budget
  // for V8's built-in reader. This does not modify or bypass the compiler.
  try {
    const bytes = statSync(profilePath).size;
    if (bytes > summary.trace_read_limit_bytes) throw new Error("profile exceeds read bound");
    const remaining = Math.floor(180_000 - (performance.now() - started));
    if (remaining < 1) throw new Error("no profile processing budget remains");
    const processed = spawnSync(process.execPath, [
      "--prof-process", "--call-graph-size=20", profilePath,
    ], {
      encoding: "utf8", timeout: remaining, killSignal: "SIGKILL",
      maxBuffer: 1024 * 1024,
    });
    const output = processed.stdout ?? "";
    const heavyIndex = output.indexOf(" [Bottom up (heavy) profile]:");
    summary.profile = {
      bytes, status: processed.status, signal: processed.signal,
      error: processed.error?.message ?? null,
      stdout_bytes: Buffer.byteLength(output),
      stderr: (processed.stderr ?? "").slice(0, 1000),
      overview: output.slice(0, heavyIndex < 0 ? 12000 : Math.min(heavyIndex, 12000)),
      heavy: heavyIndex < 0 ? null : output.slice(heavyIndex, heavyIndex + 40000),
      truncated: heavyIndex >= 0 && output.length > heavyIndex + 40000,
    };
  } catch (error) {
    summary.profile = { error: error instanceof Error ? error.message : String(error) };
  }
}
summary.duration_ms = Math.round(performance.now() - started);

console.log("WORKER_TYPECHECK_DIAGNOSTIC " + JSON.stringify(summary));
process.exit(child.error ? (summary.timed_out ? 124 : 1) : (child.status ?? 1));
