# Local workspace integration preview

From `glim-think`, run `npm run preview:workspace`, then open
`http://127.0.0.1:8797/workspace`.

This separate Wrangler entry binds only loopback and uses isolated local KV,
D1, and real Think Durable Object storage in `.wrangler/workspace-preview`.
It has no Workers AI binding, remote resource bindings, production configuration,
credentials, scheduled jobs, or authentication bypass in the production entry.
Its environment is explicitly limited to the three local bindings. Replies are
deterministic, and all evidence rows are clearly labeled synthetic fixtures.
Do not deploy this preview entry or expose its port outside the Mac.

Check these interaction paths:

1. Create and rename a conversation. Refresh and open its copied link in a
   second browser tab; the same title and messages should load.
2. Send `Show the saved hypotheses and evidence`. The real read-only tool should
   show a completed evidence panel with a synthetic record ID.
3. Send `Hello`, stop the slowly streamed reply, and send another message.
4. Reconnect while a reply streams, then reload after it finishes; history should
   remain available.
5. Select another available Workers profile; the actual reply identity should
   still explicitly say `local-preview / deterministic-fixture`.

The preview proves interface/protocol/persistence behavior; it does not verify
provider entitlement, external model quality, Cloudflare Access, or deployment.
Stop with Ctrl-C. Local preview data is git-ignored and separate from production.
