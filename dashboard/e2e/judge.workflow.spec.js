import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const dataRoot = process.env.TRACEX_JUDGE_DATA;
const tokenFile = dataRoot ? join(dataRoot, "supervisor_token.json") : "";
test.skip(
  !dataRoot || !existsSync(tokenFile),
  "Set TRACEX_JUDGE_DATA to a judge directory that contains supervisor_token.json (scripts/judge_setup.sh)",
);

test("judge operator key and supervisor session work in the browser", async ({ browser }) => {
  const key = readFileSync(join(dataRoot, "operator_api_key"), "utf8").trim();
  const token = JSON.parse(readFileSync(tokenFile, "utf8")).token;
  const baseURL = process.env.BASE_URL || "http://127.0.0.1:8000";
  const operator = await browser.newContext({ baseURL });
  // The sign-in page is intentionally gone from this build. Operators enter
  // the issued key on Settings; seed it the same way that page stores it.
  await operator.addInitScript((value) => {
    localStorage.setItem("frontline_api_key", value);
  }, key);
  const page = await operator.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/ui/#command");
  await expect(page.getByText(/Command center/i).first()).toBeVisible();
  expect((await page.locator("body").innerText()).length).toBeGreaterThan(20);
  const principal = await operator.request.get("/api/frontline/auth/me", { headers: { "X-API-Key": key } });
  expect((await principal.json()).signed_in).toBe(false);
  await page.goto("/ui/#demo");
  await page.getByRole("button", { name: "View recorded live proof" }).click();
  await expect(page.getByTestId("meta-workflow-result")).toContainText("Recorded synthetic run");
  await expect(page.getByTestId("meta-workflow-result")).toContainText("Accepted English:");
  await expect(page.getByTestId("meta-workflow-result")).toContainText("ledger actions verified");
  await expect(page.getByRole("button", { name: "Run Meta complaint", exact: true })).toBeDisabled();
  await operator.close();

  const supervisor = await browser.newContext({ baseURL });
  // Exchange the issued supervisor token for the real httpOnly session
  // cookie. This is the endpoint the removed sign-in page used to call.
  const exchange = await supervisor.request.post("/api/frontline/auth/session/exchange", {
    data: { token },
  });
  expect(exchange.ok(), await exchange.text()).toBe(true);
  const review = await supervisor.newPage();
  review.on("pageerror", (e) => errors.push(e.message));
  await review.goto("/ui/#command");
  await expect(review.getByText(/Command center/i).first()).toBeVisible();
  const me = await supervisor.request.get("/api/frontline/auth/me");
  expect((await me.json()).role).toBe("supervisor");
  const cookies = await supervisor.cookies();
  expect(cookies.find((c) => c.name === "frontline_session")?.httpOnly).toBe(true);
  const start = await supervisor.request.post("/api/interactions/start?channel=simulated");
  expect(start.ok()).toBe(true);
  const interaction = (await start.json()).interaction_id;
  expect(interaction).toBeTruthy();
  await review.goto(`/ui/#console?id=${interaction}`);
  await expect(review.getByRole("button", { name: "Take over", exact: true })).toBeVisible();
  const takeover = review.waitForResponse((r) => r.url().endsWith(`/${interaction}/takeover`));
  await review.getByRole("button", { name: "Take over", exact: true }).click();
  expect((await takeover).ok()).toBe(true);
  await expect(review.getByLabel("Supervisor reply")).toBeVisible();
  const release = review.waitForResponse((r) => r.url().endsWith(`/${interaction}/release`));
  await review.getByRole("button", { name: "Release to AI", exact: true }).click();
  expect((await release).ok()).toBe(true);
  await expect(review.getByRole("button", { name: "Take over", exact: true })).toBeVisible();
  await supervisor.close();
  expect(errors).toEqual([]);
});
