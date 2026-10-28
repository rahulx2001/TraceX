/**
 * Sidebar navigation, settings key save, export, enterprise, platform.
 */
import { test, expect } from "@playwright/test";
import { apiKey } from "./fixtures/env.js";
import { ConsolePage } from "./pages/ConsolePage.js";

const NAV = [
  ["Voice agent", /#call/],
  ["Live console", /#console/],
  ["Case queue", /#cases/],
  ["Early warning", /#warning/],
  ["Trust", /#audits/],
  ["Platform", /#platform/],
  ["Settings", /#settings/],
  ["Command center", /#command/],
];

test.describe("UI interactions", () => {
  test("sidebar nav clicks visit every primary item", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    await consolePage.gotoHash("command");
    await expect(page.getByRole("button", { name: "Command center", exact: true })).toBeVisible();

    const nav = page.getByRole("complementary", { name: "Primary" });
    for (const [label, hash] of NAV) {
      await nav.getByRole("button", { name: label, exact: true }).click();
      await expect(page).toHaveURL(hash);
      await expect(page.getByText("HTTP 401")).toHaveCount(0);
    }
  });

  test("pasting an operator key into settings loads packs (no 401)", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.gotoHash("settings");
    await page.getByLabel("Pilot API key", { exact: true }).fill(apiKey());
    const packs = page.waitForResponse(
      (res) => res.url().includes("/api/packs") && res.request().method() === "GET",
    );
    await page.getByRole("button", { name: "Save", exact: true }).click();
    const res = await packs;
    expect(res.status(), "packs after operator key save").toBeLessThan(400);
    await expect(page.getByRole("heading", { name: "Pilot API key" })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("case queue export button does not 401", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    await consolePage.gotoHash("cases");
    const exportBtn = page.getByRole("button", { name: "Export CSV" });
    await expect(exportBtn).toBeVisible();
    const exported = page.waitForResponse((res) => res.url().includes("/cases/export"));
    await exportBtn.click();
    const res = await exported;
    expect(res.status(), res.url()).toBeLessThan(400);
  });

  test("enterprise ops load does not 500/401", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    const bad = [];
    page.on("response", (res) => {
      if (
        res.url().includes("/api/frontline/enterprise/") &&
        (res.status() === 401 || res.status() >= 500)
      ) {
        bad.push(`${res.status()} ${res.url()}`);
      }
    });
    await consolePage.gotoHash("enterprise");
    await expect(page).toHaveURL(/#platform/);
    await expect(page.getByRole("heading", { name: "Platform", exact: true })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Ops", exact: true })).toHaveAttribute("aria-selected", "true");
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("platform OS loads without 401", async ({ page }) => {
    const consolePage = new ConsolePage(page);
    await consolePage.seedKey();
    const bad = [];
    page.on("response", (res) => {
      if (res.url().includes("/api/v3/") && res.status() === 401) {
        bad.push(res.url());
      }
    });
    await consolePage.gotoHash("platform");
    await expect(page.getByRole("heading", { name: "Platform", exact: true })).toBeVisible();
    await expect(page.getByRole("tablist", { name: "Platform OS" })).toBeVisible();
    expect(bad).toEqual([]);
  });
});
