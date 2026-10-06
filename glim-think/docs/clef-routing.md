# Optional Clef request routing

Clef Flash can classify a chat request into `fast`, `deep`, `code`, or `research`.
The application maps that task to an explicitly configured generation profile.
This is advisory model selection. It never authorizes tools, research jobs,
deployment, or spending, and it does not turn Clef into a conversational model.

Routing is **disabled by default**. A manual model selection wins and does not
call Clef. `resolveClefRoute` returns bounded decision metadata; the caller then
uses `selectModelProfile` for the actual model and its existing provider/budget
checks. Configured profiles do not establish account entitlement or model quality.

## Evaluate before enabling selection

These optional Worker variables control routing; adding this documentation does
not change deployment configuration:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLEF_ROUTER_MODE` | `disabled` | `shadow` classifies but retains the default profile; `auto` may recommend a mapped profile. |
| `CLEF_ROUTER_TASK_PROFILES` | unset | JSON map from task to configured profile ID; no implicit provider ranking. |
| `CLEF_ROUTER_MIN_CONFIDENCE` | `0.7` | Minimum API confidence, finite and between 0 and 1. |
| `CLEF_ROUTER_MIN_MARGIN` | `0.15` | Minimum difference between the top two probabilities, finite and between 0 and 1; ties always fall back. |
| `CLEF_ROUTER_TIMEOUT_MS` | `1200` | One attempt, between 100 and 3000 ms. |

For example, an operator could evaluate this mapping in `shadow` mode:

```json
{"fast":"workers-flash","deep":"workers-deep","code":"workers-deep","research":"workers-deep"}
```

This example expresses operator preference, not measured task performance.
`fast` tasks must map to a configured `fast` role; the other tasks must map to a
configured `deep` role. Any configured generation provider can be selected for
those deep tasks. Unknown profiles, unavailable credentials, decision models
(including Clef hidden behind a model override), and invalid mappings are rejected.
Partial mappings are allowed; an unmapped winning task retains the default.

Review task agreement and usefulness with representative, authorized prompts in
shadow mode before changing the environment to `auto`. A shadow decision includes
the task, probabilities, confidence, margin, and suggested profile while keeping
`profileId` at the caller's default. No model calls or quality evaluation were
performed as part of implementing this module; the tests use synthetic fixtures.

### Small shadow review

The [offline review fixture](../evals/__datasets__/clef-routing.json) contains 12
handwritten Lupine prompts, three per task, with provisional expected labels and
reasons. It includes an adversarial routing instruction. These are review inputs,
not observed Clef outputs, scientific findings, or a statistically representative
benchmark. Its integrity test checks only shape and bounds.

Before enabling `auto` in a deployment:

1. Choose task mappings appropriate for the operator's configured generation
   profiles. Set `CLEF_ROUTER_MODE=shadow` on the intended test deployment and
   keep the workspace's profile selection at **Auto**. This does make a paid
   classifier call for each submitted prompt, followed by the ordinary chat turn.
2. Submit each authorized fixture prompt once. Compare the returned routing
   `task` with `expectedTask`, and inspect `confidence`, `margin`, `reason`, and
   `suggestedProfileId`. Confirm the selected `profileId` remains the default.
   If a caller exposes only summary state, retain the bounded decision returned
   by `resolveClefRoute` in the test harness; do not add raw prompt logging.
3. Record only case ID, expected/observed task, confidence, margin, fallback
   reason, and selected/suggested profile. Count disagreements, fallbacks, and
   timeouts separately. Review the actual generation separately: a matching task
   label does not establish a model's response quality or tool compatibility.
4. Resolve label ambiguity with the operator before altering criteria or limits.
   Verify that manual selections bypass Clef and that injected launch instructions
   grant no extra tools. Keep `shadow` or `disabled` for unresolved behavior;
   enable `auto` only after accepting the measured tradeoffs.

No shadow deployment or live evaluation has been performed by adding this fixture.
Run its offline checks with:

```sh
cd glim-think
npx vitest run src/agents/__tests__/clefRouter.test.ts
```

## Bounds and failure behavior

- Only the supplied last user text is classified, at most 2,000 characters.
  No conversation history, tool payload, or environment credentials are appended.
  Do not supply text that the caller is not authorized to send to Workers AI.
- The router issues one Workers AI call. A deadline triggers an abort and fallback;
  a promise race bounds the wait even if the binding ignores cancellation. This
  cannot guarantee that already-started remote compute has stopped. Unexpected
  response streams are cancelled, including bodies arriving after the deadline;
  fallback does not wait for cancellation to complete.
- Low confidence, a small margin, malformed probabilities, missing task mappings,
  or provider failures retain the default. Invalid configuration never enables
  the classifier. No retry or model generation occurs inside the router.
- Manual and default profiles are checked against the configured catalog.
  An invalid manual selection raises an error; it is never silently overridden.
- The returned metadata contains fixed reason codes and profile IDs, never raw
  request text, raw model output, or provider errors. The module does not log them.
  Cloudflare's own account retention settings remain separate.
- The leaf defaults to profile `fast`; callers may explicitly supply another
  configured generation profile through `defaultProfileId` (the workspace uses
  `workers-flash`). Classifier output cannot change that default or the allowlist.
- Catalog roles and configured credentials are admission checks, not live tests
  of model availability, tool support, response quality, or affordability. A
  selected provider may still fail or be rejected by its downstream budget guard.

## API provenance

The input follows Cloudflare's [Clef Flash usage](https://developers.cloudflare.com/workers-ai/models/clef-flash/):
`AI.run("@cf/cloudflare/clef-flash", {model:"clef-flash", state, questions})`.
The [`choice` response schema](https://developers.cloudflare.com/workers-ai/models/clef-flash/schema-output.json)
is `answers.route = {type:"choice", choice, probabilities, confidence}`.
Confidence is distinct from the winning probability. The router verifies four
finite probabilities in `[0,1]`, their sum (rounding tolerance `0.001`), a winning
choice consistent with those probabilities, and finite confidence in `[0,1]`.
These schema checks validate a response, not the truth of its classification.
