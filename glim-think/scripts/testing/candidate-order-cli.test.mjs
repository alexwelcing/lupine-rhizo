// Public literature fixtures through the actual Rust CLI and application reader.
// Exposure differs by case; consult fixture review notes. No physical-validation claim.
import assert from "node:assert/strict";
import { before, test } from "node:test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const MAX_BYTES = 512 * 1024;
const cli = process.env.ATLAS_DISTILL_BIN;
const fixture = JSON.parse(readFileSync(new URL(
  "../../../atlas-distill/tests/fixtures/candidate_order_sources.json", import.meta.url), "utf8"));
let app;

before(async () => {
  assert.ok(cli, "ATLAS_DISTILL_BIN must name the built CLI; acceptance must not silently skip");
  assert.equal(fixture.schema, "lupine.candidate_order.source_acceptance.v1");
  assert.equal(fixture.cases.length, 5);
  const bundle = await build({
    stdin: {
      contents: `
        import React from "react";
        import { renderToStaticMarkup } from "react-dom/server";
        import { validateCandidateOrderReport } from "./workspace/candidateOrderContracts";
        import { readCandidateOrderFile, CandidateOrderReportView } from "./workspace/client/CandidateOrderReport";
        export { validateCandidateOrderReport, readCandidateOrderFile };
        export function render(report) {
          return renderToStaticMarkup(React.createElement(CandidateOrderReportView, { report }));
        }
      `,
      resolveDir: fileURLToPath(new URL("../../src", import.meta.url)),
      sourcefile: "candidate-order-acceptance-entry.ts",
      loader: "ts",
    },
    bundle: true,
    platform: "node",
    format: "cjs",
    write: false,
    logLevel: "silent",
  });
  // Execute only bundled repository/dependency code, never report-supplied code.
  const compiled = { exports: {} };
  new Function("require", "module", "exports", bundle.outputFiles[0].text)(
    createRequire(import.meta.url), compiled, compiled.exports);
  app = compiled.exports;
});

function produce(input) {
  const bytes = Buffer.from(JSON.stringify(input), "utf8");
  assert.ok(bytes.length <= MAX_BYTES);
  const run = spawnSync(cli, ["candidate-order", "--input", "-"], {
    input: bytes, encoding: "utf8", timeout: 10_000, maxBuffer: MAX_BYTES,
  });
  assert.ifError(run.error);
  assert.equal(run.status, 0, run.stderr);
  assert.equal(run.stderr, "");
  assert.ok(Buffer.byteLength(run.stdout, "utf8") <= MAX_BYTES);
  const report = JSON.parse(run.stdout);
  assert.equal(report.input_sha256, createHash("sha256").update(bytes).digest("hex"));
  assert.deepEqual(report.input, input);
  return { raw: run.stdout, report };
}

function inspect(raw) {
  return app.readCandidateOrderFile({ size: Buffer.byteLength(raw, "utf8"), text: async () => raw });
}
const q = x => x.numerator + "/" + x.denominator;
const edges = x => [q(x.lower), q(x.upper)];
const escape = x => String(x).replace(/[&<>"']/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;",
})[c]);

