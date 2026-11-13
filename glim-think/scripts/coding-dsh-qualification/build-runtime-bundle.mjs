import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import assert from 'node:assert/strict';

const [prototype, dependencies, bundle, identityOutput] = process.argv.slice(2);
assert([prototype, dependencies, bundle, identityOutput].every(p => typeof p === 'string' && path.isAbsolute(p)), 'Explicit absolute build paths required');
const require = createRequire(path.join(dependencies, 'package.json'));
const { build } = require('esbuild');
const { metafile } = await build({
  stdin: {
    contents: "export {Runtime} from './src/app/runtime.ts'; export {Store} from './src/app/store.ts'; export {SettingsSchema} from './src/policy.ts';",
    resolveDir: prototype,
    sourcefile: 'snapshot-evaluation-entry.ts',
  },
  absWorkingDir: prototype,
  outfile: bundle,
  bundle: true, platform: 'node', format: 'esm', target: 'node22.19', metafile: true,
  nodePaths: [path.join(dependencies, 'node_modules')],
  plugins: [{ name: 'installed-harness-rc-identity', setup(builder) {
    builder.onResolve({ filter: /^@deepseek-ai\// }, args => ({
      path: require.resolve(args.path, { paths: [dependencies] }), external: true,
    }));
  } }],
  banner: { js: "import {createRequire as __evaluationCreateRequire} from 'node:module';const require=__evaluationCreateRequire(import.meta.url);" },
  logLevel: 'warning',
});
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const inputs = Object.keys(metafile.inputs).filter(name => name !== 'snapshot-evaluation-entry.ts');
assert(inputs.length <= 2048, 'Unexpected build input count');
const sources = inputs.map(name => {
  const file = path.resolve(prototype, name);
  return { path: name, sha256: sha(readFileSync(file)) };
});
const result = {
  schema: 'lupine.dsh-runtime-build.v1', node: process.version, esbuild: require('esbuild/package.json').version,
  target: 'node22.19', prototypeRevision: '6337fc823ce20251c8de8085948165c81aaa701e',
  dependencyComposition: 'explicit installed Harness rc.3 resolution; not unchanged alpha peers',
  bundleSha256: sha(readFileSync(bundle)), sources,
};
const serialized = JSON.stringify(result, null, 2) + '\n';
assert(Buffer.byteLength(serialized) <= 256 * 1024, 'Build identity artifact exceeds bound');
writeFileSync(identityOutput, serialized, { flag: 'wx' });
