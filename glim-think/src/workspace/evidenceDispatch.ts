import type { PrivateEvidenceEnv } from "./evidenceObjects";
import { WORKSPACE_PRIVATE_HEADERS } from "../middleware/workspaceAccess";
import { evidenceObjectsResponse } from "./evidenceObjects";
import { corpusResponse } from "./corpus";

/** Route private evidence before automatic request/binding telemetry. */
export async function dispatchPrivateEvidence(
  request: Request, env: PrivateEvidenceEnv, fallback: () => Promise<Response>,
): Promise<Response> {
  const pathname = new URL(request.url).pathname;
  const canonical = "/" + pathname.split("/").filter(Boolean).join("/");
  const privateRoute = ["/workspace/corpus", "/workspace/evidence-objects"]
    .some(root => canonical === root || canonical.startsWith(root + "/"));
  if (!privateRoute) return fallback();
  if (pathname !== canonical) return Response.json({error:"Use the canonical private evidence path"}, {status:400,headers:WORKSPACE_PRIVATE_HEADERS});
  try {
    return await evidenceObjectsResponse(request,env) ??
      await corpusResponse(request,env) ??
      Response.json({error:"Private evidence route not found"},{status:404,headers:WORKSPACE_PRIVATE_HEADERS});
  } catch {
    // Do not send private SQL, object keys, inputs, or provider exceptions to telemetry.
    return Response.json({error:"Private evidence operation unavailable; outcome may be unknown; no retry performed"},
      {status:503,headers:WORKSPACE_PRIVATE_HEADERS});
  }
}
