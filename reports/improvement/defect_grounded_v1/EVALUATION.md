# Grounded classifier experiment: target not met

The frozen candidate scored **209/300 = 69.7%** overall (95% Wilson interval **64.2%–74.6%**). The existing baseline remains **246/300 = 82.0%** (95% interval **77.3%–85.9%**). The candidate is rejected and is not deployed. The 90% point-estimate target requires **270/300** correct records; the baseline is **24/300** correct decisions short of that target.

Results cover all **300/300** frozen records across **29 components**. Both imported human reviews, adjudicated labels, historical predictions, baseline scores and frozen sample remain unchanged. No dashboard accuracy is updated.

| Metric | Baseline numerator / denominator | Baseline | Candidate numerator / denominator | Candidate | Candidate 95% interval |
|---|---|---:|---|---:|---:|
| Overall accuracy | 246/300 records | 82.0% | 209/300 records | 69.7% | 64.2%–74.6% |
| Specific-label accuracy | 71/107 specific human labels | 66.4% | 21/107 specific human labels | 19.6% | 13.2%–28.1% |
| Missing predictions | 0/300 records | 0.0% | 6/300 records | 2.0% | — |
| Common-label macro F1 | 24.806829 summed F1 / 48 labels | 0.516809 | 9.321545 summed F1 / 48 labels | 0.194199 | 0.162–0.211 |
| Candidate own-union macro F1 | — | — | 9.321545 summed F1 / 42 labels | 0.221942 | 0.185–0.241 |

The paired overall change is **−37/300 = −12.33 percentage points** (95% paired-row bootstrap interval **−17.33 to −7.33 percentage points**). The candidate improves **14/300**, worsens **51/300**, and ties **235/300** records. Macro comparison uses the same 48-label union; the candidate’s own 42-label macro is a separate diagnostic.

The six missing predictions remain wrong in overall and specific-label denominators and false negatives for their human labels. The scorer wrote the result and returned exit code 3 under `--require-complete` to flag those missing outputs. No accuracy calculated only over available predictions is used for the claim.

## Frozen recipe and source handling

This is an evidence-grounding prompt experiment, with no supervised fitting, calibration or feature selection. Its model is `meta-models/muse-spark-open-1026`, original prompt version `defect-cls-v3-grounded`, and output handling version `defect-cls-v3-grounded-row-validation`. Part/mode definitions come from the existing frozen pre-2021 taxonomy. Separate unlabelled pre-2021 complaints were used only for software-contract sanity checks; **8/8** checks passed, which is not an accuracy estimate.

The initial **39/39** evaluation batches produced **240/300** batch-valid predictions. One exact-prompt retry was frozen for **9/39** failed batches, after which whole-batch validation retained **256/300** predictions. All original and retry attempts remain append-only in `attempts.jsonl`; the initial outputs are preserved separately.

After observing unlabelled quote-contract failures and before any candidate gold score, a separate row-handling policy was designed and frozen. Full exact batch counts and unique `c1..cN` IDs must establish mapping. Each row then passes the unchanged strict evidence validator. The chronological first valid response is retained across initial and at most one retry; no quote rewriting, label guessing, baseline fallback, confidence/gold selection, denominator removal or additional inference is used. This yields **294/300** valid predictions and **6/300** missing. The original whole-batch output is preserved.

The frozen taxonomy has only `other_unclear` available for **73/300** records, so those receive its sole allowed label without a model call. This rule and all request/validator hashes were fixed before evaluation. No candidate design changes or new attempts occur after scoring.

## Intervals, provenance and limits

Accuracy, precision and recall use 95% Wilson intervals. Per-label and own-union macro F1 use 10,000 human-label-stratified paired-row bootstrap draws, retaining 300 rows and observed human supports in each draw. The difference interval uses 10,000 paired baseline/candidate row resamples of 300 rows. These are conditional benchmark intervals, not evidence of fresh prospective performance.

The common 48-label candidate macro interval scales the saved 42-label macro interval by 42/48. The six added labels have zero human support and zero candidate predictions in every draw. This derivation is preserved in [common_macro_interval.json](common_macro_interval.json); it changes no predictions or score artifacts.

Rahul and Manish each provided **300/300** human labels with notes; agreement is **300/300**, kappa 1.0, and disagreements **0/300**. All notes and labels match. Blinding and prior assignment retain the user-attested chronology limitations documented in [the original evaluation](../human_reviews/round1/EVALUATION.md); agreement does not independently verify label correctness.

The human reviews and `synthetic_review_v1` fixtures remain evaluation-only and never enter fitting, calibration, feature selection or dashboard accuracy. This benchmark was already opened. Continuing model development requires separate pre-2021 human-labelled training/development records and a new blinded validation sample. This unsuccessful candidate result must not be used to tailor another model to these 300 answers.

## Per-label results

Human support and predicted counts use all 300 evaluation rows. Precision is TP/predicted, recall is TP/support, and F1 is 2TP/(human support + predicted). Zero-denominator precision/recall is unavailable. All precision/recall and F1 intervals are in [accuracy.json](accuracy.json).

