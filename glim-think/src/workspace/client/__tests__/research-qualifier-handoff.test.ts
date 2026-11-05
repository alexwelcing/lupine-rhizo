/// <reference types="@cloudflare/workers-types" />
import { afterEach, describe, expect, it, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DatabaseSync, type SQLInputValue } from "node:sqlite";
import { readFileSync } from "node:fs";
import { researchRunsResponse } from "../../researchRuns";
import { sha256, type ResearchRunImport, type ScientificPacket } from "../../researchRunContracts";
import { loadResearchRuns, previewResearchImport, ResearchRunCard, saveResearchImport } from "../ResearchRuns";

// Fictional packets exercise transport and display, not providers or physical models.
const cases = [
  {
    name: "auxiliary-reference",
    supports: "Fictional auxiliary reference for target PBE. Standalone melting is a separate observable.",
    limitations: "Fictional 0.1 K standard error of a sample mean. Physical bias, pressure and artifact identity remain unknown.",
  },
  {
    name: "corrected-target",
    supports: "Fictional final LDA free-energy crossing. This is the corrected target calculation.",
    limitations: "Fictional 5 K propagated sampling standard deviation. This does not bound disagreement with experiment.",
  },
] as const;

const migration = readFileSync(new URL("../../../../migrations/0020_workspace_research_runs.sql", import.meta.url), "utf8");
const databases: DatabaseSync[] = [];
afterEach(() => {
  vi.unstubAllGlobals();
  for (const db of databases.splice(0)) db.close();
});

function transportHarness() {
  const db = new DatabaseSync(":memory:");
  databases.push(db);
  db.exec(migration);
  let writes = 0;
  function statement(sql: string, values: SQLInputValue[] = []) {
    return {
      bind: (...bound: SQLInputValue[]) => statement(sql, bound),
      first: async () => db.prepare(sql).get(...values) ?? null,
      all: async () => ({ results: db.prepare(sql).all(...values), success: true, meta: {} }),
      run: async () => {
        const changes = Number(db.prepare(sql).run(...values).changes);
        writes += 1;
        return { success: true, results: [], meta: { changes } };
      },
    };
  }
  const env = { LEDGER: { prepare: statement } } as unknown as Parameters<typeof researchRunsResponse>[1];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input !== "string" || !["/workspace/research-runs", "/workspace/research-runs/import"].includes(input)) {
      throw new Error("Unexpected request; this harness has no network transport");
    }
    expect(init?.credentials).toBe("same-origin");
    if (input === "/workspace/research-runs") expect(init?.cache).toBe("no-store");
    const response = await researchRunsResponse(new Request(new URL(input, "http://localhost"), init), env, true);
    if (!response) throw new Error("Research handler did not recognize the test route");
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
    return response;
  });
  vi.stubGlobal("fetch", fetcher);
  return { db, fetcher, writes: () => writes };
}

async function qualifiedSnapshot(value: typeof cases[number]): Promise<ResearchRunImport> {
  const question = "Synthetic handoff: preserve the role and uncertainty of a reported result.";
  const packet: Extract<ScientificPacket, { role: "proposer" }> = {
    role: "proposer", research_question: question,
    synthesis: "Fictional transport fixture, not scientific evidence.",
    sources: [
      { id: "qualified-source", title: "Fictional qualified source", url: "https://example.org/qualified",
        publication_kind: "primary_research_report", year: 2026, supports: value.supports, limitations: value.limitations },
      { id: "control-source", title: "Fictional control source", url: "https://example.org/control",
        publication_kind: "preprint", year: 2026, supports: "Fictional background only.",
        limitations: "The control source has no matched numerical comparison." },
    ],
    proposals: [{
      id: "fixture-proposal", hypothesis: "Preserve the supplied qualification.",
      mechanism: "Fictional mechanism; nothing is executed.",
      closest_prior_art: [{ source_ids: ["qualified-source"], overlap: "Fictional overlap.", difference: "Unestablished." }],
      possible_novelty: "Unestablished.", novelty_status: "unverified",
      competing_explanations: ["A qualified calculation is not a physical validation."],
      falsifier: "The qualification is missing or attached to the wrong source.",
      cheap_discriminating_experiment: {
        design: "Fictional proposed test.", baseline: "Source-aware reading.", measurement: "Qualification retention.",
        decision_rule: "Reject missing context.", estimated_compute_minutes: 0, execution: "not_started",
      },
      priority_reason: "Exercise the existing report handoff.",
    }],
    independent_critique: { status: "required", questions_for_critic: ["Was the source qualification preserved?"] },
    decision: { status: "awaiting_independent_critique", rationale: "No independent review has run." },
  };
  const packetJson = JSON.stringify(packet);
  const date = "2026-11-04T00:00:00.000Z";
  return {
    schemaVersion: 1, id: "fixture-" + value.name, question, status: "running",
    startedAt: date, finishedAt: null, capturedAt: date, error: null,
    experiment: "not_started", publication: "held",
    stages: [
      {
        stage: "discovery", jobId: "fixture-discovery", provider: "codex", role: "proposer", machineId: "fixture",
        status: "completed", packetJson,
        receipt: { jobId: "fixture-discovery", jobSha256: "a".repeat(64), status: "completed",
          completionUnknown: false, automaticRetry: false, modelExecutionStarted: true,
          sessionId: "fixture-session", model: "synthetic-no-provider-execution",
          startedAt: date, finishedAt: date, resultSha256: await sha256(packetJson), receiptOrigin: "local_cli" },
      },
      { stage: "independent_critique", jobId: null, provider: "claude", role: "critic", machineId: null,
        status: "not_started", receipt: null, packetJson: null },
      { stage: "pi_decision", jobId: null, provider: "codex", role: "adjudicator", machineId: null,
        status: "not_started", receipt: null, packetJson: null },
    ],
  };
}

