import assert from "node:assert/strict";
import test from "node:test";
import { createSampleBuffer } from "../src/voiceCapture.js";
import { pcmWav, recordingMime, responseSpeechLocale, speechLocale, voiceActivity } from "../src/voiceExperience.js";

test("only mutually supported browser formats are selected", () => {
  assert.equal(recordingMime(mime => mime === "audio/mp4"), null);
  assert.equal(recordingMime(mime => mime.startsWith("audio/ogg")), "audio/ogg;codecs=opus");
  assert.equal(recordingMime(() => { throw new Error("unsupported"); }), null);
});
test("PCM pre-roll preserves the last 450ms exactly once and cancellation removes it", () => {
  const buffer = createSampleBuffer(16000);
  buffer.push(new Float32Array(16000).fill(.25));
  buffer.start(true);
  buffer.push(new Float32Array(1600).fill(.5));
  const wav = new DataView(buffer.finish());
  assert.equal(wav.getUint32(40, true), (7200 + 1600) * 2);
  assert.equal(wav.getInt16(44, true), 8191);
  assert.equal(wav.getInt16(44 + 7200 * 2, true), 16383);
  assert.equal(buffer.finish(), null, "same utterance cannot finalize twice");
  buffer.clear(); buffer.start(true);
  assert.equal(buffer.finish(), null, "new report cannot reuse previous pre-roll");
});
test("PCM segment length remains bounded and WAV contract is 16k mono PCM", () => {
  const buffer = createSampleBuffer(48000);
  buffer.start();
  for (let i = 0; i < 32; i++) buffer.push(new Float32Array(48000).fill(.1));
  const wav = new DataView(buffer.finish());
  assert.equal(wav.getUint32(24, true), 16000);
  assert.equal(wav.getUint16(22, true), 1);
  assert.equal(wav.getUint32(40, true), 30 * 16000 * 2);
  assert.throws(() => pcmWav([new Float32Array(100)], 8000), /sample rate/);
});
test("quiet speech crosses calibrated threshold; strong speech cannot train the noise floor upward", () => {
  assert.equal(voiceActivity(.025, .004).voiced, true);
  assert.equal(voiceActivity(.002, .004).voiced, false);
  assert.equal(voiceActivity(.5, .004).noiseFloor, .004);
  assert.equal(voiceActivity(Number.NaN).voiced, false);
});
test("speech preference is validated and English replies do not use a Hindi-only voice", () => {
  assert.equal(speechLocale("fr-FR"), "en-US");
  assert.equal(speechLocale("hi-IN"), "hi-IN");
  assert.equal(responseSpeechLocale("The report is stored", "hi-IN"), "en-IN");
  assert.equal(responseSpeechLocale("रिपोर्ट दर्ज है", "en-US"), "hi-IN");
});
