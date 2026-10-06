import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { decodeProgressFeed, nextStepDiscussion, ProgressCard, progressDate } from "../ProgressFeed";
import type { ProgressClip } from "../../progressContracts";

const fixture: ProgressClip = {
  id: "synthetic-ui-test", title: "Synthetic interface test briefing", summary: "Invented test data; no scientific conclusion.",
  findings: [{ text: "Synthetic report describes a proposed check.", sourceIds: ["source-one"] }],
  limitations: ["This fixture is not scientific evidence."],
  nextStep: { title: "Review the synthetic fixture", why: "Verify interface boundaries.", steps: ["Read the source receipt."], successCriterion: "Source date and analysis date remain distinct.", execution: "not_started" },
  sources: [{ id: "source-one", title: "Synthetic source report", url: "https://example.com/synthetic-report", reportDate: "2026-01-01", sha256: "a".repeat(64), excerpt: "Synthetic excerpt only." }],
  runs: [
    { role: "draft", modelId: "test-draft-model", requestId: "synthetic-draft-request", startedAt: "2026-10-05T14:00:00Z", durationMs: 1100, inputTokens: 20, outputTokens: 30 },
    { role: "review", modelId: "test-review-model", requestId: "synthetic-review-request", startedAt: "2026-10-05T14:00:02Z", durationMs: 900, inputTokens: 25, outputTokens: 15 },
  ],
  createdAt: "2026-10-05T14:01:00.000Z", sourceCommit: "b".repeat(40), evidenceKind: "report_analysis", review: { status: "source_checked", notes: ["Synthetic receipt comparison for a UI test."] },
};

describe("private progress briefing UI", () => {
  it("keeps a date-only source report on its recorded calendar day", () => {
    const expected = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date("2026-01-01"));
    expect(progressDate("2026-01-01")).toBe(expected);
    expect(progressDate("not recorded")).toBe("not recorded");
  });
  it("renders evidence limits, distinct dates, model attribution and a proposed next step", () => {
    const html = renderToStaticMarkup(React.createElement(ProgressCard, { clip: fixture, onDiscuss: () => {} }));
    for (const text of ["Source reports:", "Analysis generated:", 'dateTime="2026-01-01"', 'dateTime="2026-10-05T14:01:00.000Z"', "test-draft-model", "test-review-model", "Proposed · not started", "Analysis of existing reports; no new experiment.", "not published to the Library", "Discuss this next step", "Opens a draft. You decide when to send."]) expect(html).toContain(text);
    expect(html).toContain('href="https://example.com/synthetic-report"');
    expect(html).toContain('aria-controls="receipts-synthetic-ui-test"');
  });
  it("does not turn unsafe source URLs or report HTML into executable content", () => {
    const malicious = { ...fixture, title: "<script>not executable</script>", sources: [{ ...fixture.sources[0], url: "javascript:alert(1)" }] };
    const html = renderToStaticMarkup(React.createElement(ProgressCard, { clip: malicious }));
    expect(html).not.toContain('href="javascript:');
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });
  it("rejects malformed feed entries so the fetch path can show its recovery state", () => {
    expect(decodeProgressFeed({ clips: [fixture], truncated: false }).clips).toHaveLength(1);
    for (const invalid of [null, {}, { clips: null, truncated: false }, { clips: [{ ...fixture, nextStep: undefined }], truncated: false }, { clips: [{ ...fixture, evidenceKind: "experiment_result" }], truncated: false }]) expect(() => decodeProgressFeed(invalid)).toThrow();
  });
  it("prepares a bounded named conversation with sources and no execution claim", () => {
    const result = nextStepDiscussion(fixture);
    expect(result.title.length).toBeLessThanOrEqual(80);
    expect(result.prompt).toContain("Proposed next step (not started)");
    expect(result.prompt).toContain("report dated 2026-01-01");
    expect(result.prompt).toContain("https://example.com/synthetic-report");
    expect(result.prompt).toContain("Do not start or dispatch work.");
    const maximal = { ...fixture, title: "x".repeat(180), summary: "x".repeat(1000), limitations: Array(8).fill("x".repeat(1500)),
      nextStep: { ...fixture.nextStep, title: "x".repeat(180), why: "x".repeat(1500), successCriterion: "x".repeat(1500), steps: Array(8).fill("x".repeat(1500)) },
      sources: Array.from({ length: 3 }, (_, i) => ({ ...fixture.sources[0], id: `source-${i}`, title: "x".repeat(180), url: `https://example.com/${"x".repeat(2028)}` })) };
    expect(nextStepDiscussion(maximal).prompt.length).toBeLessThanOrEqual(16000);
  });
});
