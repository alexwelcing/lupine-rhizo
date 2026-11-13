// Prepares the pinned Runtime and Harness for the separate model composition.
// This phase runs public source/build commands only and never receives a broker capability in its child environment.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const recipe = path.dirname(fileURLToPath(import.meta.url));
const here = path.join(recipe, '../coding-dsh-qualification');
const lock = JSON.parse(readFileSync(path.join(here, 'source-lock.json'), 'utf8'));
const started = Date.now();
const suppliedDeadline = Number(process.env.LUPINE_DSH_DEADLINE_EPOCH_MS);
const deadline = Math.min(started + 850000, Number.isSafeInteger(suppliedDeadline) ? suppliedDeadline : started); // bootstrap time never reopens the original 850-second budget
const scratch = mkdtempSync(path.join(tmpdir(), 'lupine-dsh-qualification-'));
const cleanHome = path.join(scratch, 'home'); mkdirSync(cleanHome);
const userNpm = path.join(scratch, 'user.npmrc'); writeFileSync(userNpm, '');
const globalNpm = path.join(scratch, 'global.npmrc'); writeFileSync(globalNpm, '');
// A new child HOME and explicit empty npm/git config prevent credential inheritance.
// Values from any provider/credential store are never read or copied.
const env = { PATH: process.env.PATH ?? '/usr/local/bin:/usr/bin:/bin', HOME: cleanHome,
  TMPDIR: scratch, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
  NPM_CONFIG_USERCONFIG: userNpm, NPM_CONFIG_GLOBALCONFIG: globalNpm,
  NPM_CONFIG_CACHE: path.join(scratch, 'npm-cache'), NPM_CONFIG_REGISTRY: 'https://registry.npmjs.org/',
  NPM_CONFIG_FETCH_RETRIES: '0', NPM_CONFIG_FETCH_TIMEOUT: '30000', NPM_CONFIG_IGNORE_SCRIPTS: 'true',
  NPM_CONFIG_LEGACY_PEER_DEPS: 'true', NPM_CONFIG_AUDIT: 'false', NPM_CONFIG_FUND: 'false' };
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const commands = [];
function run(name, command, args, cwd, ceilingMs, extra = {}) {
  const remaining = deadline - Date.now(); assert(remaining > 0, 'Qualification deadline exhausted');
  const began = Date.now(); let stdout = Buffer.alloc(0), stderr = Buffer.alloc(0), exitCode = null, signal = null;
  let spawnErrorCode = null, outputCaptureComplete = false;
  try {
    const result = spawnSync(command, args, { cwd, env: { ...env, ...extra }, timeout: Math.min(ceilingMs, remaining),
      maxBuffer: 128 * 1024, killSignal: 'SIGKILL', stdio: ['ignore', 'pipe', 'pipe'] });
    stdout = Buffer.from(result.stdout ?? ''); stderr = Buffer.from(result.stderr ?? '');
    exitCode = Number.isInteger(result.status) ? result.status : null; signal = result.signal ?? null;
    spawnErrorCode = result.error?.code ?? null;
    outputCaptureComplete = !result.error && exitCode !== null;
    if (result.error || exitCode !== 0)
      throw new Error(`${name} did not complete successfully (${exitCode ?? 'unknown exit'}, ${signal ?? spawnErrorCode ?? 'no signal'})`);
    return stdout.toString('utf8');
  } finally {
    commands.push({ name, command, args, durationMs: Date.now() - began, exitCode, signal,
      spawnErrorCode, outputCaptureComplete,
      stdoutBytes: stdout.length, stdoutSha256: sha(stdout), stderrBytes: stderr.length, stderrSha256: sha(stderr),
      stdoutExcerpt: stdout.toString('utf8').slice(0, 8192), stderrExcerpt: stderr.toString('utf8').slice(0, 8192) });
  }
}
const root = path.resolve(process.cwd());
const output = path.join(root, '.lupine-coding-evidence'); mkdirSync(output, { recursive: true });
const names = ['dsh-qualification.json', 'dsh-package-lock.json', 'dsh-installed-identities.json',
  'dsh-build-identity.json', 'dsh-pinned-snapshot.json', 'dsh-source-lock.json', 'model-prepared.json'];
