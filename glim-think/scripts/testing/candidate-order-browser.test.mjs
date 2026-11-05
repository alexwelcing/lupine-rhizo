// Real Chrome file-input acceptance of the isolated RUNS reader.
// Public/synthetic evidence only. This does not authenticate sources or a deployment.
import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { build } from "esbuild";

const MAX_BYTES = 512 * 1024;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function produce(input) {
  assert.ok(process.env.ATLAS_DISTILL_BIN, "A built CLI is required; never silently skip");
  const bytes = Buffer.from(JSON.stringify(input));
  assert.ok(bytes.length <= MAX_BYTES);
  const result = spawnSync(process.env.ATLAS_DISTILL_BIN, ["candidate-order", "--input", "-"], {
    input: bytes, encoding: "utf8", timeout: 10_000, maxBuffer: MAX_BYTES,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, "");
  assert.ok(Buffer.byteLength(result.stdout) <= MAX_BYTES);
  return result.stdout;
}

async function connect(endpoint) {
  const socket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { socket.close(); reject(new Error("CDP connection timeout")); }, 5_000);
    socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP connection failed")); }, { once: true });
  });
  let next = 0;
  const pending = new Map();
  const listeners = new Map();
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id); clearTimeout(request.timer);
      if (message.error) request.reject(new Error(JSON.stringify(message.error)));
      else request.resolve(message.result);
    } else for (const callback of listeners.get(message.method) ?? []) callback(message.params);
  });
  socket.addEventListener("close", () => {
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error("CDP closed")); }
    pending.clear();
  });
  return {
    call(method, params = {}, sessionId) {
      return new Promise((resolve, reject) => {
        const id = ++next;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + " timed out")); }, 5_000);
        pending.set(id, { resolve, reject, timer });
        socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
      });
    },
    on(method, callback) {
      listeners.set(method, [...(listeners.get(method) ?? []), callback]);
    },
    close() { socket.close(); },
  };
}

