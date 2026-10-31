# ML improvement: Phase 0 score check and proposed protocol

Status: baseline checked; modeling blocked pending human decisions. No measured
improvement, trained candidate, new final result, or promotion is claimed.

Work is isolated on `ml-score-improvement` in the sibling worktree
`v2_ai_rca_tool_ml-score-improvement`, based on commit
`13c5ff105b3a867b949e53e51a3a1ce352377466`. The original checkout has unrelated
uncommitted work recorded in `source_checkout_status.txt`; it was not copied
into this branch. Verification therefore covers the committed baseline.

## Checked scores and provenance

`baseline.json` contains the score inventory, denominators, descriptive Wilson
intervals, source paths/keys/hashes, known configuration and input hashes,
commands and verification commit. Unrecorded historical provenance stays null
or explicitly unavailable. `pipeline_recheck.json` is a new diagnostic output;
the historical pipeline report was preserved. The pipeline command adds `--out`
solely to avoid overwriting an existing report.

`verification_runs.json`, `experiments.csv`, and `logs/` preserve every executed
verification run, including the expected human-accuracy refusal. The model
and input artifacts used for replay are inventoried in
`verification_input_hashes.json`. Python and Node dependencies were reused from
the original checkout; this is not a clean-environment reproducibility claim.

- Repair: both variants and all recorded random draws replay exactly.
- Fuel holdout: method, count reference, opportunity diagnostic and all random
  draws replay exactly.
- ONNX pipeline: category diagnostics reproduce the saved results.
- Targeted regression command: all tests passed; see its log for counts.
- Dashboard build passed with bundle-size/import warnings.
- Human accuracy: refused with zero valid labels; all frozen review rows have
  model predictions. Human accuracy remains undefined.
- Safety and OOS figures were read from their recorded results, not rerun as
  new tests. The historical OOS raw source hash differs from the newer source
  snapshot, as already recorded in `reports/CLAIMS_AUDIT.md`.
- Full `make test`, `make eval-frontline`, sign-in E2E, and clean-environment
  reproduction remain required before final success. This is not final validation.

`original_artifact_hashes.json` and `artifact_integrity_check.json` confirm the
original reports and dashboard evidence artifact remained byte-identical during
this check. No frozen report or model configuration was regenerated.

The pair diagnostic needs special care: its `novel_true` class has no positive
labels, and class-specific ranking separates negative-only candidates from the
positive controls. Its zero P@5 is a recorded fixture result, but cannot establish
novel-match recall. Preserve it and add an independent mixed-candidate benchmark
after approval; changing the old denominator is not a valid improvement.

## Proposed splits; not yet approved or certified

Keep five makes (Ford, Honda, Hyundai, Kia, Toyota), model years 2015–2024,
and the repaired FUEL SYSTEM input definition. Expanded fuel/propulsion inputs
remain a separate benchmark. Neither can be substituted for the other.

Candidate rolling-origin folds:

| Fold | Training cutoff | Validation campaign window |
|---|---|---|
| A | 2016-12-31 | 2017-01-01 through 2018-12-31 |
| B | 2018-12-31 | 2019-01-01 through 2020-12-31 |

Use only labels/outcomes available by each training cutoff. Use received dates,
completed-week availability, the existing 7–364-day match horizon and 91-day
cooldown. Preserve every validation campaign and miss, including unknown labels.
Use the existing full-follow-up precision rule; report censored alerts separately.
Campaign scope rows stay grouped by campaign ID. Prior complaints may supply
causal history, but validation outcomes must not enter features or fitting.

`split_audit.json` records counts and duplicate checks on all repaired complaints.
It found no cross-split ODINO/campaign IDs or normalized exact/near-text pairs
under the declared five-token Jaccard >=0.80 check. This does not rule out semantic
paraphrases. No complaints were removed. There is no reliable complaint-to-
physical-campaign mapping, so campaign-independent complaint training is not
certified. Initial training support is very small; the audit records the actual
counts. Do not enlarge the scope merely to improve the metric.

2021–2024 and 2025 are already opened, locked historical evaluation sets.
The existing safety report includes 2026 recall outcomes. No same-scope recent
window has been established as untouched. The unopened `evidence_v1` cohort uses
different makes and is not an authorized substitute. A new test data manifest,
custodian/access record and immutable hashes are required before any tuning.
Otherwise reserve future same-scope accrual with a complete follow-up period;
do not label an already inspected period as new.

The frozen human review sample is from 2021–2024. It can evaluate the fixed
classifier, but must not train a new classifier while preserving the OOS ban.
Supervised development needs additional independent pre-2021 human labels.

## Proposed targets and utility, awaiting approval

These are aspirations on a newly reserved evaluation set, not permission to
retune the opened holdout. Compare baseline and candidate on the same untouched
units; use paired, campaign-cluster uncertainty and retain every seed and slice.
Changing evaluation periods creates a new benchmark, not a direct percentage-point
improvement over historical reports.

