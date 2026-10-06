import { defineWranglerConfig } from "wrangler/experimental-config";

export default defineWranglerConfig({
  tsconfig: "../tsconfig.json",
  build: { command: "node ../scripts/build-workspace.mjs" },
  sendMetrics: false,
});
