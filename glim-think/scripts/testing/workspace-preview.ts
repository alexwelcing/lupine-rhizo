/** Local-only integration fixture. Never import this entry from production. */
import { routeAgentRequest } from "agents";
import type { LanguageModelV3, LanguageModelV3StreamPart } from "@ai-sdk/provider";
import type { TurnContext } from "@cloudflare/think";
import { ResearchWorkspace as ProductionWorkspace } from "../../src/workspace/ResearchWorkspace";
import { workspaceHtml, workspaceJavaScript } from "../../src/workspace/html";
import { getModelCatalog } from "../../src/agents/modelProfiles";
import { listWorkspaceConversations } from "../../src/workspace/registry";
import { workspaceProgressResponse } from "../../src/workspace/progress";
import { researchRunsResponse } from "../../src/workspace/researchRuns";
import { conversationIdSchema, type WorkspaceSettings } from "../../src/workspace/contracts";
import type { Env } from "../../src/types";

type LocalEnv = Pick<Env, "CONFIG" | "LEDGER" | "RESEARCH_WORKSPACE">;
// Whitelisting local bindings also discards any accidentally loaded .dev.vars.
function previewEnv(env: LocalEnv): Env {
  return { CONFIG: env.CONFIG, LEDGER: env.LEDGER, RESEARCH_WORKSPACE: env.RESEARCH_WORKSPACE,
    AI: { run: () => { throw new Error("Local preview cannot call Workers AI."); } },
  } as unknown as Env;
}

const usage = { inputTokens: { total: 0, noCache: 0, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 0, text: 0, reasoning: 0 } };
const model: LanguageModelV3 = {
  specificationVersion: "v3", provider: "local-preview", modelId: "deterministic-fixture", supportedUrls: {},
  doGenerate: async () => { throw new Error("Local preview supports streaming only."); },
  doStream: async (options) => {
    const last = options.prompt.at(-1);
    const user = [...options.prompt].reverse().find((message) => message.role === "user");
    const prompt = user?.content.filter((part) => part.type === "text").map((part) => part.text).join(" ") ?? "";
    const toolRead = /evidence|papers|hypothes|activity/i.test(prompt) && last?.role !== "tool";
    const chunks: LanguageModelV3StreamPart[] = [{ type: "stream-start", warnings: [] }];
    if (toolRead) {
      chunks.push({ type: "tool-call", toolCallId: crypto.randomUUID(), toolName: "read_evidence", input: JSON.stringify({ collection: /papers/i.test(prompt) ? "papers" : /activity/i.test(prompt) ? "activity" : "hypotheses", query: "", limit: 3 }) });
    } else {
      const text = last?.role === "tool"
        ? "## Local evidence preview\n\nThe read-only tool returned **synthetic fixture records** from local SQLite. These are interface test data, not scientific findings.\n\n- The evidence panel preserves the record IDs and source.\n- No experiment or remote compute was started.\n- Open [the local evidence page](/live) to see the preview boundary.\n\nYour conversation is stored in the local Think Durable Object. Reload or reopen its copied link to check continuity."
        : "## Local conversation preview\n\nThis reply is deterministic and makes **no model or network call**. It streams slowly enough to test Stop reply and Reconnect.\n\nYour named conversation and messages use the real Think Durable Object persistence path. Try asking about saved evidence to exercise the bounded read-only tool.\n\nNo experiments, devices, providers, or production data are connected to this fixture.";
      chunks.push({ type: "text-start", id: "preview-text" });
      for (const delta of text.match(/.{1,18}|\n/g) ?? []) chunks.push({ type: "text-delta", id: "preview-text", delta });
      chunks.push({ type: "text-end", id: "preview-text" });
    }
    chunks.push({ type: "finish", usage, finishReason: { unified: toolRead ? "tool-calls" : "stop", raw: "local-preview" } });
    let index = 0;
    return { stream: new ReadableStream<LanguageModelV3StreamPart>({
      async pull(controller) {
        await new Promise((resolve) => setTimeout(resolve, 160));
        if (options.abortSignal?.aborted) { controller.error(new Error("Local preview reply stopped.")); return; }
        if (index < chunks.length) controller.enqueue(chunks[index++]);
        else controller.close();
      },
    }) };
  },
};

export class ResearchWorkspace extends ProductionWorkspace {
  constructor(ctx: DurableObjectState, env: LocalEnv) { super(ctx, previewEnv(env)); }
  override getModel() { return model; }
  override async beforeTurn(_ctx: TurnContext) {
    const settings = this.getConfig<WorkspaceSettings>() ?? { title: "Research conversation", profile: "workers-flash" };
    // Production RPC validation, evidence tools, history, streaming, cancellation,
    // and Durable Object storage are retained; only model routing is replaced.
    this.setState({ ...settings, provider: model.provider, modelId: model.modelId, lastTurnAt: new Date().toISOString(),
      routing: { mode: "local-preview", profileId: settings.profile, reason: "Deterministic fixture; no provider call" } });
    return { model, tools: this.getTools(), activeTools: ["read_evidence"], maxSteps: 3 };
  }
}

export default {
  async fetch(request: Request, bindings: LocalEnv) {
    const url = new URL(request.url);
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) return new Response("Local preview only", { status: 403 });
    const origin = request.headers.get("Origin");
    if (origin && origin !== url.origin) return new Response("Same-origin preview only", { status: 403 });
    const env = previewEnv(bindings);
    const headers = { "Cache-Control": "no-store" };
    const researchRunResponse = await researchRunsResponse(request, env, true);
    if (researchRunResponse) return researchRunResponse;
    if (url.pathname === "/workspace" || url.pathname === "/") {
      const html = workspaceHtml().replace("<body>", '<body><div style="background:#f6d58a;color:#171914;padding:8px 18px;font:13px system-ui;position:relative;z-index:9">LOCAL PREVIEW · synthetic chat evidence · saved Progress analyses · deterministic replies</div>');
      return new Response(html, { headers: { ...headers, "Content-Type": "text/html;charset=utf-8" } });
    }
    if (url.pathname === "/workspace/app.js") return new Response(workspaceJavaScript, { headers: { ...headers, "Content-Type": "text/javascript;charset=utf-8" } });
    if (url.pathname === "/workspace/models") return Response.json(getModelCatalog(env), { headers });
    if (url.pathname === "/workspace/conversations") return Response.json(await listWorkspaceConversations(env), { headers });
    if (url.pathname === "/workspace/progress" && request.method === "GET") return workspaceProgressResponse(env);
    if (url.pathname === "/live") return new Response("Local preview: chat evidence tables contain synthetic fixtures. Progress shows saved source-report analyses when imported; it does not mean a new experiment ran. No production database or live model calls are connected.", { headers });
    const segments = url.pathname.split("/").filter(Boolean);
    if (segments[0] !== "agents" || segments[1] !== "research-workspace" || !conversationIdSchema.safeParse(segments[2]).success) return new Response("Not found", { status: 404 });
    return await routeAgentRequest(request, env) ?? new Response("Not found", { status: 404 });
  },
};