| Area | Minimum | Stretch |
|---|---|---|
| Human review | 300/300 plus at least 50 independently double-labelled | Cohen's kappa >=0.80 |
| Category labels accuracy | >=25% | >=50% |
| Category descriptions accuracy | >=45% | >=65% |
| Accepted precision / coverage, each profile | >=60% / >=30% | >=80% / >=40% |
| Hard-negative P@5 on valid independent benchmark | >=0.30 | >=0.60 |
| Novel-true P@5 on valid independent benchmark | >=0.20 | >=0.50 |
| Defect campaign recall / mature precision | >=55% / >=55% | >=65% / >=65% |
| Harmonic recall/precision objective | >=0.55 | >=0.65 |
| No-explicit-recall slice: recall / precision | >=40% / >=55% | >=50% / >=65% |
| New holdout recall / precision | >=62.5% / >=50% | >=75% / >=60% |
| Recent campaign recall | >=50% | >=60% |
| Validation-calibrated ECE | <=0.10 | <=0.05 |

Proposed development utility per fixed evaluation window:
`5 * detected_campaigns - 2 * unconfirmed_mature_alerts - 0.1 * total_alerts`.
This values campaign detection while charging investigation workload. Treat
55% recall and 55% mature precision as joint gates, not interchangeable rewards.
Report both rates, their units/intervals, volume, maturity and sensitivity results
beside utility; the harmonic objective is not ordinary per-example F1.
Keep equal-alert-budget count and random comparisons. Utility weights require
human approval; they are not inferred monetary or accident-prevention values.

Proposed candidate seeds: `[17, 29, 43, 71, 101]`; random reference seeds:
`2026103100` through `2026103199`, all reported. No candidate runs have started.
Freeze the approved protocol, label provenance, data and code hashes before runs.

## All known problems and remaining work

| Problems | Required action / current gate |
|---|---|
| 1–2: missing and circular labels | Human complaint and recall review; independent pre-2021 training labels; no physical-defect truth claim |
| 3–4: weak category diagnostics | Grouped template/paraphrase split, approved stronger local embeddings, supervised development, abstention curves |
| 5: retrieval | Independent mixed-candidate relevance labels with positive controls; preserve old fixture scores |
| 6–7: precision and recall mentions | Development-only count/logistic/boosting/Gamma-Poisson comparison; severity/text features; mandatory sensitivity slice |
| 8–9: recent performance and random advantage | Keep recent-window campaign units and equal budgets; paired baseline differences and all random runs |
| 10–12: tiny holdout, missed gate, narrow scope | Untouched same-scope accrual; intervals and support floors; no promotion or generalization claim |
| 13–14: metric/lead confusion | Explicit source, horizon, denominator and detected-unit lead support in the inventory |
| 15: calibration | Validation-only Platt/isotonic; ECE, Brier and reliability plot with mature outcomes |
| 16: error analysis | Blind review of at least 50 unique FP and 50 unique FN from development; if too few, report actual ceiling, never duplicate rows |
| 17: monitoring | Weekly volume/abstention/feature drift by make/component/year; delayed mature precision; recall after official outcomes; versioned monthly human audits; human escalation for failed gates |
| 18: dashboard drift | Source hash validation and generated improvement JSON only after verified results exist |
| 19: sign-in E2E | Verify/install Chromium and run the sign-in test during final validation; build alone is insufficient |
| 20: fragmented evaluation | Per-run provenance ledger and metric-level definitions; separate benchmarks |

## Human decisions needed

Approve or revise the target table and utility weights, identify the human
reviewer/adjudicator workflow, and establish a custodian-verified untouched
same-scope test window (or approve prospective accrual). These are the user's
explicit Phase 0 and stop-condition gates. Until then modeling remains blocked.
Later-phase deliverables (`results.json`, completed error review, model card,
generated dashboard results, and a before/after claim) are intentionally pending
the evidence required to produce them honestly.

## Approved ambition and execution update

The user approved the revised stretch targets and waived performing human
annotation in this run. The approved target values and prespecified methods are
in `research_protocol.json`. Earlier target tables and pending-approval language
above are preserved as history. No human accuracy claim is authorized. The
prospective-test/development authorization question remains pending; preparation,
read-only development audit and engineering tests can proceed independently.

## Current review package

The current outcome and the disposition of all original problems are in
[`FINAL_REVIEW.md`](FINAL_REVIEW.md). The original Phase 0 text above is retained
as history. Targets were approved and human annotation was deferred. No candidate
model was trained, no untouched-test improvement was demonstrated, and no merge
or promotion occurred. The prospective-test/development decision is still pending.

Delivered: immutable baseline and run ledger; pre-2021 manifest/split audit;
labeling guide; causal feature and baseline-model tooling; calibrated-metric,
abstention and retrieval evaluators; complete available machine error inventory;
model card and monitoring plan; source-generated dashboard with definitions,
denominators, intervals and the retrospective/model-labelled notice. The error
inventory is smaller than the requested review quota, and toy model tests do
not establish real-world accuracy.

[`before_after.md`](before_after.md) and [`before_after.json`](before_after.json)
show unchanged scores with provenance. [`final_validation.json`](final_validation.json)
records software checks separately from ML evidence. The reproducibility check
uses a fresh Python environment with pinned dependencies, copied immutable
data/model inputs and semantic equality of full audit/calibration outputs;
pipeline comparisons exclude only runtime timings/throughput and commit ID.
See [`clean_reproduction_comparison.json`](clean_reproduction_comparison.json).

All original inventoried artifacts are checked at their actual source location
in [`artifact_integrity_release.json`](artifact_integrity_release.json). The
earlier `integrity_release_pre_docs.json` records files absent from the sibling
worktree: those are untracked/ignored originals that were never copied, not
deleted artifacts. Existing claims-audit content is preserved as an exact prefix.
