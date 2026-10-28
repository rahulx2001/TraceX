# E2E Test Report

**Date:** 2026-10-28
**Duration:** 52.5s
**Status:** PASSING
**Runner:** Playwright 1.62.1, Chrome channel, 1 worker, no retries
**Target:** auth-required API on `http://127.0.0.1:8140` with a private copy of the `data/hackathon` warehouses

The process already listening on port 8000 is open mode (`auth_required: false`) and holds the DuckDB write lock on `data/hackathon/frontline.duckdb`. The 8140 server therefore ran against a temporary byte-for-byte copy of that warehouse, so write-path tests could run without touching the long-lived server. The temporary server was stopped after the run.

## Summary

- Total: 54 | Passed: 54 (100%) | Failed: 0 | Flaky: 0 | Skipped: 0

## Judge workflow

`judge operator key and supervisor session work in the browser` **passed** in 1.9s.

`TRACEX_JUDGE_DATA` pointed at `data/hackathon`. The sign-in page is intentionally absent from this build, so the spec seeds the operator key directly into `localStorage` (the same store the Settings page uses) and exchanges the supervisor token at `POST /api/frontline/auth/session/exchange` for the real HttpOnly cookie. It then verifies the recorded live-proof panel, supervisor takeover, and release.

## What the suite covers

- Unauthenticated reads and privileged mutations return 401. A query-string key is not accepted.
- The service principal cannot drain, run jobs, write packs, delete DSR data, or add case notes.
- Connector SSRF is denied to the service key (403). With bootstrap admin enabled, the admin path also rejects the SSRF URL with 400.
- The OpenAPI GET sweep returns no 5xx. Unconfigured Google OIDC fails closed. The audit export returns a SHA-256 manifest.
- Every primary hash renders. Theme, command palette, sidebar navigation, case drawer, export, and the `g` then `a` chord work.
- A keyless visit to settings asks for the pilot API key and surfaces the 401 responses. The removed sign-in page does not reappear as a gate. Pasting a key into Settings then loads packs with no 401.
- `#enterprise` lands on Platform with the Ops tab selected.
- The judge workflow verifies the operator key, the recorded live proof, supervisor session exchange, takeover, and release with no page exceptions.

## How to run

```bash
# API must already be auth-required. Do not point this at an open-mode server.
cd dashboard
export BASE_URL=http://127.0.0.1:8140
export E2E_API_KEY="$(cat ../data/hackathon/operator_api_key)"
export PLAYWRIGHT_CHANNEL=chrome
# required only for the judge workflow:
export TRACEX_JUDGE_DATA="$PWD/../data/hackathon"
npm run test:e2e
```

`make e2e` is the same command with `BASE_URL` defaulting to port 8000.

The server used for this run loaded a temporary copy of the seeded `data/hackathon` warehouses with `FRONTLINE_AUTH_REQUIRED=1`, `FRONTLINE_BOOTSTRAP_ADMIN=1`, and `AI_DEMO_ENABLED=1` (needed for the recorded proof panel). `META_API_KEY`/`MODEL_API_KEY` were explicitly empty, so no live Meta call was possible and no spend occurred. Copying the warehouse avoids the DuckDB write lock held by the port-8000 server.

## Artifacts

- Run log: `reports/e2e/e2e_8140_nosignin_2026-10-28.txt`
- Previous sign-in-gated run: `reports/e2e/e2e_8140_2026-10-28.txt`
- HTML report: `dashboard/playwright-report/index.html`
- JUnit: `dashboard/playwright-results.xml`
- JSON: `dashboard/playwright-results.json`
- Failure screenshots and video stay under `dashboard/test-results/` and are gitignored
