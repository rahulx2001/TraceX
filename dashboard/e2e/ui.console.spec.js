/**
 * Ops console shell: every primary hash, theme, palette, settings, cases.
 */
import { test, expect } from "@playwright/test";
import { ConsolePage } from "./pages/ConsolePage.js";

const NAV = [
  { hash: "command", label: /Command center/i },
  { hash: "call", label: /Voice agent/i },
  { hash: "console", label: /Live console/i },
  { hash: "cases", label: /Case queue/i },
  { hash: "warning", label: /Early warning/i },
  { hash: "audits", label: /Trust/i },
  { hash: "platform", label: /Platform/i },
  { hash: "settings", label: /Settings/i },
  { hash: "insights", label: /Early warning/i },
  { hash: "studio", label: /Settings/i },
];

test.describe("UI shell — all nav routes", () => {
  test.beforeEach(async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
  });

  test("loads command center with health", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("command");
    await expect(page.getByText(/Command center/i).first()).toBeVisible();
    const text = await page.locator("body").innerText();
    expect(text.length).toBeGreaterThan(20);
  });

  for (const item of NAV) {
    test(`nav #${item.hash} renders without crash`, async ({ page }) => {
      const consolePage = new ConsolePage(page);
      const errors = consolePage.trackErrors();
      await consolePage.gotoHash(item.hash);
      await expect(page.getByText(item.label).first()).toBeVisible();
      const txt = await page.locator("body").innerText();
      expect(txt.length, `empty page for #${item.hash}`).toBeGreaterThan(10);
      expect(errors, errors.join("\n")).toEqual([]);
    });
  }

  test("theme toggle cycles dark/light", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("command");
    await expect(page.getByText(/Command center/i).first()).toBeVisible();
    const before = await page.locator("html").getAttribute("data-theme");
    await page.keyboard.press("t");
    await expect
      .poll(async () => page.locator("html").getAttribute("data-theme"))
      .not.toBe(before);
    const theme = await page.locator("html").getAttribute("data-theme");
    expect(["dark", "light"]).toContain(theme);
  });

  test("command palette opens with mod+k", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("command");
    await expect(page.getByText(/Command center/i).first()).toBeVisible();
    await consolePage.openPalette();
  });
});

test.describe("UI Settings — API key + packs under auth", () => {
  test("settings shows pack list after key is stored", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    const packs = page.waitForResponse((res) => res.url().includes("/api/packs"));
    await consolePage.gotoHash("settings");
    const res = await packs;
    expect(res.status(), "packs with a stored key").toBeLessThan(400);
    await expect(page.getByRole("heading", { name: "Pilot API key" })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByText(/active pack|pack id/i).first()).toBeVisible();
  });

  test("without key, settings opens credential entry", async ({ page, request }) => {
    const health = await (await request.get("/health")).json();
    test.skip(health.auth_required === false, "open-mode server has no key to require");
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("settings");
    await expect(page.getByTestId("signin-page")).toBeVisible();
    await expect(page.getByRole("button", { name: /Have an operator API key/ })).toBeVisible();
  });
});

test.describe("UI Case queue — authenticated list", () => {
  test("cases page loads without hard error when key present", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    const cases = page.waitForResponse((res) => res.url().includes("/api/frontline/cases"));
    await consolePage.gotoHash("cases");
    const res = await cases;
    expect(res.status(), res.url()).toBeLessThan(400);
    await expect(page.locator("body")).not.toContainText("HTTP 401");
  });
});

test.describe("UI Command center — metrics fetch", () => {
  test("wallboard/metrics requests succeed with key", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    const metric = page.waitForResponse(
      (res) =>
        res.url().includes("/api/frontline/wallboard") ||
        res.url().includes("/api/frontline/metrics") ||
        res.url().includes("/api/frontline/usage"),
    );
    await consolePage.gotoHash("command");
    const res = await metric;
    expect(res.status(), res.url()).toBeLessThan(400);
  });
});
