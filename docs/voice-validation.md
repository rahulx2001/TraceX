# Real-audio validation: collection pending

No consented microphone recordings were available for the 30 October readiness
pass. The saved demo narration is synthetic. `reports/latency_benchmark.json` is
`offline_simulated` / `offline_lognormal_model`; it cannot establish live latency.
The [current aggregate](../reports/voice_validation/results.json) therefore has
zero participants and no reported p50 or p95. The software fixes below are not
substitutes for actual speakers, devices or independent grading.

| Review item | Implemented | Acceptance still needed |
|---|---|---|
| 10 | Start/session/recognition language validation and propagation; actual synthesis model shown; English reply-script limitation explicit | Real English, Hindi and Hinglish turns preserving negation, dates, years, vehicle names and corrections |
| 11 | Preferred PCM WAV and mutually accepted WebM/Ogg fallback; unsupported MP4 refused before capture | Real files from each browser/device advertised in the final demo; Safari/iOS currently unverified |
| 12 | Explicit interruption; optional 450 ms PCM pre-roll; turn/capture generation guards | Spoken correction appears once, changes the correct fact, without echo or lost words |
| 13 | Quiet-floor preflight, actual input meter, adaptive segmentation and manual finish | Quiet speech, background noise, headset, laptop-speaker and Bluetooth trials |
| 14 | Misleading saved-resume promise removed; navigation warning; same-report retry IDs and old-audio guards | Real refresh/network/device interruption exercise; no claim of persistent call resume |
| 16 | Queued/joined/unavailable event states; authenticated second-operator takeover test and stored claimant | Two-person live demonstration with context; no staffing/SLA claim |
| 17 | Consent/hash/timing-gated analyzer retaining failures, unknowns and subgroup counts | Consented real recordings and independent grades; this dependency remains open |
| 44 | PCM capture, language/codec/feedback contracts separated into focused modules | Further large-scale transport/state refactoring intentionally deferred; no late rewrite |

## Collect a small, honest sample

1. Identify the installed code revision, browser/OS, microphone and output path,
   actual provider/model, and provider configuration before collection. An unknown
   browser-internal speech model should say `undisclosed`, with the browser version
   as evidence; do not invent an API/model version.
2. Recruit consenting speakers and a reviewer who will listen to the original
   audio. Show the exact voice consent, name the providers actually receiving
   speech/text, provide a contact and deletion date, and retain an anonymous
   participant code. The collector retains the affirmative consent record/hash.
   The analyzer does not collect audio, send invites or make any provider calls.
3. Use a stated matrix: actual language (English/Hindi/Hinglish), headset/laptop
   speakers/Bluetooth, quiet/background noise, normal/quiet speech. Include fresh
   multi-turn reports, a negation such as “no fire”, model-year/date/vehicle-name
   corrections, and “No, I said 2018” during playback. Use fictional identifiers;
   a real voice reading a fictional task is still labelled a scripted test, not
   a real vehicle incident. Keep failed/incomplete attempts in the manifest.
4. Record microphone input plus an observer/loopback trace of the actual first
   audible response on one timeline. Do not substitute HTTP completion,
   `agent_turn` arrival, `audio.play()` invocation or simulated timestamps for
   audibility. A timeout/no audible response has a null timestamp and stays counted.
5. A human listens to the recording to write the reference, then independently
   grades recognized text. Record the expected and observed entity for negation,
   dates, model year, vehicle name, part and correction; classify correct,
   incorrect, omitted or unknown. Keep ambiguity. Record correction/interruption
   success, repetition, endpointing error and agent echo as true/false/null. Null
   means not exercised/ungraded, never a success. Retain the reviewer and expertise.
6. Double-grade a subset before aggregating. Preserve disagreement privately.
   Report participants, sessions, attempted/completed/failed turns and quality with
   latency. A small usability sample is not population proof or an OEM outcome.

## Local files and commands

```bash
.venv/bin/python scripts/voice_validation.py init data/voice_validation
.venv/bin/python scripts/voice_validation.py analyze data/voice_validation/manifest.json --output reports/voice_validation/results.json
```

Initialization creates an **empty** manifest and unaccepted/blank templates for
turn, consent, timing and grade records. It will not overwrite an existing file.
Only add actual collected turns to `manifest.json` after the source records exist.
Each file reference has relative `path` and `sha256`; sources must stay inside the
private collection, including symlinks. `data/voice_validation/` is gitignored.
Use `shasum -a 256 path/to/file` to obtain a source hash. Consent's exact text hash
is printed at initialization. Never transfer old text-only consent into these
provider-audio records.

Each turn must include an opaque unique ID, anonymous participant/session code,
`source_kind: real_microphone`, `synthetic: false`, language, device, browser
version, hardware `audio_path`, noise condition, capture timestamp, code revision,
recording reference, consent reference, provider evidence reference, and timing
evidence reference. Providers have `stt`, `reply`, `tts` entries with actual name,
model and version evidence. Outcome is `completed`, `fallback`, or `failed`;
fallback/failed records need a non-identifying failure category. `human_grade`
is null until an actual human record exists; it is not filled from model output.

The timing record contains `source_kind: observed_playback` or `loopback_audio`,
an observer, `clock_basis: same_recording_timeline` or `single_monotonic_clock`,
and `events.end_of_speech_ms` / `events.first_audible_response_ms`. Loopback timing
also requires a hashed playback recording reference. All offsets are measured
milliseconds on the same timeline. Save actual provider request/output metadata
privately in `provider_evidence`; remove credentials. Do not include keys in any
public artifact.

The analyzer rejects synthetic/unspecified microphone origins, mismatched or
missing hashes, invalid language/provider consent, consent after capture and
simulated/request-based timing. Human and capture attestations still require
independent audit; this tool cannot prove that a person participated. Aggregates
include outcomes, failures, ungraded observations, critical-field counts and
language/hardware subgroups. p50 is suppressed below 5 audible turns; p95 below
40. These minimums are publication guards, not proof of an adequate population
sample. Inspect subgroup sizes and participant diversity before using either.

Do not publish private recordings, consent records, exact transcripts or personal
device names. The committed empty result documents the outstanding dependency;
replace it only after real collection and review. No paid call or recording is
triggered by either command above.
