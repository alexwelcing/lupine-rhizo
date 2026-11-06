import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CorrectionReview, LibraryCorrections, previewCorrection, publishCorrection, readCorrectionFile, verifyCorrection } from "../LibraryCorrections";
import { PUBLIC_ACTIVITY_FEED_SCHEMA, PUBLIC_ACTIVITY_MAX_BYTES, publicActivitySha256, type PublicResearchActivity } from "../../researchActivityContracts";

function fixture() {
  const original: PublicResearchActivity = {
    schema: "lupine.public_research_activity.v1", id: "original-report", activityId: "original-report", evidenceKind: "research_cycle",
    state: "completed", verification: "pending", title: "Synthetic literature review", summary: "No independent validation exists.",
    observedAt: "2026-10-01T10:00:00.000Z", reviewedAt: "2026-10-01T11:00:00.000Z", datasets: [], findings: ["A fictional source reports a simulation."],
    limitations: ["Supplied abstract only."], nextStep: "Obtain methods and independent data.", sources: [{ label: "Original source", url: "https://arxiv.org/abs/2401.01234" }],
    hashes: [{ label: "Public evidence", sha256: "a".repeat(64) }], repositoryLinks: [], releaseLinks: [], supersedes: null, correctionReason: null,
  };
  const record: PublicResearchActivity = { ...original, id: "clarification-one", reviewedAt: "2026-10-02T11:00:00.000Z", supersedes: original.id,
    summary: "No independent validation was supplied or performed in this excerpt-based review; existence elsewhere was not assessed.",
    correctionReason: "Local Codex excerpt review clarifies the scope; this is not a hosted Reviewer response.", hashes: [{ label: "Original public evidence", sha256: "a".repeat(64) }] };
  const response = (record: PublicResearchActivity) => Response.json({ schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items: [record], truncated: false });
  return { original, record, response };
}
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("operator Library correction interface", () => {
  it("offers local input and preview, never publication on initial render", () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    const html = renderToStaticMarkup(React.createElement(LibraryCorrections));
    expect(html).toContain("Library corrections"); expect(html).toContain('accept=".json,application/json"');
    expect(html).toContain("Selecting a file does not upload it"); expect(html).toContain("Preview correction");
    expect(html).not.toContain("Publish clarification to Library"); expect(fetcher).not.toHaveBeenCalled();
  });
  it("bounds files before reading and catches inaccurate file sizes after reading", async () => {
    const text = vi.fn().mockResolvedValue("{}");
    for (const size of [0, -1, NaN, PUBLIC_ACTIVITY_MAX_BYTES + 1]) await expect(readCorrectionFile({ size, text })).rejects.toThrow();
    expect(text).not.toHaveBeenCalled();
    await expect(readCorrectionFile({ size: 2, text: async () => "é".repeat(PUBLIC_ACTIVITY_MAX_BYTES) })).rejects.toThrow();
    expect(await readCorrectionFile({ size: 2, text })).toBe("{}");
  });
  it("rejects invalid or non-correction data locally without any request", async () => {
    const { original, record } = fixture(); const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    for (const value of ["{", " ".repeat(PUBLIC_ACTIVITY_MAX_BYTES + 1), JSON.stringify(original), JSON.stringify({ ...record, state: "running" }),
      JSON.stringify({ ...record, correctionReason: null }), JSON.stringify({ ...record, hashes: original.hashes }), JSON.stringify({ ...record, privatePath: "/private/local" })]) {
      await expect(previewCorrection(value)).rejects.toThrow();
    }
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("previews only the exact public predecessor with no proposed payload transmission", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValue(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record, null, 2));
    expect(fetcher).toHaveBeenCalledOnce(); expect(fetcher.mock.calls[0][0]).toBe("/research/activity/original-report");
    expect(fetcher.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty("body");
    expect(preview.body).toBe(JSON.stringify(record)); expect(preview.sha256).toBe(await publicActivitySha256(preview.body));
    expect(preview.originalSha256).toBe(await publicActivitySha256(JSON.stringify(original)));
    const html = renderToStaticMarkup(React.createElement(CorrectionReview, { preview }));
    for (const text of [original.summary, record.summary, record.correctionReason!, "Original record", "New correction", "Preserved outcome", "Original public evidence"]) expect(html).toContain(text);
  });
  it("rejects wrong or missing original identity, extra records and incomplete envelopes", async () => {
    const { original, record } = fixture(); const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    for (const value of [{ schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items: [{ ...original, id: "wrong" }], truncated: false },
      { schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items: [], truncated: false }, { schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items: [original, original], truncated: false },
      { schema: PUBLIC_ACTIVITY_FEED_SCHEMA, items: [original], truncated: true }]) {
      fetcher.mockResolvedValueOnce(Response.json(value)); await expect(previewCorrection(JSON.stringify(record))).rejects.toThrow();
    }
  });
  it("keeps original identity, observation and terminal state and requires later review", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockImplementation(() => response(original)); vi.stubGlobal("fetch", fetcher);
    for (const change of [{ activityId: "other" }, { evidenceKind: "workflow_repair" }, { state: "failed" }, { observedAt: "2026-10-01T10:01:00.000Z" }, { reviewedAt: original.reviewedAt }]) {
      await expect(previewCorrection(JSON.stringify({ ...record, ...change }))).rejects.toThrow();
    }
  });
  it("publishes only the reviewed normalized bytes then reads back both records", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValueOnce(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record)); fetcher.mockClear();
    fetcher.mockResolvedValueOnce(Response.json({ id: record.id, activityId: record.activityId, state: record.state, duplicate: false }))
      .mockResolvedValueOnce(response(record)).mockResolvedValueOnce(response(original));
    await publishCorrection(preview);
    expect(fetcher.mock.calls.map(call => call[0])).toEqual(["/workspace/research-activity/import", "/research/activity/clarification-one", "/research/activity/original-report"]);
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: "POST", credentials: "same-origin", redirect: "error", headers: { "Content-Type": "application/json" }, body: preview.body });
    expect(fetcher.mock.calls.filter(call => call[1].method === "POST")).toHaveLength(1);
  });
  it("refuses changed preview bytes before a write", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValue(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record)); fetcher.mockClear(); preview.record.summary = "Changed after review.";
    await expect(publishCorrection(preview)).rejects.toThrow("Preview changed"); expect(fetcher).not.toHaveBeenCalled();
  });
  it("snapshots reviewed content before asynchronous hashing or transport", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValueOnce(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record));
    fetcher.mockResolvedValueOnce(Response.json({ id: record.id, activityId: record.activityId, state: record.state, duplicate: false })).mockResolvedValueOnce(response(record)).mockResolvedValueOnce(response(original));
    const pending = publishCorrection(preview); preview.body = "{}"; preview.record.summary = "Mutation.";
    await pending; expect(fetcher.mock.calls[1][1].body).toBe(JSON.stringify(record));
  });
  it("does not retry denied, conflicting or unknown writes", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValueOnce(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record));
    for (const status of [403, 409, 503]) { fetcher.mockClear(); fetcher.mockResolvedValueOnce(new Response("unavailable", { status })); await expect(publishCorrection(preview)).rejects.toThrow(); expect(fetcher).toHaveBeenCalledOnce(); }
    fetcher.mockClear(); fetcher.mockRejectedValueOnce(new Error("Lost response")); await expect(publishCorrection(preview)).rejects.toThrow(); expect(fetcher).toHaveBeenCalledOnce();
  });
  it("does not treat mismatched acknowledgement or altered readback as success", async () => {
    const { original, record, response } = fixture(); const fetcher = vi.fn().mockResolvedValueOnce(response(original)); vi.stubGlobal("fetch", fetcher);
    const preview = await previewCorrection(JSON.stringify(record));
    fetcher.mockClear(); fetcher.mockResolvedValueOnce(Response.json({ id: "other", activityId: record.activityId, state: record.state, duplicate: false }));
    await expect(publishCorrection(preview)).rejects.toThrow("acknowledgement"); expect(fetcher).toHaveBeenCalledOnce();
    fetcher.mockClear(); fetcher.mockResolvedValueOnce(response({ ...record, summary: "Altered." })); await expect(verifyCorrection(preview)).rejects.toThrow("differs");
    fetcher.mockClear(); fetcher.mockResolvedValueOnce(response(record)).mockResolvedValueOnce(response({ ...original, summary: "Altered original." }));
    await expect(verifyCorrection(preview)).rejects.toThrow("Original record differs");
    expect(fetcher.mock.calls.every(call => !call[1].method)).toBe(true);
  });
  it("bounds public read bodies and rejects malformed or oversized replies", async () => {
    const { record } = fixture(); const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    for (const reply of [new Response("x", { headers: { "Content-Length": "999999" } }), new Response("x".repeat(PUBLIC_ACTIVITY_MAX_BYTES + 1025)), new Response("not json")]) {
      fetcher.mockResolvedValueOnce(reply); await expect(previewCorrection(JSON.stringify(record))).rejects.toThrow();
    }
  });
});
