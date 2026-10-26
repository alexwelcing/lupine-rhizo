import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import ts from "typescript";

// Transpile this small route and its real Access middleware entirely in memory.
const urls = new Map();
function loadTs(path) {
  path = resolve(path);
  if (urls.has(path)) return urls.get(path);
  let js = ts.transpileModule(readFileSync(path, "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  js = js.replace(/from\s+["'](\.\.?\/[^"']+)["']/g, (_, relative) =>
    'from "' + loadTs(resolve(dirname(path), relative + ".ts")) + '"');
  const url = "data:text/javascript;base64," + Buffer.from(js).toString("base64");
  urls.set(path, url);
  return url;
}
const { evidenceObjectsResponse: route, EVIDENCE_OBJECT_MAX_BYTES: cap } =
  await import(loadTs("src/workspace/evidenceObjects.ts"));
const hash = async bytes => Buffer.from(await crypto.subtle.digest("SHA-256", bytes)).toString("hex");
const text = new TextEncoder().encode("research bytes\n");
const sha = await hash(text);
const key = "sha256/" + sha;
const url = "https://research.example/workspace/evidence-objects/" + sha;

test("private evidence object boundary", async t => {
  const keys = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"]);
  const jwk = await crypto.subtle.exportKey("jwk", keys.publicKey);
  const segment = value => Buffer.from(JSON.stringify(value)).toString("base64url");
  async function token(email = "operator@example.test") {
    const input = segment({ alg: "RS256", kid: "evidence-test" }) + "." + segment({
      aud: "private-evidence-test", iss: "https://evidence-test.cloudflareaccess.com",
      exp: Math.floor(Date.now() / 1000) + 600, email,
    });
    return input + "." + Buffer.from(await crypto.subtle.sign("RSASSA-PKCS1-v1_5", keys.privateKey,
      new TextEncoder().encode(input))).toString("base64url");
  }
  const jwt = await token();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async input => {
    assert.equal(String(input), "https://evidence-test.cloudflareaccess.com/cdn-cgi/access/certs");
    return Response.json({ keys: [{ ...jwk, kid: "evidence-test" }] });
  };
  t.after(() => { globalThis.fetch = originalFetch; });
  function harness(options = {}) {
    const objects = new Map();
    let reads = 0, writes = 0;
    function object(k) {
      const item = objects.get(k);
      if (!item) return null;
      return { key: k, size: item.bytes.length, customMetadata: item.metadata,
        body: new ReadableStream({ start(c) { c.enqueue(item.bytes.slice()); c.close(); } }) };
    }
    const bucket = {
      async get(k) { reads++; return object(k); },
      async head(k) { reads++; const v = object(k); if (v) delete v.body; return v; },
      async put(k, bytes, opts) {
        writes++;
        if (options.beforePut) await options.beforePut();
        assert.equal(opts.onlyIf.get("If-None-Match"), "*");
        assert.equal(Buffer.from(opts.sha256).toString("hex"), await hash(bytes));
        if (options.race || objects.has(k)) return null;
        objects.set(k, { bytes: bytes.slice(), metadata: opts.customMetadata });
        if (options.unknown) throw new Error("synthetic response loss");
        return object(k);
      },
    };
    const publicBucket = new Proxy({}, { get() { throw new Error("Public bucket must not be accessed"); } });
    const env = { ADMIN_EMAIL: "operator@example.test", CF_ACCESS_TEAM_DOMAIN: "evidence-test",
      CF_ACCESS_AUD: "private-evidence-test", PRIVATE_EVIDENCE_ENABLED: "true",
      PRIVATE_EVIDENCE: bucket, ARTIFACTS: publicBucket };
    return { env, objects, bucket, stats: () => ({ reads, writes }) };
  }
  function req(method = "GET", body, headers = {}, target = url) {
    return new Request(target, { method, headers: { "Cf-Access-Jwt-Assertion": jwt, ...headers },
      ...(body === undefined ? {} : { body, duplex: "half" }) });
  }
  await t.test("no operator JWT means no storage access, including legacy bypass credentials", async () => {
    const h = harness();
    Object.assign(h.env, { DEV_MODE: "true", INTERNAL_TASK_TOKEN: "legacy" });
    for (const method of ["PUT", "GET", "HEAD"]) {
      const r = await route(req(method, method === "PUT" ? text : undefined,
        { "Cf-Access-Jwt-Assertion": "", "X-Internal-Token": "legacy" }), h.env);
      assert.equal(r.status, 403); assert.equal(r.headers.get("Cache-Control"), "private, no-store");
    }
    assert.deepEqual(h.stats(), { reads: 0, writes: 0 });
  });
  await t.test("wrong operator and cross-origin requests are rejected", async () => {
    const h = harness();
    assert.equal((await route(req("GET", undefined, { "Cf-Access-Jwt-Assertion": await token("other@example.test") }), h.env)).status, 403);
    assert.equal((await route(req("PUT", text, { Origin: "https://elsewhere.example" }), h.env)).status, 403);
    assert.deepEqual(h.stats(), { reads: 0, writes: 0 });
  });
  await t.test("missing, disabled, or aliased private binding fails closed", async () => {
    for (const mode of ["missing", "disabled", "aliased"]) {
      const h = harness();
      if (mode === "missing") delete h.env.PRIVATE_EVIDENCE;
      if (mode === "disabled") h.env.PRIVATE_EVIDENCE_ENABLED = "false";
      if (mode === "aliased") h.env.PRIVATE_EVIDENCE = h.env.ARTIFACTS;
      assert.equal((await route(req("GET"), h.env)).status, 503);
      assert.deepEqual(h.stats(), { reads: 0, writes: 0 });
    }
  });
  await t.test("invalid key, unsupported method, encoding, or digest never reaches storage", async () => {
    const h = harness();
    assert.equal(await route(req("GET", undefined, {}, "https://research.example/health"), h.env), null);
    assert.equal((await route(req("GET", undefined, {}, url + "/extra"), h.env)).status, 400);
    assert.equal((await route(req("DELETE"), h.env)).status, 405);
    assert.equal((await route(req("PUT", text, { "Content-Encoding": "gzip" }), h.env)).status, 415);
    assert.equal((await route(req("PUT", "changed"), h.env)).status, 422);
    assert.deepEqual(h.stats(), { reads: 0, writes: 0 });
  });
  await t.test("declared and streamed size caps, and declared-length mismatch, precede storage", async () => {
    const h = harness();
    assert.equal((await route(req("PUT", text, { "Content-Length": String(cap + 1) }), h.env)).status, 413);
    let cancelled = false;
    const stream = new ReadableStream({
      start(c) { c.enqueue(new Uint8Array(cap + 1)); },
      cancel() { cancelled = true; },
    });
    assert.equal((await route(req("PUT", stream), h.env)).status, 413);
    assert.equal(cancelled, true);
    assert.equal((await route(req("PUT", text, { "Content-Length": "1" }), h.env)).status, 400);
    assert.deepEqual(h.stats(), { reads: 0, writes: 0 });
  });
  await t.test("put, exact duplicate, and hashed readback preserve immutable bytes", async () => {
    const h = harness();
    const first = await route(req("PUT", text), h.env);
    assert.equal(first.status, 201);
    assert.deepEqual(await first.json(), { sha256: sha, bytes: text.length, duplicate: false,
      state: "stored", evidenceStatus: "unreviewed" });
    const duplicate = await route(req("PUT", text), h.env);
    assert.equal(duplicate.status, 200);
    assert.equal((await duplicate.json()).duplicate, true);
    assert.equal(h.stats().writes, 1);
    const read = await route(req("GET"), h.env);
    assert.equal(await hash(await read.arrayBuffer()), sha);
    assert.equal(read.headers.get("Cache-Control"), "private, no-store");
    assert.equal(read.headers.get("Access-Control-Allow-Origin"), null);
    assert.match(read.headers.get("Content-Disposition"), /^attachment;/);
    assert.equal(read.headers.get("Content-Type"), "application/octet-stream");
    const head = await route(req("HEAD"), h.env);
    assert.equal(head.status, 200); assert.equal(await head.text(), "");
    assert.equal(head.headers.get("Content-Length"), String(text.length));
  });
  await t.test("one upload per isolate bounds concurrent buffering and releases after completion", async () => {
    let entered, release;
    const started = new Promise(r => { entered = r; });
    const waiting = new Promise(r => { release = r; });
    const h = harness({ beforePut: async () => { entered(); await waiting; } });
    const first = route(req("PUT", text), h.env);
    await started;
    try {
      assert.equal((await route(req("PUT", text), h.env)).status, 429);
      assert.equal(h.stats().writes, 1);
    } finally { release(); }
    assert.equal((await first).status, 201);
    assert.equal((await route(req("PUT", text), h.env)).status, 200);
  });
  await t.test("corrupt existing bytes are never silently repaired or overwritten", async () => {
    const h = harness();
    h.objects.set(key, { bytes: new TextEncoder().encode("corrupted"), metadata: { sha256: sha } });
    assert.equal((await route(req("PUT", text), h.env)).status, 409);
    assert.equal(h.stats().writes, 0);
  });
  await t.test("conditional-write conflict causes no automatic retry", async () => {
    const h = harness({ race: true });
    assert.equal((await route(req("PUT", text), h.env)).status, 409);
    assert.equal(h.stats().writes, 1);
  });
  await t.test("lost storage acknowledgement stays unknown and can be collected read-only", async () => {
    const h = harness({ unknown: true });
    const response = await route(req("PUT", text), h.env);
    assert.equal(response.status, 503);
    assert.match((await response.json()).error, /outcome may be unknown/);
    assert.equal(h.stats().writes, 1);
    const read = await route(req("GET"), h.env);
    assert.equal(await hash(await read.arrayBuffer()), sha);
    assert.equal(h.stats().writes, 1);
  });
  await t.test("missing object and invalid stored metadata remain visible failures", async () => {
    const h = harness();
    assert.equal((await route(req("GET"), h.env)).status, 404);
    h.objects.set(key, { bytes: text, metadata: { sha256: "wrong" } });
    assert.equal((await route(req("HEAD"), h.env)).status, 502);
  });
  await t.test("server dispatches private bytes before generic text parsing", async () => {
    const server = readFileSync("src/server.ts", "utf8");
    assert.ok(server.includes('import { evidenceObjectsResponse } from "./workspace/evidenceObjects";'));
    assert.ok(server.indexOf("await evidenceObjectsResponse(request, env)") <
      server.indexOf('const bodyText ='));
  });
});
