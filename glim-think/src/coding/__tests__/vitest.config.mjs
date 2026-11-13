// Standalone runner tests do not inherit the main application's generated UI
// prerequisites. Production code is checked separately by tsconfig.coding.json.
export default {
  test: {
    environment: "node",
    globals: false,
    include: ["src/coding/__tests__/**/*.test.ts", "src/__tests__/agendaClaims.test.ts"],
    testTimeout: 10000,
    typecheck: { enabled: false },
  },
};
