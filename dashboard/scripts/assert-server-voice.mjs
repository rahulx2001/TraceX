import assert from "node:assert/strict";
import {
  SERVER_AUDIO_MAX_BYTES,
  SERVER_AUDIO_WAIT_MS,
  SERVER_CAPTURE_MAX_MS,
  SERVER_CAPTURE_SILENCE_MS,
  serverVoiceSelection,
  userAudioFrame,
} from "../src/voiceHelpers.js";

assert.equal(SERVER_AUDIO_WAIT_MS, 6000, "audio wait stays inside the TTS budget conversation");
assert.equal(SERVER_AUDIO_MAX_BYTES, 2000000, "matches DEEPGRAM_MAX_AUDIO_BYTES default");
assert.equal(SERVER_CAPTURE_SILENCE_MS, 900);
assert.equal(SERVER_CAPTURE_MAX_MS, 30000);

// Server wins when both ends agree.
assert.deepEqual(
  serverVoiceSelection({
    serverStt: true, serverTts: true,
    mediaRecorder: true, audioElement: true,
    hasSpeechRecognition: true, hasSpeechSynthesis: true,
  }),
  { stt: "server", tts: "server" }
);

// Firefox-class browser: no Web Speech, but MediaRecorder + Audio exist.
assert.deepEqual(
  serverVoiceSelection({
    serverStt: true, serverTts: true,
    mediaRecorder: true, audioElement: true,
    hasSpeechRecognition: false, hasSpeechSynthesis: false,
  }),
  { stt: "server", tts: "server" }
);

// Server off: the shipped browser path is kept.
assert.deepEqual(
  serverVoiceSelection({
    serverStt: false, serverTts: false,
    mediaRecorder: true, audioElement: true,
    hasSpeechRecognition: true, hasSpeechSynthesis: true,
  }),
  { stt: "browser", tts: "browser" }
);

// Server on but browser cannot capture: STT degrades, TTS still upgrades.
assert.deepEqual(
  serverVoiceSelection({
    serverStt: true, serverTts: true,
    mediaRecorder: false, audioElement: true,
    hasSpeechRecognition: true, hasSpeechSynthesis: true,
  }),
  { stt: "browser", tts: "server" }
);

// Nothing available: text in, silence out.
assert.deepEqual(serverVoiceSelection({}), { stt: "text", tts: "none" });
assert.deepEqual(serverVoiceSelection(), { stt: "text", tts: "none" });

// user_audio frame shape matches the server parser.
const frame = userAudioFrame({
  audio: "aGVsbG8=",
  mime: "audio/webm;codecs=opus",
  turnId: "t1",
  turnSeq: 3,
  locale: "en-US",
  region: "CA",
  driving: true,
});
assert.equal(frame.type, "user_audio");
assert.equal(frame.audio, "aGVsbG8=");
assert.equal(frame.mime, "audio/webm;codecs=opus");
assert.equal(frame.turn_id, "t1");
assert.equal(frame.turn_seq, 3);
assert.equal(frame.locale, "en-US");
assert.equal(frame.region, "CA");
assert.equal(frame.drive_hint, true);

const minimal = userAudioFrame({ audio: "eA==", turnId: "t2" });
assert.equal(minimal.mime, "audio/webm");
assert.equal(minimal.turn_seq, 0);
assert.ok(!("locale" in minimal), "empty optionals are omitted");
assert.ok(!("region" in minimal), "empty optionals are omitted");
assert.ok(!("drive_hint" in minimal), "false drive_hint is omitted");

console.log("server voice selection: ok");
