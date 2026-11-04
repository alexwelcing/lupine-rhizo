import { defineConfig } from "vitest/config";
import config from "./vitest.config";

// The workspace smoke check has its own UI tsc step. Vitest 4.1.6 does not
// forward --typecheck.enabled=false to projects, so using the main config
// here also starts the complete worker typecheck. Keep that work in npm test.
// Reuse the real workspace decorator transform without inheriting projects.
export default defineConfig({
  ...config,
  test: {
    ...config.test,
    projects: undefined,
    include: ["src/workspace/__tests__/workspace.test.ts"],
    typecheck: { enabled: false },
  },
});
