import { z } from "zod";

export const conversationIdSchema = z.string().regex(/^[a-z0-9][a-z0-9-]{0,63}$/);
export const settingsSchema = z.object({
  title: z.string().trim().min(1).max(80).refine((s) => !/[\x00-\x1f\x7f]/.test(s), "Use a single-line title."),
  profile: z.string().min(1).max(32),
}).strict();

export interface WorkspaceSettings { title: string; profile: string }
export interface WorkspaceState extends WorkspaceSettings {
  provider: string | null;
  modelId: string | null;
  lastTurnAt: string | null;
  routing?: { mode: string; reason: string; profileId: string; confidence?: number; margin?: number; task?: string; suggestedProfileId?: string; contextTruncated?: boolean };
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