for (const name of names) assert(!existsSync(path.join(output, name)), `Refusing to overwrite ${name}`);
function write(name, value, ceiling = 256 * 1024) {
  const bytes = Buffer.from(JSON.stringify(value, null, 2) + '\n'); assert(bytes.length <= ceiling, `${name} exceeds bound`);
  writeFileSync(path.join(output, name), bytes, { flag: 'wx' });
}
const summary = { schema: 'lupine.dsh-model-preparation.v1', startedAt: new Date(started).toISOString(),
  status: 'preparing', prototypeRevision: lock.prototype.revision, harnessVersion: lock.harness.version,
  sourceLockSha256: sha(readFileSync(path.join(here, 'source-lock.json'))),
  commandCeilingSeconds: 850, runnerCeilingSeconds: 900, node: process.version,
  modelExecution: 'not-performed-preparation-only', realProvider: null, realModel: null, providerTokens: null,
  externalDshInferenceCalls: 0, credentialStoreRead: false, containerCleanupConfirmed: null,
  dependencyMode: 'captured first-hosted lock plus three explicit source-qualified peers; all 644 baseline nonroot entries preserved',
  networkScope: 'Network permitted for public Git/npm acquisition by the outer task. No claim of total HTTP count or kernel-level egress denial.',
  finalReportDeliveryQualified: false, joinedCrashRecoveryQualified: false, commands };
