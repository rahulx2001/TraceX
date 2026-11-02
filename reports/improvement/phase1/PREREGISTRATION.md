# Prospective fuel-defect replication or candidate comparison

Version 1. Date 2026-10-31T15:10:06.484940+00:00. Author Rahul Kumar Singh; prepared by the ML improvement
engineer. Repository v2_ai_rca_tool; branch ml-score-improvement. Recorded source
commit `0d088f6ddcb869482427578cb0c02a6758fdbe17`. The first commit containing this document is the preregistration
event; its hash is resolved from git history and pinned in the freeze.

## Background and baseline

Historical-opened evidence only; no candidate result. Label source: model
complaint/recall labels and official recall dates. The 2025 holdout includes the
separate expanded fuel/propulsion source definition; it is not substituted for
the repaired fuel benchmark. Category rows are authored diagnostics, not
acceptance-eligible semantic accuracy. Full row-level provenance (commands,
config/data hashes, commit, scope) remains in ../baseline.json.

| Benchmark metric | Numerator / denominator | Value | Descriptive 95% CI |
|---|---:|---:|---:|
| defect.all_reports.rolling_defect.recall | 22/41 | 53.659% | 38.7%–67.9% |
| defect.all_reports.rolling_defect.mature_episode_precision | 14/31 | 45.161% | 29.2%–62.2% |
| defect.excluding_explicit_recall_reports.rolling_defect.recall | 14/41 | 34.146% | 21.6%–49.5% |
| defect.excluding_explicit_recall_reports.rolling_defect.mature_episode_precision | 7/13 | 53.846% | 29.1%–76.8% |
| fuel_holdout.method.recall | 5/8 | 62.500% | 30.6%–86.3% |
| fuel_holdout.method.mature_episode_precision | 6/18 | 33.333% | 16.3%–56.3% |
| category.labels.accuracy | 4/76 | 5.263% | 2.1%–12.8% |
| category.descriptions.accuracy | 22/76 | 28.947% | 20.0%–40.0% |

## Scope and definitions

Ford, Honda, Hyundai, Kia and Toyota; model years 2015–2024; repaired FUEL SYSTEM
definition; vehicle recalls; unchanged taxonomy and model provenance from
reports/defect/repair/protocol.json. A campaign is a unique official campno,
with all scope rows kept together. An eligible campaign has an in-scope vehicle
row and an official date in 2027–2028. Unknown labels and campaigns without
preceding complaints remain in the recall denominator. Unknown labels never
establish a match. Matching is make + component + specific defect label, not
physical-part identity. Completed-week availability, 91-day cooldown and
7–364-day lead/confirmation horizon stay unchanged.

A mature alert has complete 364-day follow-up by the outcome cutoff; censored
alerts remain reported separately even when a match is already known. The
sensitivity slice excludes explicit recall/campaign mentions using the existing
regex. Development means 2015–2020; historical-opened means inspected 2021–2026;
prospective-sealed means the future reserved cohort under procedural custody.

## Conditional hypotheses

Mode A: H1 candidate improves campaign recall; H2 candidate improves mature-alert
precision; H3 gains do not depend on explicit recall mentions. Mode B: H1 is
prospective replication of historical baseline estimates. Mode B has no
improvement hypothesis and cannot demonstrate improvement.

## Primary and secondary outcomes

Recall = unique detected eligible campaigns / all eligible 2027–2028 campaigns.
Precision = confirmed mature alert episodes / all mature episodes issued in
2027–2028. Precision may use qualifying later recalls through 2029-12-31; these
2029 confirmations do not enlarge the primary recall denominator. The existing
evaluator is called separately for these two declared windows; its matching
and full-follow-up rules are unchanged. No rows are removed to improve scores.
Secondary outcomes: sensitivity recall/precision, median lead among detected
campaigns (with support), total/censored alerts, per-make descriptive rates,
and ECE/Brier only if a calibrated score is used. Gamma-Poisson tails are not
calibrated probabilities; no ECE claim is made for that ranking score.

## Window, sample and timeline

Flags: 2027-01-01 through 2028-12-31. Outcomes: through 2029-12-31. Freeze by
2026-12-31; final analysis by 2030-06-30. Minimum 25 eligible campaigns with
complete follow-up; prefer 30. One final analysis. Below 25: INCONCLUSIVE_SAMPLE,
counts only, no performance metrics. Stop; a human may preregister an extension
before any metric access. Never lower the threshold after seeing data.
The opened 2025 cohort had 8 campaigns; 2021–2024 had 41 across four years
(10.25/year). One year is underpowered for a 70% versus 50% recall comparison.
Two years and a sample floor improve the chance of an interpretable estimate;
they do not guarantee power or narrow intervals.

