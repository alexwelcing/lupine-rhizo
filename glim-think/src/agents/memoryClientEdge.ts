/**
 * Edge-local memory client — Vectorize + Workers AI path for the coordinator
 * flywheel. Drops the cross-cloud GCP hop for consultMemory/emitTrace.
 *
 * Design: additive, never a dependency. All callers fall back to GCP behavior
 * if the edge path fails or is unconfigured.
 *
 * Embedding: @cf/baai/bge-small-en-v1.5 (384 dims) with query-side prefix
 * for asymmetric search: "Represent this sentence for searching relevant
 * coordination traces: " + prompt.
 */
import type { Env } from "../types";
import type { MemoryBias, SearchHit } from "./memoryClient";

const EMBEDDING_MODEL = "@cf/baai/bge-small-en-v1.5";
const VECTOR_DIMS = 384;
const QUERY_PREFIX = "Represent this sentence for searching relevant coordination traces: ";

interface VectorizeQueryMatch {
  id: string;
  score: number;
  metadata?: Record<string, unknown>;
}

/** Generate a single embedding via Workers AI. */
async function embedText(env: Env, text: string): Promise<number[]> {
  const response = await env.AI.run(EMBEDDING_MODEL, { text: [text] });
  const data = (response as { data?: number[][] }).data;
  if (!data || !Array.isArray(data) || data.length === 0) {
    throw new Error("Workers AI embedding returned empty data");
  }
  const vec = data[0];
  if (!Array.isArray(vec) || vec.length !== VECTOR_DIMS) {
    throw new Error(`Unexpected embedding shape: ${vec?.length} dims (expected ${VECTOR_DIMS})`);
  }
  return vec;
}

/** Compute per-strategy hit-rate bias from Vectorize matches. Mirrors memoryClient._computeBias. */
export function computeBiasFromMatches(matches: VectorizeQueryMatch[]): MemoryBias {
  if (!matches || matches.length === 0) return {};
  const buckets: Record<string, { hits: number; total: number }> = {};
  for (const m of matches) {
    const strategy = String(m.metadata?.strategy ?? "");
    const hit = Number(m.metadata?.coordination_hit ?? 0);
    if (!strategy) continue;
    if (!buckets[strategy]) buckets[strategy] = { hits: 0, total: 0 };
    buckets[strategy].total++;
    if (hit === 1) buckets[strategy].hits++;
  }
  const bias: MemoryBias = {};
  for (const [s, b] of Object.entries(buckets)) {
    bias[s] = b.hits / b.total;
  }
  return bias;
}

function mapMatchesToHits(matches: VectorizeQueryMatch[]): SearchHit[] {
  return matches.map((m) => ({
    id: m.id,
    kind: String(m.metadata?.kind ?? "coordination_trace"),
    ref_id: String(m.metadata?.ref_id ?? m.id),
    text: String(m.metadata?.text ?? ""),
    score: m.score,
    metadata: m.metadata ?? {},
  }));
}

/**
 * Edge-local consultMemory. Embeds the prompt via Workers AI, queries
 * COORD_MEMORY with a `kind=coordination_trace` metadata filter, and returns
 * the per-strategy bias. Falls back to empty on any error.
 */
export async function consultMemoryEdge(
  env: Env,
  prompt: string,
  _intent?: string,
  limit = 5,
): Promise<{ bias: MemoryBias; hits: SearchHit[] }> {
  if (!env.COORD_MEMORY) return { bias: {}, hits: [] };

  const start = Date.now();
  try {
    const embedding = await embedText(env, QUERY_PREFIX + prompt.slice(0, 500));
    const queryStart = Date.now();

    const results = await env.COORD_MEMORY.query(embedding, {
      topK: limit,
      returnMetadata: "all",
      filter: { kind: { $eq: "coordination_trace" } },
    });

    const matches = (results.matches ?? []) as VectorizeQueryMatch[];
    const bias = computeBiasFromMatches(matches);
    const hits = mapMatchesToHits(matches);

    console.log(JSON.stringify({
      level: "debug",
      source: "coord_memory_edge",
      action: "consult",
      latency_embed_ms: queryStart - start,
      latency_query_ms: Date.now() - queryStart,
      latency_total_ms: Date.now() - start,
      hits: matches.length,
    }));

    return { bias, hits };
  } catch (e) {
    console.warn("[coord_memory_edge] consult failed:", e instanceof Error ? e.message : String(e));
    return { bias: {}, hits: [] };
  }
}

/**
 * Edge-local emitTrace. Embeds the trace text via Workers AI and upserts into
 * COORD_MEMORY with full metadata. Fire-and-forget; never throws.
 */
export async function emitTraceEdge(
  env: Env,
  trace: {
    id: string;
    text: string;
    kind?: string;
    ref_id?: string;
    metadata?: Record<string, unknown>;
  },
): Promise<void> {
  if (!env.COORD_MEMORY) return;

  try {
    const embedding = await embedText(env, trace.text.slice(0, 1500));
    await env.COORD_MEMORY.upsert([
      {
        id: trace.id,
        values: embedding,
        metadata: {
          kind: trace.kind ?? "coordination_trace",
          ref_id: trace.ref_id ?? trace.id,
          text: trace.text.slice(0, 500),
          ...trace.metadata,
        },
      },
    ]);
  } catch (e) {
    console.warn("[coord_memory_edge] emit failed:", e instanceof Error ? e.message : String(e));
  }
}

/**
 * Shadow-mode comparator: runs edge + GCP in parallel, logs latencies and
 * agreement, and returns the GCP result (the safe path). Used during Phase E.
 */
export async function consultMemoryShadow(
  env: Env,
  prompt: string,
  gcpConsult: (env: Env, prompt: string, intent?: string, limit?: number) => Promise<{ bias: MemoryBias; hits: SearchHit[] }>,
  intent?: string,
  limit = 5,
): Promise<{ bias: MemoryBias; hits: SearchHit[] }> {
  const t0 = Date.now();
  const [edgeResult, gcpResult] = await Promise.allSettled([
    consultMemoryEdge(env, prompt, intent, limit),
    gcpConsult(env, prompt, intent, limit),
  ]);

  const edge = edgeResult.status === "fulfilled" ? edgeResult.value : { bias: {}, hits: [] };
  const gcp = gcpResult.status === "fulfilled" ? gcpResult.value : { bias: {}, hits: [] };

  const edgeLatency = Date.now() - t0;
  const edgeTop = Object.entries(edge.bias).sort(([, a], [, b]) => b - a)[0]?.[0] ?? null;
  const gcpTop = Object.entries(gcp.bias).sort(([, a], [, b]) => b - a)[0]?.[0] ?? null;
  const agreed = edgeTop === gcpTop;

  console.log(JSON.stringify({
    level: "info",
    source: "coord_memory_shadow",
    edge_latency_ms: edgeLatency,
    gcp_latency_ms: null,
    edge_hits: edge.hits.length,
    gcp_hits: gcp.hits.length,
    edge_top_strategy: edgeTop,
    gcp_top_strategy: gcpTop,
    agreed,
    prompt_prefix: prompt.slice(0, 60),
  }));

  return gcp;
}
