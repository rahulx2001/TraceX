# Voice report repair — 30 October 2026

Scope: the owner's reported missed words and repeated questions. This pass
changes capture/endpointing, safe answer binding and the existing bounded text
understanding adapter. It is not a fresh live test of every feature, a microphone
evaluation, human classification, or proof of user productivity.

- Indexed Web Speech results keep final and unfinished segments together;
  session restart retains the draft and repeated index updates do not duplicate it.
- Pause control offers 2.2 seconds, 1.4 seconds, or manual Finish speaking.
  Microphone activity holds a pending turn; quiet calibrated amplitudes are covered
  by synthetic capture tests. Device quality remains unmeasured.
- Short answers such as Honda and Toyota are kept even when the assistant named
  them as examples. “Oh no” binds the injury answer; contradictions remain pending.
  “11” asks whether the caller means 2011 and requires confirmation. “Hello” never
  fills a make. Original report text, year proposal and confirmation stay distinct.
- Muse Spark sees the previous question and captured facts as context, with
  exact caller words as source evidence. The Baseten adapter always supplies the
  schema in the prompt and validates the response locally. Operation metadata is
  saved and surfaced separately from the global configuration badge.

## Actual development requests

Two live **synthetic text** probes used the existing pinned
`meta-models/muse-spark-open-1026` endpoint and persistent budget/cap. No audio,
new human labels, holdout inspection or budget reset was involved.

| Artifact | Outcome | Measured scope |
|---|---|---|
| [First probe](meta_text_probe.json) | HTTP 200; schema rejected for missing `normalization_confidence`; deterministic fallback | One synthetic Hindi text input; 2,757 ms for the enhancer, excluding microphone and playback |
| [After schema fix](meta_text_probe_after_schema_fix.json) | HTTP 200; schema accepted; original year retained; make/model/category filled through validated normalization; translated description rejected as unsupported by original words | Same synthetic text input; 3,186 ms for the enhancer, excluding microphone and playback |

The exact [first request](meta_text_probe_request.json) and [second request](meta_text_probe_after_schema_fix_request.json)
were reconstructed and verified against the recorded outbound SHA256 values.
They contain fictional text and schemas, with no credentials. The probes record
the base commit and dirty source-diff fingerprint; they are development executions,
not a live validation of a later release commit. Request/prompt/schema fingerprints
and per-attempt timestamps are in each operation record. The two calls provide
neither a p50/p95 nor an independently graded accuracy comparison.

Reserved lifetime spend increased from $24.477857 to $24.532293 under the existing
$30 cap: $0.054436 in conservative reservations. The configured token-rate estimate
increased by $0.005776; provider billing was not measured. Both requests, including
the rejected one, stay charged in the ledger. See the artifacts for token counts
and pricing scope. No further model calls are needed to reproduce the tests below.

## Verification

```sh
cd dashboard
node --test scripts/speech-draft.test.mjs scripts/voice-capture.test.mjs
PLAYWRIGHT_CHANNEL=chrome npm run test:signin
cd ..
.venv-hackathon/bin/python -m pytest -q tests/frontline/test_voice_report_repair.py tests/frontline/test_voice_multiturn_regression.py tests/frontline/test_voice_widget_multiturn.py tests/frontline/test_voice_helpers.py tests/frontline/test_live_voice_lifecycle.py tests/frontline/test_live_safety_voice.py tests/frontline/test_live_corrections.py tests/frontline/test_orchestrator.py tests/frontline/ai_layer/test_intake_enhancer.py tests/frontline/ai_layer/test_baseten_backend.py
```

The [committed-source verification](release_verification.json) pins the tested
source commit and code hashes, with actual [Python](release-python.txt),
[Node](release-node.txt), and [browser](release-browser.txt) logs. The
[localhost check](localhost_check.json) confirms the restarted app serves the UI,
uses the configured Baseten text provider, and refuses unauthenticated API access.
It does not invoke a model or record audio.

Nine Node contract checks passed. The 95-test focused Python run passed; the later
88-test run added coverage of the updated Baseten adapter and its existing client
contracts. These counts overlap and must not be added together. The browser run
passed current credential entry, authorization/refusal, stored-source handoff,
correction, review/export, manual speech capture, mixed final/interim retention,
short answers and recognition restart. Speech events are explicitly synthetic.
Sampled text contrast had a minimum of 6.07:1 in that browser check; 200% equivalent
viewport reflow had no horizontal overflow. No claim covers untested browsers.

Real headphone, speaker and Bluetooth captures, languages, negation/corrections,
interruption success and audible latency remain pending under
[the real-audio collection protocol](../../../docs/voice-validation.md).
The documented Baseten audio model slug differs from the pinned hackathon slug;
direct Muse Spark audio remains disabled. Browser Web Speech is still the configured
recognizer here; no Deepgram key was configured for these checks.
