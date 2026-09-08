/**
 * Structured JSON logs on stdout, one object per line, so journald / a log
 * shipper can index them by `component` and `event`.
 */
export type LogLevel = "debug" | "info" | "warn" | "error";

export interface Logger {
  debug(event: string, fields?: Record<string, unknown>): void;
  info(event: string, fields?: Record<string, unknown>): void;
  warn(event: string, fields?: Record<string, unknown>): void;
  error(event: string, fields?: Record<string, unknown>): void;
  child(component: string): Logger;
}

const LEVELS: Record<LogLevel, number> = { debug: 10, info: 20, warn: 30, error: 40 };

export interface LoggerOptions {
  level?: LogLevel;
  sink?: (line: string) => void;
  base?: Record<string, unknown>;
}

export function errorFields(e: unknown): Record<string, unknown> {
  if (e instanceof Error) return { error: e.message, error_name: e.name };
  return { error: String(e) };
}

export function createLogger(component: string, options: LoggerOptions = {}): Logger {
  const level = options.level ?? ((process.env.BRIDGE_LOG_LEVEL as LogLevel | undefined) || "info");
  const threshold = LEVELS[level] ?? LEVELS.info;
  const sink = options.sink ?? ((line: string) => process.stdout.write(`${line}\n`));
  const base = options.base ?? {};

  function emit(lvl: LogLevel, event: string, fields?: Record<string, unknown>): void {
    if (LEVELS[lvl] < threshold) return;
    sink(JSON.stringify({ ts: new Date().toISOString(), level: lvl, component, event, ...base, ...fields }));
  }

  return {
    debug: (event, fields) => emit("debug", event, fields),
    info: (event, fields) => emit("info", event, fields),
    warn: (event, fields) => emit("warn", event, fields),
    error: (event, fields) => emit("error", event, fields),
    child: (sub) => createLogger(`${component}.${sub}`, { level, sink, base }),
  };
}

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal?.aborted) return resolve();
    const timer = setTimeout(done, ms);
    function done(): void {
      clearTimeout(timer);
      signal?.removeEventListener("abort", done);
      resolve();
    }
    signal?.addEventListener("abort", done, { once: true });
  });
}

/** Exponential backoff with full jitter, capped. attempt is 0-based. */
export function backoffMs(attempt: number, baseMs = 1_000, maxMs = 5 * 60 * 1000): number {
  const cap = Math.min(maxMs, baseMs * 2 ** Math.min(attempt, 20));
  return Math.floor(Math.random() * cap);
}