try {
  assert(process.env.LUPINE_DSH_BOOTSTRAP_IDENTITY, 'Explicit pinned Node bootstrap required; no runtime fallback');
  const bootstrap = JSON.parse(readFileSync(process.env.LUPINE_DSH_BOOTSTRAP_IDENTITY, 'utf8'));
  assert.equal(bootstrap.schema, 'lupine.pinned-node-bootstrap.v1');
  assert.equal(bootstrap.status, 'runtime-prepared');
  assert.equal(bootstrap.version, lock.runtime.version);
  assert.equal(bootstrap.archiveUrl, lock.runtime.archiveUrl);
  assert.equal(bootstrap.archiveSha256, lock.runtime.archiveSha256);
  assert.equal(process.version, lock.runtime.version);
  assert.equal(process.execPath, bootstrap.executable);
  assert.equal(bootstrap.absoluteDeadlineEpochMs, bootstrap.startedAtEpochMs + 850000);
  assert.equal(suppliedDeadline, bootstrap.absoluteDeadlineEpochMs);
  assert(bootstrap.preparationElapsedMs >= 0 && bootstrap.preparationElapsedMs < 50000);
  assert(bootstrap.startedAtEpochMs <= started && suppliedDeadline > started);
  summary.runtimeBootstrap = bootstrap;
  summary.runtimeExecutionObserved = { processVersion: process.version, executable: process.execPath, matchesDeclared: true };
  // bootstrap.runtimeExecuted=false is the preserved pre-exec stdout observation;
  summary.remainingBudgetMsAtRecipeStart = deadline - started;
  assert.equal(run('target-root', 'git', ['rev-parse', '--show-toplevel'], root, 5000).trim(), root,
    'Invoke qualification from the pinned repository root');
  const [major, minor] = process.versions.node.split('.').map(Number);
  assert((major === 22 && minor >= 19) || major >= 24, 'Observed Node engine unsupported; no implicit Node download/fallback');
  for (const [name, digest] of Object.entries(lock.portableDerivation).filter(([name]) => name.endsWith('.mjs') || name.endsWith('.patch')))
    assert.equal(sha(readFileSync(path.join(here, name))), digest, `Portable source mismatch: ${name}`);
  for (const [name, digest] of Object.entries(lock.recipeFiles ?? {}))
    assert.equal(sha(readFileSync(path.join(here, name))), digest, `Recipe source mismatch: ${name}`);
  const modelLockBytes = readFileSync(path.join(recipe, 'source-lock.json'));
  const modelLock = JSON.parse(modelLockBytes);
  for (const [name, digest] of Object.entries(modelLock.files)) assert.equal(sha(readFileSync(path.join(recipe, name))), digest, `Model recipe source differs: ${name}`);
  assert.equal(sha(readFileSync(path.join(here, 'source-lock.json'))), modelLock.frozenQualificationLockSha256);
  summary.modelRecipeSha256 = sha(modelLockBytes);
  write('dsh-source-lock.json', { frozenQualification: lock, modelRecipe: modelLock });
  const revision = run('target-revision', 'git', ['rev-parse', 'HEAD'], root, 5000).trim(); assert.match(revision, /^[0-9a-f]{40}$/);
  const readme = run('target-readme', 'git', ['show', `${revision}:README.md`], root, 5000);
  const snapshot = { schema: 'lupine.dsh-pinned-snapshot.v1', repository: 'alexwelcing/lupine-rhizo', revision,
    readme: { sha256: sha(Buffer.from(readme)), bytes: Buffer.byteLength(readme), excerpt: readme.slice(0, 8192) },
    fixture: { measurements: [1, 2, 4], meaning: 'synthetic tool integration data, not physical measurement' } };
  write('dsh-pinned-snapshot.json', snapshot, 32 * 1024); summary.targetRevision = revision;

  const prototype = path.join(scratch, 'prototype'); mkdirSync(prototype);
  run('prototype-init', 'git', ['init', '--quiet'], prototype, 5000);
  run('prototype-fetch', 'git', ['fetch', '--depth=1', lock.prototype.repository, lock.prototype.revision], prototype, 120000);
  assert.equal(run('prototype-pin', 'git', ['rev-parse', 'FETCH_HEAD'], prototype, 5000).trim(), lock.prototype.revision);
  run('prototype-checkout', 'git', ['checkout', '--detach', '--quiet', 'FETCH_HEAD'], prototype, 15000);
  assert.equal(sha(readFileSync(path.join(prototype, 'package.json'))), lock.prototype.originalPackageSha256, 'Pinned prototype package differs');
  run('snapshot-patch-check', 'git', ['apply', '--check', path.join(here, 'snapshot-setup-v2.patch')], prototype, 5000);
  run('snapshot-patch', 'git', ['apply', path.join(here, 'snapshot-setup-v2.patch')], prototype, 5000);
  for (const source of lock.prototype.patchedSources) assert.equal(sha(readFileSync(path.join(prototype, source.path))), source.sha256, source.path);

  const dependencies = path.join(scratch, 'dependencies'); mkdirSync(dependencies);
  writeFileSync(path.join(dependencies, 'package.json'), readFileSync(path.join(here, 'dependencies.json')));
  const packageLockBytes = readFileSync(path.join(here, 'dependency-lock.json'));
  assert.equal(sha(packageLockBytes), lock.dependencyGraph.augmentedLockSha256, 'Reviewed dependency lock differs');
  writeFileSync(path.join(dependencies, 'package-lock.json'), packageLockBytes, { flag: 'wx' });
  assert(packageLockBytes.length <= 2 * 1024 * 1024, 'Dependency lock exceeds artifact bound');
  const packageLock = JSON.parse(packageLockBytes), entries = Object.entries(packageLock.packages ?? {});
  assert.equal(entries.length, lock.dependencyGraph.augmentedPackageEntries, 'Reviewed dependency entry count changed');
  assert(entries.length > 1 && entries.length <= 4000, 'Dependency graph outside bounded recipe');
  const expected = JSON.parse(readFileSync(path.join(here, 'dependencies.json'), 'utf8')).dependencies;
  assert.deepEqual(packageLock.packages[''].dependencies, expected, 'Top-level dependency pins changed');
  for (const [name, item] of entries) {
    if (!name || item.inBundle) continue;
    assert(typeof item.resolved === 'string' && item.resolved.startsWith('https://registry.npmjs.org/'), `Non-registry dependency: ${name}`);
    assert(typeof item.integrity === 'string' && item.integrity.startsWith('sha512-'), `Unpinned dependency integrity: ${name}`);
  }
  writeFileSync(path.join(output, 'dsh-package-lock.json'), packageLockBytes, { flag: 'wx' });
  run('dependency-install', 'npm', ['ci', '--ignore-scripts', '--no-audit', '--no-fund', '--legacy-peer-deps', '--loglevel=error'], dependencies, 300000);
  summary.dependencyLockAfterInstallSha256 = sha(readFileSync(path.join(dependencies, 'package-lock.json')));
  assert.equal(summary.dependencyLockAfterInstallSha256, lock.dependencyGraph.augmentedLockSha256, 'npm ci changed the reviewed lock');
  const topManifest = path.join(dependencies, 'node_modules/@deepseek-ai/dsh/package.json');
  assert.equal(sha(readFileSync(topManifest)), lock.harness.manifestSha256, 'Installed Harness manifest differs from retained version');
  const installed = lock.harness.serviceFiles.map(source => {
    const file = path.join(dependencies, 'node_modules', source.path), actual = sha(readFileSync(file));
    assert.equal(actual, source.sha256, `Installed service differs: ${source.path}`); return { ...source, verifiedSha256: actual };
  });
  write('dsh-installed-identities.json', { schema: 'lupine.dsh-installed-identities.v1', packageLockSha256: sha(packageLockBytes),
    topLevel: expected, dependencyEntries: entries.length, lifecycleScriptsExecuted: false,
    dependencyGraph: lock.dependencyGraph,
    harnessManifestSha256: sha(readFileSync(topManifest)), installed, originalAlphaGraphQualified: false });
  const bundle = path.join(prototype, 'eval-runtime-bundle.mjs');
  run('runtime-build', process.execPath, [path.join(here, 'build-runtime-bundle.mjs'), prototype, dependencies,
    bundle, path.join(output, 'dsh-build-identity.json')], root, 45000);
  write('model-prepared.json', { schema: 'lupine.dsh-model-prepared.v1',
    dependencies, bundle, scratch, targetRoot: root, targetRevision: revision,
    nodeExecutable: process.execPath, nodeVersion: process.version,
    deadlineAtMs: deadline, modelRecipeSha256: summary.modelRecipeSha256,
    providerExecuted: false, preparedAt: new Date().toISOString() });
  summary.status = 'prepared-for-separate-model-command';
} catch (error) {
  summary.status = 'failed-qualification'; summary.error = String(error.message ?? error).slice(0, 2048); process.exitCode = 1;
} finally {
  summary.finishedAt = new Date().toISOString(); summary.elapsedMs = Date.now() - started;
  summary.notProduced = [];
  // A failed setup still exports an explicit absence record for each requested
  // artifact. These are not lockfiles/results and must never be treated as one.
  for (const name of names.filter(name => name !== 'dsh-qualification.json')) {
    if (!existsSync(path.join(output, name))) {
      summary.notProduced.push(name);
      write(name, { schema: 'lupine.qualification-artifact-absent.v1', artifact: name,
        produced: false, reason: summary.error ?? 'Stage did not produce evidence',
        measurement: null, qualification: false });
    }
  }
  summary.artifacts = names.filter(name => name !== 'dsh-qualification.json' && existsSync(path.join(output, name))).map(name => {
    const file = path.join(output, name), bytes = statSync(file).size;
    assert(bytes <= 2 * 1024 * 1024, `${name} exceeds per-file runner limit`);
    return { path: `.lupine-coding-evidence/${name}`, bytes, sha256: sha(readFileSync(file)) };
  });
  assert(summary.artifacts.reduce((n, a) => n + a.bytes, 0) <= 8 * 1024 * 1024 - 256 * 1024, 'Artifact total exceeds runner limit');
  write('dsh-qualification.json', summary);
  console.log(JSON.stringify({ status: summary.status, error: summary.error ?? null, artifacts: summary.artifacts.length,
    externalDshInferenceCalls: 0, providerTokens: null, containerCleanupConfirmed: null }));
  // Owned scratch/raw Session/SQLite data remain private inside the disposable
  // container. Only explicit seven artifact paths are exported. The outer runner
  // must destroy the container and attest cleanup; this script cannot do that.
}
