/** Read-only local checks; display fixtures never enter either database. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const report = path.join(root, "reports/improvement/early_warning_data_2026_11_02");
const isolatedBase = process.env.EWB_TEST_BASE || "http://127.0.0.1:8766";
const regularBase = process.env.EWB_REGULAR_BASE || "http://127.0.0.1:8000";
const checks = [];
const snapshots = {};
const browser = await chromium.launch({ channel: "chrome" });

function tile(page, label) {
  return page.locator(".snapshot-tile").filter({ has: page.locator(".k", { hasText: new RegExp(`^${label}$`) }) }).locator(".v");
}

try {
  await fs.mkdir(report, { recursive: true });
  for (const [name, base] of [["isolated", isolatedBase], ["regular", regularBase]]) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await context.addInitScript(() => localStorage.setItem("fl.includeSimulated", "true"));
    const page = await context.newPage();
    // The regular process serves an older sibling UI build. Preview its GET
    // data in this project's current UI without changing either installation.
    if (name === "regular") {
      await page.route("**/api/**", async route => {
        if (route.request().method() !== "GET") return route.abort();
        const incoming = new URL(route.request().url());
        const response = await context.request.get(`${base}${incoming.pathname}${incoming.search}`);
        return route.fulfill({ response });
      });
    }
    const response = await context.request.get(`${base}/api/frontline/metrics?window_days=7&include_simulated=true`);
    assert.equal(response.status(), 200);
    const metrics = await response.json();
    const board = await (await context.request.get(`${base}/api/frontline/early-warning?window_days=7&include_simulated=true`)).json();
    snapshots[name] = { base, metrics, funnel: board.funnel, spike_week: board.spike_week, spikes: board.spikes };
    await page.goto(`${isolatedBase}/ui/#warning`);
    await expect(tile(page, "Open cases")).toHaveText(String(metrics.cases.open));
    await expect(tile(page, "Critical open")).toHaveText(String(metrics.cases.critical_open));
    await expect(tile(page, "Investigations")).toHaveText(String(metrics.investigations.open));
    await expect(tile(page, "Active calls")).toHaveText(String(metrics.interactions_active));
    await expect(page.getByText(`Pending follow-up: ${metrics.cases.pending_followup}`, { exact: true })).toBeVisible();
    await expect(page.getByText(/These counts are separate from operational cases/)).toBeVisible();
    if (board.funnel.started === 0) await expect(page.getByRole("status").filter({ hasText: "No contacts started" })).toBeVisible();
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: path.join(report, `${name}.png`), fullPage: true });
    checks.push(`${name}: current UI counts match the running API, with explicit corpus/operations scope${name === "regular" ? " (read-only browser forwarding for this check)" : ""}`);
    await page.unrouteAll({ behavior: "wait" });
    await context.close();
  }

  const context = await browser.newContext();
  await context.addInitScript(() => localStorage.setItem("fl.includeSimulated", "false"));
  const page = await context.newPage();
  let failMetrics = false;
  let holdExcluded = false;
  let heldRoute;
  const requests = [];
  await page.route("**/api/frontline/metrics?*", async route => {
    const included = new URL(route.request().url()).searchParams.get("include_simulated") === "true";
    requests.push(included);
    if (holdExcluded && !included) { heldRoute = route; return; }
    if (failMetrics) return route.fulfill({ status: 503, json: { detail: "Display test outage" } });
    return route.fulfill({ json: { cases: { open: included ? 25 : 7, critical_open: included ? 5 : 2, pending_followup: 3 }, investigations: { open: 2 }, interactions_active: 0 } });
  });
  await page.route("**/api/frontline/early-warning?*", route => route.fulfill({ json: {
    live_risk: [], funnel: { started: 30, completed: 25, cases_created: 25 }, spikes: [],
  } }));
  await page.route("**/api/frontline/simulate?*", route => route.fulfill({ json: {
    completed: 25, abandoned: 0, escalated: 0, cases_created: 25, investigations_opened: 0, errors: [],
  } }));
  await page.goto(`${isolatedBase}/ui/#warning`);
  const filter = page.getByRole("checkbox", { name: "Include simulated traffic", exact: true });
  const refresh = page.getByRole("button", { name: "Refresh", exact: true });
  await expect(tile(page, "Open cases")).toHaveText("7");
  await refresh.click();
  await expect(tile(page, "Open cases")).toHaveText("7");
  assert.ok(requests.every(included => included === false), "Refresh must not turn a click event into include_simulated=true");
  checks.push("Refresh respects an unchecked simulated-traffic filter");

  const requestStart = requests.length;
  await page.getByRole("button", { name: "Simulate traffic", exact: true }).first().click();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(filter).toBeChecked();
  await expect(tile(page, "Open cases")).toHaveText("25");
  assert.ok(requests.slice(requestStart).every(included => included === true));
  await page.getByRole("button", { name: "Close", exact: true }).click();
  checks.push("Simulation refresh uses the new included filter; simulation response is display-only");

  holdExcluded = true;
  await filter.uncheck();
  await expect.poll(() => Boolean(heldRoute)).toBe(true);
  await filter.check();
  await expect(tile(page, "Open cases")).toHaveText("25");
  await heldRoute.fulfill({ json: { cases: { open: 99 } } });
  await expect(refresh).toBeEnabled();
  await expect(tile(page, "Open cases")).toHaveText("25");
  holdExcluded = false;
  checks.push("Late responses cannot replace counts for the currently selected filter");

  failMetrics = true;
  await refresh.click();
  await expect(page.getByRole("alert").filter({ hasText: "Operational counts are unavailable" })).toBeVisible();
  await expect(tile(page, "Open cases")).toHaveText("—");
  checks.push("A metrics outage clears stale counts and shows unavailable instead of zero");
  failMetrics = false;
  await refresh.click();
  await expect(tile(page, "Open cases")).toHaveText("25");
  await expect(page.getByRole("alert").filter({ hasText: "Operational counts are unavailable" })).toHaveCount(0);
  checks.push("Refresh recovers the counts after the outage");
  await context.close();
  await fs.writeFile(path.join(report, "verification.json"), JSON.stringify({ verified_at: new Date().toISOString(), checks, snapshots, scope: "Read-only API checks plus browser display fixtures. No database seeding, inference, customer messages or model evaluation." }, null, 2) + "\n");
  console.log(`Passed ${checks.length}/${checks.length} focused checks; API snapshots and screenshots saved in ${report}.`);
} finally {
  await browser.close();
}
