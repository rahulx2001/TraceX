/** Real local API + WebSocket + durable source + packet. Text only; inference disabled. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { expect } from "@playwright/test";

export async function runReportHandoffTest({ page, context, base, fixture }) {
  await page.goto(`${base}/ui/#call`);
  const startResponse = page.waitForResponse(r => r.url().includes("/api/interactions/start?") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Type instead", exact: true }).click();
  const started = await startResponse;
  assert.equal(started.status(), 200);
  const interaction = await started.json();
  const reports = ["Yes, I consent.", "My 2019 Toyota Camry knocks over bumps. No smoke or fire.", "No, I said model year 2018, not 2019."];
  for (const text of reports) {
    await page.getByRole("textbox", { name: "Type a reply or correction" }).fill(text);
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled({ timeout: 15000 });
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect.poll(async () => {
      const detail = await (await context.request.get(`${base}/api/interactions/${interaction.interaction_id}`)).json();
      return detail.turns?.some(t => t.speaker === "customer" && t.text === text);
    }, { timeout: 15000, message: "typed turn must reach durable backend storage" }).toBe(true);
  }
  await page.getByRole("button", { name: "End call", exact: true }).click();
  const sourcePath = `/api/safety-campaigns/report-sources/interactions/${interaction.interaction_id}`;
  await expect.poll(async () => (await context.request.get(`${base}${sourcePath}`)).status(),
    { timeout: 15000, message: "ended report must become available for review" }).toBe(200);
  const original = await (await context.request.get(`${base}${sourcePath}`)).json();
  assert.ok(original.source.turns.some(t => t.text === reports[2]));
  await page.getByRole("link", { name: "Investigate this report →", exact: true }).click();
  await expect(page.getByTestId("report-source-preview")).toContainText(reports[2]);
  await page.getByLabel("Select safety campaign").selectOption(fixture.campaign_id);
  const campaign = await (await context.request.get(`${base}/api/safety-campaigns/${fixture.campaign_id}`)).json();
  await page.getByLabel("Investigation vehicle", { exact: true }).selectOption(campaign.vehicles[0].vehicle_id);
  await page.getByLabel("I reviewed these stored report turns.").check();
  await page.getByLabel(/I confirm this report concerns the selected vehicle/).check();
  const responsePromise = page.waitForResponse(r => r.url().endsWith("/investigations") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Run sourced investigation", exact: true }).click();
  const response = await responsePromise;
  assert.equal(response.status(), 200, await response.text());
  const request = response.request().postDataJSON(), draft = await response.json();
  assert.equal(Object.hasOwn(request, "text"), false);
  assert.deepEqual(request.source_ref, original.source_ref);
  assert.equal(draft.model_calls, 0);
  assert.equal(draft.extraction.mode, "manual");
  assert.deepEqual(draft.report_sources[0].turns.map(t => t.turn_id), original.source_ref.turn_ids);
  await page.getByLabel("Draft decision", { exact: true }).selectOption("accepted_for_investigation");
  await page.getByLabel("Evidence review note", { exact: true }).fill("Fictional browser test: checked original stored turns, including the model-year correction. No mechanical finding asserted.");
  await page.getByLabel("I reviewed the original sources and the draft interpretations.").check();
  const reviewPromise = page.waitForResponse(r => r.url().endsWith(`/${draft.run_id}/review`) && r.request().method() === "POST");
  await page.getByRole("button", { name: "Record draft review", exact: true }).click();
  assert.equal((await reviewPromise).status(), 200);
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export evidence ↗", exact: true }).click();
  const download = await downloading;
  const packet = JSON.parse(await fs.readFile(await download.path(), "utf8"));
  const exported = packet.investigation_drafts.find(r => r.run_id === draft.run_id);
  assert.deepEqual(exported.report_sources[0].source_ref, original.source_ref);
  assert.equal(exported.review.actor, "browser-test-supervisor");
  assert.ok(exported.report_sources[0].text.includes(reports[2]));
  console.log("PASS: real local text contact → stored correction turns → reviewed source-reference handoff → manual fallback → supervisor review → downloaded evidence packet. No mocked transport, model or real-audio claim.");
}
