/** Web Speech results are revisions by index, not independent utterances.
 * Preserve final AND interim segments until the caller's turn is submitted.
 * A browser session ending must not turn a pause into a second report turn.
 */
export function createSpeechDraft() {
  let saved = [], results = new Map(), at = 0;
  function snapshot() {
    const current = [...results.values()];
    const final = [...saved, ...current.filter(row => row.final).map(row => row.text)].join(" ").trim();
    const interim = current.filter(row => !row.final).map(row => row.text).join(" ").trim();
    return { final, interim, text: [final, interim].filter(Boolean).join(" "), at };
  }
  return {
    observe(rows, now) {
      for (const row of rows) {
        const text = String(row.text || "").replace(/\s+/g, " ").trim();
        if (text) results.set(row.index, { text, final: Boolean(row.final) });
        else results.delete(row.index);
      }
      at = now;
      return snapshot();
    },
    endSession() {
      saved.push(...[...results.values()].map(row => row.text));
      results.clear();
      return snapshot();
    },
    snapshot,
    clear() { saved = []; results.clear(); at = 0; },
  };
}

export const SPEECH_PAUSES = [1400, 2200, 0]; // 0: explicit Finish speaking
export function speechPause(value) {
  const parsed = Number(value);
  return SPEECH_PAUSES.includes(parsed) ? parsed : 2200;
}
