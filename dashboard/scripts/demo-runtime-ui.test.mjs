/** Open local demo against the real isolated API. Fictional records; no model calls. */
import assert from "node:assert/strict";
import { expect } from "@playwright/test";
import { runReportHandoffTest } from "./report-handoff.test.mjs";

export async function runDemoRuntimeUiTest({ page, context, base }) {
  await page.goto(`${base}/ui/#command`);
  await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI assistance: off");
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toHaveCount(0);
  const filter = page.getByRole("checkbox", { name: "Include test traffic", exact: true });
  await expect(filter).not.toBeChecked();
  const openCases = page.locator(".stat-card").filter({ hasText: "Open cases" }).locator(".value");
  await expect(openCases).toHaveText("0");
  const seeded = page.waitForResponse(r => r.url().includes("/api/frontline/simulate?") && r.request().method() === "POST", { timeout: 300000 });
  await page.getByRole("button", { name: "Seed demo traffic", exact: true }).click();
  const seedResponse = await seeded;
  assert.equal(seedResponse.status(), 200);
  const seed = await seedResponse.json();
  assert.deepEqual(seed.errors, []);
  assert.equal(seed.completed, 15);
  assert.ok(seed.cases_created > 0);
  await expect(filter).toBeChecked();
  await expect(openCases).toHaveText(String(seed.cases_created));
  await page.reload();
  await expect(filter).toBeChecked();
  await expect(openCases).toHaveText(String(seed.cases_created));
  await filter.uncheck();
  await expect(openCases).toHaveText("0");
  await filter.check();
  await expect(openCases).toHaveText(String(seed.cases_created));
  await page.locator(".stat-card").filter({ hasText: "Open cases" }).click();
  await expect(page.getByRole("heading", { name: "Case queue", exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Include simulated traffic", exact: true })).toBeChecked();
  const cases = await (await context.request.get(`${base}/api/frontline/cases?include_simulated=true&status=open`)).json();
  assert.ok(cases.cases.length > 0);
  await expect(page.getByText(cases.cases[0].case_id, { exact: true }).first()).toBeVisible();
  console.log(`PASS: real API seeded ${seed.completed} simulated contacts and ${seed.cases_created} cases; filter updates, survives reload and carries into the case queue.`);

  const demoResponse = await context.request.post(`${base}/api/safety-campaigns/demo`);
  assert.equal(demoResponse.status(), 200);
  const campaign = await demoResponse.json();
  assert.equal(campaign.synthetic_demo, true);
  await runReportHandoffTest({ page, context, base, fixture: campaign, expectedActor: "operator" });
  await page.goto(`${base}/ui/#safety-campaigns?tab=trace&campaign=${campaign.campaign_id}&vehicle=${campaign.vehicles[0].vehicle_id}`);
  await expect(page.getByRole("heading", { name: "Verify or correct installed-part evidence", exact: true })).toBeVisible();
  await expect(page.getByLabel("Installation record contents", { exact: true })).toBeVisible();
  await page.goto(`${base}/ui/#safety-campaigns?tab=evidence&campaign=${campaign.campaign_id}`);
  await expect(page.getByRole("heading", { name: "Evidence timeline", exact: true })).toBeVisible();
  const health = await (await context.request.get(`${base}/health`)).json();
  assert.equal(health.auth_required, false);
  const principal = await (await context.request.get(`${base}/api/frontline/auth/verify`)).json();
  assert.equal(principal.role, "agent");
  console.log("PASS: real open API + WebSocket text report, stored-source handoff, zero-model manual draft, synthetic review, installation view and evidence export; no sign-in or supervisor elevation.");

  // Display-only mocks verify failure/configuration labels, never hosted inference.
  const statusPath = "**/api/ai/status";
  await page.route(statusPath, route => route.fulfill({ status: 503, json: { detail: "Test outage" } }));
  await page.goto(`${base}/ui/#demo`);
  await page.reload();
  await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI assistance: unavailable");
  await expect(page.getByTestId("demo-ai-notice")).toContainText("Assistance status is unavailable");
  await page.unroute(statusPath);
  await page.route(statusPath, route => route.fulfill({ json: { mode: "enhanced", models: { text: "display-test-only" } } }));
  await page.reload();
  await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI assistance: on");
  await page.unroute(statusPath);
  await page.reload();
  await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI assistance: off");
  await expect(page.getByTestId("demo-ai-notice")).toContainText("Reports, record lookups and manual review remain available");
  console.log("PASS: AI mode distinguishes healthy local rules, configured provider and unavailable status without claiming an inference.");
}
