import type { Env } from "../types";
import { conversationIdSchema, type ConversationSummary } from "./contracts";

const PREFIX = "workspace:conversation:";
export async function rememberWorkspaceConversation(env: Env, entry: ConversationSummary) {
  conversationIdSchema.parse(entry.id);
  await env.CONFIG.put(PREFIX + entry.id, JSON.stringify(entry), {
    metadata: entry,
  });
}

/** Shared operator directory. No messages, credentials, or model output in KV. */
export async function listWorkspaceConversations(env: Env) {
  const page = await env.CONFIG.list<ConversationSummary>({ prefix: PREFIX, limit: 100 });
  const conversations = page.keys.flatMap(({ metadata }) => {
    if (!metadata || !conversationIdSchema.safeParse(metadata.id).success ||
        typeof metadata.title !== "string" || typeof metadata.updatedAt !== "string") return [];
    return [{ id: metadata.id, title: metadata.title.slice(0, 80), updatedAt: metadata.updatedAt }];
  }).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  return { conversations, truncated: !page.list_complete };
}
