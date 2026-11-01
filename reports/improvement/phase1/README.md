# Prospective fuel-system evaluation — engineering record

Phases 0–5 are complete under the explicitly approved historical-preparation
amendment DEV-20261101-01. Phase 6 supplies the operations runbooks. The
prospective test is reserved and pre-registered; **no improved score has been
demonstrated**. Frozen mode: **Mode B, baseline replication**. No candidate was
forced; both training folds had zero mature labelled outcomes.

The historical preparation read is retained in the append-only
[`DEVIATIONS.md`](../prospective/DEVIATIONS.md). The subsequent pre-registered
experiment's two inputs and date ranges are independently checked in
`phase5_final_audit.json`; no preparation or model fitting was rerun.

## Protocol and frozen artifacts

Pre-registration commit: `440b90e5452f199dd9cf6e08ae3be640d59b7300`,
2026-10-31 20:40:06 IST; recorded Phase 2 start: 20:48:44 IST.
[`PREREGISTRATION.md`](PREREGISTRATION.md) SHA-256: `a462493785c582e03930d7ab81027a7aa221943006f19c06cad083ecd38b7469`.
[`protocol.json`](protocol.json) SHA-256: `a8bc1e0374a3f3871678527ac260b13bebb0562217632200d2328e80ee2cc06d`.
Freeze tag: `ml-prospective-freeze-2026` → `e96338df3cce113a182b0cf1be5bf760abc00b31`.
C1: `b3aaaede66678096d0572413039956dad62ac668`. All 339 frozen dependency
hashes, the tagged index and the C1 tree verify. Calendar receipt exists, but
Bitcoin timestamp verification remains pending; no confirmed external timestamp
is claimed. See `timestamp_receipt.json` and `TIMESTAMP_INSTRUCTIONS.md`.

Flags: 2027-01-01 through 2028-12-31. Outcome cutoff: 2029-12-31. Minimum
25 evaluable campaigns; prefer 30. Below 25: INCONCLUSIVE_SAMPLE, counts only,
nonzero exit, no performance metrics. One final analysis, by 2030-06-30.
No real prospective data has been collected; the manifest remains reserved,
its snapshot list empty and the collection log empty.

## Baseline context

| Benchmark | Numerator / denominator | Value | 95% CI | Split |
|---|---:|---:|---|---|
| Repair campaign recall | 22/41 | 53.7% | 38.7%–67.9% | historical-opened |
| Repair mature-alert precision | 14/31 | 45.2% | 29.2%–62.2% | historical-opened |
| Sensitivity recall | 14/41 | 34.1% | 21.6%–49.5% | historical-opened |
| Sensitivity precision | 7/13 | 53.8% | 29.1%–76.8% | historical-opened |
| 2025 fuel holdout recall | 5/8 | 62.5% | 30.6%–86.3% | historical-opened |
| 2025 fuel holdout precision | 6/18 | 33.3% | 16.3%–56.3% | historical-opened |

Label source: frozen model complaint/recall labels plus official recall dates; no human semantic truth.
Scope: Ford, Honda, Hyundai, Kia, Toyota, MY2015–2024, repaired FUEL SYSTEM;
the 2025 holdout retains its separately documented expanded fuel/propulsion
definition. Baseline comparison: unchanged historical baseline, not a candidate
comparison. Exact original commands, config hashes, data hashes, code commits,
source hashes, and `is_candidate_result: false` accompany every metric in
`final_validation_phase1.json` → `baseline_metrics`. Category labels 4/76 and
descriptions 22/76 remain authored diagnostics, not acceptance-eligible accuracy.

## Development record

Development-only evidence; not a candidate result and not a prospective estimate.

The 263 complaints and 36 campaigns are limited to 2015–2020. Fold A validates
2017–2018 after fitting through 2016; Fold B validates 2019–2020 after fitting
through 2018. Campaign identities are disjoint. The 16 evaluated model/fold/slice
records retain all five bootstrap seeds, 2,000 draws each, and all 100 random
reference seeds. Twenty logistic seed/fold/slice records state
`insufficient_training_support`; no calibration was fitted. The deterministic
selection rule reproduces `mode_b_baseline`.

Development-only evidence; not a candidate result and not a prospective estimate.

Actual baseline error inventory: all reports contain 2 mature false positives and
33 missed campaigns; sensitivity has 1 and 35, respectively. These overlapping
inventories cannot supply 50 unique errors of each type. Nothing was duplicated.
See `development_results.json`, `development_results.md`, `error_analysis.md`,
`model_card.md`, `phase2_decision.json`, and `research_environment.json`.

## Validation

| Command | Exit | Observed counts | Log |
|---|---:|---|---|
| defect_verify | 0 | not a test count | `reports/improvement/phase1/logs/defect_verify_resume_20261101.txt` |
| pipeline | 0 | not a test count | `reports/improvement/phase1/logs/pipeline_resume_20261101.txt` |
| targeted | 0 | 46 passed | `reports/improvement/phase1/logs/targeted_resume_20261101.txt` |
| full_frontline | 0 | 1,989 passed | `reports/improvement/phase1/logs/full_frontline_resume_20261101.txt` |
| make_test | 0 | 1,989 passed | `reports/improvement/phase1/logs/make_test_resume_20261101.txt` |
| make_eval | 0 | 23/23 gates passed | `reports/improvement/phase1/logs/make_eval_resume_20261101.txt` |
| compileall | 0 | not a test count | `reports/improvement/phase1/logs/compileall_resume_20261101.txt` |
| dashboard_ui | 0 | 1 browser test passed | `reports/improvement/phase1/logs/dashboard_ui_resume_20261101_attempt2.txt` |
| dashboard_build | 0 | not a test count | `reports/improvement/phase1/logs/dashboard_build_resume_20261101.txt` |
| dashboard_source | 0 | not a test count | `reports/improvement/phase1/logs/dashboard_source_resume_20261101.txt` |

Each exact command, environment override, timestamp, input manifest and log
SHA-256 is in `final_validation_phase1.json`. Browser sandbox failure and
successful retry are both retained. The replay compares the entire frozen
output objects, including 100 random references per slice. Test counts are
engineering evidence, not accuracy estimates. Evaluation ran the same Makefile
target in an isolated report directory; pipeline output used a new path to
preserve prior evidence.

## Custody, limitations and next steps

Custodian: Rahul Kumar Singh. The encrypted APFS image is human-managed outside
the repository; its passphrase is human-held, absent from repo/env/history and
agent-accessible keychain items. Custody is **procedural and tamper-evident, not
enforced access control**. Public NHTSA outcomes can be re-fetched; no-peeking is
an honor-system limitation. Integrity relies on prior registration, frozen code,
published hashes, committed manifest chain and the human attestation.

Human semantic validation remains **0/300**. Recall-confirmed precision is not
semantic truth. The sample is tiny, the future test may be underpowered, and
fuel-system results do not generalize to other components. Complete future
classification artifacts with pinned model/prompt/taxonomy provenance will be
required; absent coverage blocks analysis. No paid calls were made here.

No merge, push, tag movement, or production promotion occurred. See
`merge_readiness.md`, `FINAL_REVIEW_ADDENDUM.md`, `claims_addendum.md`, and the
Phase 6 [`human runbook`](../prospective/RUNBOOK.md). Phases 7–8 are human-only;
they are not executed or marked complete by this engineering record.
