import { ResearchWorkspace as Workspace } from "../src/workspace/ResearchWorkspace";
import { workspacePreviewEnv, type PreviewEnv } from "./environment";
import { previewFetch } from "./handler";

/** Real Think chat, persistence, model routing and read-only evidence tools. */
export class ResearchWorkspace extends Workspace {
  constructor(ctx: DurableObjectState, env: PreviewEnv) { super(ctx, workspacePreviewEnv(env)); }
  override getSystemPrompt() {
    return super.getSystemPrompt() + " This is an isolated hosted preview. Every ledger record is synthetic interface test data, not scientific evidence. Label it accordingly.";
  }
}

// No scheduled, queue, Workflow, telemetry or production server entrypoint.
export default { fetch: previewFetch };
