# Merge readiness — separate human decision

Recommendation: **do not merge before the demo; decide separately**. No merge
is required for the demo. No merge, push, production promotion, history rewrite,
or tag movement was performed.

## Topology and scope

Main remains `b8afe3856f9fd705f7cc6f3751e9b79343a4b491`. The original checkout remains on
`submission/readiness-2026-10-30` at `13c5ff1`, with its unrelated uncommitted
work preserved. At starting HEAD `b490dd5`, this branch was 23 commits ahead:
17 readiness/voice/container/navigation commits plus six ML commits. At this
Phase 5 parent `e96338df3cce113a182b0cf1be5bf760abc00b31`, it is 29 commits ahead. This
Phase 5 commit and the subsequent Phase 6 commit add to that total; they do
not remove the 17 unrelated readiness commits. Merging brings the whole branch.
The two-commit Phase 4 freeze explains the extra freeze commit.

```text
03ed794 Preserve punctuation-free report citations through reviewed revisions
fac3515 Keep the engineer workflow in the primary entry and navigation
6a0bd2d Ship review assets matching the independent-grading templates
e6517f1 Record clean-checkout acceptance evidence and public candidate access
8edc0fd Pin the packaged readiness source and evidence manifest
e240143 Fix fresh container trust bootstrap and package migrations
41f7d87 Complete legacy container schema and exercise report workflow in CI
edfda13 Include DuckDB timezone runtime and validate each readiness commit
6d77406 Record clean Docker execution and verify documented Compose workflow
db6c7ba Pin verified source and container evidence in submission manifest
cc27cda Retain final candidate CI and anonymous source verification
d75beff Seal the source and verification artifact inventory
b74c695 Keep one Report entry and remove duplicate workflow navigation
80efff3 Refresh submission inventory after navigation cleanup
26b3a3f Keep spoken report drafts intact and clarify ambiguous intake answers
bff515b Record voice repair checks against the committed source
13c5ff1 Pin the packaged voice repair source manifest
b63d7a7 Record immutable ML baseline checks and improvement proposal
19bd5cf Add guarded ML research evaluation and source-verified evidence dashboard
1590fb5 Improve mobile evidence display and allow immutable calibration replays
3e4add4 Require unique calibration evidence and improve metric label contrast
c602bdd Record reproducible validation and honest ML research limits
b490dd5 Record Phase 1 starting audit and independent custody blocker
0d088f6 Phase 0: re-verify starting state
440b90e Phase 1: preregister prospective 2027-2028 test
2a710a0 Phase 2: development-only experiments on 2015-2020
1c540ef Phase 3: add sealed prospective collection and final-analysis harness
b3aaaed Phase 4: freeze baseline/candidate for prospective test
e96338d Phase 4: seal freeze hashes and calendar receipt
```

## Files changed versus main at the Phase 5 parent

