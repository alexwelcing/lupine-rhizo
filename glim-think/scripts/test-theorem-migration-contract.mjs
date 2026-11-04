import assert from "node:assert/strict";
import { copyFile, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(projectDir, "..");
const wranglerBin = path.join(projectDir, "node_modules", "wrangler", "bin", "wrangler.js");
const sourceMigrations = path.join(projectDir, "migrations");
const tempParent = path.join(tmpdir(), "opencode");
await mkdir(tempParent, { recursive: true });
const tempRoot = await mkdtemp(path.join(tempParent, "glim-theorem-migration-"));
const productionConfigPath = path.join(projectDir, "wrangler.toml");
const throughNineConfigPath = path.join(tempRoot, "wrangler-through-0009.toml");
const beforeNamingConfigPath = path.join(tempRoot, "wrangler-before-naming.toml");
const namingMigration = "0024_theorem_store_naming.sql";
const allMigrationNames = (await readdir(sourceMigrations))
  .filter((name) => /^\d{4}_.*\.sql$/.test(name))
  .sort();
assert.ok(allMigrationNames.includes(namingMigration));
const beforeNamingMigrationNames = allMigrationNames.filter((name) => name < namingMigration);

function runWrangler(args, { expectFailure = false } = {}) {
  const result = spawnSync(process.execPath, [wranglerBin, ...args], {
    cwd: projectDir,
    encoding: "utf8",
    env: { ...process.env, NO_COLOR: "1" },
  });

  if (expectFailure) {
    assert.notEqual(
      result.status,
      0,
      `expected Wrangler to reject command:\n${args.join(" ")}\n${result.stdout}\n${result.stderr}`,
    );
    return;
  }

  assert.equal(
    result.status,
    0,
    `Wrangler command failed:\n${args.join(" ")}\n${result.stdout}\n${result.stderr}`,
  );
  return result.stdout;
}

function runJust(recipe, persistTo) {
  const command = process.platform === "win32" ? "just.exe" : "just";
  const result = spawnSync(command, [recipe, persistTo.replaceAll("\\", "/")], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, NO_COLOR: "1" },
  });
  assert.equal(
    result.status,
    0,
    `just ${recipe} failed:\n${result.stdout}\n${result.stderr}`,
  );
}

function localArgs(persistTo, configPath = productionConfigPath) {
  return ["--local", "--persist-to", persistTo, "--config", configPath];
}

function query(persistTo, sql, configPath = productionConfigPath) {
  const output = runWrangler([
    "d1",
    "execute",
    "LEDGER",
    ...localArgs(persistTo, configPath),
    "--command",
    sql,
    "--json",
  ]);
  const payload = JSON.parse(output);
  assert.equal(payload[0]?.success, true, output);
  return payload[0]?.results ?? [];
}

function execute(persistTo, sql, options, configPath = productionConfigPath) {
  return runWrangler(
    ["d1", "execute", "LEDGER", ...localArgs(persistTo, configPath), "--command", sql],
    options,
  );
}

function executeFile(persistTo, filePath, configPath = productionConfigPath) {
  runWrangler([
    "d1",
    "execute",
    "LEDGER",
    ...localArgs(persistTo, configPath),
    "--file",
    filePath,
  ]);
}

function applyMigrations(persistTo, configPath = productionConfigPath) {
  runWrangler([
    "d1",
    "migrations",
    "apply",
    "LEDGER",
    ...localArgs(persistTo, configPath),
  ]);
}

function assertMigrationHistory(persistTo, expected = allMigrationNames) {
  assert.deepEqual(
    query(persistTo, "SELECT name FROM d1_migrations ORDER BY name").map((row) => row.name),
    [...expected].sort(),
  );
}

function assertForeignKeys(persistTo) {
  assert.deepEqual(query(persistTo, "PRAGMA foreign_key_check"), []);
}

