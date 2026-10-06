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
 * `typecheck.enabled` runs `tsc --noEmit` on every test file and fails the
 * run on type errors — this is what makes the schema-contract test
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
    include: ["src/**/__tests__/**/*.test.ts"],
    environment: "node",
    globals: false,
    testTimeout: 10_000,
    typecheck: {
      enabled: true,
      tsconfig: "./tsconfig.test.json",
      include: ["src/**/__tests__/**/*.test.ts"],
    },
  },
});
