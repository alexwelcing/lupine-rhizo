/**
 * Grounded child-dispatch helpers, split from `orchestrator.ts` into a leaf
 * module for the same reason as `named-stub.ts`: `orchestrator.ts` statically
 * imports `GlimThinkAgent` (→ `@cloudflare/think` → `cloudflare:workers`),
 * which Vitest's default ESM loader cannot resolve. Anything a plain-node
 * test needs to pin must live behind an import graph free of the Worker
 * runtime modules. This module imports only telemetry + theorem types, so
 * tests can load it directly.
 */

import { traceAgentCycle } from "../telemetry/rpc";
import { trace } from "@opentelemetry/api";
import type { FormalBasis } from "../atlas/theorems";

/**
 * The child-stub surface the orchestrator's dispatch path needs: the Think
 * `chat()` relay plus the §8.4 formal-basis RPC every GlimThinkAgent exposes.
 * `subAgent()` stubs satisfy this structurally.
 */
export interface GroundedChild {
  chat(
    prompt: string,
    relay: { onEvent(json: string): void; onDone(): void; onError?(error: string): void },
  ): Promise<void>;
  buildFormalBasis(opts?: {
    theoremNames?: ReadonlyArray<string>;
    helpers?: Readonly<Record<string, string>>;
  }): Promise<FormalBasis[]>;
}

/**
 * Resolve the formal basis for a child dispatch by RPCing the child's own
 * `buildFormalBasis()` — grounding is computed by the facet that owns the
 * theorems, so the payload can only ever carry that facet's verified /
 * approved-extended rows. Never throws: a failed resolution (unprovisioned
 * facet, ledger error) degrades to an ungrounded dispatch with a warning,
 * matching the telemetry opt-in posture.
 */
export async function resolveChildFormalBasis(child: GroundedChild): Promise<FormalBasis[]> {
  try {
    return await child.buildFormalBasis();
  } catch (e) {
    console.warn("[orchestrator] formal basis resolution failed — dispatching ungrounded:", e);
    return [];
  }
}

/**
 * The actual grounded dispatch path used by every orchestrator tool: resolve
 * the child's formal basis, attach it to the prompt (and the AGENT span),
 * then run the child chat. Exported so the grounding attachment is testable
 * without booting the Think DO runtime.
 */
export async function dispatchGroundedChild(
  child: GroundedChild,
  prompt: string,
  agentLabel = "subagent",
): Promise<string> {
  const formalBasis = await resolveChildFormalBasis(child);
  // When a formal basis is attached, prepend a compact grounding preamble so
  // the receiving facet reasons within the proven theorems, and surface the
  // basis on the span for Phoenix.
  const groundedPrompt =
    formalBasis.length > 0
      ? `${formalGroundingPreamble(formalBasis)}\n\n${prompt}`
      : prompt;
  // Wrap every sub-agent dispatch in an OpenInference AGENT span so the
  // hypothesis-generation cycle (not just its LLM calls) is visible in Phoenix.
  return traceAgentCycle(agentLabel, groundedPrompt, async () => {
    if (formalBasis.length > 0) {
      const span = trace.getActiveSpan();
      span?.setAttribute("lupine.formal_basis.count", formalBasis.length);
      span?.setAttribute(
        "lupine.formal_basis.theorems",
        formalBasis.map((b) => b.theorem).join(","),
      );
    }
    const events: string[] = [];
    await child.chat(groundedPrompt, {
      onEvent: (json: string) => {
        events.push(json);
      },
      onDone: () => {},
      onError: (error: string) => {
        events.push(JSON.stringify({ type: "error", error }));
      },
    });
    return events.slice(-8).join("\n");
  });
}

/**
 * Render a `formal_basis[]` into a compact natural-language grounding preamble
 * for a facet-to-facet dispatch. Pure + immutable.
 */
export function formalGroundingPreamble(basis: ReadonlyArray<FormalBasis>): string {
  const lines = basis.map((b) => {
    const helper = b.helper ? ` — ${b.helper}` : "";
    return `- ${b.theorem} (${b.module} @ ${b.revision}, ${b.status})${helper}`;
  });
  return [
    "Formal basis (ATLAS-Lean theorems underwriting this task; reason within them):",
    ...lines,
  ].join("\n");
}