async function configureHarness() {
  const migrationsDir = path.join(tempRoot, "migrations-through-0009");
  await mkdir(migrationsDir);
  for (const name of allMigrationNames.slice(0, 9)) {
    await copyFile(path.join(sourceMigrations, name), path.join(migrationsDir, name));
  }
  const productionConfig = await readFile(productionConfigPath, "utf8");
  const databaseName = productionConfig.match(/database_name\s*=\s*"([^"]+)"/)?.[1];
  const databaseId = productionConfig.match(/database_id\s*=\s*"([^"]+)"/)?.[1];
  assert.ok(databaseName && databaseId, "wrangler.toml must define the LEDGER D1 database");
  await writeFile(
    throughNineConfigPath,
    `name = "glim-theorem-migration-contract"\nmain = "noop.js"\ncompatibility_date = "2026-04-25"\n\n[[d1_databases]]\nbinding = "LEDGER"\ndatabase_name = "${databaseName}"\ndatabase_id = "${databaseId}"\nmigrations_dir = "migrations-through-0009"\n`,
    "utf8",
  );
  const beforeNamingDir = path.join(tempRoot, "migrations-before-naming");
  await mkdir(beforeNamingDir);
  for (const name of beforeNamingMigrationNames) {
    await copyFile(path.join(sourceMigrations, name), path.join(beforeNamingDir, name));
  }
  const throughNineConfig = await readFile(throughNineConfigPath, "utf8");
  await writeFile(
    beforeNamingConfigPath,
    throughNineConfig.replace("migrations-through-0009", "migrations-before-naming"),
    "utf8",
  );
  await writeFile(path.join(tempRoot, "noop.js"), "export default {};\n", "utf8");
}


function assertCanonicalStoreObjects(persistTo) {
  const objects = query(
    persistTo,
    "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'",
  );
  const names = new Set(objects.map((row) => row.name));
  for (const name of [
    "theorems", "facet_registry", "facet_state",
    "theorems_0011_canonical_snapshot", "facet_state_0011_canonical_snapshot",
    "theorems_0011_reconciliation_applied",
    "idx_theorems_identity", "idx_theorems_facet", "idx_theorems_status",
    "idx_theorems_proof_revision",
    "theorems_0011_snapshot_insert", "theorems_0011_snapshot_update",
    "theorems_0011_snapshot_delete", "facet_state_0011_snapshot_insert",
    "facet_state_0011_snapshot_update", "facet_state_0011_snapshot_delete",
  ]) {
    assert.equal(names.has(name), true, `canonical store object missing: ${name}`);
  }
  for (const { name, sql } of objects) {
    assert.equal(/atlas_(?:theorems|facet|0011)/.test(name), false, `legacy object remains: ${name}`);
    assert.equal(/atlas_(?:theorems|facet|0011)/.test(sql ?? ""), false, `legacy SQL reference in ${name}`);
  }
}

function assertSnapshotMirroring(persistTo) {
  execute(
    persistTo,
    `INSERT INTO theorems (id, facet, theorem_name, module, revision, status)
     VALUES (53, 'causal', 'Local.snapshot', 'Local.Core', 'snapshot-r1', 'verified');
     UPDATE theorems SET used_in_hypotheses = 7 WHERE id = 53;`,
  );
  assert.deepEqual(
    query(persistTo, "SELECT * FROM theorems_0011_canonical_snapshot WHERE id = 53"),
    query(persistTo, "SELECT * FROM theorems WHERE id = 53"),
  );
  execute(persistTo, "DELETE FROM theorems WHERE id = 53");
  assert.deepEqual(
    query(persistTo, "SELECT id FROM theorems_0011_canonical_snapshot WHERE id = 53"),
    [],
  );
  execute(
    persistTo,
    `INSERT INTO facet_state (facet, theorem_inventory) VALUES ('causal', '{"total":0}');
     UPDATE facet_state SET theorem_inventory = '{"total":1}' WHERE facet = 'causal';`,
  );
  assert.deepEqual(
    query(persistTo, "SELECT * FROM facet_state_0011_canonical_snapshot WHERE facet = 'causal'"),
    query(persistTo, "SELECT * FROM facet_state WHERE facet = 'causal'"),
  );
  execute(persistTo, "DELETE FROM facet_state WHERE facet = 'causal'");
  assert.deepEqual(
    query(persistTo, "SELECT facet FROM facet_state_0011_canonical_snapshot WHERE facet = 'causal'"),
    [],
  );
  assertForeignKeys(persistTo);
}

