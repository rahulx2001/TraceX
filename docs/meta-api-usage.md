# Meta API usage in TraceX

TraceX was built for the **Meta Global AI Developer Hackathon** (Indie track,
primarily Build for Your World). The Meta Model API is not a logo on the
pitch deck: it is the live inference backend behind the optional AI layer,
behind guardrails, with a recorded live proof and a deterministic fallback
when no key is configured.

## Which Meta models, through what code

All calls go through one adapter, `src/ai_layer/meta_client.py` (~700 lines):

| Meta model | Endpoint shape | Used for |
|---|---|---|
| Muse Spark 1.3 (text) | `POST {base}/chat/completions`, `response_format: json_schema` | Intake slot filling, normalize, severity + sentiment, vehicle-risk explanation, grounded brief, symptom extraction |
| Muse Spark 1.3 (vision) | Same, with `image_url` content | Photo evidence analysis (`evidence.py`) |
| SAM 3.1 | `POST {base}/responses`, `sam_segment()` parses `<0f>…box…mask…` tokens | Region boxes overlaid on defect photos |
| Muse Image 1.0 | `POST {base}/images/generations` | Offline demo-asset script only, never a live product path |

Backend selection lives in `src/ai_layer/config.py`: `META_BACKEND=auto|meta|baseten`.
`META_API_KEY` (or `MODEL_API_KEY`) selects the Meta endpoint `api.meta.ai`;
`BASETEN_API_KEY` routes the same calls to the pinned Baseten-hosted
`meta-models/muse-spark-open-1026`. With no key, **zero** Meta network calls
are made and every feature returns its deterministic result.

## Where Meta inference drives product behavior

Structured, schema-validated `chat_json` calls (`temperature: 0`,
locally re-validated, fallback on any miss):

- `safety_campaigns.py` — symptom extraction (English/Hindi/Hinglish)
- `grounded_brief.py` — cited investigation brief (must pass Qubot)
- `severity.py` — severity + sentiment, `final = max(rule, AI)` (AI can only raise)
- `intake_enhancer.py` — fill only empty slots, validated
- `vehicle_risk.py` — risk explanation; `normalize.py` — Hindi/Hinglish normalize
- `evidence.py` — evidence vision + `sam_segment()` region boxes
- `complaint_evidence.py`, `campaign_investigator.py` — sourced extraction, evidence lookups, brief
- `meta_narrate()` — narration with deterministic fallback; `image_generate()` — demo assets only

Every structured caller catches `MetaError` and keeps the deterministic
value. The kill-switch, `assess_safety`, Qubot and the spend ledger always run
and have the final say.

## Proof it is really called, and how it is watched

- **Recorded live proof:** `reports/hackathon/meta_live_smoke.json` (2026-10-28,
  `api.meta.ai`, `muse-spark-1.3`, Hindi intake, `live_transport: true`).
  A configured key alone never counts as verification.
- **Re-runnable check:** `python -m scripts.ai_meta_smoke` (add `--vision --sam --image`
  for the media paths). Runs synthetic input on a fresh fixture warehouse; missing
  keys or failed ledger verification never produce a success marker.
- **Per-call telemetry:** `call_health.py` records latency/success/fallback per
  call type in the ops DB; served at `GET /api/ai/call-health` and
  `GET /api/ai/status`, shown in the dashboard AiStatus page, `MetaTag` and
  `MlImprovementEvidence` panels. Each operation is tagged live vs fallback.
- **Spend guardrails:** daily call cap (cross-process file lock), $30 lifetime
  ledger (`META_BUDGET_USD`), bounded timeouts/retries, PII redaction before
  anything leaves the process, HTTPS allowlist + SSRF guard.
- **Tests:** `tests/frontline/ai_layer/test_meta_client.py` and
  `test_meta_smoke.py` (all Meta calls mocked in the suite); 33 pass.

## Honest limits

- Live text intake is verified; **vision/SAM/image have not been called
  against the live API** and remain unverified beyond the smoke harness.
- The WhatsApp intake is a **mock** — no WhatsApp Cloud API call is made.
- Model video analysis is disabled; Muse Spark does not transcribe audio here
  (browser Web Speech does recognition/synthesis).
- With no key everything above reads "not run" and the deterministic pipeline
  is the product.

Setup: keep `META_API_KEY` in server-side `.env` (see `.env.example`);
`bash scripts/judge_setup.sh` wires deps, build and demo data.
