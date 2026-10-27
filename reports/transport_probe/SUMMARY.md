# LOCAL STUB probe — NOT Meta verification

**This is not a live API test.** It runs the repo's real
`src/ai_layer/meta_client` against an in-process loopback HTTP stub that returns
synthetic, hand-written envelopes. No external network call was made. No real
credential was used. No credits were spent.

`HACKATHON.md` §6 must not be changed on the basis of this run. Nothing here
verifies a Meta endpoint, model, rate limit, price, or response shape.

- Run (UTC): 2026-10-26T17:10:36+00:00
- Stub base: `http://127.0.0.1:51834/v1` (ephemeral loopback port)
- Models in the captures are **stub names**, not real models:
  `stub-text-model`, `stub-vision-model`, `stub-sam-model`, `stub-image-model`
- Credential: a dummy non-credential string was set only so the client's
  `meta_enabled()` check would pass. It is not a real key and is not reproduced
  here. Authorization is recorded only as `<REDACTED>`.
- Guard: `meta_client.guard_url` was replaced **in the diagnostic process only**
  to permit plain HTTP on loopback. Product code and tests are unchanged.
- Latency is loopback stub time, not network or API latency. It is not
  comparable to a live call.
- Usage/tokens/cost: **none**. The stub returns no `usage` object, so no token
  or cost number exists for this run.
- Raw redacted exchanges: `text.json`, `vision.json`, `sam.json`, `image.json`,
  `error.json`.

| Probe | Result | HTTP | Latency ms | Stub model | Error | Stub contract checks |
|---|---|---|---|---|---|---|
| text | ok | 200 | 224.6 | `stub-text-model` | — | all expected values |
| vision | ok | 200 | 14.6 | `stub-vision-model` | — | all expected values |
| sam | ok | 200 | 13.2 | `stub-sam-model` | — | all expected values |
| image | ok | 200 | 13.6 | `stub-image-model` | — | all expected values |
| error | raised as expected | 400 | 1.8 | `—` | MetaError: meta_http_400 | all expected values |

## What this proves

- The real client opens a socket, sends `Content-Type: application/json` and a
  Bearer header, and parses an OpenAI-shaped chat envelope.
- `chat_json` sends `response_format.type = json_schema`, a schema name and
  `strict: false`, then validates the returned JSON against the schema.
- The vision request is sent as a `text` part plus an `image_url` part, and is
  parsed through the same envelope path.
- `sam_segment` sends `stream: true` with `input_text` + `input_image`, reads a
  `text/event-stream`, extracts `response.output_text.delta`, and parses the
  box token into:
  `[{"ordinal": 0, "x1": 10, "y1": 20, "x2": 110, "y2": 120, "w": 128, "h": 128, "has_mask": true, "pct": {"left": 7.81, "top": 15.62, "width": 78.12, "height": 78.12}}]`
- `image_generate` sends `model`, `prompt`, `size`, `n` and reads `data[0]`.
- A non-2xx response is raised as `MetaError`, not converted to a success.

## What this does not prove

- That Meta accepts any of these paths, models, headers, or payloads.
- That Meta supports `json_schema` strict mode (the probe only shows our client
  sends `strict: false` and our stub accepts it).
- That the SAM box-token grammar is Meta's real grammar.
- That the vision part, image-generation envelope, rate limits, pricing, or
  error bodies match Meta.
- Anything about latency, tokens, or cost of a real call.

The only way to verify the Meta items is a real Meta Model API key (or a
hackathon-provided sandbox) and a live smoke run.
