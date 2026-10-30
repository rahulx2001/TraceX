#!/usr/bin/env node
/** Render a fresh production build against the real, isolated API. No model calls. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";
import { build } from "vite";

const dashboard = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.dirname(dashboard);
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "tracex-signin-browser-"));
const dist = path.join(temporary, "ui");
const visuals = path.join(os.tmpdir(), "tracex-entry-ui-review");
const python = process.env.E2E_PYTHON || path.join(root, ".venv-hackathon/bin/python");
const children = [];
let browser;
let passed = false;
const missingRouteControl = process.argv.includes("--missing-route-control");

async function startServer(mode) {
  console.log(`Starting isolated ${mode}-mode API…`);
  const listener = net.createServer();
  await new Promise(resolve => listener.listen(0, "127.0.0.1", resolve));
  const port = listener.address().port;
  await new Promise(resolve => listener.close(resolve));
  const state = path.join(temporary, mode);
  const child = spawn(python, [path.join(dashboard, "scripts/signin-test-server.py"),
    "--state", state, "--dist", dist, "--port", String(port), "--mode", mode], { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
  children.push(child);
  let output = "", startupError, lastHealth = "unreachable";
  child.once("error", error => { startupError = error; });
  for (const stream of [child.stdout, child.stderr]) stream.on("data", data => { output = (output + data).slice(-8000); });
  const base = `http://127.0.0.1:${port}`;
  for (let attempt = 0; attempt < 150; attempt++) {
    if (startupError || child.exitCode !== null) throw startupError || new Error(`API did not start: ${output}`);
    try {
      const health = await fetch(`${base}/health`, { signal: AbortSignal.timeout(1000) });
      if (health.ok) return { base, fixture: JSON.parse(await fs.readFile(path.join(state, "fixture.json"), "utf8")) };
      lastHealth = `${health.status}: ${await health.text()}`;
    } catch { /* allow bounded startup */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`API startup timed out (${lastHealth}): ${output}`);
}