```text
.gitattributes                                     |     4 +
 .github/workflows/container-readiness.yml          |    36 +
 .github/workflows/frontline.yml                    |    12 +
 .gitignore                                         |     6 +
 Dockerfile                                         |     2 +
 Dockerfile.hackathon                               |     2 +
 ELIGIBLE_WORK.md                                   |    17 +-
 HACKATHON.md                                       |     6 +-
 README.md                                          |    24 +-
 dashboard/package.json                             |     1 +
 dashboard/public/review-scripts/evidence-review.js |    10 +-
 dashboard/public/review-scripts/reviewer-study.js  |    10 +-
 dashboard/routes/CallWidget.jsx                    |   161 +-
 dashboard/routes/DefectLevel.jsx                   |     2 +
 dashboard/routes/DemoMode.jsx                      |     8 +-
 dashboard/routes/JudgeEntry.jsx                    |     2 +-
 dashboard/scripts/assert-qa-labels.mjs             |     2 +-
 dashboard/scripts/assert-signin-reachable.mjs      |    21 +-
 dashboard/scripts/check-public-links.mjs           |    16 +-
 dashboard/scripts/container-readiness.test.mjs     |    47 +
 dashboard/scripts/ml-evidence-ui.test.mjs          |    35 +
 dashboard/scripts/public-link-scope.mjs            |    32 +
 dashboard/scripts/public-link-scope.test.mjs       |    26 +
 dashboard/scripts/report-handoff.test.mjs          |    43 +-
 dashboard/scripts/speech-draft.test.mjs            |    41 +
 dashboard/scripts/voice-capture.test.mjs           |     1 +
 dashboard/scripts/voice-ui.test.mjs                |    44 +-
 dashboard/src/App.jsx                              |    39 +-
 dashboard/src/ai/MlImprovementEvidence.jsx         |    38 +
 dashboard/src/ai/ml-improvement-evidence.css       |    33 +
 dashboard/src/ai/mlImprovement.json                |   144 +
 dashboard/src/speechDraft.js                       |    37 +
 dashboard/src/styles.css                           |     3 +
 dashboard/src/ui/opsActions.js                     |     2 +-
 dashboard/src/voiceExperience.js                   |     4 +-
 dashboard/src/voiceHelpers.js                      |     4 +
 data/prospective/.gitignore                        |     6 +
 data/prospective/README.md                         |    12 +
 data/prospective/custody.json                      |    14 +
 data/prospective/manifest.json                     |    28 +
 docker-compose.hackathon.yml                       |     5 +-
 docker/entrypoint.sh                               |     4 +
 docs/container-validation.md                       |    83 +
 docs/entry-auth-validation.md                      |     2 +-
 docs/sourced-investigation.md                      |    10 +-
 docs/voice-validation.md                           |    37 +
 migrations/004_ops_runtime_columns.sql             |    24 +
 reports/CLAIMS_AUDIT.md                            |    68 +
 reports/defect/evidence_v1/development_review.html |    26 +-
 .../defect/evidence_v1/fuel_complaint_review.html  |    26 +-
 reports/defect/evidence_v1/recall_review.html      |    26 +-
 reports/hackathon/CLAIM_INDEX.md                   |     9 +
 .../hackathon/COMPETITIVENESS_REVIEW_2026-10-30.md |     4 +
 reports/hackathon/IMPROVEMENT_PLAN_2026-10-30.md   |     5 +
 reports/hackathon/READINESS_STATUS_2026-10-30.md   |   135 +
 .../41f7d87-arm64-attempt1.browser.log             |    16 +
 .../41f7d87-arm64-attempt1.container.log           |   227 +
 .../41f7d87-arm64-attempt1.json                    |    72 +
 .../container_validation/41f7d87.build.log         |   363 +
 .../41f7d87.full-revision-label.log                |   138 +
 .../8edc0fd-arm64-attempt1.container.log           |   163 +
 .../8edc0fd-arm64-attempt1.json                    |    19 +
 .../container_validation/8edc0fd.build.log         |   437 +
 reports/hackathon/container_validation/README.md   |    65 +
 .../hackathon/container_validation/ci-db6c7ba.json |   115 +
 .../hackathon/container_validation/ci-edfda13.json |   120 +
 .../e240143-arm64-attempt1.browser.log             |    21 +
 .../e240143-arm64-attempt1.container.log           |   233 +
 .../e240143-arm64-attempt1.json                    |    65 +
 .../e240143-arm64-attempt2.container.log           |   150 +
 .../e240143-arm64-attempt2.json                    |    60 +
 .../container_validation/e240143.build.log         |   363 +
 .../edfda13-arm64-attempt1.browser.log             |     2 +
 .../edfda13-arm64-attempt1.container.log           |   240 +
 .../edfda13-arm64-attempt1.json                    |    94 +
 .../edfda13-compose-arm64-attempt1.browser.log     |     2 +
 .../edfda13-compose-arm64-attempt1.container.log   |   240 +
 .../edfda13-compose-arm64-attempt1.json            |    96 +
 .../edfda13-compose-arm64-attempt2.browser.log     |     2 +
 .../edfda13-compose-arm64-attempt2.container.log   |   248 +
 .../edfda13-compose-arm64-attempt2.json            |    96 +
 .../container_validation/edfda13.build.log         |   366 +
 .../container_validation/focused-tests.log         |     8 +
 .../public-source-db6c7ba.json                     |    23 +
 .../container_validation/verification.json         |    27 +
 reports/hackathon/link_checks/repository.png       |   Bin 141571 -> 84460 bytes
 reports/hackathon/link_checks/results.json         |    25 +-
 reports/hackathon/link_checks/source_commit.png    |   Bin 0 -> 84974 bytes
 .../hackathon/navigation_2026_10_30/browser.log    |    36 +
 .../navigation_2026_10_30/verification.json        |    19 +
 reports/hackathon/readiness_2026_10_30/browser.log |    36 +
 .../readiness_2026_10_30/clean-setup-smoke.json    |    22 +
 .../hackathon/readiness_2026_10_30/judge-entry.png |   Bin 0 -> 128942 bytes
 .../readiness_2026_10_30/public-replay.json        |    67 +
 .../signin-negative-control.log                    |   162 +
 .../readiness_2026_10_30/targeted-tests.log        |    12 +
 .../readiness_2026_10_30/verification.json         |   134 +
 .../voice-controls-synthetic.png                   |   Bin 0 -> 137946 bytes
 .../voice-reflow-synthetic.png                     |   Bin 0 -> 33496 bytes
 reports/hackathon/reviewer_study/study.html        |    16 +-
 reports/hackathon/source_manifest.json             |  7748 ++-
 reports/hackathon/submission_links.json            |    13 +-
 .../hackathon/voice_repair_2026_10_30/README.md    |    78 +
 .../voice_repair_2026_10_30/localhost_check.json   |    34 +
 .../voice_repair_2026_10_30/meta_text_probe.json   |    72 +
 .../meta_text_probe_after_schema_fix.json          |   110 +
 .../meta_text_probe_after_schema_fix_request.json  |   170 +
 .../meta_text_probe_request.json                   |   170 +
 .../voice_repair_2026_10_30/release-browser.txt    |    38 +
 .../voice_repair_2026_10_30/release-node.txt       |    17 +
 .../voice_repair_2026_10_30/release-python.txt     |     3 +
 .../release_verification.json                      |    41 +
 reports/improvement/FINAL_REVIEW.md                |    92 +
 reports/improvement/README.md                      |   192 +
 reports/improvement/artifact_integrity_check.json  |     4 +
 .../improvement/artifact_integrity_release.json    |    15 +
 reports/improvement/baseline.json                  |  4645 ++
 reports/improvement/before_after.json              |   448 +
 reports/improvement/before_after.md                |    16 +
 .../improvement/clean_reproduction_comparison.json |    24 +
 reports/improvement/clean_run_status.json          |    37 +
 reports/improvement/development_manifest.json      |    47 +
 .../improvement/development_metric_records.json    |  3401 +
 reports/improvement/error_analysis.md              |    92 +
 reports/improvement/experiments.csv                |    39 +
 reports/improvement/final_validation.json          |   415 +
 .../historical_verification_ledger_addendum.json   |    53 +
 .../improvement/integrity_release_pre_docs.json    |   549 +
 reports/improvement/labeling_guide.md              |   302 +
 reports/improvement/logs/audit_v1.txt              |     5 +
 .../improvement/logs/baseline_calibration_v1.txt   |     5 +
 .../improvement/logs/baseline_failure_details.txt  |    45 +
 .../logs/calibration_identity_guard.txt            |     2 +
 reports/improvement/logs/clean_audit_command.txt   |     5 +
 .../improvement/logs/clean_calibration_command.txt |     5 +
 reports/improvement/logs/clean_defect_replay.txt   |     6 +
 .../improvement/logs/clean_dependency_freeze.txt   |    66 +
 reports/improvement/logs/clean_fuel_replay.txt     |     5 +
 reports/improvement/logs/clean_identity_guard.txt  |     2 +
 reports/improvement/logs/clean_install.txt         |   201 +
 reports/improvement/logs/clean_install_attempt.txt |    19 +
 reports/improvement/logs/clean_pipeline.txt        |    84 +
 reports/improvement/logs/clean_report_check.txt    |     1 +
 reports/improvement/logs/clean_research_freeze.txt |    17 +
 .../improvement/logs/clean_research_install.txt    |    57 +
 .../logs/clean_research_install_attempt.txt        |    10 +
 reports/improvement/logs/clean_targeted.txt        |     3 +
 reports/improvement/logs/dashboard_build.txt       |    25 +
 reports/improvement/logs/dashboard_build_final.txt |    25 +
 .../improvement/logs/dashboard_build_release.txt   |    25 +
 reports/improvement/logs/defect_replay.txt         |     6 +
 reports/improvement/logs/final_defect_replay.txt   |     6 +
 reports/improvement/logs/final_frontline_eval.txt  |    90 +
 reports/improvement/logs/final_fuel_replay.txt     |     5 +
 reports/improvement/logs/final_pipeline.txt        |    84 +
 reports/improvement/logs/final_targeted.txt        |     3 +
 reports/improvement/logs/fuel_replay.txt           |     5 +
 reports/improvement/logs/human_accuracy.txt        |    12 +
 .../logs/make_eval_frontline_baseline.json         |    18 +
 .../logs/make_eval_frontline_baseline.txt          |    90 +
 reports/improvement/logs/make_test_baseline.json   |    15 +
 reports/improvement/logs/make_test_baseline.txt    |    93 +
 reports/improvement/logs/make_test_final.txt       |    69 +
 reports/improvement/logs/make_test_release.txt     |    69 +
 .../improvement/logs/new_and_repaired_tests_v2.txt |     2 +
 .../improvement/logs/new_and_repaired_tests_v3.txt |     2 +
 .../improvement/logs/operational_recheck_v1.txt    |    29 +
 reports/improvement/logs/pipeline.txt              |    84 +
 reports/improvement/logs/prepare_v1.txt            |    51 +
 .../improvement/logs/release_frontline_eval.txt    |    90 +
 reports/improvement/logs/report_validation.txt     |     2 +
 reports/improvement/logs/signin_baseline.json      |    16 +
 reports/improvement/logs/signin_baseline.txt       |    45 +
 reports/improvement/logs/signin_final.txt          |    38 +
 reports/improvement/logs/signin_installed.txt      |    75 +
 reports/improvement/logs/signin_mobile_final.txt   |    38 +
 reports/improvement/logs/signin_release.txt        |    38 +
 reports/improvement/logs/signin_unsandboxed.txt    |    37 +
 reports/improvement/logs/targeted_tests.txt        |     2 +
 reports/improvement/model_card.md                  |    88 +
 reports/improvement/monitoring_plan.md             |    44 +
 reports/improvement/original_artifact_hashes.json  |   821 +
 reports/improvement/phase1/BLOCKED.md              |    67 +
 reports/improvement/phase1/CUSTODY.md              |    19 +
 reports/improvement/phase1/FREEZE_HASHES.json      |    11 +
 reports/improvement/phase1/FREEZE_HASHES.sha256    |     1 +
 .../improvement/phase1/FREEZE_HASHES.sha256.ots    |   Bin 0 -> 980 bytes
 reports/improvement/phase1/HASHES.json             |     7 +
 reports/improvement/phase1/PHASE_STATE.json        |    14 +
 reports/improvement/phase1/PREREGISTRATION.md      |   147 +
 .../improvement/phase1/TIMESTAMP_INSTRUCTIONS.md   |    27 +
 reports/improvement/phase1/baseline_model.json     |    40 +
 .../improvement/phase1/development_results.json    | 64336 +++++++++++++++++++
 reports/improvement/phase1/development_results.md  |    38 +
 reports/improvement/phase1/error_analysis.md       |    98 +
 reports/improvement/phase1/freeze_manifest.json    |   404 +
 reports/improvement/phase1/freeze_manifest.sha256  |     1 +
 .../improvement/phase1/logs/ots_environment.txt    |    10 +
 .../phase1/logs/ots_install_attempt.txt            |     7 +
 .../phase1/logs/ots_install_escalated.txt          |    34 +
 .../improvement/phase1/logs/ots_receipt_info.txt   |    59 +
 reports/improvement/phase1/logs/ots_stamp.txt      |     5 +
 .../phase1/logs/ots_stamp_escalated.txt            |     4 +
 .../phase1/logs/phase2_development_v1.txt          |     8 +
 .../phase1/logs/phase2_environment_freeze.txt      |    68 +
 reports/improvement/phase1/logs/phase2_tests.txt   |     2 +
 .../improvement/phase1/logs/phase3_tests_v1.txt    |     2 +
 .../improvement/phase1/logs/phase3_tests_v2.txt    |     2 +
 .../phase1/logs/starting_state_commands.json       |    47 +
 reports/improvement/phase1/model_card.md           |    33 +
 reports/improvement/phase1/phase0_recheck.json     |   401 +
 reports/improvement/phase1/phase2_decision.json    |     9 +
 reports/improvement/phase1/phase3_validation.json  |     8 +
 reports/improvement/phase1/protocol.json           |   306 +
 .../phase1/requirements-prospective.txt            |    68 +
 .../improvement/phase1/research_environment.json   |    17 +
 reports/improvement/phase1/starting_state.json     |   609 +
 .../improvement/phase1/starting_state.sha256.json  |     4 +
 reports/improvement/phase1/timestamp_receipt.json  |    13 +
 reports/improvement/pipeline_clean.json            |  1886 +
 reports/improvement/pipeline_final.json            |  1886 +
 reports/improvement/pipeline_recheck.json          |  1886 +
 .../improvement/prospective/collection_log.jsonl   |     0
 reports/improvement/reproduction.md                |    89 +
 reports/improvement/research_protocol.json         |   203 +
 reports/improvement/results.json                   |  7876 +++
 .../runs/audit_clean_replay/finished.json          |     5 +
 .../runs/audit_clean_replay/results.json           |  2940 +
 .../runs/audit_clean_replay/started.json           |    19 +
 reports/improvement/runs/audit_v1/finished.json    |     5 +
 reports/improvement/runs/audit_v1/results.json     |  2940 +
 reports/improvement/runs/audit_v1/started.json     |    19 +
 .../runs/baseline_calibration_v1/all_reports.png   |   Bin 0 -> 60950 bytes
 .../excluding_explicit_recall_reports.png          |   Bin 0 -> 65826 bytes
 .../runs/baseline_calibration_v1/finished.json     |     5 +
 .../runs/baseline_calibration_v1/results.json      |   541 +
 .../runs/baseline_calibration_v1/started.json      |    21 +
 .../runs/calibration_clean_replay/all_reports.png  |   Bin 0 -> 60950 bytes
 .../excluding_explicit_recall_reports.png          |   Bin 0 -> 65826 bytes
 .../runs/calibration_clean_replay/finished.json    |     5 +
 .../runs/calibration_clean_replay/results.json     |   541 +
 .../runs/calibration_clean_replay/started.json     |    21 +
 .../runs/clean_audit_command/finished.json         |     5 +
 .../runs/clean_audit_command/started.json          |    32 +
 .../runs/clean_calibration_command/finished.json   |     5 +
 .../runs/clean_calibration_command/started.json    |    31 +
 .../runs/clean_defect_replay/finished.json         |     5 +
 .../runs/clean_defect_replay/started.json          |    29 +
 .../runs/clean_fuel_replay/finished.json           |     5 +
 .../runs/clean_fuel_replay/started.json            |    30 +
 .../improvement/runs/clean_pipeline/finished.json  |     5 +
 .../improvement/runs/clean_pipeline/started.json   |    33 +
 .../runs/clean_report_check/finished.json          |     5 +
 .../runs/clean_report_check/started.json           |    30 +
 .../improvement/runs/clean_targeted/finished.json  |     5 +
 .../improvement/runs/clean_targeted/started.json   |    39 +
 .../runs/dashboard_build_final/finished.json       |     5 +
 .../runs/dashboard_build_final/started.json        |    26 +
 .../runs/dashboard_build_release/finished.json     |     5 +
 .../runs/dashboard_build_release/started.json      |    26 +
 .../runs/final_defect_replay/finished.json         |     5 +
 .../runs/final_defect_replay/started.json          |    23 +
 .../runs/final_frontline_eval/finished.json        |     5 +
 .../runs/final_frontline_eval/started.json         |    25 +
 .../runs/final_fuel_replay/finished.json           |     5 +
 .../runs/final_fuel_replay/started.json            |    24 +
 .../improvement/runs/final_pipeline/finished.json  |     5 +
 .../improvement/runs/final_pipeline/started.json   |    27 +
 .../improvement/runs/final_targeted/finished.json  |     5 +
 .../improvement/runs/final_targeted/started.json   |    33 +
 .../runs/phase1_development_v1/finished.json       |     5 +
 .../runs/phase1_development_v1/results.json        | 64335 ++++++++++++++++++
 .../runs/phase1_development_v1/started.json        |   322 +
 reports/improvement/runs/prepare_v1/finished.json  |     5 +
 reports/improvement/runs/prepare_v1/started.json   |    44 +
 .../runs/release_frontline_eval/finished.json      |     5 +
 .../runs/release_frontline_eval/started.json       |    27 +
 .../reports/qubot/eval/eval_2026-10-31.md          |    42 +
 .../reports/qubot/eval/eval_2026-10-31.md          |    42 +
 .../reports/qubot/eval/eval_2026-10-31.md          |    42 +
 reports/improvement/source_checkout_status.txt     |    60 +
 reports/improvement/split_audit.json               |    27 +
 reports/improvement/ui_desktop.png                 |   Bin 0 -> 149955 bytes
 reports/improvement/ui_desktop_v2.png              |   Bin 0 -> 131726 bytes
 reports/improvement/ui_desktop_v3.png              |   Bin 0 -> 132900 bytes
 reports/improvement/ui_mobile.png                  |   Bin 0 -> 54867 bytes
 reports/improvement/ui_mobile_v2.png               |   Bin 0 -> 73484 bytes
 reports/improvement/ui_mobile_v3.png               |   Bin 0 -> 73705 bytes
 .../improvement/validation_ledger_addendum.json    |   152 +
 reports/improvement/verification_input_hashes.json |    91 +
 .../improvement/verification_log_inventory.json    |   457 +
 reports/improvement/verification_runs.json         |   104 +
 reports/voice_validation/results.json              |    69 +
 requirements-docker.txt                            |     2 +
 requirements-ml-improvement.txt                    |    19 +
 scripts/bootstrap_container_trust.py               |    59 +
 scripts/docker_readiness.py                        |   157 +
 scripts/final_prospective_eval.py                  |   173 +
 scripts/ml_baseline_calibration.py                 |    75 +
 scripts/ml_improvement.py                          |   196 +
 scripts/ml_improvement_report.py                   |   108 +
 scripts/ml_score_snapshot.py                       |   178 +
 scripts/seal_prospective.py                        |    77 +
 scripts/voice_intake_probe.py                      |    67 +
 src/agents/intake.py                               |    96 +-
 src/agents/orchestrator.py                         |    13 +
 src/ai_layer/complaint_evidence.py                 |     7 +-
 src/ai_layer/intake_enhancer.py                    |    44 +-
 src/ai_layer/meta_client.py                        |     8 +-
 src/eval/improvement_detection.py                  |   137 +
 src/eval/improvement_metrics.py                    |   145 +
 src/eval/improvement_models.py                     |    67 +
 src/eval/improvement_monitoring.py                 |    50 +
 src/eval/improvement_protocol.py                   |    78 +
 src/eval/prospective_io.py                         |   141 +
 src/eval/prospective_research.py                   |   185 +
 tests/frontline/ai_layer/prospective_fixture.py    |    83 +
 tests/frontline/ai_layer/test_baseten_backend.py   |     2 +
 .../ai_layer/test_final_prospective_eval.py        |    75 +
 tests/frontline/ai_layer/test_ml_improvement.py    |   189 +
 tests/frontline/ai_layer/test_prospective_seal.py  |    64 +
 tests/frontline/ai_layer/test_report_handoff.py    |    40 +
 tests/frontline/test_backlog_p0_p1.py              |     3 +-
 tests/frontline/test_container_migrations.py       |    53 +
 tests/frontline/test_container_trust_bootstrap.py  |    66 +
 tests/frontline/test_dashboard_ui_surface.py       |    12 +-
 tests/frontline/test_deploy_hygiene.py             |     5 +
 tests/frontline/test_live_handoff_outcomes.py      |     5 +-
 tests/frontline/test_mapping_ingest.py             |     4 +
 tests/frontline/test_safety_gate_preemption.py     |     4 +-
 tests/frontline/test_voice_report_repair.py        |    59 +
 tests/frontline/test_voice_tierA_wiring.py         |     4 +-
 tests/frontline/test_wallboard_labels.py           |     6 +-
 333 files changed, 183638 insertions(+), 823 deletions(-)
```

