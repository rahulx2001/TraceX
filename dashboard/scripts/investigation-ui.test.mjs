/** Current-build UI contract checks. Source/model responses are explicitly test fixtures. */
import assert from "node:assert/strict";
import { expect } from "@playwright/test";

export async function runInvestigationUiTest({ page, context, base, fixture }) {
  const root = `/api/safety-campaigns/${fixture.campaign_id}`;
  const stored = await (await context.request.get(`${base}${root}`)).json();
  const first = stored.vehicles[0];
  const second = { ...first, vehicle_id: "UI-FIXTURE-002", owner_ref: "UI-TEST-OWNER-2", replies: [] };
  const campaign = { ...stored, vehicles: [{ ...first, replies: [{ reply_id: "ui-reply", text: "No fire occurred.", at: "2026-10-30T10:00:00Z", by: "ui-test", symptoms: ["other"] }] }, second] };
  const iid = "ui-test-interaction";
  const sourceUrl = `/api/safety-campaigns/report-sources/interactions/${iid}`;
  const sourceRef = { kind: "interaction", interaction_id: iid, turn_ids: ["ui-turn-1", "ui-turn-2"], sha256: "a".repeat(64) };
  const source = { source_id: `interaction-${iid}`, kind: "stored_interaction_report", text: "No fire occurred.\nCorrection: my car is a 2018 model.", sha256: "a".repeat(64),
    provenance: { url: sourceUrl, interaction_id: iid, at: "2026-10-30T10:00:00Z" }, turns: [
      { turn_id: "ui-turn-1", speaker: "customer", at: "2026-10-30T10:00:00Z", text: "No fire occurred." },
      { turn_id: "ui-turn-2", speaker: "customer", at: "2026-10-30T10:00:04Z", text: "Correction: my car is a 2018 model." },
    ] };
  const evidence = { source_id: source.source_id, sentence_id: `${source.source_id}:1`, quote: "No fire occurred.", turn_id: "ui-turn-1", speaker: "customer", at: source.turns[0].at, provenance: source.provenance };
  const bodies = [], runs = [];
  let originalReads = 0, reviewBody;
  const handler = async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const respond = json => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (path === "/api/safety-campaigns") return respond({ campaigns: [campaign] });
    if (path === root) return respond(campaign);
    if (path === sourceUrl) { originalReads++; return respond({ source_ref: sourceRef, source, status: "completed", channel: "web_text" }); }
    if (path === `${root}/report-sources/replies/${first.vehicle_id}/ui-reply`) return respond({ source_ref: { kind: "campaign_reply", reply_id: "ui-reply", sha256: "b".repeat(64) }, source: { ...source, source_id: "reply-ui-reply", kind: "stored_owner_reply", turns: [], text: "No fire occurred." } });
    if (path === `${root}/investigations` && request.method() === "GET") return respond({ runs });
    if (path === `${root}/investigations` && request.method() === "POST") {
      const body = request.postDataJSON(); bodies.push(body);
      const parent = runs.find(r => r.run_id === body.parent_run_id);
      const run = { run_id: `ui-handoff-run-${bodies.length}`, request_id: body.request_id, campaign_id: campaign.campaign_id,
        vehicle_id: body.vehicle_id, snapshot_revision: campaign.revision, status: "complete", stage: "ready_for_review", turn: bodies.length,
        started_at: "2026-10-30T10:05:00Z", elapsed_ms: 10, model_calls: 0, review: null, parent_run_id: body.parent_run_id,
        report_sources: [source], sources: [source], tool_trace: [],
        extraction: { mode: "manual", model_id: null, observations: [], unknown_fields: ["cause"] },
        brief: { claims: [{ relationship: "unresolved", interpretation: parent ? "The owner denied fire; the car is a 2018 model." : "UI test claim requiring correction.", evidence: [evidence] }], next_step: "review_trace", next_step_label: "Review installed-part documentation", followup_question: "Add any missing installation record." },
        ...(parent ? { correction_context: { parent_run_id: parent.run_id, review: parent.review } } : {}),
        note: "Synthetic UI test fixture; no provider was called." };
      runs.push(run); return respond(run);
    }
    if (path.endsWith("/review") && path.startsWith(`${root}/investigations/`)) {
      reviewBody = request.postDataJSON();
      const run = runs.find(r => path.endsWith(`/${r.run_id}/review`));
      run.review = { ...reviewBody, actor: "ui-test-reviewer", at: "2026-10-30T10:06:00Z", synthetic_demo: true };
      return respond(run);
    }
    return route.continue();
  };
  const pattern = /\/api\/safety-campaigns(?:\/|$)/;
  await page.route(pattern, handler);
  try {
    await page.goto(`${base}/ui/#safety-campaigns?tab=investigate&campaign=${campaign.campaign_id}&interaction=${iid}`);
    await page.reload();
    await expect(page.getByTestId("report-source-preview")).toBeVisible();
    await expect(page.getByTestId("report-source-preview")).toContainText("ui-turn-2");
    await expect(page.getByTestId("report-source-preview")).toContainText("Correction: my car is a 2018 model.");
    assert.equal(bodies.length, 0, "loading handoff must not start inference");
    const start = page.getByRole("button", { name: "Run sourced investigation", exact: true });
    await expect(start).toBeDisabled();
    await page.getByLabel("Investigation vehicle", { exact: true }).selectOption(first.vehicle_id);
    await page.getByLabel("I reviewed these stored report turns.").check();
    await expect(start).toBeDisabled();
    await page.getByLabel(/I confirm this report concerns the selected vehicle/).check();
    await expect(start).toBeEnabled();
    await page.getByLabel("Investigation vehicle", { exact: true }).selectOption(second.vehicle_id);
    await expect(page.getByLabel(/I confirm this report concerns the selected vehicle/)).not.toBeChecked();
    await expect(start).toBeDisabled();
    await page.getByLabel(/I confirm this report concerns the selected vehicle/).check();
    await start.click();
    await expect(page.getByTestId("investigation-result")).toContainText("UI test claim requiring correction.");
    assert.deepEqual(bodies[0].source_ref, sourceRef);
    assert.equal(bodies[0].source_reviewed, true);
    assert.equal(bodies[0].vehicle_association_confirmed, true);
    assert.equal(bodies[0].vehicle_id, second.vehicle_id);
    assert.equal(Object.hasOwn(bodies[0], "text"), false, "handoff sends source references, not copied text");
    const readsBeforeCitation = originalReads;
    const original = page.getByTestId("investigation-result").getByText(`Source ${evidence.sentence_id}`, { exact: true });
    await original.click();
    await page.getByTestId("investigation-result").getByRole("button", { name: "Open original record", exact: true }).first().click();
    await expect(page.getByTestId("original-source-record")).toContainText("ui-turn-1");
    assert.equal(originalReads, readsBeforeCitation + 1, "citation reopens server source endpoint");
    await page.getByLabel("Review claim 1", { exact: true }).selectOption("correct");
    await page.getByLabel("Correction for claim 1", { exact: true }).fill("The owner denied fire; the car is a 2018 model.");
    await page.getByLabel("Evidence review note", { exact: true }).fill("UI fixture review: preserve denial and the year correction.");
    await page.getByLabel("I reviewed the original sources and the draft interpretations.").check();
    await page.getByRole("button", { name: "Record draft review", exact: true }).click();
    await expect(page.getByRole("button", { name: "Create revised investigation", exact: true })).toBeEnabled();
    assert.deepEqual(reviewBody.corrections, [{ claim_index: 0, decision: "correct", correction: "The owner denied fire; the car is a 2018 model." }]);
    await page.getByRole("button", { name: "Create revised investigation", exact: true }).click();
    await expect(page.getByText("Linked revision of ui-handoff-run-1.", { exact: false })).toBeVisible();
    assert.equal(bodies[1].parent_run_id, "ui-handoff-run-1");
    assert.equal(Object.hasOwn(bodies[1], "text"), false, "a correction-only revision needs no retyping");
    assert.equal(runs[0].review.corrections[0].decision, "correct", "the original review remains unchanged");
    await page.getByLabel("Draft decision", { exact: true }).selectOption("accepted_for_investigation");
    await page.getByLabel("Review claim 1", { exact: true }).selectOption("accept");
    await page.getByLabel("Evidence review note", { exact: true }).fill("UI fixture corrected draft reviewed.");
    await page.getByLabel("I reviewed the original sources and the draft interpretations.").check();
    await page.getByRole("button", { name: "Record draft review", exact: true }).click();
    await page.getByRole("button", { name: "Review installed-part documentation →", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Verify or correct installed-part evidence", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: second.vehicle_id, exact: true })).toBeVisible();
    await expect(page.getByLabel("Installation record contents", { exact: true })).toBeVisible();
    // A hash change on the mounted page must select its target tab and vehicle.
    await page.evaluate(({ cid, vid }) => { window.location.hash = `safety-campaigns?tab=investigate&campaign=${cid}&vehicle=${vid}`; }, { cid: campaign.campaign_id, vid: first.vehicle_id });
    await expect(page.getByLabel("Investigation vehicle", { exact: true })).toHaveValue(first.vehicle_id);
    await page.getByRole("button", { name: "Use latest recorded report", exact: true }).click();
    await expect(page.getByTestId("report-source-preview")).toContainText("reply-ui-reply");
    await expect(page.getByLabel("Owner report to investigate", { exact: true })).toHaveCount(0);
    await expect(start).toBeDisabled();
    await page.goto(`${base}/ui/#safety-campaigns?campaign=${campaign.campaign_id}&vehicle=${first.vehicle_id}&reply=ui-reply&assistance_mode=extraction_only`);
    await expect(page.getByTestId("report-source-preview")).toContainText("reply-ui-reply");
    await expect(page.getByLabel("Investigation vehicle", { exact: true })).toHaveValue(first.vehicle_id);
    await expect(start).toBeDisabled();
    assert.equal(bodies.length, 2, "exact-reply study launch resolves the source without starting the task");
    console.log("PASS: UI fixtures verify reviewed source handoff, vehicle reconfirmation, original citations, correction-only revision and trace-review routing (no model calls).");
  } finally { await page.unroute(pattern, handler); }
}
