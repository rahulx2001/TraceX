# Expanded fuel-source holdout — 29 October 2026

**The requested campaign recall above 86% was not achieved.** The frozen
2025 experiment detected **5/8 campaigns (62.5%)**. It matched the fixed count
baseline and had **6/18 (33.3%) mature-alert precision**. No candidate met the
development precision requirement, so this method is not promoted to production.
These are measured historical matches against model-labelled references, not
human-validated classification accuracy or proof of accidents prevented.

## Measured results

Source: [holdout_results.json](holdout_results.json). All eight scoped campaigns
remain in the denominator, including misses and an unknown defect label.

| Strategy on the same 2025 inputs | Campaign recall | Alerts | Mature alerts matching later campaigns |
|---|---:|---:|---:|
| Frozen selected method | 5/8 (62.5%) | 24 | 6/18 (33.3%) |
| Fixed count baseline | 5/8 (62.5%) | 24 | 6/18 (33.3%) |
| Random reference, 100 runs | 44.375% mean | 24 per run | Individual runs preserved in JSON |

The selected detector is itself the 13-week count policy, using a ridge
classifier trained on existing Meta labels. There is no measured advantage over
that baseline. Nineteen of 100 workload-matched random runs reached or exceeded
62.5% recall; this is not convincing evidence of superiority to random selection.
The random reference is a conditional historical comparison using each month's
candidate pool, not a deployable online policy.

The descriptive Wilson 95% interval for recall is **30.6%–86.3%**. Eight campaigns
are too few for a precise estimate, and related campaigns need not be independent.
The interval's upper endpoint is not an achieved score. Median lead time among
the five matched campaigns was 25 weeks, measured from the earliest matching
alert. Matches use make plus model-assigned defect category, not verified model,
model-year or physical-part identity; one alert can match multiple campaigns.

Precision uses a full 364-day follow-up. Outcomes were observed through
2026-09-30, leaving 18 mature alerts and six without complete follow-up. Twelve
of the mature alerts had no qualifying later campaign. A missing campaign match
does not prove that no underlying defect existed.

## Campaign audit

| Campaign | Recall date | Make | Detected | Earliest matching alert lead |
|---|---|---|---|---:|
| 25V028000 | 2025-01-22 | TOYOTA | No | — |
| 25V031000 | 2025-01-23 | HONDA | No | — |
| 25V165000 | 2025-03-14 | FORD | Yes | 32 days |
| 25V455000 | 2025-07-07 | FORD | Yes | 175 days |
| 25V467000 | 2025-07-11 | FORD | No; reference label is `other_unclear` | — |
| 25V597000 | 2025-09-11 | FORD | Yes | 213 days |
| 25V794000 | 2025-11-17 | KIA | Yes | 7 days |
| 25V796000 | 2025-11-17 | HYUNDAI | Yes | 245 days |

The opportunity diagnostic found preceding make/category evidence for 7/8
campaigns. **87.5% is an input-opportunity diagnostic, not achieved prediction
recall.** It ignores alert competition and may count evidence from before the
evaluation start. Changing the denominator to only reachable campaigns would
misrepresent the declared task.

## What was improved and tested

The earlier repaired input contained only `FUEL SYSTEM` complaints. Its
[opportunity diagnostic](original_input_ceiling.json) found prior specific-defect
evidence for 29/41 campaigns, or 27/41 after excluding explicit recall mentions.
These bounds are conditional on those labels and the 7–364-day horizon; they
are not universal limits on prediction. Strictly above 86% would require 36/41.

This experiment also includes `FUEL/PROPULSION SYSTEM`, with complaint IDs
deduplicated across the two codes. That source includes unrelated propulsion
issues, so an explicit unknown class and low-margin abstention remain necessary.
The target population remains Ford, Honda, Hyundai, Kia and Toyota, model years
2015–2024, with vehicle fuel-system recalls and complete scope rows.