function testActualLocalInitPath() {
  const persistTo = path.join(tempRoot, "blank");
  runJust("think-d1-init", persistTo);
  assertMigrationHistory(persistTo);
  assertForeignKeys(persistTo);

  assertCanonicalStoreObjects(persistTo);
  const registry = query(
    persistTo,
    "SELECT facet, agent_class FROM facet_registry ORDER BY facet",
  );
  assert.deepEqual(registry, [
    { facet: "causal", agent_class: "Causal" },
    { facet: "experiment", agent_class: "Experiment" },
    { facet: "manifold", agent_class: "Manifold" },
    { facet: "theorist", agent_class: "Theorist" },
  ]);

  const statusColumn = query(persistTo, "PRAGMA table_info(theorems)").find(
    (column) => column.name === "status",
  );
  assert.equal(statusColumn?.notnull, 1);

  execute(
    persistTo,
    `INSERT INTO records (record_id, element, property)
     VALUES ('migration-rerun-sentinel', 'Ni', 'C44')`,
  );
  runJust("think-d1-init", persistTo);
  assertMigrationHistory(persistTo);
  assert.deepEqual(
    query(
      persistTo,
      `SELECT record_id, element, property FROM records
        WHERE record_id = 'migration-rerun-sentinel'`,
    ),
    [{ record_id: "migration-rerun-sentinel", element: "Ni", property: "C44" }],
  );
}

