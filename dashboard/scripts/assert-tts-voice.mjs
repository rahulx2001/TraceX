import assert from "node:assert/strict";
import { isNoveltyVoice, pickBestVoice, rankVoices } from "../src/ttsVoice.js";

const voices = [
  { name: "Rishi", lang: "en-IN", voiceURI: "Rishi", default: true, localService: true },
  { name: "Samantha", lang: "en-US", voiceURI: "Samantha", localService: true },
  { name: "Kathy", lang: "en-US", voiceURI: "Kathy", localService: true },
  { name: "Daniel", lang: "en-GB", voiceURI: "Daniel", localService: true },
  { name: "Lekha", lang: "hi-IN", voiceURI: "Lekha", localService: true },
  { name: "Bells", lang: "en-US", voiceURI: "Bells", localService: true },
  { name: "Zarvox", lang: "en-US", voiceURI: "Zarvox", localService: true },
  { name: "Ava (Premium)", lang: "en-US", voiceURI: "Ava (Premium)", localService: true },
];

assert.equal(isNoveltyVoice(voices[5]), true, "Bells is a novelty voice");
assert.equal(isNoveltyVoice(voices[1]), false, "Samantha is a normal voice");

const rankedUs = rankVoices(voices, "en-US");
assert.equal(rankedUs.some((v) => v.name === "Lekha"), false, "hi-IN voice is excluded for en-US");
assert.equal(rankedUs.some((v) => v.name === "Bells"), false, "novelty voice is excluded");
assert.equal(rankedUs[0].name, "Ava (Premium)", "premium voice outranks compact system voices");

const rishiIndex = rankedUs.findIndex((v) => v.name === "Rishi");
const danielIndex = rankedUs.findIndex((v) => v.name === "Daniel");
const samanthaIndex = rankedUs.findIndex((v) => v.name === "Samantha");
assert.ok(rishiIndex > samanthaIndex, "en-IN is usable but ranks below exact en-US");
assert.ok(danielIndex > samanthaIndex, "en-GB is usable but ranks below exact en-US");
assert.ok(rishiIndex > -1, "other English variants stay available as fallbacks");

const autoUs = pickBestVoice(voices, "en-US");
assert.equal(autoUs.name, "Ava (Premium)");

const autoWithSamanthaOnly = pickBestVoice(
  voices.filter((v) => v.lang === "en-US" && v.name !== "Ava (Premium)"),
  "en-US"
);
assert.equal(autoWithSamanthaOnly.name, "Samantha", "Samantha is preferred over Kathy");

const preferred = pickBestVoice(voices, "en-US", "Kathy");
assert.equal(preferred.name, "Kathy", "operator override wins");

const hindi = pickBestVoice(voices, "hi-IN");
assert.equal(hindi.name, "Lekha", "Hindi selects the Hindi voice");

const fallback = pickBestVoice(voices.filter((v) => v.lang !== "en-US"), "en-US");
assert.equal(fallback.name, "Daniel", "falls back to another English voice");

console.log("tts voice ranking: ok");
