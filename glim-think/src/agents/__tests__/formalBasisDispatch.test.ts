/**
 * Pins the actual orchestrator dispatch path: every specialist dispatch
 * (dispatch_manifold / dispatch_causal / dispatch_theorist /
 * dispatch_experiment / parallel_sweep) routes through
 * `dispatchGroundedChild`, which must RPC the child's own buildFormalBasis()
 * and attach the resulting formal_basis[] to the chat prompt. Before this,
 * runChildChat accepted a formal basis but no call site ever supplied one.
 */
import { describe, expect, it } from "vitest";
import {
  dispatchGroundedChild,
  resolveChildFormalBasis,
  type GroundedChild,
} from "../groundedDispatch";
import type { FormalBasis } from "../../atlas/theorems";

const VERIFIED_BASIS: FormalBasis = {
  theorem: "OpenDistillationFactory.Materials.Theory.HyperRibbon.hyper_ribbon_bound_4d",
  module: "OpenDistillationFactory.Materials.Theory.HyperRibbon",
  revision: "8c0ccf7",
  status: "verified",
  helper: "bounds the ribbon rank for 4d embeddings",
};

function fakeChild(opts: {
  basis?: FormalBasis[];
  basisError?: Error;
  events?: string[];
}) {
  const calls = { buildFormalBasis: 0, chatPrompts: [] as string[] };
  const child: GroundedChild = {
    async buildFormalBasis() {
      calls.buildFormalBasis += 1;
      if (opts.basisError) throw opts.basisError;
      return opts.basis ?? [];
    },
    async chat(prompt, relay) {
      calls.chatPrompts.push(prompt);
      for (const event of opts.events ?? [JSON.stringify({ type: "done" })]) {
        relay.onEvent(event);
      }
      relay.onDone();
    },
  };
  return { child, calls };
}

describe("dispatchGroundedChild", () => {
  it("resolves the child's formal basis and prepends the grounding preamble", async () => {
    const { child, calls } = fakeChild({ basis: [VERIFIED_BASIS] });

    const reply = await dispatchGroundedChild(child, "Analyze the error manifold for Cu.", "manifold");

    expect(calls.buildFormalBasis).toBe(1);
    expect(calls.chatPrompts).toHaveLength(1);
    const prompt = calls.chatPrompts[0];
    expect(prompt).toContain("Formal basis (ATLAS-Lean theorems underwriting this task");
    expect(prompt).toContain(VERIFIED_BASIS.theorem);
    expect(prompt).toContain(VERIFIED_BASIS.module);
    expect(prompt).toContain(VERIFIED_BASIS.revision);
    expect(prompt).toContain("verified");
    expect(prompt).toContain(VERIFIED_BASIS.helper as string);
    expect(prompt).toContain("Analyze the error manifold for Cu.");
    expect(reply).toContain("done");
  });

  it("sends the bare prompt when the facet has no groundable theorems", async () => {
    const { child, calls } = fakeChild({ basis: [] });

    await dispatchGroundedChild(child, "Screen for aggregation bias.", "causal");

    expect(calls.buildFormalBasis).toBe(1);
    expect(calls.chatPrompts[0]).toBe("Screen for aggregation bias.");
  });

  it("degrades to an ungrounded dispatch when basis resolution fails", async () => {
    const { child, calls } = fakeChild({ basisError: new Error("ledger unavailable") });

    const reply = await dispatchGroundedChild(child, "Design experiments.", "experiment");

    expect(calls.chatPrompts[0]).toBe("Design experiments.");
    expect(reply).toContain("done");
  });
});

describe("resolveChildFormalBasis", () => {
  it("returns the child's basis unchanged", async () => {
    const { child } = fakeChild({ basis: [VERIFIED_BASIS] });
    expect(await resolveChildFormalBasis(child)).toEqual([VERIFIED_BASIS]);
  });

  it("returns an empty basis (never throws) on RPC failure", async () => {
    const { child } = fakeChild({ basisError: new Error("DO down") });
    expect(await resolveChildFormalBasis(child)).toEqual([]);
  });
});
