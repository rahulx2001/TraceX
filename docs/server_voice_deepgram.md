# Server voice (Deepgram STT + TTS)

The browser Call Widget (`dashboard/routes/CallWidget.jsx`) ships with
browser-native speech: Web Speech API for STT and `speechSynthesis` for TTS.
That path is Chrome-only and varies by OS voice. Server voice keeps the
orchestrator as the brain and uses Deepgram as the ears (Nova STT) and voice
(Aura TTS), so any browser with a microphone and `<audio>` can hold the call.

## Setup

```bash
# .env (gitignored — never commit the key)
DEEPGRAM_ENABLED=1
DEEPGRAM_API_KEY=<key from console.deepgram.com>
# Optional overrides (defaults shown):
# DEEPGRAM_STT_MODEL=nova-3
# DEEPGRAM_TTS_MODEL=aura-2-thalia-en
# DEEPGRAM_TIMEOUT_S=20
# DEEPGRAM_MAX_AUDIO_BYTES=2000000
# DEEPGRAM_MAX_TTS_CHARS=5000
```

Restart the API server. The widget negotiates automatically: the WS `ready`
frame advertises `voice: {server_stt, server_tts}`, and the widget picks
server capture/playback only when both ends agree (see
`serverVoiceSelection` in `dashboard/src/voiceHelpers.js`). Without the two
env lines, everything behaves exactly as before — browser STT/TTS, and the
test suite stays fully offline.

No new Python dependency: the provider (`src/channels/deepgram.py`) uses
prerecorded REST (`POST /v1/listen`, `POST /v1/speak`) over stdlib urllib.

## How a turn flows

1. Widget records one utterance with `MediaRecorder` (opus/webm preferred),
   segmented by mic RMS (same 0.14 threshold as barge-in): stop after ~900ms
   of trailing silence, 30s cap. Pure silence never sends.
2. `{"type":"user_audio","audio":"<base64>","mime":"audio/webm",...}` →
   server transcribes in a worker thread (WS loop never blocks), replies
   `heard_turn` with the transcript, then feeds the text through the normal
   `user_turn` path — dedup, confidence/readback policy, `turn_result` ack,
   and the supervisor console all unchanged.
3. Each `agent_turn` is followed by `agent_audio` (base64 MP3, linked by
   `utterance_id`) when server TTS is up. Playback reuses the shipped
   `notePlayback` states, so barge-in reconcile and the speak watchdog work
   unchanged.

## Failure behavior (fail closed, never wedged)

- No speech in the audio → `stt_empty`; the widget stays in LISTENING.
- STT/TTS error or timeout → recoverable error frame / skipped `agent_audio`;
  the widget falls back to browser speech for that utterance after 6s.
- Oversize or malformed `user_audio` → `bad_audio` error, orchestrator never
  called, nothing invented.
- The REST greeting always uses browser TTS (it has no server audio).

## Privacy notes

- Enabling server voice sends customer call audio to api.deepgram.com for
  transcription and agent text for synthesis. The existing recording-consent
  script (`src/voice/policy.py`) already covers this disclosure; keep it on.
- The API key is sent only to `https://api.deepgram.com` (fixed host, no
  redirect following, no base-URL override). It never reaches the browser:
  the widget uploads audio to your server, which calls Deepgram server-side.

## Follow-ups (not in this cut)

- Streaming STT (Deepgram WS) for interim transcripts instead of
  per-utterance upload; lower latency, more moving parts.
- Rolling capture during agent speech so barge-in words are kept as the next
  turn (today the caller repeats them).
- Server audio for the REST greeting and for the Twilio pilot channel.
