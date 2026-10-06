import { describe, expect, it, vi } from "vitest";
import type { Env } from "../../types";
import { progressClipSchema, PROGRESS_PAYLOAD_MAX_BYTES, type ProgressClip } from "../progressContracts";
import { listWorkspaceProgress, PROGRESS_LIST_SQL, workspaceProgressResponse } from "../progress";

function clip(id = "progress-test"): ProgressClip {
  return {
    id, title: "Synthetic test report analysis", summary: "This fixture exercises the feed, not scientific results.",
    findings: [{ text: "The fixture report records a test observation.", sourceIds: ["source-one"] }],
    limitations: ["This is test data."],
    nextStep: { title: "Review the fixture", why: "Confirm source attribution.", steps: ["Read the cited excerpt."], successCriterion: "The finding matches its source.", execution: "not_started" },
    sources: [{ id: "source-one", title: "Synthetic source", url: "https://example.test/report", reportDate: "2026-10-05", sha256: "a".repeat(64), excerpt: "A synthetic observation was recorded." }],
    runs: ["draft", "review"].map(role => ({ role: role as "draft" | "review", modelId: `fixture-${role}`, requestId: `${role}-receipt`, startedAt: "2026-10-05T12:00:00Z", durationMs: 12.5, inputTokens: 100, outputTokens: 20 })),
    createdAt: "2026-10-05T12:01:00.000Z", sourceCommit: "b".repeat(40), evidenceKind: "report_analysis",
    review: { status: "source_checked", notes: ["Checked against the test excerpt."] },
  };
}
function row(value = clip()) { return { id: value.id, created_at: value.createdAt, payload: JSON.stringify(value) }; }
function database(rows: unknown[]) {
  const all = vi.fn().mockResolvedValue({ success: true, results: rows });
  const prepare = vi.fn(() => ({ all }));
  return { env: { LEDGER: { prepare } } as unknown as Env, prepare, all };
}

describe("progress contract", () => {
  it("preserves report provenance, explicit unstarted work and two run receipts", () => {
    expect(progressClipSchema.parse(clip())).toEqual(clip());
  });
  it.each(["not a URL", "http://example.test/report", "javascript:alert(1)", "https://user:password@example.test/report"])("rejects unsafe source link %s", url => {
    const value = clip(); value.sources[0].url = url;
    expect(progressClipSchema.safeParse(value).success).toBe(false);
  });
  it("rejects missing or ambiguous citations", () => {
    const unresolved = clip(); unresolved.findings[0].sourceIds = ["absent"];
    expect(progressClipSchema.safeParse(unresolved).success).toBe(false);
    const duplicate = clip(); duplicate.sources.push({ ...duplicate.sources[0] });
    expect(progressClipSchema.safeParse(duplicate).success).toBe(false);
  });
  it("rejects an unreviewed clip, fabricated execution status and hidden fields", () => {
    const missingReview = clip(); missingReview.runs[1].role = "draft";
    expect(progressClipSchema.safeParse(missingReview).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), nextStep: { ...clip().nextStep, execution: "completed" } }).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), evidenceKind: "experiment_result" }).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), review: { status: "model_approved", notes: [] } }).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), secret: "should not be saved" }).success).toBe(false);
  });
  it("bounds text, collection sizes, dates, hashes and numeric receipts", () => {
    expect(progressClipSchema.safeParse({ ...clip(), summary: "x".repeat(1001) }).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), findings: Array(9).fill(clip().findings[0]) }).success).toBe(false);
    const oversized = clip(); oversized.sources[0].excerpt = "x".repeat(6001);
    expect(progressClipSchema.safeParse(oversized).success).toBe(false);
    const badDate = clip(); badDate.sources[0].reportDate = "2026-02-31";
    expect(progressClipSchema.safeParse(badDate).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), sourceCommit: "main" }).success).toBe(false);
    expect(progressClipSchema.safeParse({ ...clip(), createdAt: "2026-10-05T12:01:00Z" }).success).toBe(false);
    for (const invalid of [-1, Infinity, NaN]) {
      const value = clip(); value.runs[0].durationMs = invalid;
      expect(progressClipSchema.safeParse(value).success).toBe(false);
    }
    const tokens = clip(); tokens.runs[0].inputTokens = 1.5;
    expect(progressClipSchema.safeParse(tokens).success).toBe(false);
  });
});

describe("private progress reads", () => {
  it("returns an explicit empty feed when the existing table has no records", async () => {
    const { env } = database([]);
    await expect(listWorkspaceProgress(env)).resolves.toEqual({ clips: [], truncated: false });
  });
  it("uses a bounded newest-first query and preserves the stored attribution", async () => {
    const { env, prepare } = database([row()]);
    await expect(listWorkspaceProgress(env)).resolves.toEqual({ clips: [clip()], truncated: false });
    expect(prepare).toHaveBeenCalledExactlyOnceWith(PROGRESS_LIST_SQL);
    expect(PROGRESS_LIST_SQL).toContain("ORDER BY created_at DESC, id DESC LIMIT 21");
    expect(PROGRESS_LIST_SQL).toContain("length(CAST(payload AS BLOB)) <= 131072");
  });
  it("returns twenty clips with an honest truncation flag", async () => {
    const { env } = database(Array.from({ length: 21 }, (_, index) => row(clip(`progress-${index}`))));
    const result = await listWorkspaceProgress(env);
    expect(result.clips).toHaveLength(20);
    expect(result.truncated).toBe(true);
  });
  it.each([
    { ...row(), payload: "{invalid" },
    { ...row(), payload: null },
    { ...row(), payload: JSON.stringify({ ...clip(), summary: "" }) },
    { ...row(), payload: " ".repeat(PROGRESS_PAYLOAD_MAX_BYTES + 1) },
    { ...row(), id: "wrong-id" },
    { ...row(), created_at: "2020-01-01T00:00:00Z" },
  ])("does not hide a malformed record behind an empty or partial success", async invalid => {
    const { env } = database([row(clip("valid-first")), invalid]);
    const response = await workspaceProgressResponse(env);
    expect(response.status).toBe(503);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
    expect(await response.json()).toEqual({ error: "Progress feed contains an invalid saved record.", code: "invalid_progress_data" });
  });
  it("makes missing tables and failed D1 responses visible without leaking raw errors", async () => {
    const { env, all } = database([]);
    all.mockRejectedValueOnce(new Error("private database details"));
    const missing = await workspaceProgressResponse(env);
    expect(missing.status).toBe(503);
    expect(await missing.text()).not.toContain("private database details");
    all.mockResolvedValueOnce({ success: false, results: [] });
    expect((await workspaceProgressResponse(env)).status).toBe(503);
  });
});
