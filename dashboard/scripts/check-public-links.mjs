/** Fresh anonymous browser check. No saved profile, account or POST requests. */
import { chromium } from "playwright";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { targets, summarize } from "./public-link-scope.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const manifestPath = resolve(root, "reports/hackathon/submission_links.json");
const contents = readFileSync(manifestPath);
const manifest = JSON.parse(contents);
const results = [];
const browser = await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {});
const output = resolve(root, "reports/hackathon/link_checks");
mkdirSync(output, { recursive: true });
try {
  for (const [kind, url] of targets(manifest)) {
    if (!url) { results.push({ kind, status: "pending_missing_url" }); continue; }
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || parsed.username || parsed.password) throw new Error(`Public ${kind} URL must use HTTPS without embedded credentials`);
    const context = await browser.newContext({ storageState: { cookies: [], origins: [] }, serviceWorkers: "block" });
    await context.route("**/*", route => ["GET", "HEAD"].includes(route.request().method()) ? route.continue() : route.abort());
    try {
      const page = await context.newPage();
      const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
      const status = response?.status() ?? null;
      const title = await page.title();
      const visible = await page.locator("body").innerText();
      const signIn = await page.getByRole("link", { name: "Sign in", exact: true }).count();
      const loggedIn = (await context.cookies()).find(c => c.name === "logged_in")?.value;
      const source = ["repository", "source_commit"].includes(kind);
      const accessible = status >= 200 && status < 300 && visible.length > 100 &&
        (!source || (signIn > 0 && loggedIn !== "yes" && visible.includes("TraceX"))) &&
        (kind !== "source_commit" || (page.url().replace(/\/$/, "") === url && visible.includes("README.md")));
      await page.screenshot({ path: resolve(output, `${kind}.png`), fullPage: false });
      results.push({ kind, url, final_url: page.url(), http_status: status, title,
        status: accessible ? "anonymous_page_access_verified" : "access_not_established",
        fresh_browser_context: true, repository_login_link_visible: source ? signIn > 0 : undefined,
        note: kind === "hosted_demo" ? "Page accessibility only; this does not certify authenticated workflow completion." : undefined });
    } catch (error) { results.push({ kind, url, status: "access_check_failed", error: error.message }); }
    finally { await context.close(); }
  }
} finally { await browser.close(); }
const body = { checked_at: new Date().toISOString(), manifest_sha256: createHash("sha256").update(contents).digest("hex"),
  browser: "fresh Playwright context; no user cookies or credentials; GET/HEAD only", results,
  ...summarize(manifest, results) };
writeFileSync(resolve(output, "results.json"), JSON.stringify(body, null, 2)+"\n");
console.log(JSON.stringify(body, null, 2));
if (results.some(r => ["access_check_failed", "access_not_established"].includes(r.status))) process.exitCode = 1;