The complete path inventory at that parent is below. The Phase 5 commit adds
the reports, audited logs, metadata-only dashboard overlay and reporter/test
changes; Phase 6 adds human runbooks and the final phase-state update.

```text
A	.gitattributes
A	.github/workflows/container-readiness.yml
M	.github/workflows/frontline.yml
M	.gitignore
M	Dockerfile
M	Dockerfile.hackathon
M	ELIGIBLE_WORK.md
M	HACKATHON.md
M	README.md
M	dashboard/package.json
M	dashboard/public/review-scripts/evidence-review.js
M	dashboard/public/review-scripts/reviewer-study.js
M	dashboard/routes/CallWidget.jsx
M	dashboard/routes/DefectLevel.jsx
M	dashboard/routes/DemoMode.jsx
M	dashboard/routes/JudgeEntry.jsx
M	dashboard/scripts/assert-qa-labels.mjs
M	dashboard/scripts/assert-signin-reachable.mjs
M	dashboard/scripts/check-public-links.mjs
A	dashboard/scripts/container-readiness.test.mjs
A	dashboard/scripts/ml-evidence-ui.test.mjs
A	dashboard/scripts/public-link-scope.mjs
A	dashboard/scripts/public-link-scope.test.mjs
M	dashboard/scripts/report-handoff.test.mjs
A	dashboard/scripts/speech-draft.test.mjs
M	dashboard/scripts/voice-capture.test.mjs
M	dashboard/scripts/voice-ui.test.mjs
M	dashboard/src/App.jsx
A	dashboard/src/ai/MlImprovementEvidence.jsx
A	dashboard/src/ai/ml-improvement-evidence.css
A	dashboard/src/ai/mlImprovement.json
A	dashboard/src/speechDraft.js
M	dashboard/src/styles.css
M	dashboard/src/ui/opsActions.js
M	dashboard/src/voiceExperience.js
M	dashboard/src/voiceHelpers.js
A	data/prospective/.gitignore
A	data/prospective/README.md
A	data/prospective/custody.json
A	data/prospective/manifest.json
M	docker-compose.hackathon.yml
M	docker/entrypoint.sh
A	docs/container-validation.md
M	docs/entry-auth-validation.md
M	docs/sourced-investigation.md
M	docs/voice-validation.md
A	migrations/004_ops_runtime_columns.sql
M	reports/CLAIMS_AUDIT.md
M	reports/defect/evidence_v1/development_review.html
M	reports/defect/evidence_v1/fuel_complaint_review.html
M	reports/defect/evidence_v1/recall_review.html
M	reports/hackathon/CLAIM_INDEX.md
M	reports/hackathon/COMPETITIVENESS_REVIEW_2026-10-30.md
M	reports/hackathon/IMPROVEMENT_PLAN_2026-10-30.md
A	reports/hackathon/READINESS_STATUS_2026-10-30.md
A	reports/hackathon/container_validation/41f7d87-arm64-attempt1.browser.log
A	reports/hackathon/container_validation/41f7d87-arm64-attempt1.container.log
A	reports/hackathon/container_validation/41f7d87-arm64-attempt1.json
A	reports/hackathon/container_validation/41f7d87.build.log
A	reports/hackathon/container_validation/41f7d87.full-revision-label.log
A	reports/hackathon/container_validation/8edc0fd-arm64-attempt1.container.log
A	reports/hackathon/container_validation/8edc0fd-arm64-attempt1.json
A	reports/hackathon/container_validation/8edc0fd.build.log
A	reports/hackathon/container_validation/README.md
A	reports/hackathon/container_validation/ci-db6c7ba.json
A	reports/hackathon/container_validation/ci-edfda13.json
A	reports/hackathon/container_validation/e240143-arm64-attempt1.browser.log
A	reports/hackathon/container_validation/e240143-arm64-attempt1.container.log
A	reports/hackathon/container_validation/e240143-arm64-attempt1.json
A	reports/hackathon/container_validation/e240143-arm64-attempt2.container.log
A	reports/hackathon/container_validation/e240143-arm64-attempt2.json
A	reports/hackathon/container_validation/e240143.build.log
A	reports/hackathon/container_validation/edfda13-arm64-attempt1.browser.log
A	reports/hackathon/container_validation/edfda13-arm64-attempt1.container.log
A	reports/hackathon/container_validation/edfda13-arm64-attempt1.json
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt1.browser.log
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt1.container.log
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt1.json
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt2.browser.log
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt2.container.log
A	reports/hackathon/container_validation/edfda13-compose-arm64-attempt2.json
A	reports/hackathon/container_validation/edfda13.build.log
A	reports/hackathon/container_validation/focused-tests.log
A	reports/hackathon/container_validation/public-source-db6c7ba.json
A	reports/hackathon/container_validation/verification.json
M	reports/hackathon/link_checks/repository.png
M	reports/hackathon/link_checks/results.json
A	reports/hackathon/link_checks/source_commit.png
A	reports/hackathon/navigation_2026_10_30/browser.log
A	reports/hackathon/navigation_2026_10_30/verification.json
A	reports/hackathon/readiness_2026_10_30/browser.log
A	reports/hackathon/readiness_2026_10_30/clean-setup-smoke.json
A	reports/hackathon/readiness_2026_10_30/judge-entry.png
A	reports/hackathon/readiness_2026_10_30/public-replay.json
A	reports/hackathon/readiness_2026_10_30/signin-negative-control.log
A	reports/hackathon/readiness_2026_10_30/targeted-tests.log
A	reports/hackathon/readiness_2026_10_30/verification.json
A	reports/hackathon/readiness_2026_10_30/voice-controls-synthetic.png
A	reports/hackathon/readiness_2026_10_30/voice-reflow-synthetic.png
M	reports/hackathon/reviewer_study/study.html
M	reports/hackathon/source_manifest.json
M	reports/hackathon/submission_links.json
A	reports/hackathon/voice_repair_2026_10_30/README.md
A	reports/hackathon/voice_repair_2026_10_30/localhost_check.json
A	reports/hackathon/voice_repair_2026_10_30/meta_text_probe.json
A	reports/hackathon/voice_repair_2026_10_30/meta_text_probe_after_schema_fix.json
A	reports/hackathon/voice_repair_2026_10_30/meta_text_probe_after_schema_fix_request.json
A	reports/hackathon/voice_repair_2026_10_30/meta_text_probe_request.json
A	reports/hackathon/voice_repair_2026_10_30/release-browser.txt
A	reports/hackathon/voice_repair_2026_10_30/release-node.txt
A	reports/hackathon/voice_repair_2026_10_30/release-python.txt
A	reports/hackathon/voice_repair_2026_10_30/release_verification.json
A	reports/improvement/FINAL_REVIEW.md
A	reports/improvement/README.md
A	reports/improvement/artifact_integrity_check.json
A	reports/improvement/artifact_integrity_release.json
A	reports/improvement/baseline.json
A	reports/improvement/before_after.json
A	reports/improvement/before_after.md
A	reports/improvement/clean_reproduction_comparison.json
A	reports/improvement/clean_run_status.json
A	reports/improvement/development_manifest.json
A	reports/improvement/development_metric_records.json
A	reports/improvement/error_analysis.md
A	reports/improvement/experiments.csv
A	reports/improvement/final_validation.json
A	reports/improvement/historical_verification_ledger_addendum.json
A	reports/improvement/integrity_release_pre_docs.json
A	reports/improvement/labeling_guide.md
A	reports/improvement/logs/audit_v1.txt
A	reports/improvement/logs/baseline_calibration_v1.txt
A	reports/improvement/logs/baseline_failure_details.txt
A	reports/improvement/logs/calibration_identity_guard.txt
A	reports/improvement/logs/clean_audit_command.txt
A	reports/improvement/logs/clean_calibration_command.txt
A	reports/improvement/logs/clean_defect_replay.txt
A	reports/improvement/logs/clean_dependency_freeze.txt
A	reports/improvement/logs/clean_fuel_replay.txt
A	reports/improvement/logs/clean_identity_guard.txt
A	reports/improvement/logs/clean_install.txt
A	reports/improvement/logs/clean_install_attempt.txt
A	reports/improvement/logs/clean_pipeline.txt
A	reports/improvement/logs/clean_report_check.txt
A	reports/improvement/logs/clean_research_freeze.txt
A	reports/improvement/logs/clean_research_install.txt
A	reports/improvement/logs/clean_research_install_attempt.txt
A	reports/improvement/logs/clean_targeted.txt
A	reports/improvement/logs/dashboard_build.txt
A	reports/improvement/logs/dashboard_build_final.txt
A	reports/improvement/logs/dashboard_build_release.txt
A	reports/improvement/logs/defect_replay.txt
A	reports/improvement/logs/final_defect_replay.txt
A	reports/improvement/logs/final_frontline_eval.txt
A	reports/improvement/logs/final_fuel_replay.txt
A	reports/improvement/logs/final_pipeline.txt
A	reports/improvement/logs/final_targeted.txt
A	reports/improvement/logs/fuel_replay.txt
A	reports/improvement/logs/human_accuracy.txt
A	reports/improvement/logs/make_eval_frontline_baseline.json
A	reports/improvement/logs/make_eval_frontline_baseline.txt
A	reports/improvement/logs/make_test_baseline.json
A	reports/improvement/logs/make_test_baseline.txt
A	reports/improvement/logs/make_test_final.txt
A	reports/improvement/logs/make_test_release.txt
A	reports/improvement/logs/new_and_repaired_tests_v2.txt
A	reports/improvement/logs/new_and_repaired_tests_v3.txt
A	reports/improvement/logs/operational_recheck_v1.txt
A	reports/improvement/logs/pipeline.txt
A	reports/improvement/logs/prepare_v1.txt
A	reports/improvement/logs/release_frontline_eval.txt
A	reports/improvement/logs/report_validation.txt
A	reports/improvement/logs/signin_baseline.json
A	reports/improvement/logs/signin_baseline.txt
A	reports/improvement/logs/signin_final.txt
A	reports/improvement/logs/signin_installed.txt
A	reports/improvement/logs/signin_mobile_final.txt
A	reports/improvement/logs/signin_release.txt
A	reports/improvement/logs/signin_unsandboxed.txt
A	reports/improvement/logs/targeted_tests.txt
A	reports/improvement/model_card.md
A	reports/improvement/monitoring_plan.md
A	reports/improvement/original_artifact_hashes.json
A	reports/improvement/phase1/BLOCKED.md
A	reports/improvement/phase1/CUSTODY.md
A	reports/improvement/phase1/FREEZE_HASHES.json
A	reports/improvement/phase1/FREEZE_HASHES.sha256
A	reports/improvement/phase1/FREEZE_HASHES.sha256.ots
A	reports/improvement/phase1/HASHES.json
A	reports/improvement/phase1/PHASE_STATE.json
A	reports/improvement/phase1/PREREGISTRATION.md
A	reports/improvement/phase1/TIMESTAMP_INSTRUCTIONS.md
A	reports/improvement/phase1/baseline_model.json
A	reports/improvement/phase1/development_results.json
A	reports/improvement/phase1/development_results.md
A	reports/improvement/phase1/error_analysis.md
A	reports/improvement/phase1/freeze_manifest.json
A	reports/improvement/phase1/freeze_manifest.sha256
A	reports/improvement/phase1/logs/ots_environment.txt
A	reports/improvement/phase1/logs/ots_install_attempt.txt
A	reports/improvement/phase1/logs/ots_install_escalated.txt
A	reports/improvement/phase1/logs/ots_receipt_info.txt
A	reports/improvement/phase1/logs/ots_stamp.txt
A	reports/improvement/phase1/logs/ots_stamp_escalated.txt
A	reports/improvement/phase1/logs/phase2_development_v1.txt
A	reports/improvement/phase1/logs/phase2_environment_freeze.txt
A	reports/improvement/phase1/logs/phase2_tests.txt
A	reports/improvement/phase1/logs/phase3_tests_v1.txt
A	reports/improvement/phase1/logs/phase3_tests_v2.txt
A	reports/improvement/phase1/logs/starting_state_commands.json
A	reports/improvement/phase1/model_card.md
A	reports/improvement/phase1/phase0_recheck.json
A	reports/improvement/phase1/phase2_decision.json
A	reports/improvement/phase1/phase3_validation.json
A	reports/improvement/phase1/protocol.json
A	reports/improvement/phase1/requirements-prospective.txt
A	reports/improvement/phase1/research_environment.json
A	reports/improvement/phase1/starting_state.json
A	reports/improvement/phase1/starting_state.sha256.json
A	reports/improvement/phase1/timestamp_receipt.json
A	reports/improvement/pipeline_clean.json
A	reports/improvement/pipeline_final.json
A	reports/improvement/pipeline_recheck.json
A	reports/improvement/prospective/collection_log.jsonl
A	reports/improvement/reproduction.md
A	reports/improvement/research_protocol.json
A	reports/improvement/results.json
A	reports/improvement/runs/audit_clean_replay/finished.json
A	reports/improvement/runs/audit_clean_replay/results.json
A	reports/improvement/runs/audit_clean_replay/started.json
A	reports/improvement/runs/audit_v1/finished.json
A	reports/improvement/runs/audit_v1/results.json
A	reports/improvement/runs/audit_v1/started.json
A	reports/improvement/runs/baseline_calibration_v1/all_reports.png
A	reports/improvement/runs/baseline_calibration_v1/excluding_explicit_recall_reports.png
A	reports/improvement/runs/baseline_calibration_v1/finished.json
A	reports/improvement/runs/baseline_calibration_v1/results.json
A	reports/improvement/runs/baseline_calibration_v1/started.json
A	reports/improvement/runs/calibration_clean_replay/all_reports.png
A	reports/improvement/runs/calibration_clean_replay/excluding_explicit_recall_reports.png
A	reports/improvement/runs/calibration_clean_replay/finished.json
A	reports/improvement/runs/calibration_clean_replay/results.json
A	reports/improvement/runs/calibration_clean_replay/started.json
A	reports/improvement/runs/clean_audit_command/finished.json
A	reports/improvement/runs/clean_audit_command/started.json
A	reports/improvement/runs/clean_calibration_command/finished.json
A	reports/improvement/runs/clean_calibration_command/started.json
A	reports/improvement/runs/clean_defect_replay/finished.json
A	reports/improvement/runs/clean_defect_replay/started.json
A	reports/improvement/runs/clean_fuel_replay/finished.json
A	reports/improvement/runs/clean_fuel_replay/started.json
A	reports/improvement/runs/clean_pipeline/finished.json
A	reports/improvement/runs/clean_pipeline/started.json
A	reports/improvement/runs/clean_report_check/finished.json
A	reports/improvement/runs/clean_report_check/started.json
A	reports/improvement/runs/clean_targeted/finished.json
A	reports/improvement/runs/clean_targeted/started.json
A	reports/improvement/runs/dashboard_build_final/finished.json
A	reports/improvement/runs/dashboard_build_final/started.json
A	reports/improvement/runs/dashboard_build_release/finished.json
A	reports/improvement/runs/dashboard_build_release/started.json
A	reports/improvement/runs/final_defect_replay/finished.json
A	reports/improvement/runs/final_defect_replay/started.json
A	reports/improvement/runs/final_frontline_eval/finished.json
A	reports/improvement/runs/final_frontline_eval/started.json
A	reports/improvement/runs/final_fuel_replay/finished.json
A	reports/improvement/runs/final_fuel_replay/started.json
A	reports/improvement/runs/final_pipeline/finished.json
A	reports/improvement/runs/final_pipeline/started.json
A	reports/improvement/runs/final_targeted/finished.json
A	reports/improvement/runs/final_targeted/started.json
A	reports/improvement/runs/phase1_development_v1/finished.json
A	reports/improvement/runs/phase1_development_v1/results.json
A	reports/improvement/runs/phase1_development_v1/started.json
A	reports/improvement/runs/prepare_v1/finished.json
A	reports/improvement/runs/prepare_v1/started.json
A	reports/improvement/runs/release_frontline_eval/finished.json
A	reports/improvement/runs/release_frontline_eval/started.json
A	reports/improvement/runtime/baseline_eval/reports/qubot/eval/eval_2026-10-31.md
A	reports/improvement/runtime/final_eval/reports/qubot/eval/eval_2026-10-31.md
A	reports/improvement/runtime/release_eval/reports/qubot/eval/eval_2026-10-31.md
A	reports/improvement/source_checkout_status.txt
A	reports/improvement/split_audit.json
A	reports/improvement/ui_desktop.png
A	reports/improvement/ui_desktop_v2.png
A	reports/improvement/ui_desktop_v3.png
A	reports/improvement/ui_mobile.png
A	reports/improvement/ui_mobile_v2.png
A	reports/improvement/ui_mobile_v3.png
A	reports/improvement/validation_ledger_addendum.json
A	reports/improvement/verification_input_hashes.json
A	reports/improvement/verification_log_inventory.json
A	reports/improvement/verification_runs.json
A	reports/voice_validation/results.json
M	requirements-docker.txt
A	requirements-ml-improvement.txt
A	scripts/bootstrap_container_trust.py
A	scripts/docker_readiness.py
A	scripts/final_prospective_eval.py
A	scripts/ml_baseline_calibration.py
A	scripts/ml_improvement.py
A	scripts/ml_improvement_report.py
A	scripts/ml_score_snapshot.py
A	scripts/seal_prospective.py
A	scripts/voice_intake_probe.py
M	src/agents/intake.py
M	src/agents/orchestrator.py
M	src/ai_layer/complaint_evidence.py
M	src/ai_layer/intake_enhancer.py
M	src/ai_layer/meta_client.py
A	src/eval/improvement_detection.py
A	src/eval/improvement_metrics.py
A	src/eval/improvement_models.py
A	src/eval/improvement_monitoring.py
A	src/eval/improvement_protocol.py
A	src/eval/prospective_io.py
A	src/eval/prospective_research.py
A	tests/frontline/ai_layer/prospective_fixture.py
M	tests/frontline/ai_layer/test_baseten_backend.py
A	tests/frontline/ai_layer/test_final_prospective_eval.py
A	tests/frontline/ai_layer/test_ml_improvement.py
A	tests/frontline/ai_layer/test_prospective_seal.py
M	tests/frontline/ai_layer/test_report_handoff.py
M	tests/frontline/test_backlog_p0_p1.py
A	tests/frontline/test_container_migrations.py
A	tests/frontline/test_container_trust_bootstrap.py
M	tests/frontline/test_dashboard_ui_surface.py
M	tests/frontline/test_deploy_hygiene.py
M	tests/frontline/test_live_handoff_outcomes.py
M	tests/frontline/test_mapping_ingest.py
M	tests/frontline/test_safety_gate_preemption.py
A	tests/frontline/test_voice_report_repair.py
M	tests/frontline/test_voice_tierA_wiring.py
M	tests/frontline/test_wallboard_labels.py
```

