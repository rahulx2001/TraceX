// Record the real judge UI after authenticating outside the recording.
// Uses a recorded live Meta proof; never calls a model or records credentials.
import { chromium } from "playwright";
import { readFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";

const dataRoot = process.env.TRACEX_JUDGE_DATA;
if (!dataRoot) throw new Error("Set TRACEX_JUDGE_DATA to an isolated judge-v2 data directory");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:8000";
const out = resolve(process.env.TRACEX_RECORD_OUT || "../reports/hackathon/demo-draft.webm");
mkdirSync(resolve(out, ".."), { recursive: true });
const session = JSON.parse(readFileSync(join(dataRoot, "supervisor_token.json"), "utf8")).token;
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });
const context = await browser.newContext({ baseURL, viewport: { width: 1280, height: 900 },
  recordVideo: { dir: resolve(out, ".."), size: { width: 1280, height: 900 } } });
try {
  const login = await context.request.post("/api/frontline/auth/session/exchange", { data: { token: session } });
  if (!login.ok()) throw new Error("Supervisor session rejected");
  const page = await context.newPage();
  const video = page.video();
  async function caption(text) {
    await page.evaluate((words) => {
      let box = document.getElementById("recording-caption");
      if (!box) {
        box = document.createElement("div"); box.id = "recording-caption";
        box.style.cssText = "position:fixed;bottom:0;left:0;right:0;padding:18px 28px;background:rgba(0,0,0,.94);color:#fff;font:20px/1.4 system-ui;z-index:99999;pointer-events:none;white-space:pre-line;border-top:2px solid #bbb";
        document.body.appendChild(box);
      }
      box.textContent = words;
    }, text);
  }
  async function hold(seconds) { await page.waitForTimeout(seconds * 1000); }
  await page.goto("/ui/#demo");
  await caption("TraceX • Indie developer • Build for Your World\nAn automotive quality intake prototype. The operations platform is reused; examples in this draft are synthetic.");
  await hold(20);
  await page.getByRole("button", { name: "View recorded live proof" }).click();
  const result = page.getByTestId("meta-workflow-result");
  await result.waitFor(); await result.scrollIntoViewIfNeeded();
  await caption("Recorded live Muse Spark result • synthetic Hindi complaint\nThis is the actual saved API result from 28 October. Viewing it makes no new model call.");
  await hold(25);
  await caption("Meta adds a readable English complaint beside the local glossary result.\nVehicle facts remain grounded in the original text. Local safety rules and human review retain authority.");
  await hold(20);
  await page.getByText("View proposed and accepted facts", { exact: true }).click();
  await caption("The accepted output is linked to its original intake event.\nThe exported ledger actions can be checked locally. A valid chain proves record integrity, not the truth of a complaint.");
  await hold(25);
  await page.goto("/ui/#cases");
  await caption("Case review • fixture and simulated data\nThe reused case queue gives a quality engineer a place to review complaints. These rows do not establish real-fleet effectiveness.");
  await hold(20);
  const started = await context.request.post("/api/interactions/start?channel=simulated");
  if (!started.ok()) throw new Error("Synthetic contact did not start");
  const interaction = (await started.json()).interaction_id;
  await page.goto(`/ui/#console?id=${interaction}`);
  await page.getByRole("button", { name: "Take over", exact: true }).waitFor();
  await caption("Human control • a separate simulated contact\nThe issued supervisor session establishes a named operator. Takeover and release belong to the reused operations foundation.");
  await page.getByRole("button", { name: "Take over", exact: true }).click();
  await page.getByLabel("Supervisor reply").waitFor();
  await hold(22);
  await page.getByRole("button", { name: "Release to AI", exact: true }).click();
  await caption("The supervisor releases the contact back to the agent.\nThese are real browser actions on the local judge server; no external message is sent.");
  await hold(19);
  await context.request.post(`/api/interactions/${interaction}/hangup`);
  await page.goto("/ui/#demo");
  await page.getByRole("button", { name: "View recorded live proof" }).click();
  await page.getByTestId("meta-workflow-result").scrollIntoViewIfNeeded();
  await caption("Event contribution: verified Meta text intake, stricter grounding, and a reliable judge path.\nHistorical recall statistics are deterministic; Hindi examples are synthetic; human defect-label accuracy remains unmeasured.");
  await hold(26);
  await page.close(); await context.close();
  await video.saveAs(out);
  console.log("Recorded draft:", out);
} finally {
  await context.close(); await browser.close();
}
