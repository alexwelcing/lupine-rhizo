/**
 * Test-only helpers for stubbing Cloudflare Worker bindings.
 *
 * Each binding (D1, R2, KV, Queue) is reduced to the minimum surface
 * area the production code actually touches in the lanes under test.
 * Anything broader belongs in `@cloudflare/vitest-pool-workers`.
 */
import { vi } from "vitest";
import type { Env } from "../types";

export interface D1Row {
  [key: string]: unknown;
}

/**
 * Per-query D1 result. `first` returns the first row (or null), `all`
 * returns `{ results }`, `run` is a no-op success. Each registered
 * SQL fragment matches if it's contained in the prepared statement —
 * substring match keeps the fixtures terse.
 */
export interface D1QueryHandler {
  match: string;
  first?: D1Row | null;
  all?: D1Row[];
}

export interface StubLedgerOptions {
  queries?: D1QueryHandler[];
  /** Called every time a statement is prepared — useful for assertions. */
  onPrepare?: (sql: string, bindings: readonly unknown[]) => void;
}

/**
 * Build a D1Database stub. Each `.prepare(sql).bind(...).first()` /
 * `.all()` / `.run()` call walks the registered handlers and returns
 * the first one whose `match` substring is contained in `sql`.
 */
export function stubLedger(options: StubLedgerOptions = {}): D1Database {
  const handlers = options.queries ?? [];

  function pick(sql: string): D1QueryHandler | undefined {
    return handlers.find((h) => sql.includes(h.match));
  }

  function makeStatement(sql: string, bindings: unknown[] = []): D1PreparedStatement {
    const stmt = {
      bind: (...args: unknown[]) => makeStatement(sql, [...bindings, ...args]),
      first: async () => {
        options.onPrepare?.(sql, bindings);
        const handler = pick(sql);
        return handler?.first ?? null;
      },
      all: async () => {
        options.onPrepare?.(sql, bindings);
        const handler = pick(sql);
        return {
          results: handler?.all ?? [],
          success: true,
          meta: {},
        };
      },
      run: async () => {
        options.onPrepare?.(sql, bindings);
        return {
          results: [],
          success: true,
          meta: {},
        };
      },
    };
    return stmt as unknown as D1PreparedStatement;
  }

  return {
    prepare: (sql: string) => makeStatement(sql),
    batch: async (statements: D1PreparedStatement[]) => {
      const results = [];
      for (const statement of statements) {
        results.push(await statement.run());
      }
      return results;
    },
    exec: async () => ({ count: 0, duration: 0 }),
    dump: async () => new ArrayBuffer(0),
    withSession: () => ({}) as never,
  } as unknown as D1Database;
}

export interface StubR2Options {
  /** key → JSON object (already parsed). */
  objects?: Record<string, unknown>;
}

export function stubArtifacts(options: StubR2Options = {}): R2Bucket {
  const objects = options.objects ?? {};
  return {
    get: vi.fn(async (key: string) => {
      if (!(key in objects)) return null;
      const payload = objects[key];
      return {
        json: async () => payload,
        text: async () => JSON.stringify(payload),
        arrayBuffer: async () => new ArrayBuffer(0),
        body: null,
      } as unknown as R2ObjectBody;
    }),
    put: vi.fn(async () => ({}) as R2Object),
    delete: vi.fn(async () => undefined),
    list: vi.fn(async () => ({ objects: [], truncated: false }) as unknown as R2Objects),
    head: vi.fn(async () => null),
  } as unknown as R2Bucket;
}

export function stubConfig(initial: Record<string, string> = {}): KVNamespace {
  const store = new Map<string, string>(Object.entries(initial));
  return {
    get: vi.fn(async (key: string) => store.get(key) ?? null),
    put: vi.fn(async (key: string, value: string) => {
      store.set(key, value);
    }),
    delete: vi.fn(async (key: string) => {
      store.delete(key);
    }),
    list: vi.fn(async () => ({ keys: [], list_complete: true, cacheStatus: null })),
    getWithMetadata: vi.fn(async () => ({ value: null, metadata: null, cacheStatus: null })),
  } as unknown as KVNamespace;
}

export function stubQueue(): Queue<unknown> & { sent: unknown[] } {
  const sent: unknown[] = [];
  const queue = {
    send: vi.fn(async (msg: unknown) => {
      sent.push(msg);
    }),
    sendBatch: vi.fn(async (msgs: Array<{ body: unknown }>) => {
      for (const m of msgs) sent.push(m.body);
    }),
    sent,
  };
  return queue as unknown as Queue<unknown> & { sent: unknown[] };
}

/**
 * Build a minimal `Env` covering the bindings used by the three
 * tested lanes. Tests pass `overrides` to attach scenario-specific
 * stubs without rebuilding the whole env.
 */
export function stubVectorize(
  opts: { vectors?: VectorizeVector[] } = {},
): VectorizeIndex {
  const store = new Map<string, VectorizeVector>();
  for (const v of opts.vectors ?? []) store.set(v.id, v);

  return {
    describe: async () => ({
      id: "test-index",
      name: "test",
      config: { dimensions: 384, metric: "cosine" },
      vectorsCount: store.size,
    }),
    query: async (vector: number[], options?: VectorizeQueryOptions) => {
      // Naïve brute-force cosine similarity for tests
      const topK = options?.topK ?? 10;
      const matches = Array.from(store.values())
        .map((v: VectorizeVector) => {
          const dot = (v.values as number[]).reduce((s: number, val: number, i: number) => s + val * vector[i], 0);
          const normA = Math.sqrt((v.values as number[]).reduce((s: number, val: number) => s + val * val, 0));
          const normB = Math.sqrt(vector.reduce((s: number, val: number) => s + val * val, 0));
          const score = normA && normB ? dot / (normA * normB) : 0;
          return { id: v.id, score, metadata: v.metadata };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, topK);
      return { matches, count: matches.length } as VectorizeMatches;
    },
    insert: async (vectors: VectorizeVector[]) => {
      for (const v of vectors) store.set(v.id, v);
      return { ids: vectors.map((v: VectorizeVector) => v.id), count: vectors.length } as VectorizeVectorMutation;
    },
    upsert: async (vectors: VectorizeVector[]) => {
      for (const v of vectors) store.set(v.id, v);
      return { ids: vectors.map((v: VectorizeVector) => v.id), count: vectors.length } as VectorizeVectorMutation;
    },
    deleteByIds: async (ids: string[]) => {
      for (const id of ids) store.delete(id);
      return { ids, count: ids.length } as VectorizeVectorMutation;
    },
    getByIds: async (ids: string[]) => ids.map((id: string) => store.get(id)).filter(Boolean) as VectorizeVector[],
  } as unknown as VectorizeIndex;
}

export function buildStubEnv(overrides: Partial<Env> = {}): Env {
  const env: Partial<Env> = {
    LEDGER: stubLedger(),
    ARTIFACTS: stubArtifacts(),
    CONFIG: stubConfig(),
    RESEARCH_QUEUE: stubQueue(),
    ...overrides,
  };
  return env as Env;
}
