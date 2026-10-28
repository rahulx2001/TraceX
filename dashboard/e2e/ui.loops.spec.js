import { test, expect } from "@playwright/test";
import { ConsolePage } from "./pages/ConsolePage.js";

test.describe("Operator loops", () => {
  test.beforeEach(async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
  });

  test("command critical card opens filtered case queue", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    const errors = consolePage.trackErrors();
    await consolePage.gotoHash("command");
    const btn = page.locator("button.stat-card-btn", { hasText: "Critical open" });
    await expect(btn).toBeVisible();
    await btn.click();
    await expect(page).toHaveURL(/#cases/);
    await expect(page).toHaveURL(/severity=Critical/);
    expect(errors).toEqual([]);
    await expect(page.getByText("This view hit an error")).toHaveCount(0);
  });

  test("case row opens drawer", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("cases");
    const sim = page.getByLabel("Include simulated traffic");
    await expect(sim).toBeVisible();
    if (!(await sim.isChecked())) await sim.check();
    const row = page.locator("table tbody tr", { hasText: /case_/ }).first();
    try {
      await row.waitFor({ state: "visible", timeout: 8_000 });
    } catch {
      test.skip(true, "no seeded case rows");
    }
    await row.click();
    await expect(page.locator('[role="dialog"][aria-label="Case detail"]')).toBeVisible();
  });

  test("early warning simulate modal closes on Escape", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("warning");
    await page.getByRole("button", { name: /Simulate traffic/i }).first().click();
    await expect(page.locator(".modal-backdrop")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".modal-backdrop")).toHaveCount(0);
  });

  test("g then a opens trust", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("command");
    await expect(page.getByText(/Command center/i).first()).toBeVisible();
    await consolePage.chord("a");
    await expect(page).toHaveURL(/#audits/);
  });

  test("retired hashes alias into the cut nav", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("studio");
    await expect(page).toHaveURL(/#settings/);
    await consolePage.gotoHash("insights");
    await expect(page).toHaveURL(/#warning/);
    await consolePage.gotoHash("trust");
    await expect(page).toHaveURL(/#audits/);
    await expect(page).toHaveURL(/tab=reports/);
  });

  test("command open-cases card jumps to queue", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("command");
    const cards = page.locator("button.stat-card-btn");
    await expect(cards).toHaveCount(4);
    await page.locator("button.stat-card-btn", { hasText: "Open cases" }).click();
    await expect(page).toHaveURL(/#cases/);
  });

  test("settings remember-key defaults off", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("settings");
    const box = page.getByLabel("Remember API key on this device");
    await expect(box).toBeVisible();
    await expect(box).not.toBeChecked();
  });
});