/** Browser-independent contracts for capture, language and honest feedback. */
export const SPEECH_LOCALES = ["en-US", "en-IN", "hi-IN"];
export function speechLocale(value) { return SPEECH_LOCALES.includes(value) ? value : "en-US"; }
export function responseSpeechLocale(text, inputLocale) {
  return /[\u0900-\u097f]/u.test(String(text || "")) ? "hi-IN" : inputLocale === "en-IN" || inputLocale === "hi-IN" ? "en-IN" : "en-US";
}

// Deliberately excludes MP4: the current server/provider contract has not
// verified it. PCM/WAV capture is the preferred cross-browser path.
export function recordingMime(isSupported) {
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"].find((mime) => {
    try { return Boolean(isSupported(mime)); } catch { return false; }
  }) || null;
}

/** Adaptive floor changes only during quiet samples; loud speech cannot train it upward. */
export function voiceActivity(rms, noiseFloor = 0.008) {
  const level = Number.isFinite(rms) ? Math.max(0, rms) : 0;
  const floor = Math.min(0.04, Math.max(0.003, noiseFloor));
  const threshold = Math.min(0.12, Math.max(0.018, floor * 3));
  const voiced = level >= threshold;
  return { voiced, threshold, noiseFloor: voiced ? floor : floor * 0.96 + Math.min(level, threshold) * 0.04 };
}

/** Encode bounded mono Float32 microphone samples to server-supported 16k PCM WAV. */
export function pcmWav(chunks, sampleRate) {
  if (!Number.isFinite(sampleRate) || sampleRate < 16000 || sampleRate > 192000) throw new Error("Unsupported microphone sample rate");
  const length = chunks.reduce((n, c) => n + c.length, 0);
  if (!length || length > sampleRate * 31) throw new Error("Audio must be between one sample and 31 seconds");
  const input = new Float32Array(length);
  let at = 0;
  for (const chunk of chunks) { input.set(chunk, at); at += chunk.length; }
  const count = Math.floor(length * 16000 / sampleRate);
  const buffer = new ArrayBuffer(44 + count * 2);
  const view = new DataView(buffer);
  const write = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  write(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); write(8, "WAVEfmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  write(36, "data"); view.setUint32(40, count * 2, true);
  for (let i = 0; i < count; i++) {
    const start = Math.floor(i * sampleRate / 16000), end = Math.min(length, Math.floor((i + 1) * sampleRate / 16000));
    let sum = 0; for (let j = start; j < end; j++) sum += input[j];
    const value = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    view.setInt16(44 + i * 2, value < 0 ? value * 32768 : value * 32767, true);
  }
  return buffer;
}

export async function sendIntakeSurvey(fetcher, url, headers, csat) {
  const response = await fetcher(url, { method: "POST", headers,
    // Intake feedback is not a claim that the physical fault was resolved.
    body: JSON.stringify({ csat: csat || null, resolved: null }) });
  if (!response.ok) throw new Error(`Feedback was not saved (${response.status}). Please retry.`);
  return true;
}
