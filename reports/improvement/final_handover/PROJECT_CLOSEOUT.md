# Project closeout — engineering prototype

Engineering implementation, synthetic testing and handover are complete. Human
semantic validation and prospective model validation remain incomplete. This
closeout does not claim an improved model score or production readiness.

The supplied [300-case JSONL](../synthetic_review_v1/fixtures/synthetic_cases.jsonl)
and [earlier closeout](../synthetic_review_v1/PROJECT_CLOSEOUT.md) are unchanged.
Their SHA-256 hashes are recorded in [replay provenance](replay/replay.json).
The 300 records are variants of 12 authored scenarios, with zero human labels
and zero additional independent campaigns.

The new replay reads those exact records and injects their expected labels into
the frozen count-feature builder, baseline detector and fixed logistic model.
It bypasses narrative classification. On a fixed fictional 2019 timeline:

| Software observation | Count / relevant input total | Interpretation |
|---|---:|---|
| Fixture records retained | 300/300 | Includes all unclear rows |
| Specific authored labels | 150/300 | Test inputs, not verified truth |
| Unclear authored labels | 150/300 | Cannot become specific-defect candidates |
| Finite logistic scores | 120/120 candidate rows | Inference executed |
| Baseline alert episodes | 30/120 candidate rows | Software count, not precision |
| Logistic alert episodes | 0/120 candidate rows | Software count, not recall |

Split: `synthetic_software_test`. Label source: agent-authored fixture expectations.
Scope: fictional fuel-system records for five makes. Candidate result: **no**.
There are no recall outcomes in this replay, so accuracy, recall, precision,
false-positive rates and their confidence intervals are not computed. No fitting,
calibration, threshold tuning or selection was performed. Exact command, config
hash, data hash and code commit are in [replay.json](replay/replay.json).

Validation is recorded in [VALIDATION.json](VALIDATION.json), including every
selected command, exit code and log hash:

- **2039 tests passed** in the full `tests/frontline/` suite via
  `make test -o dashboard-build`, after a verified native-loader dashboard build.
- **23/23 functional gates passed** with `make eval-frontline`.
- Historical replay matched exactly, including all 100 random-reference draws;
  its complete output hash matches the prior frozen replay.
- Pipeline check, source/score integrity, desktop/mobile browser assertions,
  dashboard build and compilation passed.
- The initial suite exposed a dashboard-test import-path leak. The test-only
  repair restores `sys.path`; all frozen version gates remain intact. The
  interrupted failing run and successful rerun are retained.
- Chromium required an isolated retry outside the sandbox. The successful
  browser run retained all assertions and used native Vite config loading to
  preserve the shared dependency directory. See [reproduction details](REPRODUCE.md).
- The repaired full-suite run initially passed 2,038 tests with one sandbox
  socket-bind denial. The complete successful rerun outside the sandbox is the
  full-suite result reported above; the denied run is also retained.

Historical-opened context remains unchanged:

| Metric | Numerator / denominator | Value | Descriptive 95% Wilson CI |
|---|---:|---:|---:|
| Repair campaign recall | 22/41 | 53.7% | 38.7–67.9% |
| Repair mature-alert precision | 14/31 | 45.2% | 29.2–62.2% |
| Sensitivity campaign recall | 14/41 | 34.1% | 21.6–49.5% |
| Sensitivity mature-alert precision | 7/13 | 53.8% | 29.1–76.8% |
| 2025 fuel holdout recall | 5/8 | 62.5% | 30.6–86.3% |
| 2025 fuel holdout precision | 6/18 | 33.3% | 16.3–56.3% |

All six rows are historical-opened, model-labelled/official-recall proxy evidence,
not human semantic truth or candidate results. Scope, exact original command,
label source, config/data hashes and commits are preserved per row in
[unchanged_baseline.json](unchanged_baseline.json). Synthetic counts are not a
valid performance comparison against these historical results.

Both freeze tags and their artifact hashes verify. The original mode remains
baseline replication. The separate trained logistic prototype remains unvalidated;
its registered comparison uses the same reserved future cohort, not a second
independent replication. Human review remains **0/300**. No real 2027+ outcomes
were fetched or inspected. Custody remains procedural and tamper-evident;
no-peeking is honor-system because outcomes are public.

Phases 0–6 remain complete with their recorded deviations. Phases 7–8 remain
human-only: collect reserved 2027–2028 observations, wait for the 2029-12-31
outcome cutoff, apply the minimum 25-campaign rule, and make a separate merge
decision. The [existing runbook](../prospective/RUNBOOK.md) governs those steps;
synthetic data does not satisfy them. `PHASE_STATE.json` is preserved.

`main` remains `b8afe38`; the original checkout and its unrelated work are
unchanged. No merge, push, promotion or paid call occurred. The deliverable that
can be concluded today is the tested research prototype and its reproducible
handover. Scientific validation is explicitly left open in [STATUS.json](STATUS.json).
The verified source commit is 40 commits ahead of `main`, including the
original 17 readiness commits; this closeout adds one report commit. Merging the
branch would include all of them and remains a separate human decision.
