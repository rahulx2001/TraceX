# Finishing verification — 5 November 2026

Scope: align the current evidence statements, make a fresh offline setup
complete, and verify Report → Investigate → Review → Evidence. This work
starts from `9b81902444903ffc58b4faa3a36d2b6d9f745d33` on the
`finish/indie-release-20261105` branch.

## Changes

- The README opens with a complete clone/install/build/offline-launch path.
  The [first-run guide](getting-started.md) describes each workflow step,
  manual fallback, saved history, export and troubleshooting.
- The README, judge guide and LotGuard walkthrough use the active historical
  Round 4 result: 246/300 = 82.0%, macro-F1 0.514 over 46 labels. They identify
  the 43 AI-assisted, human-countersigned adjudications and unconfirmed
  reviewer blinding. The 85.0% Manish revision is marked as superseded assisted
  re-scoring; its original evidence is retained.
- The demo launcher reports a missing dashboard build before creating data,
  supplies the build commands, and prints the main workflow entry URL.
- Browser checks use the quickstart's `.venv` automatically. The new
  `npm run test:demo` invokes the actual offline launcher with temporary state.
  The shared report check now starts at the demo entry and verifies that a
  saved revision survives reload without creating another investigation.
  GitHub's browser job runs both the existing suite and the offline check.

## Clean setup environment

A separate Git clone was created with no `.env`, application virtual
environment, installed dashboard packages or dashboard build. A new Python
3.12 virtual environment was created without system-site packages. Package
manager download caches were available; no installed application environment
was reused.

| Component | Recorded version |
|---|---|
| OS | macOS 27.0.1, arm64 |
| Python | 3.12.13 |
| Node | 25.1.0; satisfies the documented Node 22.12+ range |
| FastAPI / Pydantic | 0.139.2 / 2.13.4 |
| DuckDB | 1.5.4 |
| pytest | 8.4.2 |
| Vite / Playwright | 8.2.1 / 1.62.1 |

The README's virtual-environment creation and constrained dependency install
completed. `npm ci --prefix dashboard` installed the locked dashboard packages;
`npm run build --prefix dashboard` generated the production UI.
`python -m pip check` reported no broken requirements. Browser execution used
the installed Playwright Chromium, temporary browser profiles and local APIs.

The first install attempt encountered the execution sandbox's network
restriction; the same command succeeded with network access. Chromium also
required permission to run outside that sandbox. These were environment
restrictions, not dependency-resolution or application failures.

## Results

| Check | Result |
|---|---|
| Fresh Python dependency install and `pip check` | Passed |
| Locked npm install and production build | Passed |
| Missing-build startup check | Passed: actionable error, exit 2, no demo state created |
| `python -m scripts.public_replay` | Passed: 48 published artifacts checked |
| `python -m scripts.review_evidence_check` | Passed: 300-record sample and 43 current disputes consistent |
| Selected Python tests | 63 passed, no skips |
| Selected JavaScript tests | 17 passed, no skips |
| `npm run test:demo` | Passed through the actual offline launcher |
| Updated `npm run test:signin` | Passed: authenticated roles, real local report/revision/reload/export, open demo, canonical LotGuard and UI edge cases |

The Python selection was:

```bash
.venv/bin/python -m pytest \
  tests/test_public_model_replay.py \
  tests/test_submission_artifacts.py \
  tests/frontline/ai_layer/test_campaign_investigator.py \
  tests/frontline/ai_layer/test_safety_campaigns.py \
  tests/frontline/test_chain_integrity.py \
  tests/frontline/test_docs_fresh.py \
  tests/frontline/test_deploy_hygiene.py -q --tb=short
```

The JavaScript selection was:

```bash
node --test dashboard/scripts/speech-draft.test.mjs \
  dashboard/scripts/voice-capture.test.mjs \
  dashboard/scripts/public-link-scope.test.mjs \
  dashboard/scripts/analytics-data.test.mjs
```

The offline browser check entered a fictional Honda City report, consent,
denial and year correction through the real local WebSocket API. It confirmed
that every customer turn was durably stored and citable, handed the original
source references to an investigation, recorded a correction, created a linked
revision, reloaded the page and checked the unchanged saved history. It then
recorded acceptance and downloaded an evidence packet containing both
investigations, their reviews, original source IDs and the correction context.
The offline actor remained `operator` with `agent` authority.

## Scope of the evidence

All new reports, campaigns and operator decisions in these tests are fictional
software fixtures. The recorded workflow uses manual fallback with provider
calls disabled. The authenticated suite also contains explicitly intercepted
browser responses for UI edge cases; those are separate from its real local
API/WebSocket workflow. No live-model correctness, microphone quality,
independent participant usefulness, productivity or accident-reduction result
was created by these checks.

The full research-model suite and Docker profiles were not rerun in this
finishing pass. Vite still reports its existing bundle-size advisory, and the
Python checks emit three upstream Starlette deprecation warnings. These do not
fail the recorded build or checks. The supported deployment remains the
documented single-process pilot.