| Label | Human support | Predicted | Precision | Recall | F1 numerator / denominator | F1 95% interval |
|---|---:|---:|---|---|---|---|
| other_unclear | 193/300 | 269/300 | 188/269 = 69.9% | 188/193 = 97.4% | 376/462 = 0.814 | 0.798–0.829 |
| electric_power_assist_system_loss_of_control | 11/300 | 2/300 | 2/2 = 100.0% | 2/11 = 18.2% | 4/13 = 0.308 | 0.000–0.625 |
| wiring_electrical | 11/300 | 1/300 | 1/1 = 100.0% | 1/11 = 9.1% | 2/12 = 0.167 | 0.000–0.429 |
| engine_and_engine_cooling_leak | 10/300 | 10/300 | 9/10 = 90.0% | 9/10 = 90.0% | 18/20 = 0.900 | 0.737–1.000 |
| air_bag_restraint_control_module_failure | 5/300 | 0/300 | 0/0 = unavailable | 0/5 = 0.0% | 0/5 = 0.000 | 0.000–0.000 |
| antilock_traction_control_electronic_limited_slip_software | 5/300 | 0/300 | 0/0 = unavailable | 0/5 = 0.0% | 0/5 = 0.000 | 0.000–0.000 |
| instrument_cluster_panel_compliance_or_label | 5/300 | 0/300 | 0/0 = unavailable | 0/5 = 0.0% | 0/5 = 0.000 | 0.000–0.000 |
| engine_and_engine_cooling_engine_missing_or_wrong_part | 4/300 | 1/300 | 0/1 = 0.0% | 0/4 = 0.0% | 0/5 = 0.000 | 0.000–0.000 |
| belts_and_associated_pulleys_detachment | 4/300 | 0/300 | 0/0 = unavailable | 0/4 = 0.0% | 0/4 = 0.000 | 0.000–0.000 |
| camera_software | 4/300 | 0/300 | 0/0 = unavailable | 0/4 = 0.0% | 0/4 = 0.000 | 0.000–0.000 |
| electrical_system_software_software | 4/300 | 0/300 | 0/0 = unavailable | 0/4 = 0.0% | 0/4 = 0.000 | 0.000–0.000 |
| hinge_and_attachments_detachment | 3/300 | 2/300 | 2/2 = 100.0% | 2/3 = 66.7% | 4/5 = 0.800 | 0.000–1.000 |
| hoses_lines_piping_and_fittings_missing_or_wrong_part | 3/300 | 0/300 | 0/0 = unavailable | 0/3 = 0.0% | 0/3 = 0.000 | 0.000–0.000 |
| relay_stall | 3/300 | 0/300 | 0/0 = unavailable | 0/3 = 0.0% | 0/3 = 0.000 | 0.000–0.000 |
| tires_compliance_or_label | 3/300 | 0/300 | 0/0 = unavailable | 0/3 = 0.0% | 0/3 = 0.000 | 0.000–0.000 |
| hybrid_propulsion_system_electrical | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| roof_and_pillars_failure | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| body_control_module_software_software | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| door_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| electronic_stability_control_esc_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| service_brakes_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| structure_body_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| brake_lights_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| electrical_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| ignition_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| recliner_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| seats_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| automatic_transmission_detachment | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| canister_failure | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| control_module_tcm_pcm_tecm_software | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| fuel_pump_failure | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| inverter_stall | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| lower_arm_crack_or_fracture | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| lugs_nuts_bolts_studs_crack_or_fracture | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| master_cylinder_leak | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| occupant_classification_software | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| seat_belts_compliance_or_label | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| sun_moon_roof_assembly_detachment | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| tie_rod_assembly_loss_of_control | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| visibility_wiper_software | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| gear_position_indication_prndl_failure | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| headlights_compliance_or_label | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |

## Saved evidence and reproduction

The full confusion matrix is in [accuracy.json](accuracy.json), with human labels as rows and model labels plus `__missing_prediction__` as columns. The matrix total is **300/300**, the diagonal **209/300**, and the missing column **6/300**. [comparison.json](comparison.json) preserves paired counts, bootstrap metadata and both source score hashes. [verification.json](verification.json) checks frozen artifacts and independent score arithmetic; it does not rerun model inference.

Frozen sample SHA-256: `7b0bf958b8756b51e3a3d550b8611f8182b56839b20e922b35abcc67e3aba1a4`. Adjudicated labels SHA-256: `4bfd3545a0e028eb2607797eb88487326f090285ffeed841d43b5edff461348b`. Candidate predictions SHA-256: `2b65db08c33a30486e0c911758d8d7016cc59da94e1eff9af5fbb4846e4aaff2`.

The scoring and comparison commands used were:

```sh
python3 -m scripts.defect_accuracy --csv reports/improvement/human_reviews/round1/adjudication/adjudicated_labels.csv --classifications reports/improvement/defect_grounded_v1/evaluation_row_validated.parquet --manifest reports/defect/repair/review_manifest.json --out reports/improvement/defect_grounded_v1/accuracy.json --require-complete
python3 -m scripts.defect_candidate_compare
```

Those artifacts already exist and must be preserved. Replay into new output paths if needed; do not overwrite scores, refreeze plans or restart evaluation calls.

Focused validator, recovery, comparison and scorer tests passed **46/46**. The baseline human-review artifact hashes passed **21/21** preservation checks; candidate frozen dependencies passed **10/10** checks.
