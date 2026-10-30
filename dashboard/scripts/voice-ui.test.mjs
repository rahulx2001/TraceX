/** UI regression with explicitly synthetic transport, not a real-audio evaluation. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { expect } from "@playwright/test";

export async function runVoiceUiTest({ page, base }) {
  const frames = [], channels = [], surveyBodies = [];
  let surveyStatus = 500, sequence = 0;
  await page.addInitScript(() => {
    window.__voiceUi = { mic: 0, recognition: 0, playback: 0, cancelled: 0 };
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", { configurable: true, value: async () => {
      window.__voiceUi.mic++;
      throw new DOMException("Synthetic microphone denial for UI regression", "NotAllowedError");
    } });
    window.SpeechRecognition = class {
      constructor() { window.__voiceUi.recog = this; }
      start() { window.__voiceUi.recognition++; }
      stop() { queueMicrotask(() => this.onend?.()); }
      abort() {}
    };
    Object.defineProperty(window, "speechSynthesis", { configurable: true, value: {
      getVoices: () => [], addEventListener() {}, removeEventListener() {},
      speak(utterance) { window.__voiceUi.playback++; utterance.onstart?.(); },
      cancel() { window.__voiceUi.cancelled++; },
    } });
  });
  await page.route("**/api/interactions/start?**", async route => {
    channels.push(new URL(route.request().url()).searchParams.get("channel"));
    sequence++;
    await route.fulfill({ json: {
      interaction_id: `ui-voice-fixture-${sequence}`,
      ws_url: `/ws/interaction/ui-voice-fixture-${sequence}`,
      greeting_text: "Fictional UI test: describe the concern with your vehicle.",
      pack: { id: "automotive_nhtsa", entity_labels: { year: "Model year", symptom: "Reported symptom" } },
    } });
  });
  await page.route("**/api/interactions/ui-voice-fixture-*/end", route => route.fulfill({ json: { status: "ended" } }));
  await page.route("**/api/interactions/ui-voice-fixture-*/outcome", route => {
    surveyBodies.push(route.request().postDataJSON());
    return route.fulfill({ status: surveyStatus, json: surveyStatus === 200 ? { recorded: true } : { detail: "Synthetic failure" } });
  });
  await page.routeWebSocket(/\/ws\/interaction\/ui-voice-fixture-/, ws => {
    ws.onMessage(raw => {
      const frame = JSON.parse(raw); frames.push(frame);
      if (frame.type === "user_turn") {
        ws.send(JSON.stringify({ type: "turn_result", turn_id: frame.turn_id, status: "accepted" }));
        ws.send(JSON.stringify({ type: "slots_update", slots: { year: frame.text.includes("2018") ? "2018" : "2017", symptom: "No fire; knocking over bumps" } }));
        ws.send(JSON.stringify({ type: "agent_turn", text: "Recorded for review. Is there another correction?", turn_id: `reply-${frame.turn_id}` }));
      }
    });
    // Server advertises voice in the text session to ensure client preference
    // survives ready/reconnect capability selection.
    ws.send(JSON.stringify({ type: "ready", authenticated: true, attached: true,
      voice: { server_stt: sequence === 1, server_tts: sequence === 1 } }));
  });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`${base}/ui/#call`);
  await page.reload(); // Hash navigation alone does not run the speech test stubs.
  const start = page.getByRole("button", { name: "Start voice report", exact: true });
  const type = page.getByRole("button", { name: "Type instead", exact: true });
  await expect(start).toBeVisible();
  await expect(type).toBeVisible();
  assert.equal(await start.evaluate(el => !!el.closest('[aria-hidden="true"]')), false);
  const initialBox = await start.boundingBox();
  assert.ok(initialBox.y + initialBox.height < 800, "primary action is above the laptop fold");
  const startContrast = await start.evaluate(el => {
    const style = getComputedStyle(el);
    const lum = value => value.match(/[\d.]+/g).slice(0, 3).map(Number).map(n => n / 255)
      .map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4)
      .reduce((sum, n, i) => sum + n * [.2126, .7152, .0722][i], 0);
    const values = [lum(style.color), lum(style.backgroundColor)].sort((a, b) => b - a);
    return (values[0] + .05) / (values[1] + .05);
  });
  assert.ok(startContrast >= 4.5, `Start voice report contrast ${startContrast.toFixed(2)}:1`);
  await expect(page.getByRole("heading", { name: "What we understood" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Still needed" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Next step" })).toBeVisible();

  // A half-width viewport exercises reflow equivalent to 200% desktop zoom.
  await page.setViewportSize({ width: 640, height: 400 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, "200% equivalent reflow has no horizontal page overflow");
  await expect(start).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 800 });
  await type.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Text report active. Microphone and spoken playback are off.")).toBeVisible();
  await expect(page.getByRole("log", { name: "Report transcript" })).toContainText("Fictional UI test");
  assert.deepEqual(channels, ["web_text"]);
  assert.deepEqual(await page.evaluate(() => ({ mic: __voiceUi.mic, recognition: __voiceUi.recognition, playback: __voiceUi.playback })),
    { mic: 0, recognition: 0, playback: 0 }, "Type instead must not acquire, recognize or play audio");
  await page.getByRole("textbox", { name: "Type a reply or correction" }).fill("My 2017 car knocks over bumps. No fire occurred.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".voice-fact").filter({ hasText: "Model year" })).toContainText("2017");
  await page.getByRole("button", { name: "Correct Model year", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Type a reply or correction" })).toBeFocused();
  await page.getByRole("textbox", { name: "Type a reply or correction" }).fill("Correction: Model year should be 2018, not 2017.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".voice-fact").filter({ hasText: "Model year" })).toContainText("2018");
  const log = page.getByRole("log", { name: "Report transcript" });
  await expect(log).toContainText("My 2017 car knocks over bumps. No fire occurred.");
  await expect(log).toContainText("Correction: Model year should be 2018, not 2017.");

  const screenshotDir = path.join(os.tmpdir(), "tracex-voice-ui-review");
  await fs.mkdir(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, "voice-report-laptop.png"), animations: "disabled" });
  await page.setViewportSize({ width: 640, height: 400 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, "active report reflows at 200% equivalent viewport");
  assert.equal(await page.locator("main").evaluate(el => el.scrollWidth > el.clientWidth + 1), false, "active report has no hidden horizontal overflow inside its scroll region");
  await page.screenshot({ path: path.join(screenshotDir, "voice-report-200pct-equivalent.png"), animations: "disabled" });
  await log.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(screenshotDir, "voice-report-200pct-transcript.png"), animations: "disabled" });
  await page.setViewportSize({ width: 1280, height: 800 });

  const contrasts = await page.evaluate(() => {
    const parse = value => { const p = value.match(/[\d.]+/g)?.map(Number) || []; return [p[0] || 0, p[1] || 0, p[2] || 0, p[3] ?? 1]; };
    const blend = (fg, bg) => fg.slice(0, 3).map((n, i) => n * fg[3] + bg[i] * (1 - fg[3]));
    const lum = c => c.map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4).reduce((v, n, i) => v + n * [.2126, .7152, .0722][i], 0);
    return [...document.querySelectorAll('.voice-page .sub, .voice-page .voice-note, .voice-page .turn, .voice-page .turn .who, .voice-page .voice-fact strong, .voice-page button:not(:disabled)')].filter(el => el.getClientRects().length).map(el => {
      const ancestors = []; for (let p = el; p; p = p.parentElement) ancestors.unshift(p);
      const bg = ancestors.reduce((color, p) => blend(parse(getComputedStyle(p).backgroundColor), color), [255, 255, 255]);
      const fg = blend(parse(getComputedStyle(el).color), bg);
      const values = [lum(fg), lum(bg)].sort((a, b) => b - a);
      return { text: el.textContent.slice(0, 45), ratio: (values[0] + .05) / (values[1] + .05) };
    });
  });
  assert.ok(contrasts.length > 0);
  for (const result of contrasts) assert.ok(result.ratio >= 4.5, `text contrast ${result.ratio.toFixed(2)}: ${result.text}`);
  console.log(`PASS: keyboard start, text-only capture, visible correction history, reflow and sampled text contrast (minimum ${Math.min(startContrast, ...contrasts.map(r => r.ratio)).toFixed(2)}:1; Start ${startContrast.toFixed(2)}:1). Synthetic transport; no real audio.`);
  console.log(`Voice UI screenshots (synthetic transport): ${screenshotDir}`);

  page.once("dialog", dialog => dialog.dismiss());
  await page.getByRole("complementary", { name: "Primary", exact: true }).getByRole("button", { name: "Judge start →", exact: true }).click();
  await expect(page).toHaveURL(/#call$/);
  assert.equal(frames.filter(f => f.type === "hangup").length, 0, "cancelled navigation preserves the active report");

  await page.getByRole("button", { name: "End call", exact: true }).click();
  const handoff = page.getByRole("link", { name: "Investigate this report →", exact: true });
  await expect(handoff).toHaveAttribute("href", "#safety-campaigns?tab=investigate&interaction=ui-voice-fixture-1");
  assert.equal(frames.filter(f => f.type === "user_turn").length, 2, "correction is sent once");
  assert.equal(frames.filter(f => f.type === "user_audio").length, 0);
  for (const status of [401, 404, 500]) {
    surveyStatus = status;
    await page.getByRole("button", { name: "Capture rating 4", exact: true }).click();
    await page.getByRole("button", { name: "Save feedback", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(`Feedback was not saved (${status})`);
    await expect(page.getByRole("button", { name: "Capture rating 4", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "Save feedback", exact: true })).toBeEnabled();
  }
  surveyStatus = 200;
  await page.getByRole("button", { name: "Save feedback", exact: true }).click();
  await expect(page.getByRole("button", { name: "Feedback saved", exact: true })).toBeDisabled();
  assert.ok(surveyBodies.every(body => body.csat === 4 && body.resolved === null), "intake rating must not claim repair resolution");

  await start.click();
  await expect(page.getByRole("button", { name: "Interrupt playback", exact: true })).toBeEnabled();
  assert.equal(channels.at(-1), "web_voice");
  assert.equal(frames.filter(f => f.type === "user_turn").length, 2, "a new report must not replay an old report's pending turn");
  const hangupsBefore = frames.filter(f => f.type === "hangup").length;
  await page.getByRole("button", { name: "Mute microphone", exact: true }).click();
  await expect(page.getByRole("button", { name: "Unmute microphone", exact: true })).toBeVisible();
  assert.equal(frames.filter(f => f.type === "hangup").length, hangupsBefore, "microphone control must never hang up");
  await page.getByRole("button", { name: "Interrupt playback", exact: true }).click();
  await expect(page.getByRole("button", { name: "Interrupt playback", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "End call", exact: true })).toBeVisible();
  assert.equal(frames.filter(f => f.type === "hangup").length, hangupsBefore, "interrupt must preserve the contact");
  assert.equal(frames.filter(f => f.type === "barge_in").length, 1);
  await page.getByRole("button", { name: "Unmute microphone", exact: true }).click();
  await page.getByRole("button", { name: "End call", exact: true }).click();
  console.log("PASS: separate mute/interrupt/end controls, source-ID handoff and feedback failure/retry semantics. Speech is stubbed; no multilingual/audio quality claim.");

  // Drive the shipped recognizer callbacks, not a source-string assertion.
  // These are synthetic recognition events; no microphone recording or STT model.
  const turnsBeforeSpeech = frames.filter(f => f.type === "user_turn").length;
  await page.getByLabel("Pause before sending", { exact: true }).selectOption("0");
  await start.click();
  await page.getByRole("button", { name: "Interrupt playback", exact: true }).click();
  await expect(page.getByRole("button", { name: "Finish speaking", exact: true })).toBeEnabled();
  await page.evaluate(() => {
    const results = [Object.assign([{ transcript: "The panel is damaged" }], { isFinal: true }),
      Object.assign([{ transcript: "plus the brake" }], { isFinal: false })];
    __voiceUi.recog.onresult({ resultIndex: 0, results });
    __voiceUi.recog.onresult({ resultIndex: 1, results }); // same final is still in the result list
  });
  await expect(log).toContainText("The panel is damaged plus the brake");
  await page.waitForTimeout(2400);
  assert.equal(frames.filter(f => f.type === "user_turn").length, turnsBeforeSpeech, "manual capture does not auto-send at a pause");
  await page.getByRole("button", { name: "Finish speaking", exact: true }).click();
  await expect.poll(() => frames.filter(f => f.type === "user_turn").length).toBe(turnsBeforeSpeech + 1);
  assert.equal(frames.filter(f => f.type === "user_turn").at(-1).text, "The panel is damaged plus the brake");
  await expect(page.getByRole("button", { name: "Interrupt playback", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Interrupt playback", exact: true }).click();
  await page.getByLabel("Pause before sending", { exact: true }).selectOption("1400");
  await page.evaluate(() => __voiceUi.recog.onresult({ resultIndex: 0,
    results: [Object.assign([{ transcript: "Honda" }], { isFinal: true })] }));
  await expect.poll(() => frames.filter(f => f.type === "user_turn").length).toBe(turnsBeforeSpeech + 2);
  assert.equal(frames.filter(f => f.type === "user_turn").at(-1).text, "Honda");
  await expect(page.getByRole("button", { name: "Interrupt playback", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Interrupt playback", exact: true }).click();
  await page.getByLabel("Pause before sending", { exact: true }).selectOption("0");
  await page.evaluate(() => {
    __voiceUi.recog.onresult({ resultIndex: 0,
      results: [Object.assign([{ transcript: "Oh no" }], { isFinal: false })] });
    __voiceUi.recog.onend();
  });
  await expect(log).toContainText("Oh no");
  await page.getByRole("button", { name: "Finish speaking", exact: true }).click();
  await expect.poll(() => frames.filter(f => f.type === "user_turn").length).toBe(turnsBeforeSpeech + 3);
  assert.equal(frames.filter(f => f.type === "user_turn").at(-1).text, "Oh no");
  await page.getByRole("button", { name: "End call", exact: true }).click();
  console.log("PASS: rendered voice capture sends final + interim words once, keeps manual pauses, accepts a short brand and rescues an interim-only answer across recognizer restart. Synthetic events; no audio-quality result.");
}
