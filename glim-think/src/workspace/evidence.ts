import { tool } from "ai";
import { z } from "zod";
import type { Env } from "../types";

const evidenceInput = z.object({
  collection: z.enum(["hypotheses", "papers", "activity"]),
  query: z.string().trim().max(160).default(""),
  limit: z.number().int().min(1).max(8).default(5),
}).strict();

/** Fixed SELECT statements, projected text bounds, bound values, and bounded rows. */
export const EVIDENCE_SQL = {
  hypotheses: "SELECT id, substr(title,1,400) AS title, status, confidence, substr(evidence_ids,1,800) AS evidence_ids, updated_at FROM hypotheses WHERE title LIKE ? ESCAPE '\\' ORDER BY updated_at DESC LIMIT ?",
  papers: "SELECT doi, arxiv_id, substr(title,1,400) AS title, substr(abstract,1,1600) AS abstract, year, source, fetched_at FROM literature_papers WHERE title LIKE ? ESCAPE '\\' ORDER BY fetched_at DESC LIMIT ?",
  activity: "SELECT beat_id, agent, substr(summary,1,1200) AS summary, ts FROM lab_beats WHERE summary LIKE ? ESCAPE '\\' ORDER BY ts DESC LIMIT ?",
} as const;

export async function readWorkspaceEvidence(env: Env, input: unknown) {
  const { collection, query, limit } = evidenceInput.parse(input);
  const escaped = query.replace(/[\\%_]/g, "\\$&");
  const result = await env.LEDGER.prepare(EVIDENCE_SQL[collection]).bind(`%${escaped}%`, limit).all();
  return {
    collection, observedAt: new Date().toISOString(),
    records: (result.results ?? []).slice(0, limit),
    source: collection === "papers" ? "https://library.lupine.science/#/read/research-index" : "/live",
    note: "Saved ledger evidence. A recorded hypothesis or activity report does not prove a scientific claim.",
  };
}

export function workspaceEvidenceTools(env: Env) {
  return {
    read_evidence: tool({
      description: "Read bounded saved research hypotheses, literature, or reported lab activity. No web fetch, simulation, research dispatch, or writes. Cite the returned record IDs and distinguish proposals from verified results.",
      inputSchema: evidenceInput,
      execute: (input) => readWorkspaceEvidence(env, input),
    }),
  };
}
