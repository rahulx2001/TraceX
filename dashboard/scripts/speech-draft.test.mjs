import assert from "node:assert/strict";
import test from "node:test";
import { createSpeechDraft, speechPause } from "../src/speechDraft.js";
import { looksLikeAgentEcho, decideSpeechFinal } from "../src/voiceHelpers.js";

test("final words and the unfinished correction survive together exactly once", () => {
  const draft = createSpeechDraft();
  draft.observe([{ index: 0, text: "The panel is damaged", final: true },
    { index: 1, text: "plus the bra", final: false }], 1000);
  draft.observe([{ index: 0, text: "The panel is damaged", final: true },
    { index: 1, text: "plus the brake", final: false }], 1100);
  assert.equal(draft.snapshot().text, "The panel is damaged plus the brake");
  draft.endSession();
  draft.observe([{ index: 0, text: "No, I said 2018", final: false }], 2000);
  assert.equal(draft.snapshot().text, "The panel is damaged plus the brake No, I said 2018");
  draft.observe([{ index: 0, text: "No, I said 2018", final: true }], 2100);
  assert.equal(draft.snapshot().text, "The panel is damaged plus the brake No, I said 2018");
  draft.clear();
  assert.equal(draft.snapshot().text, "");
});

test("short interim-only answers survive recognition ending", () => {
  const draft = createSpeechDraft();
  draft.observe([{ index: 0, text: "Oh no", final: false }], 500);
  draft.endSession(); draft.endSession();
  assert.equal(draft.snapshot().text, "Oh no");
});

test("question examples and readback years are valid answers, not echo", () => {
  for (const text of ["Honda", "Toyota", "Ford", "2011", "No, I said 2018"]) {
    assert.equal(looksLikeAgentEcho(text, "What's the make? For example, Honda, Ford, Toyota. Model year 2011?"), false);
  }
  assert.equal(looksLikeAgentEcho("Is anyone hurt", "Is anyone hurt?"), true);
});

test("physical speech holds a turn when recognizer text delivery stalls", () => {
  assert.equal(decideSpeechFinal({ committedAt: 1000, lastSpeechAt: 2900, now: 3000, debounceMs: 2200 }).flush, false);
  assert.equal(decideSpeechFinal({ committedAt: 1000, lastSpeechAt: 2900, now: 5200, debounceMs: 2200 }).flush, true);
  assert.equal(speechPause("0"), 0);
  assert.equal(speechPause("broken"), 2200);
});
