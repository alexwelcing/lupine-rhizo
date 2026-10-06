import { afterEach, describe, expect, it, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { decodeResearchRuns, ImportResearchRun, loadResearchRuns, previewResearchImport, readResearchSnapshotFile, ResearchRunCard, saveResearchImport } from "../ResearchRuns";
import { sha256, type ResearchRun, type ResearchRunImport, type ResearchRunStage, type ScientificPacket } from "../../researchRunContracts";

const date = "2026-10-06T05:00:00.000Z";
const question = "Synthetic UI fixture: can a held-out test distinguish two explanations?";
const experiment = { design: "Compare synthetic groups using a held-out split.", baseline: "A fictional fixed baseline.", measurement: "Synthetic error only.",
  decision_rule: "Reject the fictional hypothesis if the effect disappears.", estimated_compute_minutes: 1, execution: "not_started" as const };
const discovery: Extract<ScientificPacket, { role: "proposer" }> = {
  role: "proposer", research_question: question, synthesis: "Fictional research for an interface test, not scientific evidence.",
  sources: [1, 2].map(n => ({ id: `source-${n}`, title: `Fictional source ${n}`, url: `https://example.org/paper-${n}`, publication_kind: "preprint", year: 2026,
    supports: "Illustrates a source attribution.", limitations: "Invented fixture only." })),
  proposals: [{ id: "hypothesis-one", hypothesis: "Synthetic hypothesis under review.", mechanism: "Fictional mechanism.",
    closest_prior_art: [{ source_ids: ["source-1"], overlap: "Shares an earlier fictional approach.", difference: "Different fictional control." }],
    possible_novelty: "Possible new control, not established.", novelty_status: "unverified", competing_explanations: ["Synthetic confound."],
    falsifier: "The held-out effect vanishes.", cheap_discriminating_experiment: experiment, priority_reason: "The synthetic check is cheap." }],
  independent_critique: { status: "required", questions_for_critic: ["Does this control distinguish the explanations?"] },
  decision: { status: "awaiting_independent_critique", rationale: "Independent assessment required." },
};

async function fixture(complete = false): Promise<{ run: ResearchRun; imported: ResearchRunImport }> {
  const discoveryHash = await sha256(JSON.stringify(discovery));
  const critique: Extract<ScientificPacket, { role: "critic" }> = {
    role: "critic", reviewed_job_id: "test-discovery", reviewed_packet_sha256: discoveryHash, verdict: "revise",
    source_checks: [{ source_id: "source-1", status: "provided_only", reason: "Only supplied text was assessed." }],
    critiques: [{ proposal_id: "hypothesis-one", prior_art_overlap: "Could overlap with the fictional source.", confounds: ["Synthetic confound survives."],
      discriminating_experiment_assessment: "Needs a matched control.", decision: "revise", required_changes: ["Add a matched control."] }],
    strongest_alternative: "A fictional nuisance effect.", next_step: "Revise the proposed control.", execution: "not_started",
  };
  const critiqueHash = await sha256(JSON.stringify(critique));
  const decision: Extract<ScientificPacket, { role: "adjudicator" }> = {
    role: "adjudicator", reviewed_job_id: "test-discovery", reviewed_packet_sha256: discoveryHash, critique_job_id: "test-critique", critique_packet_sha256: critiqueHash,
    selected_proposal_id: "hypothesis-one", recommendation: "revise", reason: "The independent critique identified a confound.",
    response_to_critique: [{ critique_point: "Control is unmatched.", response: "The objection is valid.", change: "Match the control before testing." }],
    revised_hypothesis: "Synthetic revised hypothesis.", closest_prior_art_boundary: "Prior evidence does not establish this effect.", novelty_status: "unverified",
    competing_explanation: "A nuisance effect.", falsifier: "No held-out gain.", source_ids: ["source-1"], cheap_discriminating_experiment: experiment, publication: "held",
  };
  const packets: (ScientificPacket | null)[] = [discovery, complete ? critique : null, complete ? decision : null];
  const stages: ResearchRunStage[] = await Promise.all((["discovery", "independent_critique", "pi_decision"] as const).map(async (stage, n) => {
    const result = packets[n]; const jobId = n === 0 ? "test-discovery" : n === 1 ? "test-critique" : "test-decision";
    const status = result ? "completed" : n === 1 ? "timeout" : "not_started";
    return { stage, jobId: status === "not_started" ? null : jobId, provider: n === 1 ? "claude" : "codex", role: n === 0 ? "proposer" : n === 1 ? "critic" : "adjudicator",
      machineId: status === "not_started" ? null : n === 1 ? "linux-laptop" : "mac-controller", status, result,
      receipt: status === "not_started" ? null : { jobId, jobSha256: "a".repeat(64), status, completionUnknown: !result, automaticRetry: false,
        modelExecutionStarted: true, sessionId: result ? `${jobId}-session` : null, model: n === 1 && result ? "fictional-review-model" : null,
        startedAt: date, finishedAt: date, resultSha256: result ? await sha256(JSON.stringify(result)) : null, receiptOrigin: "local_cli" } };
  }));
  const run: ResearchRun = { schemaVersion: 1, id: "synthetic-run", question, status: complete ? "completed" : "stopped", startedAt: date,
    finishedAt: date, capturedAt: date, error: complete ? null : "Independent review exceeded its bounded deadline.", experiment: "not_started", publication: "held", stages };
  return { run, imported: { ...run, stages: run.stages.map(({ result, ...stage }) => ({ ...stage, packetJson: result ? JSON.stringify(result) : null })) } };
}

afterEach(() => vi.unstubAllGlobals());

describe("private research run interface", () => {
  it("shows completed discovery, a timed-out critique and an unstarted decision without inventing review", async () => {
    const { run } = await fixture();
    const html = renderToStaticMarkup(React.createElement(ResearchRunCard, { run }));
    for (const text of [question, "1 of 3 stages complete", "Timed out", "Completion is unknown.", "No final PI decision has been recorded.",
      "has not received a completed independent critique", "Novelty remains unverified", "Experiments are not started", "Library publication is on hold", "Not reported by the provider", "Fictional source 1"])
      expect(html).toContain(text);
    expect(html).toContain('href="https://example.org/paper-1"');
    expect(html).not.toContain("Reviewer recommendation:");
    expect(html).not.toContain("PI RECOMMENDATION");
  });
  it("shows the independent objection and the PI response distinctly on a completed research cycle", async () => {
    const { run } = await fixture(true);
    const html = renderToStaticMarkup(React.createElement(ResearchRunCard, { run }));
    for (const text of ["3 of 3 stages complete", "Reviewer recommendation:", "Needs a matched control.", "PI RECOMMENDATION", "How the critique changed the decision",
      "Match the control before testing.", "fictional-review-model", "Supplied evidence only", "Proposed discriminating test", "Not started", 'dateTime="2026-10-06T05:00:00.000Z"']) expect(html).toContain(text);
    expect(html).not.toContain("No final PI decision has been recorded.");
    expect(html).toContain('href="#research-stage-synthetic-run-pi_decision"');
    expect(html).toContain('id="research-stage-synthetic-run-pi_decision"');
  });
  it("preserves a refined research question separately from the original brief", async () => {
    const { run } = await fixture();
    run.stages[0].result = { ...discovery, research_question: "A narrower fictional question after reading." };
    const html = renderToStaticMarkup(React.createElement(ResearchRunCard, { run }));
    expect(html).toContain(question);
    expect(html).toContain("Question after literature review");
    expect(html).toContain("A narrower fictional question after reading.");
  });
  it("escapes research text and makes unsafe or internal source references non-clickable", async () => {
    const { run } = await fixture();
    run.question = "<script>not executable</script>";
    const packet = run.stages[0].result as typeof discovery;
    run.stages[0].result = { ...packet, sources: [{ ...packet.sources[0], url: "javascript:alert(1)" }, { ...packet.sources[1], url: "urn:lupine:test-discovery:context" }] };
    const html = renderToStaticMarkup(React.createElement(ResearchRunCard, { run }));
    expect(html).toContain("&lt;script&gt;"); expect(html).not.toContain("<script>"); expect(html).not.toContain('href="javascript:');
    expect(html).not.toContain('href="urn:'); expect(html).toContain("Provided research context");
  });
  it("rejects contradictory completion and malformed feeds instead of rendering a success", async () => {
    const { run } = await fixture();
    expect(decodeResearchRuns({ runs: [run], truncated: false }).runs).toHaveLength(1);
    for (const invalid of [null, {}, { runs: [run], truncated: "false" }, { runs: [run, run], truncated: false },
      { runs: [{ ...run, status: "completed" }], truncated: false },
      { runs: [{ ...run, stages: [run.stages[1], run.stages[0], run.stages[2]] }], truncated: false },
      { runs: [{ ...run, stages: [{ ...run.stages[0], receipt: null }, ...run.stages.slice(1)] }], truncated: false }]) expect(() => decodeResearchRuns(invalid)).toThrow();
  });
  it("validates the import packet hashes and links before presenting its preview", async () => {
    const { imported } = await fixture(true);
    expect((await previewResearchImport(JSON.stringify(imported))).id).toBe("synthetic-run");
    imported.stages[0].packetJson = imported.stages[0].packetJson!.replace("Fictional research", "Rewritten research");
    await expect(previewResearchImport(JSON.stringify(imported))).rejects.toThrow("fingerprint");
    await expect(previewResearchImport(" ".repeat(196_609))).rejects.toThrow("too large");
  });
  it("offers both local file selection and pasted JSON without an immediate import action", () => {
    const html = renderToStaticMarkup(React.createElement(ImportResearchRun, { onImported: () => {} }));
    expect(html).toContain('type="file"');
    expect(html).toContain('accept=".json,application/json"');
    expect(html).toContain("Or paste exported snapshot JSON");
    expect(html).toContain("Preview snapshot");
    expect(html).toContain("file stays on this device");
    expect(html).not.toMatch(/<button[^>]*>Import snapshot<\/button>/);
  });
  it("rejects oversized or empty files before reading them", async () => {
    const read = vi.fn().mockResolvedValue("{}");
    for (const size of [0, -1, 196_609, Number.NaN]) await expect(readResearchSnapshotFile({ size, text: read })).rejects.toThrow();
    expect(read).not.toHaveBeenCalled();
  });
  it("reads a local file without sending it and preserves the normal preview validation", async () => {
    const { imported } = await fixture(true); const raw = JSON.stringify(imported);
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    const text = await readResearchSnapshotFile({ size: new TextEncoder().encode(raw).length, text: async () => raw });
    expect(text).toBe(raw);
    expect((await previewResearchImport(text)).id).toBe("synthetic-run");
    expect(fetcher).not.toHaveBeenCalled();
    const invalid = await readResearchSnapshotFile({ size: 2, text: async () => "{}" });
    await expect(previewResearchImport(invalid)).rejects.toThrow();
    await expect(readResearchSnapshotFile({ size: 2, text: async () => "é".repeat(98_305) })).rejects.toThrow("too large");
  });
  it("refreshes only the same-origin saved feed and propagates cancellation", async () => {
    const { run } = await fixture(); const signal = new AbortController().signal;
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ runs: [run], truncated: false })));
    vi.stubGlobal("fetch", fetcher);
    expect((await loadResearchRuns(signal)).runs[0].id).toBe(run.id);
    expect(fetcher).toHaveBeenCalledExactlyOnceWith("/workspace/research-runs", { credentials: "same-origin", cache: "no-store", signal });
  });
  it("accepts only an import acknowledgement for the previewed identity and state", async () => {
    const { run, imported } = await fixture(); const text = JSON.stringify(imported);
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: run.id, status: run.status, duplicate: false })));
    vi.stubGlobal("fetch", fetcher);
    await expect(saveResearchImport(text, run)).resolves.toBeUndefined();
    expect(fetcher).toHaveBeenCalledExactlyOnceWith("/workspace/research-runs/import", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: text });
    fetcher.mockResolvedValue(new Response(JSON.stringify({ id: "wrong-run", status: run.status, duplicate: false })));
    await expect(saveResearchImport(text, run)).rejects.toThrow("acknowledgement");
    fetcher.mockResolvedValue(new Response("Conflict", { status: 409 }));
    await expect(saveResearchImport(text, run)).rejects.toThrow("Import failed");
  });
});
