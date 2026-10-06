import { routeAgentRequest } from "agents";
import { checkAccess } from "../src/middleware/access";
import { checkWorkspaceRequest, WORKSPACE_PRIVATE_HEADERS } from "../src/middleware/workspaceAccess";
import { getModelCatalog } from "../src/agents/modelProfiles";
import { listWorkspaceConversations } from "../src/workspace/registry";
import { workspaceHtml, workspaceJavaScript } from "../src/workspace/html";
import { workspacePreviewEnv, type PreviewEnv } from "./environment";

function privateResponse(response: Response) {
  if (response.status === 101) return response;
  const result = new Response(response.body, response);
  for (const [name, value] of Object.entries(WORKSPACE_PRIVATE_HEADERS)) result.headers.set(name, value);
  result.headers.set("X-Robots-Tag", "noindex, nofollow");
  return result;
}

export async function previewFetch(request: Request, bindings: PreviewEnv): Promise<Response> {
  const env = workspacePreviewEnv(bindings);
  const url = new URL(request.url);
  // Every staging response, including assets and evidence links, requires Access.
  if (!env.ADMIN_EMAIL?.trim()) return privateResponse(new Response("Preview operator is not configured", { status: 403 }));
  const denial = await checkAccess(request, env, [env.ADMIN_EMAIL ?? ""].filter(Boolean));
  if (denial) return privateResponse(denial);
  const invalid = checkWorkspaceRequest(request);
  if (invalid) return privateResponse(invalid);

  const segments = url.pathname.split("/").filter(Boolean);
  if (segments[0] === "agents" && segments[1] === "research-workspace") {
    return privateResponse(await routeAgentRequest(request, env) ?? new Response("Not found", { status: 404 }));
  }
  if (request.method !== "GET") return privateResponse(new Response("Not found", { status: 404 }));
  if (url.pathname === "/") return privateResponse(Response.redirect(new URL("/workspace", url).toString(), 302));
  if (url.pathname === "/workspace" || url.pathname === "/workspace/") {
    const html = workspaceHtml().replace("<body>", '<body><div style="background:#f6d58a;color:#171914;padding:8px 18px;font:13px system-ui">HOSTED PREVIEW · synthetic evidence · real model calls · separate conversation storage</div>');
    return privateResponse(new Response(html, { headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    } }));
  }
  if (url.pathname === "/workspace/app.js") return privateResponse(new Response(workspaceJavaScript, { headers: { "Content-Type": "text/javascript; charset=utf-8" } }));
  if (url.pathname === "/workspace/models") return privateResponse(Response.json(getModelCatalog(env)));
  if (url.pathname === "/workspace/conversations") return privateResponse(Response.json(await listWorkspaceConversations(env)));
  if (url.pathname === "/live") return privateResponse(new Response("Hosted preview: ledger records are synthetic interface fixtures, not scientific results. No production ledger or experiment dispatch is connected."));
  return privateResponse(new Response("Not found", { status: 404 }));
}