test("actual Chrome local-file interaction and evidence boundaries", { timeout: 90_000 }, async t => {
  const fixture = JSON.parse(await readFile(new URL(
    "../../../atlas-distill/tests/fixtures/candidate_order_sources.json", import.meta.url), "utf8"));
  assert.equal(fixture.schema, "lupine.candidate_order.source_acceptance.v1");
  assert.equal(fixture.cases.length, 4);
  const scratch = await mkdtemp(join(tmpdir(), "candidate-order-browser-"));
  let server, chrome, chromeClosed, cdp;
  t.after(async () => {
    let closed = !chrome;
    try {
      if (chrome) {
        // Browser.close shuts down profile writers before the main process exits.
        // A signal exit leaves exitCode null, so it is not a liveness test.
        if (cdp) await cdp.call("Browser.close").catch(error => {
          t.diagnostic("Browser shutdown transport: " + error.message);
        });
        else if (chrome.exitCode === null && chrome.signalCode === null) chrome.kill("SIGTERM");
        closed = await Promise.race([chromeClosed.then(() => true), delay(1_000).then(() => false)]);
        if (!closed) {
          chrome.kill("SIGKILL");
          closed = await Promise.race([chromeClosed.then(() => true), delay(1_000).then(() => false)]);
        }
      }
    } finally {
      cdp?.close();
      if (server) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
    }
    assert.ok(closed, "Chrome did not close; preserve its profile instead of deleting under a writer");
    await rm(scratch, { recursive: true, force: true });
  });

  const cases = [];
  for (const item of fixture.cases) {
    const raw = produce(item.input);
    const path = join(scratch, item.id + ".json");
    await writeFile(path, raw);
    cases.push({ ...item, raw, path });
  }
  const bundle = await build({
    stdin: {
      contents: 'import React from "react"; import { createRoot } from "react-dom/client";' +
        'import { InspectCandidateOrderReport } from "./workspace/client/CandidateOrderReport";' +
        'createRoot(document.getElementById("root")).render(React.createElement(InspectCandidateOrderReport));',
      resolveDir: fileURLToPath(new URL("../../src", import.meta.url)),
      loader: "ts", sourcefile: "candidate-order-browser-entry.ts",
    },
    bundle: true, platform: "browser", format: "iife", write: false, minify: true,
    define: { "process.env.NODE_ENV": '"production"' }, logLevel: "silent",
  });
  assert.ok(bundle.outputFiles[0].contents.length < 2 * 1024 * 1024);
  const served = [];
  server = createServer((req, res) => {
    served.push(req.method + " " + req.url);
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("Content-Security-Policy", "default-src 'none'; script-src 'self'; connect-src 'none'; img-src data:");
    if (req.method === "GET" && req.url === "/") {
      res.setHeader("Content-Type", "text/html");
      res.end('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Reader acceptance</title>' +
        '<link rel="icon" href="data:,"></head><body><div id="root"></div><script src="/app.js"></script></body></html>');
    } else if (req.method === "GET" && req.url === "/app.js") {
      res.setHeader("Content-Type", "application/javascript"); res.end(bundle.outputFiles[0].contents);
    } else { res.statusCode = 404; res.end(); }
  });
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
  const origin = "http://127.0.0.1:" + server.address().port;
  // Use the hosted runner's preinstalled browser; never download or replace it.
  const executable = process.env.CHROME_BIN || "google-chrome";
  chrome = spawn(executable, [
    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--no-first-run",
    "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
    "--disable-sync", "--disable-extensions", "--disable-default-apps", "--metrics-recording-only",
    "--no-proxy-server", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
    "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
    "--user-data-dir=" + join(scratch, "profile"), "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"], env: { PATH: process.env.PATH, LANG: "C.UTF-8" } });
  chromeClosed = new Promise(resolve => chrome.once("close", resolve));
  const endpoint = await new Promise((resolve, reject) => {
    let stderr = "";
    const timer = setTimeout(() => reject(new Error("Chrome startup timeout")), 10_000);
    chrome.once("error", error => { clearTimeout(timer); reject(error); });
    chrome.once("exit", code => { clearTimeout(timer); reject(new Error("Chrome exited during startup: " + code)); });
    chrome.stderr.on("data", bytes => {
      stderr = (stderr + bytes.toString()).slice(-16_384);
      const match = stderr.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:\d+\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
  });
  cdp = await connect(endpoint);
  const version = await cdp.call("Browser.getVersion");
  t.diagnostic("Browser " + version.product + "; protocol " + version.protocolVersion);
  const target = await cdp.call("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.call("Target.attachToTarget", { targetId: target.targetId, flatten: true });
  const call = (method, params) => cdp.call(method, params, sessionId);
  const evaluate = async expression => {
    const reply = await call("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    assert.equal(reply.exceptionDetails, undefined, JSON.stringify(reply.exceptionDetails));
    return reply.result.value;
  };
  const requests = [], exceptions = [];
  cdp.on("Network.requestWillBeSent", event => requests.push(event.request.url));
  cdp.on("Runtime.exceptionThrown", event => exceptions.push(event.exceptionDetails.text));
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Network.enable");
  await call("Page.addScriptToEvaluateOnNewDocument", { source: String.raw`
    window.__readerEffects = [];
    const deny = name => function () { window.__readerEffects.push(name); throw new Error("Unexpected " + name); };
    window.fetch = deny("fetch");
    XMLHttpRequest.prototype.send = deny("XHR");
    navigator.sendBeacon = deny("beacon");
    window.WebSocket = deny("WebSocket");
    window.EventSource = deny("EventSource");
    Storage.prototype.setItem = deny("storage");
    IDBFactory.prototype.open = deny("indexedDB");
    window.__releaseReads = [];
    window.__holdNextRead = false;
    window.__readsStarted = 0; window.__readsFinished = 0;
    const read = File.prototype.text;
    File.prototype.text = async function () {
      ++window.__readsStarted;
      try {
        const contents = read.call(this);
        if (window.__holdNextRead) {
          window.__holdNextRead = false;
          await new Promise(resolve => window.__releaseReads.push(resolve));
        }
        return await contents;
      } finally { ++window.__readsFinished; }
    };
  ` });
  await call("Page.navigate", { url: origin + "/" });
  async function until(expression) {
    const end = Date.now() + 5_000;
    do { if (await evaluate(expression)) return; await delay(25); } while (Date.now() < end);
    assert.fail("Browser condition timed out: " + expression);
  }
  const section = 'document.querySelector(\'[aria-label="Candidate order inspection"]\')';
  const input = 'document.querySelector(\'input[type="file"]\')';
  await until(input + " !== null");
  async function click(selector) {
    const box = await evaluate('(() => { const el = document.querySelector(' + JSON.stringify(selector) +
      '); if (!el) throw new Error("Missing control"); el.scrollIntoView(); const r=el.getBoundingClientRect();' +
      'return {x:r.x+r.width/2,y:r.y+r.height/2}; })()');
    await call("Input.dispatchMouseEvent", { type: "mousePressed", ...box, button: "left", clickCount: 1 });
    await call("Input.dispatchMouseEvent", { type: "mouseReleased", ...box, button: "left", clickCount: 1 });
  }
  await click("summary");
  async function choose(path) {
    const { result } = await call("Runtime.evaluate", { expression: input });
    await call("DOM.setFileInputFiles", { files: [path], objectId: result.objectId });
    await call("Runtime.releaseObject", { objectId: result.objectId });
  }
  async function show(item) {
    await choose(item.path);
    await until(section + '?.querySelector("h3")?.textContent === ' + JSON.stringify(item.input.context.model_id));
    assert.equal(await evaluate(input + ".value"), "", "Same file can be selected again");
  }
  async function clear() {
    await click("button");
    await until(section + " === null && !document.querySelector('[role=alert]') && !document.querySelector('[role=status]')");
  }

  async function check(name, action) {
    let failure;
    await t.test(name, async () => {
      try { await action(); } catch (error) { failure = error; throw error; }
    });
    if (failure) throw failure; // Stop this acceptance sequence at its first failed check.
  }

  for (const item of cases) await check(item.id + ": file selection, decision and visible limits", async () => {
    await show(item);
    const visible = await evaluate(section + ".innerText");
    assert.ok(visible.includes(item.expected.relation === "same_unique_minimum"
      ? "select the same candidate" : "select different candidates"));
    for (const limit of ["A global ground state is not established", "search is not exhaustive",
      "Source authenticity and physical applicability have not been verified",
      "Printing bounds are assumptions", "does not approve a simulation"]) assert.ok(visible.includes(limit), limit);
    await click('section[aria-label="Candidate order inspection"] details:last-of-type summary');
    const expanded = await evaluate(section + ".innerText");
    const c = item.input.context;
    for (const text of [c.source_id, c.reference_convention, c.protocol, c.fit_exposure, ...item.input.rows.map(row => row.anchor)].filter(Boolean))
      assert.ok(expanded.includes(text), text);
    const unique = await evaluate(section + '?.querySelector("table tbody tr:last-child")?.innerText');
    for (const id of [item.expected.reference_unique, item.expected.prediction_unique]) assert.ok(unique.includes("(" + id + ")"));
    await clear();
  });

  await check("clear and same-file reselection", async () => {
    await show(cases[0]); await clear(); await show(cases[0]);
  });
  async function rejected(name, raw, pattern) {
    const path = join(scratch, name);
    await writeFile(path, raw); await choose(path);
    await until("!!document.querySelector('[role=alert]')");
    assert.match(await evaluate("document.querySelector('[role=alert]').innerText"), pattern);
    assert.equal(await evaluate(section + " === null"), true, "Old valid result must disappear");
    await clear();
  }
  await check("corrupt arithmetic replaces a previous valid report with rejection", async () => {
    const corrupt = JSON.parse(cases[0].raw);
    corrupt.assessment.pairs[0].reference_gap_ev.lower.numerator = "999";
    await rejected("corrupt.json", JSON.stringify(corrupt), /not a consistent candidate-order report/);
  });
  await check("malformed JSON, empty and oversized files reject", async () => {
    await rejected("malformed.json", "{", /not a consistent candidate-order report/);
    await rejected("empty.json", "", /nonempty/);
    await rejected("oversized.json", " ".repeat(MAX_BYTES + 1), /512 KiB/);
  });
  await check("unknown evidence remains explicit", async () => {
    const unknown = structuredClone(cases[0].input);
    Object.assign(unknown.context, { model_id: "synthetic-unknown-context", comparability: "unknown",
      reference_convention: null, protocol: null, fit_exposure: null });
    const path = join(scratch, "unknown.json");
    await writeFile(path, produce(unknown));
    await show({ path, input: unknown });
    const visible = await evaluate(section + ".innerText");
    for (const text of ["Comparability of these candidates is unknown", "reference convention or evaluation protocol is unknown",
      "Fitting exposure is unknown"]) assert.ok(visible.includes(text), text);
    await clear();
  });

  async function hold(item) {
    await evaluate("window.__holdNextRead = true");
    await choose(item.path);
    await until("window.__releaseReads.length === 1 && !!document.querySelector('[role=status]')");
  }
  async function release() {
    await evaluate("window.__releaseReads.shift()()");
    await until("window.__readsFinished === window.__readsStarted");
    await evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))");
  }
  await check("clear invalidates an unfinished native file read", async () => {
    await hold(cases[0]); await clear(); await release();
    assert.equal(await evaluate(section + " === null"), true);
    assert.equal(await evaluate("document.querySelector('[role=status]') === null"), true);
  });
  await check("newer file wins when an older native read finishes later", async () => {
    await hold(cases[0]); await show(cases[1]); await release();
    assert.equal(await evaluate(section + '?.querySelector("h3")?.textContent'), cases[1].input.context.model_id);
    await clear();
  });
  await check("reader does not upload, persist or request application data", async () => {
    assert.deepEqual(await evaluate("window.__readerEffects"), []);
    assert.deepEqual(served, ["GET /", "GET /app.js"]);
    assert.deepEqual(requests, [origin + "/", origin + "/app.js"]);
    assert.deepEqual(exceptions, []);
  });
});
