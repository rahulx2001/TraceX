import { expect } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import test from "node:test";
import assert from "node:assert/strict";

export async function runMlEvidenceUiTest({ page, base }) {
  await page.goto(`${base}/ui/#defect-level`);
  const section = page.getByTestId("ml-improvement-evidence");
  await expect(section).toBeVisible();
  await expect(section.getByRole("note")).toHaveText("Prospective 2027-2028 test reserved. No improved score has been demonstrated. Human semantic validation remains pending.");
  await expect(section.getByTestId("prospective-custody")).toContainText("tamper-evident, not enforced access control");
  await expect(section.getByText(/minimum 25 campaigns; no data collected yet/)).toBeVisible();
  await expect(section.getByText(/Frozen mode: baseline replication/)).toBeVisible();
  await expect(section.getByText("Retrospective, model-labelled, not production-validated", { exact: true })).toBeVisible();
  await expect(section.getByText(/80.0% mature-alert precision and 70.0% campaign recall/)).toBeVisible();
  await expect(section.getByText(/These targets have not been demonstrated/)).toBeVisible();
  await expect(section.getByText(/0\/300 review rows labelled/)).toBeVisible();
  const table = section.getByRole("table");
  await expect(table.getByRole("row")).toHaveCount(9);
  await expect(table.getByRole("cell", { name: "22/41", exact: true })).toBeVisible();
  await expect(table.getByRole("cell", { name: "14/31", exact: true })).toBeVisible();
  await expect(table.getByRole("cell", { name: "5/8", exact: true })).toBeVisible();
  await section.getByText("Evidence integrity", { exact: true }).click();
  await expect(section.getByText("reports/improvement/results.json", { exact: true })).toBeVisible();
  const folder = process.env.ML_UI_ARTIFACT_DIR || path.join(os.tmpdir(), "tracex-ml-evidence-review");
  await fs.mkdir(folder, { recursive: true });
  await section.getByRole("heading", { name: "ML evidence and research targets" }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(folder, "desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await section.getByRole("heading", { name: "ML evidence and research targets" }).scrollIntoViewIfNeeded();
  await expect(section).toBeVisible();
  const fits = await section.evaluate(el => el.getBoundingClientRect().right <= innerWidth + 1);
  expect(fits).toBe(true);
  const intervalsFit = await section.locator("td:last-child").evaluateAll(cells => cells.every(cell => cell.getBoundingClientRect().right <= innerWidth + 1));
  expect(intervalsFit).toBe(true);
  await page.screenshot({ path: path.join(folder, "mobile.png"), fullPage: true });
  await page.setViewportSize({ width: 1280, height: 720 });
  console.log("PASS: ML evidence renders source-checked denominators, intervals, unachieved targets and unavailable human accuracy; mobile section fits.");
}

// Direct node --test execution runs the real isolated browser harness. When that
// harness imports the helper, no nested test process is registered.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  test("prospective evidence renders in the real dashboard", { timeout: 180000 }, async () => {
    const script = fileURLToPath(new URL("./assert-signin-reachable.mjs", import.meta.url));
    const child = spawn(process.execPath, [script], { stdio: "inherit", env: process.env });
    const code = await new Promise((resolve, reject) => {
      child.once("error", reject);
      child.once("exit", resolve);
    });
    assert.equal(code, 0, "Browser harness must pass, including the ML evidence assertions");
  });
}
