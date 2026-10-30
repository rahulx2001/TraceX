# Evaluation readiness — 30 October 2026

The evaluation software now distinguishes prepared-draft review, live
investigation work, broad historical alert matching and exact part/lot
association. **Human labels, independent packet grades and participant results
remain pending.** No model calls or invented participant records were created
for these fixes. The historical 5/8 recall and 6/18 mature-alert precision have
not changed.

## Review-point status

| ID | Implemented and testable now | Acceptance still requiring evidence |
|---|---|---|
| 27 | Separate live comparison of the complete existing deterministic workflow, extraction-only assistance and full investigation, with the same original report refs and missing/contradictory/irrelevant record tasks. Replay runs are rejected; original attempts, failures, deviations and costs remain visible. | Relevant people must perform independently reviewed tasks. No usefulness improvement or fact-recovery benefit has been measured. |
| 28 | The 32-record development review captures supported fields and reviewer expertise. An unfilled development error-analysis worksheet links every development record to any recorded outputs. Original 300, development 32, reserved 100 and recall 5 remain distinct. | The owner must recruit actual relevant reviewers. No human error analysis or participant result is complete. |
| 29 | Review instructions distinguish reported symptom, claimed part, suspected cause, timing, denial, uncertainty and unknown. Partial second reviews and separate adjudication retain all original disagreements. | Independent application of the instructions, actual expertise and adjudication require people. |
| 30 | Independent, blinded field grading records support, quotation entailment, omissions, attribution, timing, denial, uncertainty and critical number/identifier errors. Empty outputs remain in the denominator. Classification failures are abstentions. | No field accuracy is published before real reference reviews and independent grades cover the same examples for each method. A classification-only student has no measured extraction capability. |
| 31 | Prepared-draft study is explicitly scoped. A separate live recorder starts before task reveal/app opening and includes waiting, lookup, correction and review. Exports record actual outcomes and expertise. | Actual participants, timings and acceptable packets. Four to six relevant people may inform usability; they cannot establish population productivity or accident reduction. |
| 32 | Independently attested task-specific material-fact rubric is required. Live grading hides participant, condition and time; primary grading covers every attempted task, additional graders can grade a subset; disagreements and failed tasks remain visible. | An appropriate independent person must author the rubric and grade packets. Code cannot certify expertise or prevent undisclosed outside access. |
| 33 | Candidate freezes from complete development review before reserved-gold attachment. Code, model, endpoint fingerprint, taxonomy, available embedding assets and input hashes are checked. Gold attachment is a separate hash-identified record with custodian attestation. Partial scoring and replacement are refused. | No candidate has been frozen or holdout evaluated by this work. Actual access-order attestations must be true; data already inspected for tuning cannot become fresh by using this command. |
| 34 | Broad make/component/defect matching is explicitly separate from unmeasured vehicle/model-year/part/lot prediction. Multiple campaign matches, misses and unknowns are retained. | Exact physical association prediction remains unmeasured. Fictional trace review is not a prediction result. |
| 35 | Evaluation emits original alerts and matched subsets, every calendar month including zero-alert months, precision, recall, lead times and multiple-match counts. Retrospective quota matching is labelled. | No new completed holdout comparison or separately specified online policy has been measured. |
| 36 | Preflight includes full cohort plus warm-up, source/sentence serialization, retry limits and Baseten's token floor/schema-format retry. Per-attempt operations, fallbacks, rejected output, recorded latency and reservation/token estimates are retained. Actual billing stays null when unavailable. | Full bounded inference, independently acceptable drafts, real correction effort and actual billing. Existing budget remains unchanged; a preflight is not permission to reset it. |

## Development review and independent field grading

Open `reports/defect/evidence_v1/development_review.html` and complete the
review without first inspecting model outputs. Every item requires an explicit
check that all seven fields were considered; an absent field remains unknown.
Do not fill uncertain causes from domain expectations. A quote must support its
interpretation, not merely appear in the source.

The generated
[`development_error_analysis_pending.json`](../reports/defect/evidence_v1/development_error_analysis_pending.json)
is a worksheet, with **0 reviewed rows** and empty human judgments. Its recorded
output links can be inspected after independent labels are retained. It is not
an error-rate report.

```bash
.venv/bin/python -m scripts.evidence_benchmark import-review --review /path/to/development-review.json
.venv/bin/python -m scripts.evidence_benchmark compare-reviews --reviews /path/to/reviewer-a.json /path/to/reviewer-b-subset.json
```

The disagreement document retains wording differences for human interpretation;
it does not treat differing wording as automatically contradictory. To record
adjudication, supply an independent named adjudicator, expertise, attestation,
`source_disagreements_sha256` (the digest of the pending document) and one
decision per difference. A decision has `record_id`, `resolution` (`adjudicated`
or `unresolved`) and `rationale`; an adjudicated decision additionally has
`label_id` and independently reviewed `observations`. Preserve coverage-only
differences and unresolved ambiguity.

```bash
.venv/bin/python -m scripts.evidence_benchmark adjudicate \
  --disagreements /path/to/pending.json --grading /path/to/actual-adjudication.json
.venv/bin/python -m scripts.evidence_benchmark prepare-field-grading \
  --review /path/to/development-review.json --predictions /path/to/recorded-method-outputs.json
.venv/bin/python -m scripts.evidence_benchmark score-fields \
  --grading /path/to/independently-completed-pack.json --mapping /path/to/private-mapping.json
```

