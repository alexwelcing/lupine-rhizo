import { bindings, defineConfig, exports } from "cf/config";
import { PREVIEW_WORKER_NAME, readPreviewSettings } from "./settings.ts";

// Set these in the launching process. Auth stays in cf's existing profile.
const settings = readPreviewSettings(process.env);

export default defineConfig({
  accountId: settings.accountId,
  worker: {
    name: PREVIEW_WORKER_NAME,
    entrypoint: "./worker.ts",
    compatibilityDate: "2026-04-25",
    compatibilityFlags: ["nodejs_compat"],
    workersDev: true,
    previewUrls: false,
    triggers: [],
    tailConsumers: [],
    observability: { enabled: false },
    exports: { ResearchWorkspace: exports.durableObject({ storage: "sqlite" }) },
    env: {
      RESEARCH_WORKSPACE: bindings.durableObject({ worker: PREVIEW_WORKER_NAME, exportName: "ResearchWorkspace" }),
      CONFIG: bindings.kv({ id: settings.kvId }),
      LEDGER: bindings.d1({ id: settings.d1Id }),
      AI: bindings.ai(),
      PROOF_SERVICE: bindings.worker({ worker: "glim-think-v1" }),
      CF_ACCESS_TEAM_DOMAIN: bindings.text(settings.team),
      CF_ACCESS_AUD: bindings.text(settings.audience),
      ADMIN_EMAIL: bindings.text(settings.adminEmail),
    },
  },
});
