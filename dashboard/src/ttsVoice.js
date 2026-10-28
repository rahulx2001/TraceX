/**
 * Browser TTS voice selection.
 *
 * Web Speech exposes every installed system voice, including novelty voices
 * ("Bells", "Zarvox", "Grandma") and low-quality compact variants. Picking the
 * first/default voice can therefore sound robotic. Rank by language match and
 * known natural/premium names instead, and let the operator override it.
 *
 * Pure ranking helpers stay DOM-free so the shipped logic is easy to test.
 */

export const TTS_VOICE_STORAGE = "tracex.tts.voice";

const PREFERRED_NAMES = [
  "samantha",
  "ava",
  "allison",
  "serena",
  "karen",
  "moira",
  "tessa",
  "daniel",
  "rishi",
  "lekha",
  "kathy",
  "zoe",
  "nicky",
  "aaron",
  "nathan",
  "joelle",
  "noelle",
];

const NATURAL_PATTERNS = [
  /natural/i,
  /neural/i,
  /premium/i,
  /enhanced/i,
  /siri/i,
  /google/i,
  /microsoft.*online/i,
];

// macOS/Chrome novelty and character voices. These are never a support agent.
const NOVELTY_PATTERN =
  /(albert|bad news|bahh|bells|boing|bubbles|cellos|fred|good news|grandma|grandpa|jester|junior|organ|ralph|rocko|sandy|shelley|superstar|trinoids|whisper|wobble|zarvox|flo|eddy|reed)/i;

function baseLang(lang) {
  return String(lang || "").toLowerCase().split("-")[0];
}

/** Higher is better. Non-matching languages are excluded. */
export function scoreVoice(voice, lang = "en-US") {
  if (!voice) return -Infinity;
  const target = String(lang || "en-US").toLowerCase();
  const voiceLang = String(voice.lang || "").toLowerCase();
  if (!voiceLang) return -Infinity;

  let score = 0;
  if (voiceLang === target) score += 120;
  else if (baseLang(voiceLang) === baseLang(target)) score += 70;
  else return -Infinity;

  const name = `${voice.name || ""} ${voice.voiceURI || ""}`;
  if (NATURAL_PATTERNS.some((re) => re.test(name))) score += 55;

  const preferredIndex = PREFERRED_NAMES.findIndex((n) => name.toLowerCase().includes(n));
  if (preferredIndex >= 0) score += 70 - preferredIndex * 4;

  if (voice.default) score += 2;
  if (voice.localService) score += 1;
  if (NOVELTY_PATTERN.test(name)) score -= 500;
  if (/compact|eloquence/i.test(name)) score -= 120;
  return score;
}

/** True for macOS/Chrome novelty and character voices. */
export function isNoveltyVoice(voice) {
  if (!voice) return false;
  return NOVELTY_PATTERN.test(`${voice.name || ""} ${voice.voiceURI || ""}`);
}

/** Voices for this language, best first. Novelty voices are excluded. */
export function rankVoices(voices, lang = "en-US") {
  return (Array.isArray(voices) ? voices : [])
    .map((voice, index) => ({ voice, index, score: scoreVoice(voice, lang) }))
    .filter((row) => Number.isFinite(row.score) && !isNoveltyVoice(row.voice))
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map((row) => row.voice);
}

export function pickBestVoice(voices, lang = "en-US", preferredURI = "") {
  const list = Array.isArray(voices) ? voices : [];
  if (preferredURI) {
    const preferred = list.find(
      (v) => v.voiceURI === preferredURI || v.name === preferredURI
    );
    if (preferred) return preferred;
  }
  const ranked = rankVoices(list, lang);
  if (ranked.length) return ranked[0];
  // A Hindi/English-India selection with no matching voice should still speak
  // rather than fall back to the engine's arbitrary default.
  if (baseLang(lang) !== "en") {
    const english = rankVoices(list, "en-US");
    if (english.length) return english[0];
  }
  return null;
}

export function getPreferredVoiceURI() {
  try {
    return window.localStorage.getItem(TTS_VOICE_STORAGE) || "";
  } catch {
    return "";
  }
}

export function setPreferredVoiceURI(uri) {
  try {
    const value = String(uri || "").trim();
    if (value) window.localStorage.setItem(TTS_VOICE_STORAGE, value);
    else window.localStorage.removeItem(TTS_VOICE_STORAGE);
  } catch {
    /* storage may be disabled; the in-memory caller still works */
  }
}

/**
 * Speak a short sample with the same voice/rate the call uses. Called from a
 * user gesture, so browsers allow audio.
 */
export function previewVoice({ text, lang = "en-US", voiceURI } = {}) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  const synth = window.speechSynthesis;
  const sample =
    text ||
    (baseLang(lang) === "hi"
      ? "नमस्ते, मैं TraceX सहायता से बोल रही हूँ। मैं आपकी कार की समस्या में मदद कर सकती हूँ।"
      : "Hi, this is TraceX support. How can I help with your vehicle today?");
  try {
    synth.cancel();
  } catch {
    /* ignore */
  }
  const utterance = new SpeechSynthesisUtterance(sample);
  const voice = pickBestVoice(
    synth.getVoices() || [],
    lang,
    voiceURI === undefined ? getPreferredVoiceURI() : voiceURI
  );
  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang || lang;
  } else {
    utterance.lang = lang;
  }
  utterance.rate = 0.98;
  utterance.pitch = 1;
  utterance.volume = 1;
  try {
    synth.speak(utterance);
    return true;
  } catch {
    return false;
  }
}
