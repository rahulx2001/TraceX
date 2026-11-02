# Server voice: current contract and validation limits

The voice report uses browser Web Speech recognition and `speechSynthesis` by
default. Deepgram Nova recognition and Aura synthesis are optional server
providers. Meta does not transcribe audio in this path. Reply generation uses
the installed deterministic domain script; the current automotive scripts are
English. Meta's separate contribution is the subsequent evidence investigation.

Chrome is the browser exercised by the automated UI checks. Those checks use
synthetic speech transports, and the Python integration tests fake the provider.
They establish software contracts, not real speech accuracy, latency or Safari,
iOS, headset or Bluetooth reliability. See [voice-validation.md](voice-validation.md)
for the consented recording protocol and still-pending device acceptance.

## Setup

```bash
# .env is private. Enabling this path sends audio to Deepgram.
DEEPGRAM_ENABLED=1
DEEPGRAM_API_KEY=<your key>
# Optional defaults:
# DEEPGRAM_STT_MODEL=nova-3
# DEEPGRAM_TTS_MODEL=aura-2-thalia-en
# DEEPGRAM_TIMEOUT_S=20
# DEEPGRAM_MAX_AUDIO_BYTES=2000000
# DEEPGRAM_MAX_TTS_CHARS=5000
```

Restart the API. The socket `ready.voice` describes the actual configured speech
capabilities: `server_stt`, `server_tts`, `accepted_audio_mime`, `stt_locales`,
`tts_model` and `tts_locales`. These are configuration, not evidence of a successful
provider request. The browser chooses server speech only when capability and
capture/playback support agree. A missing key leaves the browser/text path intact.

The start request sends a validated `locale` (`en-US`, `en-IN`, `hi-IN`) and an
idempotency key. That locale remains fixed for the report and follows every
recognition request, including retransmission after a socket reconnect. A
conflicting per-turn language is rejected. `hi-IN` asks Deepgram for Hindi;
this does not establish Hinglish quality. The start response states the installed
reply language. English replies use an English synthesis voice even under Hindi
input; Devanagari replies use browser Hindi synthesis when available. The current
English Aura configuration does not advertise Hindi synthesis.

## Capture and interaction

1. **Check microphone** asks for the microphone on click, samples the local quiet
   floor for 1.8 seconds, displays actual input level, and closes the device. It
   uploads nothing. Keep quiet during this setup check; it does not measure speech
   quality. **Type instead** never requests a microphone or starts spoken playback.
2. Server capture prefers 16 kHz mono PCM WAV from `voiceCapture.js`. It encodes
   browser audio locally with a 30-second cap. The fallback only chooses WebM/Opus
   or Ogg supported by both browser and server. MP4 is not advertised or selected.
   When no accepted format is available, the UI offers typed input before upload.
3. An adaptive noise floor detects normal utterance boundaries, with roughly
   900 ms of trailing silence. **Finish speaking** submits a quiet utterance
   manually. Silence alone is discarded. The visible meter reflects sampled RMS,
   not the decorative speaking animation. Buffer limits also apply during silence.
4. Each `user_audio` frame carries the report language and one turn ID. The server
   transcribes the complete utterance in a worker thread, emits `heard_turn`, then
   uses the existing idempotent text-turn workflow. This is **utterance upload,
   not streaming transcription**.
5. Use **Interrupt playback**, then speak the correction. It leaves the report
   open. Mute and End call have separate labels and stable meanings. Optional
   automatic speech interruption is explicitly experimental and off by default:
   the PCM path includes the last 450 ms before the detector fires. Browser
   recognition cannot recover speech while it was paused, so its UI asks the
   caller to repeat those words. Actual interruption/echo behavior remains pending.
6. Mute clears capture buffers. End/unmount closes recorder nodes and microphone
   tracks. Late audio completions are checked against the originating report and
   capture generation. Navigation during an active report requires the user's
   confirmation; there is no claimed saved-resume URL. Same-page reconnect keeps
   the existing report and turn IDs rather than creating a fresh report.

The local rolling PCM buffer contains at most 450 ms during playback, plus an
active utterance of at most 30 seconds. It is in memory, not persisted. It is only
uploaded as part of a finished server-recognition utterance. Browser speech may
use the browser vendor's servers; disclose that provider when obtaining consent.

## Errors, handoff and scope

Empty recognition gives `stt_empty`; malformed/oversize audio gives `bad_audio`.
Provider errors are recoverable and leave text input available. Server synthesis
failure emits a voice-fallback event; after the bounded audio wait the browser can
read the actual reply. The greeting uses browser synthesis. No transcript is
invented when audio fails, and the widget does not relabel fallback as Meta speech.

Requesting a person queues a handoff. The UI says **Request queued** until a real
takeover event, then **Specialist joined**; timeout means **Unavailable**. The
spoken reply also says queued and does not promise a staffed pickup time. An
authenticated second supervisor can inspect stored turns, claim the report and
release it. The queue stores that actor; other operators cannot take or release
the claim. The authorization test demonstrates API behavior, not staffed service.

Deepgram requests use fixed HTTPS endpoints without redirects; the API key stays
server-side. Keep the existing call consent policy enabled. The older
`eval/real_hindi` consent only allows local audio/manual transcription and cannot
authorize this provider-audio evaluation. Obtain the new voice-specific consent
before collecting recordings for the protocol below.

```bash
.venv/bin/python -m pytest tests/frontline/test_deepgram_voice.py tests/frontline/test_voice_validation.py -q
cd dashboard
node --test scripts/voice-capture.test.mjs
npm run test:server-voice
npm run test:tts-voice
PLAYWRIGHT_CHANNEL=chrome npm run test:signin
```

These commands are offline contract/UI tests. No real-device measurements or
multilingual speech success rate can be inferred from their passing result.