function testProductionShapedMigrationPath() {
  const persistTo = path.join(tempRoot, "production-shaped");
  executeFile(persistTo, path.join(projectDir, "schema.bootstrap.sql"), throughNineConfigPath);
  applyMigrations(persistTo, throughNineConfigPath);
  assertMigrationHistory(persistTo, allMigrationNames.slice(0, 9));

  // Production created the 0010 tables out of band before Wrangler recorded 0010.
  executeFile(persistTo, path.join(sourceMigrations, "0010_atlas_theorems.sql"));
  execute(
    persistTo,
    `INSERT INTO atlas_theorems
       (id, facet, theorem_name, module, revision, status, used_in_hypotheses, created_at)
     VALUES
       (41, 'Experiment', 'OpenDistillationFactory.trace_is_sound',
        'OpenDistillationFactory.Computation.Trace', 'atlas-r1', 'failed', 3,
        '2026-07-14 12:00:00'),
       (42, 'Manifold', 'Atlas.Manifold.prCongr', 'Atlas.Manifold.Core',
        'atlas-r1', NULL, 0, '2026-07-14 12:01:00');
     INSERT INTO atlas_facet_state
       (facet, atlas_revision, mathlib_revision, theorem_inventory, updated_at)
     VALUES
       ('Experiment', 'atlas-r1', 'mathlib-r1',
        '{"facet":"Experiment","total":1,"by_status":{"failed":1},"theorems":[]}',
        '2026-07-14 12:05:00');`,
  );

  // Upgrade the permissive rows to the exact pre-0024 production schema first.
  applyMigrations(persistTo, beforeNamingConfigPath);
  assertMigrationHistory(persistTo, beforeNamingMigrationNames);
  assertForeignKeys(persistTo);
  execute(
    persistTo,
    `INSERT INTO atlas_theorems
       (id, facet, theorem_name, module, revision, status)
     VALUES
       (51, 'theorist', 'Local.old', 'Local.Core', 'proof-r1', 'verified'),
       (52, 'theorist', 'Local.new', 'Local.Core', 'proof-r2', 'verified');
     UPDATE atlas_theorems
        SET lifecycle_status = 'superseded', superseded_by_id = 52
      WHERE id = 51;`,
  );
  const preserved = [
    ["atlas_facet_registry", "facet_registry", "facet"],
    ["atlas_theorems", "theorems", "id"],
    ["atlas_facet_state", "facet_state", "facet"],
    ["atlas_theorems_0011_canonical_snapshot", "theorems_0011_canonical_snapshot", "id"],
    ["atlas_facet_state_0011_canonical_snapshot", "facet_state_0011_canonical_snapshot", "facet"],
    ["atlas_0011_reconciliation_applied", "theorems_0011_reconciliation_applied", "id"],
  ].map(([legacy, canonical, order]) => ({
    legacy,
    canonical,
    order,
    rows: query(persistTo, `SELECT * FROM ${legacy} ORDER BY ${order}`),
  }));

  applyMigrations(persistTo);
  assertMigrationHistory(persistTo);
  assertForeignKeys(persistTo);
  assertCanonicalStoreObjects(persistTo);
  for (const { canonical, order, rows } of preserved) {
    assert.deepEqual(
      query(persistTo, `SELECT * FROM ${canonical} ORDER BY ${order}`),
      rows,
      `0024 must preserve all rows and columns in ${canonical}`,
    );
  }
  assert.deepEqual(
    query(persistTo, "SELECT id, superseded_by_id FROM theorems WHERE id = 51"),
    [{ id: 51, superseded_by_id: 52 }],
  );
  execute(persistTo, "DELETE FROM theorems WHERE id = 52", { expectFailure: true });
  assertSnapshotMirroring(persistTo);

  assert.deepEqual(
    query(
      persistTo,
      `SELECT id, facet, theorem_name, module, revision, proof_repository,
              proof_revision, atlas_revision, mathlib_revision, statement_hash,
              source_hash, build_manifest_hash, status, lifecycle_status,
              used_in_hypotheses, created_at
         FROM theorems
        WHERE id = 41`,
    ),
    [
      {
        id: 41,
        facet: "experiment",
        theorem_name: "OpenDistillationFactory.trace_is_sound",
        module: "OpenDistillationFactory.Computation.Trace",
        revision: "atlas-r1",
        proof_repository: "lupine-science/open-distillation-factory",
        proof_revision: null,
        atlas_revision: "atlas-r1",
        mathlib_revision: null,
        statement_hash: null,
        source_hash: null,
        build_manifest_hash: null,
        status: "failed",
        lifecycle_status: "active",
        used_in_hypotheses: 3,
        created_at: "2026-07-14 12:00:00",
      },
    ],
  );
  assert.deepEqual(
    query(
      persistTo,
      `SELECT id, facet, proof_repository, proof_revision, atlas_revision, status
         FROM theorems
        WHERE id = 42`,
    ),
    [
      {
        id: 42,
        facet: "manifold",
        proof_repository: "facebookresearch/atlas-lean",
        proof_revision: "atlas-r1",
        atlas_revision: "atlas-r1",
        status: "imported",
      },
    ],
  );

  assert.deepEqual(
    query(
      persistTo,
      `SELECT facet, proof_repository, proof_revision, atlas_revision,
              mathlib_revision, state_schema_version, inventory_schema_version,
              json_extract(theorem_inventory, '$.total') AS inventory_total,
              updated_at
         FROM facet_state`,
    ),
    [
      {
        facet: "experiment",
        proof_repository: null,
        proof_revision: null,
        atlas_revision: "atlas-r1",
        mathlib_revision: "mathlib-r1",
        state_schema_version: 1,
        inventory_schema_version: 1,
        inventory_total: 1,
        updated_at: "2026-07-14 12:05:00",
      },
    ],
  );

  const hashes = { statement: "a".repeat(64), source: "b".repeat(64), manifest: "c".repeat(64) };
  execute(
    persistTo,
    `INSERT INTO theorems
       (facet, theorem_name, module, revision, proof_repository, proof_revision,
        atlas_revision, mathlib_revision, statement_hash, source_hash,
        build_manifest_hash, status, lifecycle_status, used_in_hypotheses)
     VALUES
       ('experiment', 'OpenDistillationFactory.trace_is_sound',
        'OpenDistillationFactory.Computation.Trace', 'atlas-r1',
        'lupine-science/open-distillation-factory', 'local-proof-r2',
        'atlas-r1', 'mathlib-r1', '${hashes.statement}', '${hashes.source}',
        '${hashes.manifest}', 'verified', 'active', 4)
     ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE SET
       proof_repository = excluded.proof_repository,
       proof_revision = excluded.proof_revision,
       atlas_revision = excluded.atlas_revision,
       mathlib_revision = excluded.mathlib_revision,
       statement_hash = excluded.statement_hash,
       source_hash = excluded.source_hash,
       build_manifest_hash = excluded.build_manifest_hash,
       status = excluded.status,
       lifecycle_status = excluded.lifecycle_status,
       used_in_hypotheses = excluded.used_in_hypotheses,
       updated_at = CURRENT_TIMESTAMP;`,
  );
  assert.deepEqual(
    query(
      persistTo,
      `SELECT (SELECT COUNT(*) FROM theorems
                WHERE facet = 'experiment'
                  AND theorem_name = 'OpenDistillationFactory.trace_is_sound') AS row_count,
              status, proof_revision, statement_hash,
              source_hash, build_manifest_hash
         FROM theorems
        WHERE id = 41`,
    ),
    [
      {
        row_count: 1,
        status: "verified",
        proof_revision: "local-proof-r2",
        statement_hash: hashes.statement,
        source_hash: hashes.source,
        build_manifest_hash: hashes.manifest,
      },
    ],
  );

  execute(
    persistTo,
    `INSERT INTO theorems
       (facet, theorem_name, module, revision, status)
     VALUES ('unknown', 'Bad.facet', 'Bad', 'r1', 'verified')`,
    { expectFailure: true },
  );
  execute(
    persistTo,
    `INSERT INTO theorems
       (facet, theorem_name, module, revision, status)
     VALUES ('Experiment', 'Bad.case', 'Bad', 'r1', 'verified')`,
    { expectFailure: true },
  );
  execute(
    persistTo,
    `INSERT INTO theorems
       (facet, theorem_name, module, revision, status)
     VALUES ('experiment', 'Bad.status', 'Bad', 'r1', 'pending')`,
    { expectFailure: true },
  );
  execute(
    persistTo,
    `INSERT INTO facet_state (facet, theorem_inventory)
     VALUES ('causal', 'not-json')`,
    { expectFailure: true },
  );
}