async function isolatedPage(base) {
  const context = await browser.newContext();
  await context.route("**/*", route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
  const page = await context.newPage();
  return { context, page };
}

async function selectDraft(page, fixture) {
  await page.goto(`${new URL(page.url()).origin}/ui/#safety-campaigns?tab=investigate`);
  await page.getByLabel("Select safety campaign").selectOption(fixture.campaign_id);
  await page.getByRole("button", { name: "Meta investigation", exact: true }).click();
  await page.getByLabel("Recorded investigations").selectOption(fixture.run_id);
  await expect(page.getByTestId("investigation-result")).toBeVisible();
}

async function submitReview(page) {
  await page.getByLabel("Draft decision").selectOption("accepted_for_investigation");
  await page.getByLabel("Evidence review note").fill("Authentication test only: reviewed this fictional source and manual draft.");
  await page.getByLabel("I reviewed the original sources and the draft interpretations.").check();
  const response = page.waitForResponse(r => r.url().endsWith("/review") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Record draft review", exact: true }).click();
  return response;
}

try {
  await build({ root: dashboard, build: { outDir: dist, emptyOutDir: true },
    plugins: missingRouteControl ? [{ name: "missing-signin-negative-control", enforce: "pre",
      transform(source, id) {
        if (id !== path.join(dashboard, "src/App.jsx")) return;
        const changed = source.replace(/^\s*\{ id: "signin", label: "Sign in", route: SignIn \},\r?\n/m, "");
        if (changed === source) throw new Error("Negative control could not find the sign-in registry entry");
        return changed;
      } }] : [] });
  if (missingRouteControl) console.log("NEGATIVE CONTROL: sign-in registry entry omitted only from this temporary build; browser assertions must fail.");
  browser = await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {});
  const auth = await startServer("auth");
  const { context, page } = await isolatedPage(auth.base);
  await page.goto(`${auth.base}/ui/#safety-campaigns?tab=investigate`);
  await expect(page.getByTestId("signin-page")).toBeVisible();
  await fs.mkdir(visuals, { recursive: true });
  await page.screenshot({ path: path.join(visuals, "signin.png"), fullPage: true });
  await page.getByRole("button", { name: /Have an operator API key/ }).click();
  await page.getByLabel("Operator API key", { exact: true }).fill("deliberately-invalid-key");
  await page.getByRole("button", { name: "Verify & Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("not accepted");
  await expect(page.getByTestId("signin-page")).toBeVisible();
  await page.getByLabel("Operator API key", { exact: true }).fill(auth.fixture.api_key);
  await page.getByRole("button", { name: "Verify & Continue", exact: true }).click();
  await expect(page.getByLabel("Select safety campaign")).toBeVisible();
  assert.equal(await page.evaluate(() => localStorage.getItem("frontline_api_key")), null, "key must not persist without opt-in");
  await selectDraft(page, auth.fixture);
  assert.equal((await submitReview(page)).status(), 403, "operator cannot review a real-campaign draft");
  await expect(page.getByRole("alert").first()).toContainText(/permission|forbidden|supervisor|case:write/i);
  console.log("PASS: clean browser reaches credential entry, rejects invalid key and refuses unauthorized review.");

  await page.goto(`${auth.base}/ui/#signin?next=safety-campaigns%3Ftab%3Dinvestigate`);
  await page.getByRole("button", { name: /Have a supervisor session/ }).click();
  await page.getByLabel("Supervisor session", { exact: true }).fill(auth.fixture.supervisor_token);
  await page.getByRole("button", { name: "Use session", exact: true }).click();
  await expect(page.getByLabel("Select safety campaign")).toBeVisible();
  const cookie = (await context.cookies()).find(c => c.name.endsWith("frontline_session"));
  assert.equal(cookie?.httpOnly, true, "supervisor credential must become an HttpOnly cookie");
  await selectDraft(page, auth.fixture);
  assert.equal((await submitReview(page)).status(), 200, "issued supervisor can record the review");
  await expect(page.getByText(/Review: accepted for investigation/)).toBeVisible();
  const saved = await (await context.request.get(`${auth.base}/api/safety-campaigns/${auth.fixture.campaign_id}/investigations`)).json();
  assert.equal(saved.runs.find(r => r.run_id === auth.fixture.run_id).review.actor, "browser-test-supervisor");
  console.log("PASS: issued supervisor session signs in and records the permitted review with the actual actor.");
  const { runReportHandoffTest } = await import("./report-handoff.test.mjs");
  await runReportHandoffTest({ page, context, base: auth.base, fixture: auth.fixture });
  const { runInvestigationUiTest } = await import("./investigation-ui.test.mjs");
  await runInvestigationUiTest({ page, context, base: auth.base, fixture: auth.fixture });
  await context.close();

  const open = await startServer("open");
  const local = await isolatedPage(open.base);
  await local.page.goto(`${open.base}/ui/#demo`);
  await expect(local.page.getByRole("heading", { name: "From an owner report to a reviewable investigation" })).toBeVisible();
  await local.page.screenshot({ path: path.join(visuals, "judge-entry.png"), fullPage: true });
  await local.page.goto(`${open.base}/ui/#signin`);
  await expect(local.page.getByTestId("signin-page")).toBeVisible();
  await expect(local.page.getByRole("button", { name: /Have a supervisor session/ })).toBeVisible();
  await local.page.getByRole("button", { name: "Open local console →", exact: true }).click();
  await expect(local.page.getByRole("heading", { name: "From an owner report to a reviewable investigation" })).toBeVisible();
  const principal = await (await local.context.request.get(`${open.base}/api/frontline/auth/verify`)).json();
  assert.equal(principal.role, "agent", "open local access must not grant supervisor authority");
  console.log("PASS: open mode needs no credentials, still renders sign-in, and retains agent authority.");
  const { runVoiceUiTest } = await import("./voice-ui.test.mjs");
  await runVoiceUiTest({ page: local.page, context: local.context, base: open.base, fixture: open.fixture });
  await local.context.close();
  passed = true;
} finally {
  await browser?.close();
  for (const child of children) child.kill("SIGTERM");
  await Promise.all(children.map(child => child.exitCode !== null ? Promise.resolve() : new Promise(resolve => {
    const timeout = setTimeout(() => { child.kill("SIGKILL"); resolve(); }, 3000);
    child.once("exit", () => { clearTimeout(timeout); resolve(); });
  })));
  if (passed) await fs.rm(temporary, { recursive: true, force: true });
  else console.error(`Isolated failure artifacts: ${temporary}`);
}