## Production source and dashboard changes already on the branch

These include readiness, voice intake, authentication/navigation and ML
research work, not merely the final reporting change:

```text
dashboard/package.json
dashboard/public/review-scripts/evidence-review.js
dashboard/public/review-scripts/reviewer-study.js
dashboard/routes/CallWidget.jsx
dashboard/routes/DefectLevel.jsx
dashboard/routes/DemoMode.jsx
dashboard/routes/JudgeEntry.jsx
dashboard/scripts/assert-qa-labels.mjs
dashboard/scripts/assert-signin-reachable.mjs
dashboard/scripts/check-public-links.mjs
dashboard/scripts/container-readiness.test.mjs
dashboard/scripts/ml-evidence-ui.test.mjs
dashboard/scripts/public-link-scope.mjs
dashboard/scripts/public-link-scope.test.mjs
dashboard/scripts/report-handoff.test.mjs
dashboard/scripts/speech-draft.test.mjs
dashboard/scripts/voice-capture.test.mjs
dashboard/scripts/voice-ui.test.mjs
dashboard/src/App.jsx
dashboard/src/ai/MlImprovementEvidence.jsx
dashboard/src/ai/ml-improvement-evidence.css
dashboard/src/ai/mlImprovement.json
dashboard/src/speechDraft.js
dashboard/src/styles.css
dashboard/src/ui/opsActions.js
dashboard/src/voiceExperience.js
dashboard/src/voiceHelpers.js
src/agents/intake.py
src/agents/orchestrator.py
src/ai_layer/complaint_evidence.py
src/ai_layer/intake_enhancer.py
src/ai_layer/meta_client.py
src/eval/improvement_detection.py
src/eval/improvement_metrics.py
src/eval/improvement_models.py
src/eval/improvement_monitoring.py
src/eval/improvement_protocol.py
src/eval/prospective_io.py
src/eval/prospective_research.py
```

