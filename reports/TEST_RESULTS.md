# Test results: current tree

Date: 2026-10-28 (IST). Repo: `/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool`.
Branch: `main`. Python: 3.12.13 (`.venv-hackathon`). pytest: 8.4.2.
pyarrow: 22.0.0. Node: 25.1.0. Playwright: 1.62.1 with installed Google Chrome.

This file records what was actually run. No backend test was deleted, skipped, or
xfailed to obtain the result below. The previous Oct 26 audit (four failures,
one deselected cluster test) is superseded; its raw logs remain in
`reports/tests_after_cleanup.txt`, `reports/tests_individual_failures.txt`,
`reports/slow_test_check.txt` and `reports/slow_test_dedicated.txt` for history.
Three browser-spec assertions that contradicted the hardened product were
updated to test the intended behavior; the changes and reasons are documented in
[`e2e/E2E_RESULTS_2026-10-28.md`](e2e/E2E_RESULTS_2026-10-28.md).

## Backend suite — complete, no deselection

Exact command:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m pytest \
  -q -rfE -p no:cacheprovider
```

Result (`reports/tests_current_full_final.txt`):

```text
1794 passed, 1 warning in 575.27s (0:09:35)
EXIT:0
```

- **No tests deselected, skipped or xfailed.** The 5,005-record cluster rebuild
  test now runs and passes in about 1.8 seconds as part of the suite.
- 1 warning: the installed Starlette/FastAPI test client deprecation notice.
  It is a warning, not a failure.
- The four Oct 26 failures (`test_live_corrections`,
  `test_live_handoff_outcomes`, `test_live_voice_lifecycle`,
  `test_voice_audit_fixes`) pass in this run.

## Documented developer command (`make test`)

`make test` builds the dashboard, verifies the pinned MiniLM artifact, then runs
`tests/frontline/` against a fresh temp database with a stricter 30-second
per-test timeout:

```bash
make test
```

Result (`reports/make_test_current.txt`):

```text
1755 passed, 1 warning in 759.59s (0:12:39)
EXIT:0
```

The dashboard production build and MiniLM verification also passed inside this
target. The remaining 39 backend tests (`tests/test_voice_invariants.py` and
`tests/real_hindi/`) are covered by the full-suite run above. No failures,
skips, or deselections in either run.

## Dashboard and browser end-to-end

Production build:

```bash
cd dashboard && npm run build
```

Passed (Vite 8.2.1). Existing bundle-size and ineffective-dynamic-import
warnings remain.

Voice ranking assertions:

```bash
cd dashboard && npm run test:tts-voice
```

Passed. Novelty voices are excluded, exact-locale voices outrank other English
variants, and an explicit operator voice choice wins.

Full Playwright suite against a clean-checkout judge server (real Chrome):

```bash
cd dashboard
BASE_URL=http://127.0.0.1:8140 \
TRACEX_JUDGE_DATA=<judge-v2 data dir> \
E2E_API_KEY=<operator key> \
PLAYWRIGHT_CHANNEL=chrome \
npx playwright test --reporter=list
```

Result: **54 passed** across
`api.aggressive.spec.js` (14), `api.deep-sweep.spec.js` (10),
`ui.console.spec.js` (17), `ui.interactions.spec.js` (5),
`ui.loops.spec.js` (7) and `judge.workflow.spec.js` (1).

The judge workflow verifies the operator key, the recorded live-proof panel,
supervisor token exchange into an HttpOnly cookie, takeover and release, with no
page exceptions. The API specs verify the auth gate, service-principal denials,
SSRF rejection, simulated-case filtering, note-author derivation and the audit
export manifest. Commands, per-spec counts and logs are in
[`e2e/E2E_RESULTS_2026-10-28.md`](e2e/E2E_RESULTS_2026-10-28.md).

## No-key AI-layer smoke

```bash
PY="$PWD/.venv-hackathon/bin/python" PORT=8131 bash scripts/ai_v2_smoke.sh
```

All expected routes and status codes matched; `EXIT:0`
(`reports/ai_v2_smoke_current.txt`).

## Defect pipeline inputs

The NHTSA parquet inputs are not committed. The portable preparation command
was run against the official flat files:

```bash
.venv-hackathon/bin/python -m scripts.defect_prepare_inputs \
  --out-dir data/defect/hackathon --complaints-limit 5000 --recalls-limit 5000
```

Wrote 5,000 complaint rows and 5,000 recall rows with source SHA-256 values and
a manifest (`reports/defect_inputs_prepare.txt`). The classifier dry run made no
network call and estimated 4,516 input tokens over 3 batches
(`reports/defect_dry_run_real.txt`). Export-only wrote 5,000 rows and preserved
`model`, `prompt_version` and `taxonomy_sha256`
(`reports/defect_export_real.txt`). Two regression tests cover preparation and
the missing-input message (`tests/frontline/ai_layer/test_defect_inputs.py`).

## Not run / still unverified

- **Docker image execution**: Docker is unavailable on this machine. The
  workflow YAML, Compose file and shell syntax were checked; a CI image run is
  still required.
- **Live vision / SAM image analysis**: only live Muse Spark text intake has
  been called. Photo upload, validation, storage and attachment run locally;
  remote vision analysis remains unverified.
- **Live defect classification at scale**: the dry run and export are verified
  locally; the 18,998-batch plan is explicitly outside the demo budget.
- **Meta spend during this verification pass**: none. The recorded live proof
  artifact from the earlier authorized run is reused.