| Input partition | Deduplicated complaints | After excluding explicit recall/campaign mentions |
|---|---:|---:|
| Development, 2015–2024 | 9,726 | 5,761 |
| Holdout, 2025 | 2,719 | 1,350 |

Fixed local MiniLM embeddings feed ridge or nearest-centroid classifiers.
Training targets are existing Muse Spark Open classifications, not human labels:
940 examples dated through 2020 for development, then 1,999 dated through 2024
for the final refit. No new model API calls were made for this experiment.

Forty combinations of classifiers and count, Gamma-Poisson and CUSUM detectors
were compared across 2021–2022 and 2023–2024. The predeclared gate required at
least 50% mature-alert precision and at least three mature alerts in **both**
folds. **Zero candidates qualified.** The fallback retained the candidate with
the highest mean harmonic score of campaign recall and mature-alert precision
as a diagnostic, not as an approved model. The protocol calls this score F1;
its two inputs use different evaluation units, so it is not ordinary
per-example classification F1.

| Selected candidate development fold | Recall | Mature-alert precision |
|---|---:|---:|
| 2021–2022 | 9/21 (42.9%) | 6/18 (33.3%) |
| 2023–2024 | 12/20 (60.0%) | 9/25 (36.0%) |

The final selection was ridge plus 13-week counts, minimum two complaints.
All 40 trials, selection rules and frozen hashes are preserved in
[selection.json](selection.json). No global claim of the "best method" is made.

The [protocol](protocol.json) was recorded before holdout scoring. The alert
budget is at most one per week and two per month, with a 91-day make/defect
cooldown. Alerts use completed weeks only and require new complaints; matching
requires 7–364 days of lead. Unknown labels never match. The 2025 outcomes were
scored once after selection and have not been used to retune the method.

## Reproduce the recorded result

From the repository root, using the existing Python 3.12 environment and frozen
local inputs:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.fuel_holdout verify
```

Exact replay passed for the method, count policy, opportunity diagnostic and all
100 random runs. This command checks the selection hash, recorded evaluation
code hashes, derived input hashes, embedding arrays and classifier weights,
then compares results excluding only the evaluation timestamp. Replay is not a
new independent test. Do not rerun `test`, replace the holdout marker, or tune
against these results.

The earlier repaired experiment also replayed exactly. The dashboard build
passed, and the published summary was checked against the holdout's metrics and
source hash. Targeted regression tests cover temporal features, abstention,
duplicate handling, alert budgets, outcome follow-up and random-reference
reproducibility. These checks establish implementation consistency, not
predictive validity.

The original sequence was `prepare`, `encode`, `develop`, `test` in
`scripts.fuel_holdout`. Preparation and selection refuse to overwrite their
existing records. Gitignored inputs are in `data/defect/fuel_holdout/`; source
ZIPs are in `data/defect/source_cache/`. Their hashes are in `protocol.json`.
For another machine, transfer the exact frozen artifacts; a fresh NHTSA download
may differ and cannot reproduce this recorded run automatically.

To regenerate the dashboard's local evidence summary:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.defect_publish
cd dashboard
npm run build
```

## What remains unproven

The 300-example [blind human review](../repair/human_review.html) is still
**0/300 completed**. No model-generated labels were entered as human answers.
The sample assesses the earlier classifier; it does not independently validate
this student on expanded propulsion inputs. Recall labels also need independent
human review.

This is a locally held-out historical test. The contemporary NHTSA snapshot may
contain revised narratives, and the Meta teacher may know historical recalls
from pretraining. Excluding explicit recall mentions reduces one leakage route;
it does not eliminate all leakage. The original 6/269 partial run and the earlier
41-campaign reanalysis remain separate: **62.5% is not a same-benchmark rise from
2.2%.**

Further progress requires independently reviewed complaint and recall labels,
better coverage before incidents, validation of actual vehicle/part matches,
and a newly reserved future evaluation period. More iteration on this opened
holdout cannot provide a new unbiased validation. The current evidence does
not support an above-86% prediction pitch.