## Test additions and changes

```text
dashboard/scripts/assert-qa-labels.mjs
dashboard/scripts/assert-signin-reachable.mjs
dashboard/scripts/check-public-links.mjs
dashboard/scripts/container-readiness.test.mjs
dashboard/scripts/ml-evidence-ui.test.mjs
dashboard/scripts/public-link-scope.mjs
dashboard/scripts/public-link-scope.test.mjs
dashboard/scripts/report-handoff.test.mjs
dashboard/scripts/speech-draft.test.mjs
dashboard/scripts/voice-capture.test.mjs
dashboard/scripts/voice-ui.test.mjs
tests/frontline/ai_layer/prospective_fixture.py
tests/frontline/ai_layer/test_baseten_backend.py
tests/frontline/ai_layer/test_final_prospective_eval.py
tests/frontline/ai_layer/test_ml_improvement.py
tests/frontline/ai_layer/test_prospective_seal.py
tests/frontline/ai_layer/test_report_handoff.py
tests/frontline/test_backlog_p0_p1.py
tests/frontline/test_container_migrations.py
tests/frontline/test_container_trust_bootstrap.py
tests/frontline/test_dashboard_ui_surface.py
tests/frontline/test_deploy_hygiene.py
tests/frontline/test_live_handoff_outcomes.py
tests/frontline/test_mapping_ingest.py
tests/frontline/test_safety_gate_preemption.py
tests/frontline/test_voice_report_repair.py
tests/frontline/test_voice_tierA_wiring.py
tests/frontline/test_wallboard_labels.py
```

