import { z } from "zod";

export const conversationIdSchema = z.string().regex(/^[a-z0-9][a-z0-9-]{0,63}$/);
export const settingsSchema = z.object({
  title: z.string().trim().min(1).max(80).refine((s) => !/[\x00-\x1f\x7f]/.test(s), "Use a single-line title."),
  profile: z.string().min(1).max(32),
}).strict();

export interface WorkspaceSettings { title: string; profile: string }

const probability = z.number().finite().min(0).max(1);
const routingChoice = <const T extends readonly [string, ...string[]]>(choices: T) => z.object({
  choice: z.enum(choices), confidence: probability, margin: probability,
});
/** Explicit metadata projection: prompts, classifier bodies and errors never enter state. */
export const workspaceRoutingSchema = z.object({
  mode: z.enum(["manual", "disabled", "shadow", "auto", "fallback"]),
  reason: z.string().max(120), profileId: z.string().min(1).max(32),
  source: z.enum(["manual", "configured-default", "clef-flash"]).optional(),
  classifierModel: z.string().max(128).optional(),
  confidence: probability.optional(), margin: probability.optional(),
  task: z.enum(["fast", "deep", "code", "research"]).optional(),
  suggestedProfileId: z.string().max(32).optional(), contextTruncated: z.boolean().optional(),
  latencyMs: z.number().finite().nonnegative().optional(), inputTokens: z.number().int().nonnegative().optional(),
  planningMode: z.enum(["auto", "shadow"]).optional(),
  evidence: routingChoice(["none", "research_runs", "ledger", "both"]).optional(),
  workflow: routingChoice(["answer", "literature", "hypothesis", "critique", "analysis"]).optional(),
});
export type WorkspaceRouting = z.infer<typeof workspaceRoutingSchema>;
export const workspaceDecisionSchema = workspaceRoutingSchema.extend({
  timestamp: z.iso.datetime(), provider: z.string().max(64), modelId: z.string().max(160),
});
export type WorkspaceDecision = z.infer<typeof workspaceDecisionSchema>;
export const workspaceRoutingCacheSchema = z.object({
  identity: z.string().regex(/^[a-f0-9]{64}$/), decision: workspaceRoutingSchema,
  provider: z.string().max(64), modelId: z.string().max(160),
});

/** Human-readable decision labels carry no tool authority. */
export function workspaceRoutingSummary(routing: WorkspaceRouting): string {
  const evidence = { none: "no saved evidence suggested", research_runs: "research runs", ledger: "saved ledger", both: "research runs + ledger" };
  const workflow = { answer: "direct answer", literature: "literature comparison", hypothesis: "hypothesis design", critique: "critical review", analysis: "measurement analysis" };
  const parts = [`Reply profile: ${routing.profileId}`];
  const applied = routing.planningMode === "auto" || (!routing.planningMode && routing.mode === "auto");
  if (routing.evidence) parts.push(`${applied ? "Evidence" : "Suggested evidence"}: ${evidence[routing.evidence.choice]}`);
  if (routing.workflow) parts.push(`${applied ? "Research task" : "Suggested research task"}: ${workflow[routing.workflow.choice]}`);
  if (routing.latencyMs !== undefined) parts.push(`Clef: ${Math.round(routing.latencyMs)} ms`);
  return parts.join(" · ");
}

export interface WorkspaceState extends WorkspaceSettings {
  provider: string | null;
  modelId: string | null;
  lastTurnAt: string | null;
  routing?: WorkspaceRouting;
  routingHistory?: WorkspaceDecision[];
  routingCache?: z.infer<typeof workspaceRoutingCacheSchema>;
}
export interface ConversationSummary { id: string; title: string; updatedAt: string }
export interface PublicModelProfile {
  id: string; label: string; role: string; provider: string; modelId: string;
  configured: boolean; availability: string;
}

export function validateChatProfile(profiles: PublicModelProfile[], id: string) {
  const profile = profiles.find((p) => p.id === id);
  if (!profile || profile.role === "decision" || !profile.configured) {
    throw new Error("Choose a configured chat model from the catalog.");
  }
  return profile;
}

export function validateWorkspaceStateChange(source: unknown) {
  if (source !== "server") throw new Error("Use the validated workspace settings action.");
}

/** Evidence results and prompts are data, never HTML. */
export function safeEvidenceHref(value: string): string | null {
  if (value.startsWith("/") && !value.startsWith("//") && !/[\\\x00-\x20]/.test(value)) return value;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch { return null; }
}
