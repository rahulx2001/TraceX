# Trained logistic prototype — unvalidated

Development-only evidence; not a candidate result and not a prospective estimate.

One fixed numpy L2 logistic recipe fitted on 12 mature rows,
including 4 positive rows, from 2015–2020.
These rows cover only 2 distinct positive campaigns;
they are not independent observations. Features: complaints_30d, complaints_90d, complaints_365d, same_make_365d.
JSON contains feature order, means, scales, coefficients, intercept and the
fixed 0.5 threshold. No pickle, sklearn, new dependency, calibration, tuning,
paid call, new generated label or human semantic label was used.

Both registered training folds still have zero mature rows. No out-of-sample
performance metric is available for this full-development fit. No training-set
recall/precision is presented as an improvement. JSON reproduction error is
0.0; this proves serialization fidelity, not predictive quality.

The existing frozen baseline and 2027–2028 Mode B prospective test are unchanged.
This prototype is excluded from that test and is neither freeze- nor production-
eligible. A new pre-registered comparison and adequate independent training and
evaluation evidence would be needed before any better-model claim.

The blank review queue contains 160 existing unclear complaint IDs.
No human review has been performed; human semantic labels remain 0/300. Review
requires the original pre-2021 source records and the existing labeling guide.
Labels alone cannot create missing early observations or complete follow-up.

Split: development, full 2015–2020 fit only. Label source: Existing frozen model hypotheses plus official recall dates. No human labels, new model-generated labels, or unknown-label matches.
Scope: unchanged five makes, MY2015–2024, repaired FUEL SYSTEM.
Baseline comparison: none; historical recall/precision remain unchanged.
Exact command: `FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -B -m scripts.ml_candidate_research --run-id logistic_prototype_v1`.
Config hash: `f60f52788b13ba44f1d03e21a1baecccd27725566ed31776e7cfed063c02cfc9`.
Data hash: `9b57071fbcf71f2680dcc412f2bb3b9799c076c2b38c60f973302c713afad4be`.
Code commit: `534a6ae0b78f19cc9b815dd5f78c890ae188e382`.
Is this a validated candidate result? No. Performance values and CIs: unavailable.
