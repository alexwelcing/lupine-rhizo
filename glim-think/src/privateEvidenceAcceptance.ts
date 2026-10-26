import type { PrivateEvidenceEnv } from "./workspace/evidenceObjects";
import { dispatchPrivateEvidence } from "./workspace/evidenceDispatch";
import { WORKSPACE_PRIVATE_HEADERS } from "./middleware/workspaceAccess";

const allowedBindings = new Set([
  "ADMIN_EMAIL", "CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD",
  "PRIVATE_EVIDENCE", "PRIVATE_EVIDENCE_ENABLED",
  "PRIVATE_CORPUS", "PRIVATE_CORPUS_ENABLED",
]);

/** Acceptance entrypoint only: no agents, queues, cron, providers, telemetry,
 * runtime ledger, public artifacts, source fetching or schema application.
 * Resource identities and upstream Access coverage still require live review.
 */
export default {
  async fetch(request: Request, env: PrivateEvidenceEnv): Promise<Response> {
    try {
      // Fail closed on accidental bindings rather than silently ignore them.
      // This cannot detect a public resource bound under an allowed private name.
      if (Object.keys(env).some(key => !allowedBindings.has(key))) {
        return Response.json({ error: "Private acceptance configuration rejected" },
          { status: 503, headers: WORKSPACE_PRIVATE_HEADERS });
      }
      return await dispatchPrivateEvidence(request, env, async () =>
        Response.json({ error: "Private acceptance route not found" },
          { status: 404, headers: WORKSPACE_PRIVATE_HEADERS }));
    } catch {
      return Response.json({ error: "Private acceptance unavailable; no retry performed" },
        { status: 503, headers: WORKSPACE_PRIVATE_HEADERS });
    }
  },
};
