import { WorkerEntrypoint } from "cloudflare:workers";
import type { Env } from "../types";
import { discoveryPublicationServiceResponse } from "./discoveryPublication";

/** Capability exposed only to the explicitly configured producer binding.
 * No default HTTP route, forwarding, model execution or private-table reads. */
export class ResearchPublication extends WorkerEntrypoint<Env> {
  fetch(request: Request): Promise<Response> {
    return discoveryPublicationServiceResponse(request, { LEDGER: this.env.LEDGER });
  }
}
