# Test results: current HEAD after dependency cleanup

Date: 2026-10-26 (IST). Repo: `/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool`.
Branch: `hackathon/ai-layer`. Code under test: `4b70a80` plus the `pyarrow`
declarations and the demo-seed path fix (uncommitted at test time). Later
commits are documentation/report only and change no test or product logic.
Python: 3.14.7. pytest: 9.1.1. pyarrow: 22.0.0.

This file records what was actually run. No test was deleted, skipped, xfailed,
or edited. The one very slow test is deselected from the main run and recorded
separately; that is a documented **NOT RUN TO COMPLETION** item, not a pass.

## Main suite

Exact command (captured at the top of `reports/tests_after_cleanup.txt`):

```bash
python3 -m pytest -q -rfE -p no:cacheprovider \
  --deselect tests/frontline/test_cluster_builds.py::test_rebuild_clusters_assigns_records_beyond_5000
```

Result:

```text
4 failed, 1711 passed, 1 skipped, 1 deselected, 1 warning in 962.55s (0:16:02)
EXIT:1
```

- 1 skipped: `tests/frontline/test_csv_load.py::test_cli_run_anomalies_flag_is_accepted`
- 1 deselected: `tests/frontline/test_cluster_builds.py::test_rebuild_clusters_assigns_records_beyond_5000`
  (see `reports/slow_test_check.txt` and `reports/slow_test_dedicated.txt`)
- 1 warning: Starlette deprecation notice from the installed FastAPI test client,
  not a test failure.

## The four failures

Each was re-run alone on the same checkout. All four fail alone too, so they are
not order-dependent or full-suite flakiness. None was modified.

| # | Test | Observed failure | Category |
|---|---|---|---|
| F1 | `tests/frontline/test_live_corrections.py::test_correction_rejection_and_diagnostic_answer` | line 80: `meta["confirmation"]` is `"confirmed"`, test expects `"unconfirmed"` after `"Actually it's a 2018, not 2019."` | Real behavior/test-expectation mismatch. Not a missing dependency or path issue. Not fixed: changing it would change product correction semantics. |
| F2 | `tests/frontline/test_live_handoff_outcomes.py::test_disabled_investigator_is_not_applicable` | line 85: `KeyError: 'skipped'`; `InvestigatorAgent._run_sync` calls `record_action` inside the same `try` as the disabled check, so when the ledger write raises the broad `except Exception: pass` falls through and the agent runs normally | Real product bug in the disabled-agent guard. Not fixed: requires product logic change; out of this documentation/dependency cleanup. |
| F3 | `tests/frontline/test_live_voice_lifecycle.py::test_scheduled_speech_turn_and_playback_events` | line 134: `assert out["bargeNo"] is True`; the helper returns the raw utterance `"No!"` (a string) | Stale test expectation. The JavaScript helper is documented to return the retained utterance text, not a boolean. Test not edited. |
| F4 | `tests/frontline/test_voice_audit_fixes.py::test_malformed_frame_does_not_fail_the_contact` | line 194: first WebSocket frame is `{"type": "ready", "authenticated": true, "attached": true, ...}`, not `{"code": "bad_message"}` | Test/protocol ordering mismatch: the server sends a ready frame first. Test not edited. |

Individual rerun log: `reports/tests_individual_failures.txt`.

## Comparison, with caveats

| Run | Commit / environment | Result | Comparable? |
|---|---|---|---|
| Historical report | `9d2c30d`, Python 3.12 venv, pyarrow **not installed**, `--timeout 120`, same slow test deselected | 47 failed, 1650 passed, 1 skipped, 1 deselected, 30:34 | No. Different commit, different interpreter, and `pyarrow` was missing. |
| Baseline attempt at current HEAD | `4b70a80`, Python 3.14.7, pyarrow missing, no per-test timeout | **NOT COMPLETED**: aborted at 16% after ~14 min stuck in the slow cluster test (`EXIT:143`) | No count. Kept as evidence in `reports/tests_baseline_attempt.txt`. |
| Current after dependency cleanup | `4b70a80`, Python 3.14.7, pyarrow 22.0.0, slow test deselected | **4 failed, 1711 passed**, 1 skipped, 1 deselected, 16:02 | This is the current, reproducible result. |

The historical 47 failure blocks included 36 that contained
`ModuleNotFoundError: No module named 'pyarrow'` (38 occurrences in those
blocks). The dependency declaration fix makes those run; the remaining four are
unrelated pre-existing failures. Do not describe the suite as “all green”. Do not compare
the 47/1650 and 4/1711 totals as a controlled before/after experiment: the
commit and interpreter differ, and the baseline run at this HEAD did not complete.

## What was not run

- `test_rebuild_clusters_assigns_records_beyond_5000` was not run to completion.
  It is deselected from the main suite; the dedicated capped run failed with
  `Timeout (>600.0s) from pytest-timeout` after 600.37s. See
  `reports/slow_test_check.txt` and `reports/slow_test_dedicated.txt`.
- No test was run on Python 3.12 in this audit. The project's CI/Docker target
  is 3.12; this box used 3.14.7.