describe("qualified source packets through the real research import and reader", () => {
  it.each(cases)("preserves $name without promoting its scientific status", async value => {
    const h = transportHarness();
    const imported = await qualifiedSnapshot(value);
    const text = JSON.stringify(imported);
    const preview = await previewResearchImport(text);
    expect(h.fetcher).not.toHaveBeenCalled();
    await saveResearchImport(text, preview);
    expect(h.writes()).toBe(1);

    const stored = h.db.prepare("SELECT payload, payload_sha256 FROM workspace_research_runs").get()!;
    expect(await sha256(stored.payload as string)).toBe(stored.payload_sha256);
    expect(JSON.parse(stored.payload as string).stages[0].packetJson).toBe(imported.stages[0].packetJson);

    const feed = await loadResearchRuns();
    expect(feed.runs).toHaveLength(1);
    expect(feed.truncated).toBe(false);
    const run = feed.runs[0];
    const packet = run.stages[0].result;
    if (packet?.role !== "proposer") throw new Error("Discovery packet was lost");
    expect(packet.sources).toEqual(JSON.parse(imported.stages[0].packetJson!).sources);
    expect(run).toMatchObject({ status: "running", experiment: "not_started", publication: "held" });
    expect(h.writes()).toBe(1);

    const html = renderToStaticMarkup(React.createElement(ResearchRunCard, { run }));
    const sourceSection = html.slice(html.indexOf('aria-label="Research sources"'));
    const articles = [...sourceSection.matchAll(/<article\b[^>]*>[\s\S]*?<\/article>/g)].map(match => match[0]);
    expect(articles).toHaveLength(2);
    expect(articles[0]).toContain(value.supports);
    expect(articles[0]).toContain(value.limitations);
    expect(articles[0]).toContain('href="https://example.org/qualified"');
    expect(articles[1]).toContain("The control source has no matched numerical comparison.");
    expect(articles[1]).not.toContain(value.limitations);
    for (const label of ["1 of 3 stages complete", "Novelty remains unverified", "Experiments are not started",
      "Library publication is on hold", "has not received a completed independent critique"]) expect(html).toContain(label);

    // A fresh valid fingerprint cannot legitimize a source with its limitation removed.
    const missing = structuredClone(imported);
    const badPacket = JSON.parse(missing.stages[0].packetJson!);
    delete badPacket.sources[0].limitations;
    missing.stages[0].packetJson = JSON.stringify(badPacket);
    missing.stages[0].receipt!.resultSha256 = await sha256(missing.stages[0].packetJson);
    await expect(saveResearchImport(JSON.stringify(missing), preview)).rejects.toThrow("Import failed");
    expect(h.writes()).toBe(1);
    expect(h.db.prepare("SELECT payload, payload_sha256 FROM workspace_research_runs").get()).toEqual(stored);
    expect(h.fetcher).toHaveBeenCalledTimes(3);
  });
});
