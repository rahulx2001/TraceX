/** Fictional fixtures for missing/unavailable evidence and recovery; no inference. */
import assert from "node:assert/strict";
import { expect } from "@playwright/test";
import path from "node:path";

export async function runCaseEvidenceUiTest({ page, base, visuals }) {
  const id = "ux-evidence-fixture";
  const routes = [];
  const route = async (pattern, handler) => { await page.route(pattern, handler); routes.push([pattern, handler]); };
  let releasePhotos;
  const firstPhotos = new Promise(resolve => { releasePhotos = resolve; });
  let photoReads = 0, imageReads = 0, noteAttempts = 0, noteKey, detailsUnavailable = true;
  let photos = [], codes = [], notes = [], followup = "", status = "open";
  const detail = () => ({
    case_id: id, category: "Electrical system", severity: "Low", status, pack_id: "automotive_nhtsa",
    description_summary: "Fictional test: dashboard light flickers.", followup_draft: followup, notes,
    completeness: {
      reported_vehicle: { year: "2019", make: "HONDA", model: "" }, vehicle_details_missing: ["model"],
      advisory: { reason: "No recall is linked to this vehicle. You can review the report without a recall match." },
      missing: [...(!photos.length ? ["photos"] : []), ...(!codes.length ? ["fault_codes"] : []),
        ...(!notes.length && !detailsUnavailable ? ["operator_notes"] : []), ...(!followup ? ["followup_draft"] : [])],
      unavailable: detailsUnavailable ? ["operator_notes"] : [],
      complete: Boolean(photos.length && codes.length && notes.length && followup && !detailsUnavailable),
    },
  });
  await route(`**/api/frontline/cases/${id}`, async r => {
    if (r.request().method() === "PATCH") { followup = r.request().postDataJSON().followup_draft ?? followup; status = r.request().postDataJSON().status ?? status; }
    await r.fulfill({ json: detail() });
  });
  await route(`**/api/frontline/cases/${id}/notes`, async r => {
    if (++noteAttempts === 1) { noteKey = r.request().headers()["idempotency-key"]; await r.fulfill({ status: 403, json: { detail: "Fictional forbidden action" } }); return; }
    assert.equal(r.request().headers()["idempotency-key"], noteKey, "retry must reuse the note identity");
    const note = { note_id: "fixture-note", author: "Test operator", created_at: "2026-11-02", body: r.request().postDataJSON().body };
    notes.unshift(note);
    await r.fulfill({ json: note });
  });
  await route(`**/api/frontline/connectors/export/${id}`, r => r.fulfill({ json: { ok: true, status: "success", sink: "outbox" } }));
  await route(`**/api/cases/${id}/evidence`, async r => {
    if (r.request().method() === "POST") {
      photos = [{ evidence_id: "ux-photo-fixture", filename: "fictional.png", mime: "image/png", width: 1, height: 1, analysis_status: "not_run" }];
      await r.fulfill({ json: photos[0] });
    } else if (++photoReads === 1) {
      await firstPhotos;
      await r.fulfill({ status: 503, json: { detail: "Fictional photo-store outage" } });
    } else await r.fulfill({ json: { evidence: photos } });
  });
  await route(`**/api/ai/cases/${id}/fault-codes`, async r => {
    if (r.request().method() === "POST") {
      codes = r.request().postDataJSON().fault_codes.map(code => ({ code, meaning: "Fictional test meaning" }));
      await r.fulfill({ json: { raised: false } });
    } else await r.fulfill({ json: { codes } });
  });
  const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==", "base64");
  await route("**/api/evidence/ux-photo-fixture/file", async r => {
    if (++imageReads === 1) await r.fulfill({ status: 503, body: "Fictional preview outage" });
    else await r.fulfill({ contentType: "image/png", body: png });
  });
  try {
    await page.goto(`${base}/ui/#cases?id=${id}`);
    const drawer = page.getByRole("dialog", { name: "Case detail" });
    const panel = drawer.getByTestId("evidence-panel");
    const guidance = drawer.getByTestId("case-evidence-guidance");
    await expect(drawer.getByRole("heading", { name: "Known now", exact: true })).toBeVisible();
    await expect(drawer.getByRole("heading", { name: "Still needed", exact: true })).toBeVisible();
    await expect(drawer.getByLabel("Operator notes", { exact: true })).not.toBeVisible();
    await expect(drawer.getByText(/Please confirm the vehicle model/)).toBeVisible();
    await page.screenshot({ path: path.join(visuals, "case-workspace-initial.png"), fullPage: true });
    await drawer.getByText("Photos & scan codes", { exact: true }).click();
    await expect(panel.getByText("Loading photos…", { exact: true })).toBeVisible();
    await expect(panel.getByText(/No photos attached/)).toHaveCount(0);
    releasePhotos();
    await expect(panel.getByRole("alert")).toContainText("Saved photos may still exist");
    await expect(panel.getByText(/No photos attached/)).toHaveCount(0);
    await panel.getByRole("button", { name: "Retry photos", exact: true }).click();
    await expect(panel.getByText(/No photos attached/)).toBeVisible();
    await expect(panel.getByRole("alert")).toHaveCount(0);
    await expect(drawer.getByText(/You can review the report without a recall match/)).toBeVisible();
    await expect(guidance).toContainText("Photos and scan codes are optional");
    await guidance.getByRole("button", { name: "Request photo", exact: true }).click();
    await expect(drawer.getByLabel("Follow-up Draft", { exact: true })).toHaveValue(/please share a photo/);
    await guidance.getByRole("button", { name: "Request scan codes", exact: true }).click();
    await expect(drawer.getByLabel("Follow-up Draft", { exact: true })).toHaveValue(/please share the fault codes/);
    await guidance.getByRole("button", { name: "Draft follow-up", exact: true }).click();
    await expect(drawer.getByLabel("Follow-up Draft", { exact: true })).toBeFocused();
    await drawer.getByLabel("Follow-up Draft", { exact: true }).fill("Unsaved follow-up survives evidence refresh.");
    await guidance.getByRole("button", { name: "Record assessment", exact: true }).click();
    await drawer.getByLabel("Operator notes", { exact: true }).fill("Unsaved assessment survives evidence refresh.");
    detailsUnavailable = false;
    await guidance.getByRole("button", { name: "Retry evidence status", exact: true }).click();
    await expect(guidance.getByRole("alert")).toHaveCount(0);
    await expect(drawer.getByLabel("Operator notes", { exact: true })).toHaveValue("Unsaved assessment survives evidence refresh.");
    await guidance.getByRole("button", { name: "Record assessment", exact: true }).click();
    await expect(drawer.getByLabel("Operator notes", { exact: true })).toBeFocused();
    await drawer.locator(".body").evaluate(el => { el.scrollTop = 0; });
    await expect(guidance).toBeVisible();
    await page.screenshot({ path: path.join(visuals, "case-evidence-next-steps.png"), fullPage: true });
    await panel.getByLabel("Upload photo evidence", { exact: true }).setInputFiles({ name: "fictional.png", mimeType: "image/png", buffer: png });
    await expect(guidance.getByRole("button", { name: "Add a photo", exact: true })).toHaveCount(0);
    await expect(panel.getByRole("alert")).toContainText("Photo preview unavailable");
    await panel.getByRole("button", { name: "Retry photo", exact: true }).click();
    await expect(panel.getByRole("img", { name: "fictional.png", exact: true })).toBeVisible();
    assert.equal(await panel.getByRole("img").evaluate(img => img.naturalWidth), 1);
    await expect(panel).toContainText("Photo analysis is currently unavailable");
    await expect(panel).not.toContainText("META_API_KEY");
    await guidance.getByRole("button", { name: "Add scan codes", exact: true }).click();
    await expect(panel.getByLabel("Fault codes", { exact: true })).toBeFocused();
    await panel.getByLabel("Fault codes", { exact: true }).fill("P0300");
    await panel.getByRole("button", { name: "Add codes", exact: true }).click();
    await expect(guidance.getByRole("button", { name: "Add scan codes", exact: true })).toHaveCount(0);
    await expect(drawer.getByLabel("Follow-up Draft", { exact: true })).toHaveValue("Unsaved follow-up survives evidence refresh.");
    await expect(drawer.getByLabel("Operator notes", { exact: true })).toHaveValue("Unsaved assessment survives evidence refresh.");
    await drawer.getByRole("button", { name: "Add note", exact: true }).click();
    await expect(drawer.getByRole("alert").filter({ hasText: "Your current access" })).toBeVisible();
    await expect(drawer.getByLabel("Operator notes", { exact: true })).toHaveValue("Unsaved assessment survives evidence refresh.");
    await expect(drawer).not.toContainText("HTTP 403");
    await drawer.getByRole("button", { name: "Add note", exact: true }).click();
    await expect(drawer.getByText("Assessment notes · 1 recorded", { exact: true })).toBeVisible();
    await drawer.getByRole("button", { name: "Save follow-up", exact: true }).click();
    await expect(guidance).toContainText("Evidence recorded");
    await drawer.getByLabel("Case status", { exact: true }).selectOption("closed");
    assert.equal(status, "open", "selecting a status must not save it");
    await drawer.getByRole("button", { name: "Save status", exact: true }).click();
    await expect(drawer.getByRole("button", { name: "Undo status change", exact: true })).toBeVisible();
    assert.equal(status, "closed");
    await drawer.getByRole("button", { name: "Undo status change", exact: true }).click();
    await expect(drawer.getByLabel("Case status", { exact: true })).toHaveValue("open");
    await drawer.getByRole("button", { name: "Save case packet", exact: true }).click();
    await expect(drawer.getByText(/Case packet saved to the local outbox/)).toBeVisible();
    await expect(drawer.getByText(/Customer message not sent/).last()).toBeVisible();
    await drawer.locator(".body").evaluate(el => { el.scrollTop = 0; });
    await page.screenshot({ path: path.join(visuals, "case-evidence-recorded.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(drawer).toBeVisible();
    assert.equal(await drawer.evaluate(el => el.scrollWidth <= el.clientWidth + 1), true, "case workspace must fit a narrow screen");
    await page.screenshot({ path: path.join(visuals, "case-workspace-mobile.png"), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 720 });
    console.log("PASS: evidence loading/outage/empty states, list and photo retry, optional evidence guidance, focus actions, refreshed saved evidence and preserved unsaved drafts; fictional fixtures only.");
  } finally {
    releasePhotos();
    for (const [pattern, handler] of routes) await page.unroute(pattern, handler);
  }
}
