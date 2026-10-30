// Real local UI actions with explicitly labelled replay of real Meta outputs.
// --check performs read-only browser validation and captures a screenshot.
import { chromium } from "playwright";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const check = process.argv.includes("--check");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:8768";
const root = resolve("..");
const outDir = resolve(root, "reports/hackathon/investigation_demo");
mkdirSync(outDir, { recursive: true });
const proof = JSON.parse(readFileSync(resolve(root, "reports/hackathon/investigation_followup_smoke.json"), "utf8"));
const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 },
  ...(check ? {} : { recordVideo: { dir: outDir, size: { width: 1440, height: 1000 } } }) });
const errors = [];
let page;
try {
  page = await context.newPage(); page.on("pageerror", e => errors.push(e.message));
  const video = page.video();
  await page.goto("/ui/#safety-campaigns");
  await page.getByRole("button", { name: "Meta investigation", exact: true }).waitFor({ timeout: 20000 });
  const light = page.getByRole("button", { name: "Light", exact: true });
  if (await light.count()) await light.click();
  if (check) {
    await page.getByRole("button", { name: "Meta investigation", exact: true }).click();
    await page.getByLabel("Recorded investigations").selectOption(proof.initial.run_id);
    await page.getByTestId("investigation-result").scrollIntoViewIfNeeded();
    await page.screenshot({ path: resolve(outDir, "investigation-ui.png"), fullPage: true });
    const text = await page.getByTestId("investigation-result").innerText();
    if (!text.includes("Recorded live Meta output on synthetic data") || !text.includes("Sourced observations") || !text.includes("installation record")) throw new Error("Missing expected evidence/replay/question UI");
    await page.getByText("Independent review and measurement", { exact: true }).click();
    const popupEvent = page.waitForEvent("popup");
    await page.getByRole("button", { name: "Fuel / propulsion review ↗", exact: true }).click();
    const popup = await popupEvent;
    await popup.getByRole("heading", { name: "Independent evidence review" }).waitFor();
    await popup.waitForFunction(() => document.getElementById("progressText")?.textContent.includes("reviewed"));
    if (!(await popup.locator("#progressText").innerText()).startsWith("0 / 100")) throw new Error("Blind review was not blank");
    await popup.close();
    if (errors.length) throw new Error(errors.join("; "));
    writeFileSync(resolve(outDir, "browser_check.json"), JSON.stringify({ ok: true, page_errors: errors,
      checks: ["recorded Meta result", "source observations", "missing-record question", "authenticated review document", "zero prefilled labels"] }, null, 2));
    console.log("Browser checks passed; screenshot saved.");
  } else {
    const started = Date.now();
    async function caption(title, text) {
      await page.evaluate(({title, text}) => {
        let box = document.getElementById("demo-caption");
        if (!box) { box = document.createElement("div"); box.id = "demo-caption";
          box.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#102a27;color:#fff;padding:18px 38px;font:18px/1.45 system-ui;pointer-events:none;border-top:3px solid #7cbaa0";
          document.body.append(box); }
        box.replaceChildren();const heading=document.createElement("strong");heading.textContent=title;const p=document.createElement("div");p.textContent=text;box.append(heading,p);
      }, {title,text});
    }
    async function until(seconds) { const left = started+seconds*1000-Date.now(); if (left > 0) await page.waitForTimeout(left); }
    async function section(name) { await page.getByRole("button", { name, exact: true }).click(); }
    async function workshop(kind, button) {
      await page.getByLabel("Next workshop action").selectOption(kind);
      await page.getByRole("button", { name: "Fill demo example", exact: true }).last().click();
      await page.getByRole("button", { name: `Save demo: ${button}`, exact: true }).click();
      await page.getByRole("status").filter({ hasText: "Update saved" }).waitFor();
    }
    await caption("TraceX · From an owner report to repair evidence", "Synthetic walkthrough. New work: sourced Meta investigation, follow-up, reviewed campaign evidence. Operations foundation reused.");
    await until(18);
    await section("Meta investigation");
    await page.getByLabel("Recorded investigations").selectOption(proof.initial.run_id);
    await page.getByTestId("investigation-result").scrollIntoViewIfNeeded();
    await caption("1 · Understand the report", "Recorded live Muse Spark Open output on fictional Hinglish input. Each observation links to the original source sentence.");
    await page.getByRole("heading", { name: "Sourced observations", exact: true }).scrollIntoViewIfNeeded();
    await until(40);
    await page.getByRole("heading", { name: "Resolve missing information", exact: true }).scrollIntoViewIfNeeded();
    await caption("2 · Ask for the evidence that is missing", "Meta selects the missing information to ask for. An unknown part stays unknown; a symptom is not a diagnosis.");
    await until(57);
    await section("Vehicle traceability");
    await page.getByRole("button", { name: /DEMO-CAR-010/ }).click();
    await page.getByRole("heading", { name: "Verify or correct installed-part evidence" }).scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Fill demo example", exact: true }).click();
    await caption("3 · A reviewer establishes the lot link", "Simulated engineering review of a fictional installation record. The model does not approve or invent the supplier, part or lot.");
    await until(70);
    await page.getByRole("button", { name: "Save demo: review installed part", exact: true }).click();
    await page.getByRole("status").filter({ hasText: "Update saved" }).waitFor();
    await until(78);
    await section("Meta investigation");
    await page.getByLabel("Recorded investigations").selectOption(proof.followup.run_id);
    await page.getByRole("heading", { name: "Evidence lookups", exact: true }).scrollIntoViewIfNeeded();
    await caption("4 · Update the investigation from the new record", "Recorded follow-up: Meta chose the installed-part lookup and updated the cited draft. Tool access is read only.");
    await until(100);
    await page.getByRole("button", { name: "Open reviewed workshop actions →", exact: true }).click();
    await page.getByLabel("Next workshop action").scrollIntoViewIfNeeded();
    await caption("5 · Record the authorized work", "Fictional recovery, inspection and replacement records. The replacement part must match the reviewed repair specification.");
    await workshop("recovery", "record recovery");
    await workshop("inspection", "record inspection");
    await until(113);
    await workshop("repair", "record part replacement");
    await until(128);
    await caption("6 · Verification and follow-up are separate", "Simulated verification and owner follow-up are recorded before reviewer resolution. Unresolved vehicles remain visible.");
    await workshop("verify_repair", "verify repair");
    await until(137);
    await workshop("followup", "record follow-up");
    await workshop("resolve", "review vehicle resolution");
    await until(150);
    await section("Evidence & close-out");
    await page.getByRole("heading", { name: "Evidence timeline", exact: true }).scrollIntoViewIfNeeded();
    await caption("7 · Export a reviewable evidence packet", "Source snapshots, actual Meta tool choices, campaign actions and repair records. No external owner message was sent.");
    const downloadEvent = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export complete packet ↓", exact: true }).click();
    await (await downloadEvent).saveAs(resolve(outDir, "demo-evidence-packet.json"));
    await until(169);
    await section("Overview");
    await page.getByRole("heading", { name: "Safety campaigns", exact: true }).scrollIntoViewIfNeeded();
    await caption("Built to be checked", "Live Meta integration is recorded. Independent human labels and reviewer measurements are pending. No above-86% or accident-prevention claim.");
    await until(180);
    if (errors.length) throw new Error(errors.join("; "));
    await page.close(); await context.close();
    await video.saveAs(resolve(outDir, "workflow.webm"));
    writeFileSync(resolve(outDir,"recording.json"),JSON.stringify({ok:true,synthetic:true,recorded_meta:true,live_model_calls_during_recording:0,
      human_study_results_created:0,planned_duration_seconds:180,wall_elapsed_seconds:(Date.now()-started)/1000,page_errors:errors},null,2));
    console.log("Recorded the real UI workflow with labelled synthetic/replayed evidence.");
  }
} catch (error) {
  if (page) await page.screenshot({ path: resolve(outDir, "browser-failure.png"), fullPage: true }).catch(()=>{});
  throw error;
} finally { await context.close(); await browser.close(); }
