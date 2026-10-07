import { routeAgentRequest } from "agents";
import { checkAccess } from "../src/middleware/access";
import { checkWorkspaceRequest, WORKSPACE_PRIVATE_HEADERS } from "../src/middleware/workspaceAccess";
import { getModelCatalog } from "../src/agents/modelProfiles";
import { listWorkspaceConversations } from "../src/workspace/registry";
import { workspaceProgressResponse } from "../src/workspace/progress";
import { researchRunsResponse } from "../src/workspace/researchRuns";
import { researchActivityResponse } from "../src/workspace/researchActivity";
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
  // Only the explicitly reviewed activity projection is public. Its import
  // verifies operator Access independently; all other preview routes stay private.
  const activityResponse = await researchActivityResponse(request, env);
  if (activityResponse) return activityResponse;
  if (!env.ADMIN_EMAIL?.trim()) return privateResponse(new Response("Preview operator is not configured", { status: 403 }));
  const denial = await checkAccess(request, env, [env.ADMIN_EMAIL ?? ""].filter(Boolean));
  if (denial) return privateResponse(denial);
  const invalid = checkWorkspaceRequest(request);
  if (invalid) return privateResponse(invalid);

  if (url.pathname === "/workspace/proof-jobs" || url.pathname.startsWith("/workspace/proof-jobs/")) {
    if (!bindings.PROOF_SERVICE) return privateResponse(Response.json({error:"Native proof service unavailable"},{status:503}));
    // Fixed Cloudflare service binding, limited to this prefix. The destination
    // independently verifies the original operator JWT and same-origin header.
    return privateResponse(await bindings.PROOF_SERVICE.fetch(request));
  }
  const researchRunResponse = await researchRunsResponse(request, env);
  if (researchRunResponse) return privateResponse(researchRunResponse);

  const segments = url.pathname.split("/").filter(Boolean);
  if (segments[0] === "agents" && segments[1] === "research-workspace") {
    return privateResponse(await routeAgentRequest(request, env) ?? new Response("Not found", { status: 404 }));
  }
  if (request.method !== "GET") return privateResponse(new Response("Not found", { status: 404 }));
  if (url.pathname === "/") return privateResponse(Response.redirect(new URL("/workspace", url).toString(), 302));
  if (url.pathname === "/workspace" || url.pathname === "/workspace/") {
    const html = workspaceHtml().replace("<body>", '<body><div style="background:#f6d58a;color:#171914;padding:8px 18px;font:13px system-ui">PRIVATE PREVIEW · imported research runs · synthetic legacy evidence · real model calls</div>');
    return privateResponse(new Response(html, { headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    } }));
  }
  if (url.pathname === "/workspace/app.js") return privateResponse(new Response(workspaceJavaScript, { headers: { "Content-Type": "text/javascript; charset=utf-8" } }));
  if (url.pathname === "/workspace/models") return privateResponse(Response.json(getModelCatalog(env)));
  if (url.pathname === "/workspace/conversations") return privateResponse(Response.json(await listWorkspaceConversations(env)));
  if (url.pathname === "/workspace/progress") return privateResponse(await workspaceProgressResponse(env));
  if (url.pathname === "/live") return privateResponse(new Response("Private preview: read_research_runs reads imported local PI cycle receipts; their research discussions do not mean an experiment ran. Legacy read_evidence uses synthetic fixtures. Progress remains separate source-report analysis. Native proof jobs use a separately authorized production service. Other production ledger and experiment dispatch routes remain unavailable."));
  return privateResponse(new Response("Not found", { status: 404 }));
}
