# TraceX claim-to-artifact index

Every number in the short submission pitch should resolve here. These are saved scoped results, not new measurements.

Run `python -m scripts.public_replay` from a clean checkout with Python 3.10+; only the standard library is used. No API key, private cache, model weights or network is needed.

| Claim | Source and date | Model/version and scope |
|---|---|---|
| 5/8 campaigns matched (62.5%); count baseline also 5/8 | [historical-campaign-recall](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | ridge student with 13-week count policy; frozen selection in artifact. Make/category historical association; model-labelled references; not exact part prediction, superiority or accidents prevented. |
| 6/18 mature alerts matched later campaigns (33.3%) | [historical-alert-precision](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | same frozen ridge/count method. 24 alerts total, 18 with full follow-up through 2026-09-30; no human mechanical-defect validation. |
| 19/100 workload-matched random runs reached or exceeded 62.5% recall | [random-reference](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | recorded retrospective random seeds. Conditional historical reference, not an online policy or new experiment. |
| Eight valid direct-Meta development outputs; four label agreements with the student | [development-agreement](../../reports/defect/evidence_v1/development_comparison.json) · 2026-10-29 (development artifact) | recorded extractor fingerprint 9d39c1dc5af2. Agreement is not accuracy; distinct from the reserved 100 complaints and five recall descriptions. |
| Prepared study: 0 participants, 0 completed tasks; time savings unavailable | [reviewer-study](../../reports/hackathon/reviewer_study/results.json) · Status snapshot indexed 2026-10-30 | prepared recorded-assistance study. No participant, usefulness, quality or productivity result exists in this artifact. |
| Two saved synthetic scenarios, each with an initial and follow-up investigation | [recorded-investigation](../../reports/hackathon/investigation_live_smoke.json) · 2026-10-29T19:09:48.694663+00:00 and 2026-10-29T19:25:16.974209+00:00 | meta-models/muse-spark-open-1026; complaint-evidence-v1. Recorded real model transport on fictional data; quotation fidelity checks do not prove interpretation accuracy, new code validation or general reliability. |
| Earlier second-review and timed-review claims were withdrawn; Rahul's original labels remain attested single-reviewer evidence | [review-provenance-withdrawal](../../reports/improvement/human_reviews/REJECTED_fabricated_rounds.md) · Withdrawal recorded before the round-4 evaluation | Provenance audit; no model inference. No independent review validation, kappa or 85% accuracy claim is supported by the withdrawn rounds. Archived files remain available for audit. |
| Current historical evaluation: 246/300 = 82.0% accuracy, macro-F1 0.514 over 46 labels; challenger 238/300 = 79.3%, rejected | [round4-evaluation](../../reports/improvement/human_reviews/round4/review_status.json) · 2026-11-03T13:18:46+00:00 | meta-models/muse-spark-open-1026; defect-cls-v2. AI-assisted adjudication, human-countersigned by Rahul Kumar Singh (all 43 confirmed). Blinding is unconfirmed; statistical agreement does not establish independence. Opened 300-record historical evaluation only; no accident prediction accuracy or demonstrated improvement. |
| Grounded candidate rejected: 209/300 = 69.7% (95% CI 64.2%–74.6%); baseline 246/300 = 82.0%; missing predictions 6/300; target 270/300 not met | [grounded-human-review-candidate](../../reports/improvement/defect_grounded_v1/comparison.json) · 2026-11-02T13:32:40+00:00 | meta-models/muse-spark-open-1026; defect-cls-v3-grounded-row-validation. Separate candidate evaluation against the original attested single-reviewer labels. Second-review independence claims were withdrawn. Missing predictions count as wrong; candidate rejected and not deployed. Historical evaluation only; no fitting or calibration. |

The machine-readable [index](claim_index.json) pins SHA-256 hashes and JSON pointers for each artifact. The source hashes detect changes to these recorded files; this does not sign the campaign evidence packet.

## Full-data replay

The public model replay recomputes frozen student predictions and the complete alert evaluation from checksummed projections, cached embeddings and fitted weights. Regenerating raw ingestion, embeddings, teacher outputs or training selection still needs the original frozen inputs and environment listed by reports/defect/fuel_holdout/protocol.json. The small standard-library replay checks published arithmetic, hashes and citations only.

Run `python3 -m scripts.public_model_replay verify --download` with NumPy and pandas installed. The [public replay guide](../../docs/public-model-replay.md) explains the release hashes, excluded free text and replay scope. Run `python3 -m scripts.review_evidence_check` to validate the five public review exports and all 43 active adjudications; the [export inventory](../improvement/human_reviews/EXPORT_INDEX.md) maps all 18 supplied filenames.

See [the frozen experiment instructions](../defect/fuel_holdout/README.md) and [input/source hashes](../defect/fuel_holdout/protocol.json). Keep opened evaluation data distinct from fresh holdouts. Do not tune against the published result or reuse its upper confidence endpoint as an achieved score.

## Current implementation checks

`PLAYWRIGHT_CHANNEL=chrome npm run test:signin` in `dashboard/` builds current assets and exercises real local entry/auth and text-report-to-packet behavior, plus clearly labelled UI fixtures. It makes no model call. Source version and acceptance details are in [entry validation](../../docs/entry-auth-validation.md). A saved historical video or model output does not validate a new build.

The [30 October container execution](container_validation/README.md) records
clean image and Compose/browser checks, public CI, exact image/source versions,
60 focused Python tests and failed attempts. Reproduce with
`python3 -m scripts.docker_readiness --image IMAGE --expected-revision SHA --compose --browser --output /tmp/result.json`
after [building the image](../../docs/container-validation.md). These are
fictional text/software checks with zero inference, not participant or audio
quality results. [Real-audio status](../voice_validation/results.json) remains
zero captures, zero participants and no latency percentiles.
