/**
 * memoryClientEdge unit tests.
 *
 * Covers:
 *   1. computeBiasFromMatches — correct per-strategy hit-rate from Vectorize matches.
 *   2. consultMemoryEdge — embedding + query round-trip via stubVectorize.
 *   3. emitTraceEdge — upsert into stub index with metadata.
 *   4. Edge empty → no bias, no hits.
 *   5. consultMemory (mode switch) — off/shadow/active behavior.
 */
import { describe, it, expect, vi } from "vitest";
import { consultMemoryEdge, emitTraceEdge, computeBiasFromMatches } from "../memoryClientEdge";
import { consultMemory, emitTrace } from "../memoryClient";
import { buildStubEnv, stubVectorize } from "../../testing/envStub";
import type { Env } from "../../types";

function stubEnvWithVectorize(overrides: Partial<Env> = {}): Env {
  return buildStubEnv({
    COORD_MEMORY: stubVectorize(),
    EVIDENCE_INDEX_URL: "",
    ...overrides,
  });
}

function fakeEmbeddingResponse(values: number[][]): unknown {
  return { data: values };
}

describe("computeBiasFromMatches", () => {
  it("computes hit-rate per strategy from matches", () => {
    const matches = [
      { id: "1", score: 0.9, metadata: { strategy: "race", coordination_hit: 1 } },
      { id: "2", score: 0.8, metadata: { strategy: "race", coordination_hit: 0 } },
      { id: "3", score: 0.7, metadata: { strategy: "fan_out_merge", coordination_hit: 1 } },
    ];
    const bias = computeBiasFromMatches(matches);
    expect(bias.race).toBe(0.5); // 1 hit / 2 total
    expect(bias.fan_out_merge).toBe(1.0); // 1 hit / 1 total
  });

  it("returns empty bias when no matches have strategy", () => {
    const bias = computeBiasFromMatches([
      { id: "1", score: 0.9, metadata: { coordination_hit: 1 } },
    ]);
    expect(Object.keys(bias)).toHaveLength(0);
  });

  it("returns empty bias for empty input", () => {
    expect(computeBiasFromMatches([])).toEqual({});
  });
});

describe("consultMemoryEdge", () => {
  it("returns empty bias when COORD_MEMORY is not bound", async () => {
    const env = buildStubEnv(); // no COORD_MEMORY
    const result = await consultMemoryEdge(env, "test prompt");
    expect(result.bias).toEqual({});
    expect(result.hits).toEqual([]);
  });

  it("queries the edge index and returns bias + hits", async () => {
    const index = stubVectorize({
      vectors: [
        {
          id: "trace:1",
          values: new Array(384).fill(0.01).map((_, i) => Math.sin(i * 0.1)),
          metadata: { strategy: "race", coordination_hit: 1, kind: "coordination_trace" },
        },
        {
          id: "trace:2",
          values: new Array(384).fill(0.01).map((_, i) => Math.cos(i * 0.1)),
          metadata: { strategy: "race", coordination_hit: 0, kind: "coordination_trace" },
        },
      ],
    });

    const env = buildStubEnv({
      COORD_MEMORY: index,
      AI: {
        run: vi.fn(async (_model: string, _inputs: unknown) =>
          fakeEmbeddingResponse([new Array(384).fill(0.01).map((_, i) => Math.sin(i * 0.1))]),
        ),
      } as unknown as Env["AI"],
    });

    const result = await consultMemoryEdge(env, "test prompt", undefined, 5);
    expect(result.hits.length).toBeGreaterThan(0);
    expect(result.hits[0].kind).toBe("coordination_trace");
    // Bias should reflect the race strategy
    expect(result.bias.race).toBeDefined();
  });
});

describe("emitTraceEdge", () => {
  it("upserts a trace into the edge index", async () => {
    const index = stubVectorize();
    const env = buildStubEnv({
      COORD_MEMORY: index,
      AI: {
        run: vi.fn(async (_model: string, _inputs: unknown) =>
          fakeEmbeddingResponse([new Array(384).fill(0.01)]),
        ),
      } as unknown as Env["AI"],
    });

    await emitTraceEdge(env, {
      id: "trace:test-1",
      text: "Strategy: race. Outcome: success.",
      kind: "coordination_trace",
      metadata: { strategy: "race", coordination_hit: 1 },
    });

    const info = await index.describe();
    expect(info.vectorsCount).toBe(1);
  });

  it("is a no-op when COORD_MEMORY is not bound", async () => {
    const env = buildStubEnv(); // no COORD_MEMORY
    await expect(
      emitTraceEdge(env, { id: "t1", text: "test" }),
    ).resolves.toBeUndefined();
  });
});

describe("memoryClient mode switch", () => {
  it("off mode uses GCP only (empty when no EVIDENCE_INDEX_URL)", async () => {
    const env = stubEnvWithVectorize({ COORD_MEMORY_MODE: "off" });
    const result = await consultMemory(env, "prompt");
    expect(result.bias).toEqual({});
  });

  it("active mode uses edge and returns edge bias", async () => {
    const index = stubVectorize({
      vectors: [
        {
          id: "trace:1",
          values: new Array(384).fill(0.01).map((_, i) => Math.sin(i * 0.1)),
          metadata: { strategy: "fan_out_merge", coordination_hit: 1, kind: "coordination_trace" },
        },
      ],
    });

    const env = buildStubEnv({
      COORD_MEMORY: index,
      COORD_MEMORY_MODE: "active",
      AI: {
        run: vi.fn(async (_model: string, _inputs: unknown) =>
          fakeEmbeddingResponse([new Array(384).fill(0.01).map((_, i) => Math.sin(i * 0.1))]),
        ),
      } as unknown as Env["AI"],
    });

    const result = await consultMemory(env, "prompt");
    expect(result.bias.fan_out_merge).toBe(1);
  });

  it("emitTrace dual-writes to edge in active mode", async () => {
    const index = stubVectorize();
    const env = buildStubEnv({
      COORD_MEMORY: index,
      COORD_MEMORY_MODE: "active",
      EVIDENCE_INDEX_URL: "",
      AI: {
        run: vi.fn(async (_model: string, _inputs: unknown) =>
          fakeEmbeddingResponse([new Array(384).fill(0.01)]),
        ),
      } as unknown as Env["AI"],
    });

    await emitTrace(env, {
      id: "trace:test",
      text: "test trace",
      kind: "coordination_trace",
      metadata: { strategy: "race" },
    });

    const info = await index.describe();
    expect(info.vectorsCount).toBe(1);
  });
});
