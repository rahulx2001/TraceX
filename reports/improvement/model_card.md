# Research model card

Status: evaluation tooling and baseline diagnostics; no promoted candidate.
The approved ambitions are in `research_protocol.json`. None has been demonstrated
on a new untouched test set. Human labeling was waived for this run, so human
classification accuracy remains unavailable.

## Intended use and scope

Offline investigation of early complaint signals and review of retrospective
recall matches. Defect scope: Ford, Honda, Hyundai, Kia and Toyota; model years
2015–2024; FUEL SYSTEM; official vehicle recalls. Category-template diagnostics,
the expanded fuel/propulsion holdout, and the all-component safety/OOS experiments
are separate benchmarks with distinct denominators.

Training/evaluation records are self-reported NHTSA complaints. Specific defect
labels are existing Muse Spark outputs, with a train-recall-derived taxonomy.
They are hypotheses, not independently verified physical defects. Recalls are
matched by make, component and specific label, with the original 7–364-day horizon,
completed-week availability, 91-day cooldown and full-follow-up precision rule.
Unknown labels never match; campaigns with unknown labels stay in recall.

## Implemented research methods

Count and frozen Gamma-Poisson references; local logistic and gradient-boosting
baseline adapters; TF-IDF and embedding logistic classification adapters; independent
Platt/isotonic calibration with support and split checks; precision/coverage and
fixed-pool query retrieval evaluation. New feature extraction records counts,
acceleration, official crash/fire/injury/death indicators, missing severity fields,
model diversity, text signals, duplicate fraction and explicit recall mentions.
These tools are not connected to production alert selection.

Supervised methods require sufficient mature outcomes. Calibration requires
independent examples, not resubstitution. No model may be selected on the opened
2021–2024 OOS or 2025 holdout. A prospective reservation alone does not authorize
claiming a final test: actual frozen data, access provenance and complete follow-up
are also required. The outstanding reservation/development question is recorded
in the conversation; the runner fails closed without explicit authorization.

## Current evidence and limits

`results.json` embeds the immutable baseline and separate pre-2021 audit.
The pre-2021 corpus has 263 complaints and 36 campaigns. Under the fixed labels,
only 7/36 campaigns have preceding matching evidence, or 4/36 after excluding
recall mentions. These are corpus opportunity counts, not achieved recalls or
universal ceilings. With any preceding same-make fuel complaint the corresponding
counts are 29/36 and 27/36; that broader opportunity is not specific-defect evidence
and cannot be substituted into the matching rule.

The frozen detector's pre-2021 results are 3/36 campaign recall (Wilson 95%:
2.9%–21.8%) and 1/3 mature-alert precision (6.1%–79.2%). Sensitivity results are
1/36 recall (0.5%–14.2%) and 0/1 precision (0%–79.3%). These denominators differ
from the historical 41-campaign reanalysis; no improvement comparison is valid.

The baseline calibration diagnostic treats `1 - predictive_tail` as a putative
probability solely to quantify unreliability. It is not calibrated defect risk.
Its units are mature candidate weeks, not deployed alert episodes. Validation
support is only 9 candidates in the all-report slice and 2 in sensitivity, and
there is no mature pre-2019 training-prevalence reference. No Brier superiority
claim or calibrated operating-point selection is justified.

The old retrieval fixture's novel_true slice has zero positives. The replacement
evaluator requires mixed relevant/irrelevant candidate pools, at least k distinct
candidates per query, and a fixed denominator. Independent relevance data and
stronger embedding comparisons remain unavailable; toy tests establish code
behavior only.

## Non-use

Do not use these scores as physical-defect probabilities, proof of identical
affected parts/vehicles, accident-prevention estimates, customer accuracy, or
production superiority. Do not use model-generated annotations as human labels.
Do not remove censored alerts, misses or hard examples to meet targets. Do not
promote without independent evidence and human sign-off.

Modern teacher pretraining may contain historical recall information; source
snapshots may contain revised narratives. Related campaigns, repeated candidate
weeks, no fleet/exposure denominator, sparse early data and reporting bias limit
generalization and confidence-interval interpretation.

## Operational controls

The dashboard is generated from `results.json`, with source-hash and value checks.
It displays denominators, definitions, confidence intervals and the visible
retrospective/model-labelled/not-production-validated notice. Runtime telemetry
is advisory: see `monitoring_plan.md`. Frozen historic report replays remain a
required regression check. Final verification is recorded separately in
`final_validation.json`; a passing software test is not an ML accuracy result.
