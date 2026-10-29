#!/usr/bin/env node
/**
 * #signin must stay reachable with an open console: it is the only place a
 * supervisor session can be pasted, and supervisor-only actions (Analyze
 * evidence, approvals) 403 without it. Guards against re-adding a bounce
 * from signin/signup to the command center.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = fs.readFileSync(path.resolve(__dirname, "..", "src", "App.jsx"), "utf8");

function fail(msg) {
  console.error("FAIL:", msg);
  process.exitCode = 1;
}

// A redirect that fires on the signin route while the console is open.
const bounce = /demoOpenConsole\s*&&\s*\(\s*route\s*===\s*"signin"/;
if (bounce.test(app)) {
  fail("App.jsx bounces #signin away when the console is open; supervisor sign-in is unreachable.");
} else {
  console.log("OK: #signin is not bounced away.");
}

// The route must still be recognised and rendered, not unknown.
if (!/route\s*===\s*"signin"/.test(app)) {
  fail("App.jsx no longer recognises the signin route.");
} else {
  console.log("OK: signin route recognised.");
}