The method-output file is `{method_name: {record_id: extractor_result}}` and
must contain the same complete reviewed record set for every method. Use actual
recorded outputs, retaining empty/fallback outputs. Do not invent extracted
fields for a method that only classifies. The unfilled grading pack hides the
method; keep its mapping away from the grader. Reference reviewers cannot act
as the independent field grader. The result reports support and omissions by
field, abstention separately from classification accuracy, and critical errors
such as negation reversal. No automatic string-overlap score is called semantic
accuracy.

## Freeze before reserved gold

Configure the intended model/backend before freezing; the code, runtime choice
and source hashes become part of the candidate. Do not import reserved human
labels before candidate freeze, and do not open reserved gold for tuning.
An independent custodian should retain those labels outside the builder's
workflow and attach them later.

```bash
.venv/bin/python -m scripts.evidence_benchmark freeze --review /path/to/development-review.json
.venv/bin/python -m scripts.evidence_benchmark preflight --limit 8
# Inspect the estimate and the unchanged remaining reservation budget first.
.venv/bin/python -m scripts.evidence_benchmark predict-holdout --limit 8
# Repeat bounded batches only within the existing authorized budget.
.venv/bin/python -m scripts.evidence_benchmark attach-reviews \
  --complaint-review /path/to/sealed-complaint-review.json \
  --recall-review /path/to/sealed-recall-review.json \
  --custodian 'Actual independent custodian' --attest-sealed
.venv/bin/python -m scripts.evidence_benchmark evaluate
```

Preflight performs no model call and no budget reset. It is a conservative
planning estimate, not provider billing. Prediction files are created once,
failures stay recorded, and final scoring requires full coverage and unchanged
inputs/code. The comparison result cannot be overwritten. Attaching gold does
not mutate the candidate body or invalidate its hash. Technical gates record
order within these tools; they cannot establish what a person opened elsewhere.
Historical/pretraining knowledge remains a limitation.

## Two distinct human studies

The existing prepared-draft study shows saved assistance before its review
timer. Its reported timings exclude live inference. Generate an unfilled
material-fact rubric for independent completion:

```bash
.venv/bin/python -m scripts.reviewer_study prepare-rubric
.venv/bin/python -m scripts.reviewer_study analyze \
  --sessions /path/to/actual-session.json --rubric /path/to/independent-rubric.json
# A later analysis adds --grading /path/to/actual-grading.json.
```

The separate live study requires at least three task candidates, collectively
covering missing, contradictory and irrelevant records. Each task identifies
`task_id`, `campaign_id`, `vehicle_id`, `instruction`, original `source_ref`
(including its hash), `source_documents` with source IDs/text, the full
`deterministic_workflow_scope`, and `challenge_types`. All conditions use those
same records. A relevant independent rubric author must specify supported
material facts, consequential errors, acceptable-packet requirements and
ambiguities before participant answers exist. The preparatory command leaves
every human judgment blank.

```bash
.venv/bin/python -m scripts.investigation_study prepare \
  --tasks /path/to/task-candidates.json --out /path/to/live-preparation
.venv/bin/python -m scripts.investigation_study freeze \
  --tasks /path/to/task-candidates.json --rubric /path/to/actual-independent-rubric.json \
  --out /path/to/frozen-live-study
```

Participants open that directory's `study.html`, record actual expertise and
start the timer **before** seeing the task. The workflow link selects its exact
vehicle/source and assistance mode. Participants retain final answers or
failure explanations, every actual run ID and deviations. The recorder does
not call a model or send data. A model-assisted task needs its original live run
export, or an explicit failure explanation if no run exists. A replay, a run
from another task/time or a changed source is refused. A protocol deviation is
retained and identified as ineligible for condition comparison.

```bash
.venv/bin/python -m scripts.investigation_study analyze \
  --study /path/to/frozen-live-study/study.json \
  --rubric /path/to/actual-independent-rubric.json \
  --sessions /path/to/actual-session.json \
  --artifacts /path/to/exported-evidence-packet.json --out /path/to/live-analysis
```

Give the resulting `grading-*.json` to an independent grader and keep
`private-mapping-*.json` private. Supply actual completed files to the same
analysis with `--grading primary.json secondary-subset.json`. The primary
grader covers all attempted packets; a second grader can retain a subset of
the original items, preserving the original `identity_sha256`. Reports retain
individual grade totals and disagreements. Do not average away unresolved
disagreement. Counts, times, quality and failures belong together. No fabricated
productivity percentage is emitted.

## Verification

```bash
.venv/bin/python -m pytest tests/frontline/ai_layer/test_evidence_benchmark.py \
  tests/frontline/ai_layer/test_evidence_readiness.py -q
.venv/bin/python -m scripts.prepare_review_assets
```

The 19 focused tests use explicitly synthetic fixtures in temporary directories.
They verify hash/order gates, original-source quotation checks, failed/empty
output handling, field errors, partial double-review, abstentions, workload
months, preflight accounting, live source/timing/mode checks, independent grading
and unknown actual costs. They are software checks, never human labels, live
provider quality, or usefulness evidence. Review-asset generation changes HTML
and JavaScript presentation only; frozen JSON and its hashes remain unchanged.
