import { defineConfig } from "vitest/config";
import { transform } from "esbuild";

/**
 * Vitest configuration for glim-think.
 *
 * We deliberately do NOT use `@cloudflare/vitest-pool-workers` — it spins up
 * workerd per test file and requires a stable Worker entry + miniflare
 * bindings. The load-bearing lanes we cover (feed serve, orchestrator
 * dispatch, queue sync, schema contract) all take an `env` parameter that
 * is trivially stubbable in plain node, so we stub D1/R2/KV/Queue bindings
 * at the call site and keep the runtime lightweight. Revisit only if a
 * test ever needs the real workerd runtime (DOs, Workers AI, real cron).
 *
 * Both projects run `tsc --noEmit` on their test files and fail the run on
 * type errors. Worker tests retain Workers globals; workspace client tests
 * use DOM globals without introducing them into the Worker typecheck.
 * This is what makes the schema-contract test
 * (`src/literature/__tests__/schema_contract.test.ts`) catch field drift
 * in `ClaimRecord` / `VectorizeClaimMetadata` at test-run time, not only
 * at `pnpm lint` time.
 */
export default defineConfig({
  plugins: [{
    name: "workspace-standard-decorators",
    enforce: "pre",
    async transform(source, id) {
      // Vite 8's Oxc currently preserves standard decorators that Node 22
      // cannot execute. Use the same lowering engine as the Worker bundle.
      if (!id.endsWith("/workspace/ResearchWorkspace.ts")) return;
      return transform(source, {
        loader: "ts", target: "es2022", format: "esm", sourcemap: "inline",
        sourcefile: id, tsconfigRaw: { compilerOptions: { experimentalDecorators: false } },
      });
    },
  }],
  test: {
    environment: "node",
    globals: false,
    testTimeout: 10_000,
    projects: [
      {
        extends: true,
        test: {
          name: "worker",
          include: ["src/**/__tests__/**/*.test.ts"],
          exclude: ["src/workspace/client/**"],
          typecheck: {
            enabled: true,
            tsconfig: "./tsconfig.test.json",
            include: ["src/**/__tests__/**/*.test.ts"],
            exclude: ["src/workspace/client/**"],
          },
        },
      },
      {
        extends: true,
        test: {
          name: "workspace-client",
          include: ["src/workspace/client/**/__tests__/**/*.test.{ts,tsx}"],
          typecheck: {
            enabled: true,
            tsconfig: "./tsconfig.workspace-client.test.json",
            include: ["src/workspace/client/**/__tests__/**/*.test.{ts,tsx}"],
          },
        },
      },
    ],
  },
});
