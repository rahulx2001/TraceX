# TraceX claim-to-artifact index

Every number in the short submission pitch should resolve here. These are saved scoped results, not new measurements.

Run `python -m scripts.public_replay` from a clean checkout with Python 3.10+; only the standard library is used. No API key, private cache, model weights or network is needed.

| Claim | Source and date | Model/version and scope |
|---|---|---|
| 5/8 campaigns matched (62.5%); count baseline also 5/8 | [historical-campaign-recall](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | ridge student with 13-week count policy; frozen selection in artifact. Make/category historical association; model-labelled references; not exact part prediction, superiority or accidents prevented. |
| 6/18 mature alerts matched later campaigns (33.3%) | [historical-alert-precision](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | same frozen ridge/count method. 24 alerts total, 18 with full follow-up through 2026-09-30; no human mechanical-defect validation. |
| 19/100 workload-matched random runs reached or exceeded 62.5% recall | [random-reference](../../reports/defect/fuel_holdout/holdout_results.json) · 2026-10-29T18:04:56.052354+00:00 | recorded retrospective random seeds. Conditional historical reference, not an online policy or new experiment. |
| Eight valid direct-Meta development outputs; four label agreements with the student | [development-agreement](../../reports/defect/evidence_v1/development_comparison.json) · 2026-10-29 (development artifact) | recorded extractor fingerprint 9d39c1dc5af2. Agreement is not accuracy; distinct from the reserved 100 complaints and five recall descriptions. |
| Original 300-example sample: 0 human labels; accuracy unavailable | [original-human-review](../../reports/defect/repair/human_validation_status.json) · Status snapshot indexed 2026-10-30 | not applicable; pending human review. A prepared review workflow is not a completed human evaluation. |
| Prepared study: 0 participants, 0 completed tasks; time savings unavailable | [reviewer-study](../../reports/hackathon/reviewer_study/results.json) · Status snapshot indexed 2026-10-30 | prepared recorded-assistance study. No participant, usefulness, quality or productivity result exists in this artifact. |
| Two saved synthetic scenarios, each with an initial and follow-up investigation | [recorded-investigation](../../reports/hackathon/investigation_live_smoke.json) · 2026-10-29T19:09:48.694663+00:00 and 2026-10-29T19:25:16.974209+00:00 | meta-models/muse-spark-open-1026; complaint-evidence-v1. Recorded real model transport on fictional data; quotation fidelity checks do not prove interpretation accuracy, new code validation or general reliability. |

The machine-readable [index](claim_index.json) pins SHA-256 hashes and JSON pointers for each artifact. The source hashes detect changes to these recorded files; this does not sign the campaign evidence packet.

## Full-data replay

Full experiment replay needs frozen gitignored inputs, source ZIPs, embeddings and weights listed by reports/defect/fuel_holdout/protocol.json. A new public download can differ. The small replay checks published arithmetic and citations only.

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