for (const item of fixture.cases) {
  test(item.id + ": CLI -> full validator -> file reader -> static view", async () => {
    const { raw, report } = produce(item.input);
    const validated = app.validateCandidateOrderReport(report);
    const a = validated.assessment;
    assert.equal(a.choice_relation, item.expected.relation);
    for (const [which, winner] of [
      ["reference", item.expected.reference_unique], ["prediction", item.expected.prediction_unique],
    ]) assert.deepEqual(a[which + "_minima"], { possible: [winner], guaranteed: [winner], unique: winner });
    assert.equal(a.pairs.length, item.expected.pairs.length);
    for (const expected of item.expected.pairs) {
      const pair = a.pairs.find(p => p.left === expected.left && p.right === expected.right);
      assert.ok(pair, expected.left + "/" + expected.right);
      assert.deepEqual(edges(pair.reference_gap_ev), expected.reference_gap);
      assert.deepEqual(edges(pair.prediction_gap_ev), expected.prediction_gap);
    }
    for (const [field, value] of [
      ["source_verification", "not_performed"], ["scientific_validation", "not_established"],
      ["global_minimum_claim", "not_established"],
    ]) assert.equal(a[field], value);
    for (const issue of [
      "source_and_physical_scope_unverified", "artifact_identity_unknown",
      "candidate_search_not_exhaustive", "printing_bounds_are_assumptions",
    ]) assert.ok(a.issues.includes(issue), issue);
    if (item.input.context.fit_exposure === null) assert.ok(a.issues.includes("fitting_exposure_unknown"));

    const oldFetch = globalThis.fetch;
    const oldStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
    let sideEffects = 0;
    globalThis.fetch = () => { sideEffects++; throw new Error("unexpected network"); };
    Object.defineProperty(globalThis, "localStorage", { configurable: true,
      value: { setItem() { sideEffects++; throw new Error("unexpected persistence"); } } });
    try {
      const read = await inspect(raw);
      assert.deepEqual(read, validated);
      const html = app.render(read);
      for (const text of [
        "REPORTED INPUT", "A global ground state is not established",
        "Printing bounds are assumptions", "search is not exhaustive",
        "This inspection does not approve a simulation",
        item.input.context.source_id, item.input.context.protocol,
        ...item.input.rows.map(r => r.anchor),
      ]) assert.ok(html.includes(escape(text)), text);
      if (item.input.context.fit_exposure === null)
        assert.ok(html.includes("Fitting exposure is unknown"));
      else assert.ok(html.includes(escape(item.input.context.fit_exposure)));
      assert.equal(sideEffects, 0);
    } finally {
      globalThis.fetch = oldFetch;
      if (oldStorage) Object.defineProperty(globalThis, "localStorage", oldStorage);
      else delete globalThis.localStorage;
    }
  });

  test(item.id + ": forged assessments and stale input fail the complete reader", async () => {
    const { report } = produce(item.input);
    const changes = [
      r => { r.assessment.pairs[0].reference_gap_ev.lower.numerator = "999"; },
      r => { r.assessment.prediction_minima.unique = "invented-winner"; },
      r => { r.assessment.issues = []; },
      r => { r.assessment.scientific_validation = "validated"; },
      r => { r.input.rows[0].prediction = { lower: "99", upper: "99" }; },
    ];
    for (const change of changes) {
      const corrupt = structuredClone(report); change(corrupt);
      await assert.rejects(() => inspect(JSON.stringify(corrupt)), /Inconsistent/);
    }
  });
}

test("unknown comparability and missing protocol remain unknown after both validators", async () => {
  const input = structuredClone(fixture.cases[0].input);
  input.context.comparability = "unknown";
  input.context.protocol = null;
  input.context.reference_convention = null;
  input.context.fit_exposure = null;
  const { raw } = produce(input);
  const got = await inspect(raw);
  for (const issue of ["comparability_unknown", "reference_or_protocol_unknown", "fitting_exposure_unknown"])
    assert.ok(got.assessment.issues.includes(issue));
  const html = app.render(got);
  for (const text of ["Comparability of these candidates is unknown", "evaluation protocol is unknown",
    "Fitting exposure is unknown", "<code>Unknown</code>"]) assert.ok(html.includes(text), text);
});

test("omitting a known mixture changes the finite choice without granting phase stability", async () => {
  const input = structuredClone(fixture.cases.find(c => c.id === "kobayashi-balanced-nn").input);
  input.rows = input.rows.filter(r => r.candidate_id !== "b_mixture");
  input.context.candidate_set_id += "-without-mixture";
  const { raw } = produce(input);
  const got = await inspect(raw);
  assert.equal(got.assessment.reference_minima.unique, "a_compound");
  assert.equal(got.assessment.prediction_minima.unique, "a_compound");
  assert.equal(got.assessment.global_minimum_claim, "not_established");
  assert.ok(got.assessment.issues.includes("candidate_search_not_exhaustive"));
  assert.ok(app.render(got).includes("search is not exhaustive"));
});

test("a synthetic endpoint-touching perturbation is not rendered as a unique choice", async () => {
  const input = structuredClone(fixture.cases[0].input);
  input.context.model_kind = "synthetic";
  input.context.source_id = "synthetic-endpoint-touch";
  input.context.protocol = "Synthetic endpoint-touching perturbation; not a published numerical value.";
  input.rows[1].reference.lower = input.rows[0].reference.upper;
  const { raw } = produce(input);
  const got = await inspect(raw);
  assert.deepEqual(got.assessment.reference_minima,
    { possible: ["a110", "b111"], guaranteed: ["a110"], unique: null });
  assert.equal(got.assessment.choice_relation, "not_unique_or_unresolved");
  assert.ok(app.render(got).includes("do not establish a unique choice"));
});

test("an internally consistent report still does not authenticate its declared input digest", async () => {
  const { report } = produce(fixture.cases[0].input);
  report.input_sha256 = "0".repeat(64);
  const got = await inspect(JSON.stringify(report));
  assert.equal(got.assessment.source_verification, "not_performed");
  assert.ok(app.render(got).includes(
    "original-input byte digest, model identity, search completeness and physical accuracy were not verified"));
});
