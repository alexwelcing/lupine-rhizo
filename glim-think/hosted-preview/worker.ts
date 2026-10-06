import { ResearchWorkspace as Workspace } from "../src/workspace/ResearchWorkspace";
import { workspacePreviewEnv, type PreviewEnv } from "./environment";
import { previewFetch } from "./handler";

/** Real Think chat, persistence, model routing and read-only evidence tools. */
export class ResearchWorkspace extends Workspace {
  constructor(ctx: DurableObjectState, env: PreviewEnv) { super(ctx, workspacePreviewEnv(env)); }
  override getSystemPrompt() {
    return super.getSystemPrompt() + " This is an isolated private preview. The read_evidence tool reads synthetic interface fixtures, not scientific evidence; label them accordingly. The read_research_runs tool reads imported local scientific PI cycle receipts and packets. Attribute stage status, source dates, model identity and receipt hashes; a completed discussion is not an executed experiment. The separate Progress feed contains source-checked analyses of cited reports, not newly executed experiments. You cannot read that feed through your current tools. Do not present a proposed next step as completed work.";
  }
}

// No scheduled, queue, Workflow, telemetry or production server entrypoint.
export default { fetch: previewFetch };
