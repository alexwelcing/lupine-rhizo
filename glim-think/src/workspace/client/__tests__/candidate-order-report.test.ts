import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { assessCandidateOrder } from "../../candidateOrderContracts";
import { CandidateOrderReportView, InspectCandidateOrderReport, readCandidateOrderFile } from "../CandidateOrderReport";
import { ResearchRuns } from "../ResearchRuns";

const fixture = JSON.parse(readFileSync(new URL(
  "../../../../../distill/tests/fixtures/candidate_order.input.json", import.meta.url), "utf8"));
const report = () => ({ schema: "lupine.candidate_order.report.v1", input_sha256: "b".repeat(64),
  input: structuredClone(fixture), assessment: assessCandidateOrder(fixture) });
const render = (r: unknown) => renderToStaticMarkup(React.createElement(CandidateOrderReportView, { report: r }));
afterEach(() => vi.unstubAllGlobals());

describe("local candidate-order inspection", () => {
  it("opens one report without upload, storage or a provider run", async () => {
    const network = vi.fn(); const save = vi.fn();
    vi.stubGlobal("fetch", network); vi.stubGlobal("localStorage", { setItem: save });
    const raw = JSON.stringify(report());
    const got = await readCandidateOrderFile({ size: raw.length, text: async () => raw });
    expect(got.assessment.choice_relation).toBe("different_unique_minima");
    expect(network).not.toHaveBeenCalled(); expect(save).not.toHaveBeenCalled();
  });
  it("shows signed gap direction and rejects a global-ground-state interpretation", () => {
    const html = render(report());
    for (const s of ["SYNTHETIC INPUT", "different candidates throughout", "A global ground state is not established",
      "constant shift", "right candidate minus left", "Opposite strict order", "not exhaustive",
      "original-input byte digest", "not verified", "<td>2</td>", "<td>-2</td>", "<td>-4</td>"])
      expect(html).toContain(s);
  });
  it("shows endpoint ties and preserves unknown provenance", () => {
    const r = report(); r.input.bounds_kind = "assumed_printing_bounds";
    r.input.rows[0].reference = { lower: "1", upper: "2" }; r.input.rows[1].reference = { lower: "2", upper: "3" };
    r.input.context.protocol = null; r.assessment = assessCandidateOrder(r.input);
    const html = render(r);
    expect(html).toContain("do not establish a unique choice");
    expect(html).toContain("Touching endpoints permit a tie");
    expect(html).toContain("Printing bounds are assumptions");
    expect(html).toContain("<code>Unknown</code>");
    expect(html).toContain("[0, 2]");
  });
  it("rejects forged report verdicts instead of rendering their claims", () => {
    const r = report(); r.assessment.issues = [];
    expect(() => render(r)).toThrow("Inconsistent");
  });
  it("bounds actual UTF-8 bytes as well as the declared file size", async () => {
    const read = vi.fn().mockResolvedValue("{}");
    for (const size of [0, -1, 1.5, NaN, Infinity, 524289])
      await expect(readCandidateOrderFile({ size, text: read })).rejects.toThrow();
    expect(read).not.toHaveBeenCalled();
    await expect(readCandidateOrderFile({ size: 2, text: async () => "é".repeat(262145) })).rejects.toThrow("exceeds");
    await expect(readCandidateOrderFile({ size: 2, text: async () => "{}" })).rejects.toThrow();
  });
  it("escapes source labels and displays tiny nonzero gaps as exact fractions", () => {
    const r = report(); r.input.rows[0].label = "<script>unsafe</script>";
    r.input.rows[0].reference = { lower: "0", upper: "0" };
    r.input.rows[1].reference = { lower: "0.00000000000000000001", upper: "0.00000000000000000001" };
    r.assessment = assessCandidateOrder(r.input);
    const html = render(r);
    expect(html).toContain("&lt;script&gt;"); expect(html).not.toContain("<script>");
    expect(html).toContain("1/100000000000000000000");
  });
  it("is reachable without any saved run", () => {
    expect(renderToStaticMarkup(React.createElement(InspectCandidateOrderReport))).toContain("without a saved run");
    expect(renderToStaticMarkup(React.createElement(ResearchRuns))).toContain("Inspect a candidate energy ordering");
  });
});
