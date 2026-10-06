import { z } from "zod";

export const PROGRESS_PAYLOAD_MAX_BYTES = 128 * 1024;
const id = z.string().regex(/^[a-z0-9][a-z0-9-]{0,95}$/);
const text = (max: number) => z.string().min(1).max(max);
const timestamp = z.iso.datetime();
const source = z.object({
  id,
  title: text(180),
  url: z.url().max(2048).refine(value => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password;
    } catch { return false; }
  }, "Sources must use HTTPS without embedded credentials."),
  reportDate: z.iso.date(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/i),
  excerpt: text(6000),
}).strict();
const run = z.object({
  role: z.enum(["draft", "review"]),
  modelId: text(200),
  requestId: text(200),
  startedAt: timestamp,
  durationMs: z.number().finite().nonnegative(),
  inputTokens: z.number().int().nonnegative(),
  outputTokens: z.number().int().nonnegative(),
}).strict();

/** A source-checked report analysis, never a claim that its proposed work ran.
 * `source_checked` records a human/agent source comparison after model review;
 * a model's approval alone must not set this status.
 */
export const progressClipSchema = z.object({
  id,
  title: text(180),
  summary: text(1000),
  findings: z.array(z.object({ text: text(1500), sourceIds: z.array(id).min(1).max(3) }).strict()).min(1).max(8),
  limitations: z.array(text(1500)).min(1).max(8),
  nextStep: z.object({
    title: text(180),
    why: text(1500),
    steps: z.array(text(1500)).min(1).max(8),
    successCriterion: text(1500),
    execution: z.literal("not_started"),
  }).strict(),
  sources: z.array(source).min(1).max(3),
  runs: z.array(run).min(2).max(4),
  // Fixed UTC precision keeps D1's text ordering chronological.
  createdAt: z.iso.datetime({ precision: 3 }),
  sourceCommit: z.string().regex(/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/i),
  evidenceKind: z.literal("report_analysis"),
  review: z.object({ status: z.literal("source_checked"), notes: z.array(text(1500)).max(8) }).strict(),
}).strict().superRefine((clip, ctx) => {
  const sourceIds = new Set(clip.sources.map(item => item.id));
  if (sourceIds.size !== clip.sources.length) ctx.addIssue({ code: "custom", path: ["sources"], message: "Source IDs must be unique." });
  for (const [index, finding] of clip.findings.entries()) {
    if (new Set(finding.sourceIds).size !== finding.sourceIds.length || finding.sourceIds.some(sourceId => !sourceIds.has(sourceId))) {
      ctx.addIssue({ code: "custom", path: ["findings", index, "sourceIds"], message: "Citations must resolve uniquely to this clip's sources." });
    }
  }
  if (!["draft", "review"].every(role => clip.runs.some(item => item.role === role))) {
    ctx.addIssue({ code: "custom", path: ["runs"], message: "Include both draft and review run receipts." });
  }
  if (new TextEncoder().encode(JSON.stringify(clip)).byteLength > PROGRESS_PAYLOAD_MAX_BYTES) {
    ctx.addIssue({ code: "custom", message: "Progress clip exceeds the saved payload limit." });
  }
});

export type ProgressClip = z.infer<typeof progressClipSchema>;
export interface ProgressFeed { clips: ProgressClip[]; truncated: boolean }