Phase 5 specifically adds a real browser entry point and verifies prospective
notices, unchanged denominators/CIs, unavailable human accuracy, mobile fit,
and refusal to publish changed score/source values. Synthetic prospective tests
cover flags, custody paths/markers, duplicates, dates, hash chain, attestation,
dirty tree, cutoff, sample floor, one-shot behavior and the 25-campaign fixture.
They prove refusal paths and tamper evidence, not cross-identity access control.

## Validation, preserved artifacts and risks

See `final_validation_phase1.json` for fresh observed counts, exact commands,
all attempts and log hashes. Main and the original checkout remain unchanged;
all frozen dependencies/index/tag hashes verify. No numerical dashboard score
changed. The approved historical-preparation amendment is retained in
`../prospective/DEVIATIONS.md`; no historical no-read claim is fabricated.

Risks: tiny development corpus; 0/300 human labels; public outcomes and
procedural custody; an underpowered future sample; the 2027–2029 collection and
follow-up wait; future availability of pinned classification provenance; and
17 unrelated readiness commits bundled into a merge. No improved score has
been demonstrated. The old evaluation-count parser error is corrected by the
new observed 23/23 gate record without rewriting the old log.

Merging now is optional because the local branch and immutable tag are enough
to review the demo and operate the future test. Pre-production requirements:
independent human labels, the prospective result, monitoring, security review,
and separate explicit human approval. No merge may rewrite frozen commits or
move `ml-prospective-freeze-2026`.

## Final engineering topology

Phase 5 commit `3a50479260598d48891aa883006d6fcbf61226e5` is 30 commits ahead of unchanged main.
The containing Phase 6 documentation commit adds one, yielding 31.
The 17 unrelated readiness commits remain included. The freeze tag still
resolves to `e96338df3cce113a182b0cf1be5bf760abc00b31`. No merge or promotion occurred.