## Development and opened periods

Development only: 2015-01-01–2020-12-31. Fold A fits through 2016-12-31 and
validates 2017–2018. Fold B fits through 2018-12-31 and validates 2019–2020.
Campaign groups cannot cross fit/validation. Calibration, if supportable, stays
inside the fit fold with disjoint identities; never use validation outcomes.
Runtime date assertions reject every 2021+ development row. 2021–2024 OOS,
2025 fuel holdout and 2026 safety backtest are descriptive history only: no
fitting, feature choice, calibration, thresholding or model selection.

## Selection and decision rules

A candidate is defensible only if it does not lose on either primary metric in either fold; and it improves at least one primary metric in both folds; and the lower bound of the paired campaign-cluster bootstrap difference for that metric is greater than 0. Otherwise freeze the baseline.

Undefined metrics cannot satisfy the rule. The same primary metric must improve
in both folds, with positive lower bounds for all five fixed bootstrap seeds.
Ties use the preregistered model order. No forced fit with fewer than 10 labelled
rows or one class. Fixed count thresholds 2/3/5 and small numpy logistic at 0.5
are the alternatives; baseline Gamma-Poisson uses window 13, min_count 2,
max_tail 0.2. No boosting/embedding fine-tuning or new model-generated labels.
Features and fixed fitting settings are enumerated in protocol.json.

Mode A target met requires recall >=70% AND precision >=80%. Improvement
confirmed separately requires lower paired cluster-bootstrap differences >0
for BOTH primaries for every seed. Either estimate below concurrent baseline,
or losing in either development fold, is failure. Intervals that cannot
separate methods are inconclusive. Mode B reports estimates and CIs only,
without 70/80 improvement gates. Sensitivity and every failed run stay visible.

## Analysis, uncertainty and freeze

Include all campaigns, misses and alerts; no imputation or cherry-picking.
Wilson 95% rate intervals are descriptive. Paired campaign-linked component
bootstrap: 2,000 draws for each seed 17, 29, 43, 71, 101. Link campaigns sharing
matched alerts across either method; retain unmatched-alert key/date components
so false positives are not discarded. Record undefined draws; fewer than 95%
valid draws means unavailable interval. Report all equal-budget count and
100 random-reference seeds 2026103100–2026103199.
Freeze code, config, threshold, JSON model (no pickle), parser/label provenance
and analysis script; tag ml-prospective-freeze-2026. Hash every dependency used
by the analysis. Mode choice is made once by Phase 2, not by future outcomes.

## Custody and sources

Custodian Rahul Kumar Singh; encrypted APFS image outside the repository, human
passphrase only. Procedural custody is tamper-evident, **not enforced access
control**. Public NHTSA outcomes can be re-fetched; no-peeking is honor-system.
The manifest chains each committed prior hash; a committed human attestation
is required before final analysis. Local git timestamps are not independent
time proofs. External timestamp status is reported honestly. See CUSTODY.md.
Sources: official FLAT_CMPL.zip and FLAT_RCL_POST_2010.zip at the URLs in
protocol.json. Quarterly snapshots preferred; annual minimum in 2027–2028,
plus a final outcome snapshot through cutoff. No fetching during this task.

## Input contract, deviations and limitations

Final analysis requires complete externally supplied classification artifacts
with the pinned model/prompt/taxonomy provenance, using the original join and
coverage checks. The harness does not call a paid model or fabricate labels;
missing coverage makes analysis unavailable. A provider/version unavailable
in 2030 is a reproducibility risk, not permission to substitute a classifier.
Human labels remain 0/300. Recall-confirmed precision is not semantic truth.
This is a prospectively frozen replay of collected records, not a historical
holdout or proof of live deployment benefit. Received-date availability and
snapshot revisions/publication delays limit lead-time interpretation. The
first snapshot version of each record is retained; no new campaign is dropped.
The scope is fuel only, the sample is small, public outcomes cannot be hidden
from a determined developer, and replication may remain inconclusive.
Every deviation after freeze is append-only: date, reason, approver, affected
files and effect on claims. No silent denominator, threshold or window changes.