function testCanonicalSchemaBootstrap() {
  const persistTo = path.join(tempRoot, "schema-bootstrap");
  const applySchema = () => runJust("think-d1-schema-init", persistTo);
  applySchema();

  const tables = new Set(
    query(persistTo, "SELECT name FROM sqlite_master WHERE type = 'table'").map(
      (row) => row.name,
    ),
  );
  for (const table of [
    "claims",
    "hypotheses",
    "critiques",
    "research_questions",
    "literature_papers",
    "research_hits",
    "lab_beats",
    "mlip_baseline_runs",
    "mlip_baseline_cells",
    "facet_registry",
    "theorems",
    "facet_state",
  ]) {
    assert.equal(tables.has(table), true, `schema.sql is missing ${table}`);
  }

  const claimColumns = new Set(
    query(persistTo, "PRAGMA table_info(claims)").map((column) => column.name),
  );
  assert.equal(claimColumns.has("claim_data"), true);
  assert.equal(claimColumns.has("created_at"), true);
  assert.deepEqual(
    query(
      persistTo,
      "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'd1_migrations'",
    ),
    [],
  );

  execute(
    persistTo,
    `INSERT INTO records (record_id, element, property)
     VALUES ('schema-preservation-sentinel', 'Ni', 'C11')`,
  );
  applySchema();
  assert.deepEqual(
    query(
      persistTo,
      `SELECT record_id, element, property FROM records
        WHERE record_id = 'schema-preservation-sentinel'`,
    ),
    [{ record_id: "schema-preservation-sentinel", element: "Ni", property: "C11" }],
  );
}

try {
  await configureHarness();
  testActualLocalInitPath();
  testProductionShapedMigrationPath();
  testCanonicalSchemaBootstrap();
  console.log("Theorem D1 migration contract passed: blank, production-shaped, preserved snapshots, and schema bootstrap");
} finally {
  if (process.env.KEEP_MIGRATION_TEST_DB !== "1") {
    await rm(tempRoot, { recursive: true, force: true });
  } else {
    console.log(`kept migration test persistence at ${tempRoot}`);
  }
}
