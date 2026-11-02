# Frozen 300-record human evaluation

Rahul and Manish each supplied 300/300 unique labels with notes. The original frozen sample and both imported reviews remain unchanged. Results cover the full sample across its 29 components; no fuel-only accuracy is reported.

| Metric | Numerator / denominator | Result | 95% interval |
|---|---|---:|---:|
| Overall accuracy | 246/300 evaluation records | 82.0% | 77.3%–85.9% |
| Specific-label accuracy | 71/107 records with a specific human label | 66.4% | 57.0%–74.6% |
| Macro F1 | 24.806829 summed F1 / 48 observed human-or-prediction labels | 0.516809 | 0.463–0.552 |
| Supplementary human-supported macro F1 | 24.806829 summed F1 / 40 human-supported labels | 0.620171 | 0.556–0.663 |
| Always other/unclear baseline | 193/300 evaluation records | 64.3% | 58.8%–69.5% |
| Missing predictions | 0/300 evaluation records | 0.0% | — |
| Invalid human labels | 0/300 evaluation records | 0.0% | — |

Accuracy, precision and recall intervals use the Wilson score method. F1 and macro F1 intervals use 10,000 human-label-stratified paired-row bootstrap draws of 300 records each, preserving human supports and the fixed observed label union. These intervals condition on observed label prevalence.

Missing predictions remain in the accuracy and specific-label denominators, count as false negatives for their human label, and appear in an explicit missing-prediction confusion column. The primary macro includes prediction-only labels; the human-supported macro is supplementary.

## Agreement before adjudication

| Measure | Result | Paired-row bootstrap interval |
|---|---|---|
| Raw agreement | 300/300 = 100.0% | 100.0%–100.0% |
| Cohen’s kappa | 1.000 on 300/300 paired records | 1.000–1.000 |
| Label disagreements | 0/300 | — |
| Exactly matching notes | 300/300 | — |

The agreement bootstrap resamples complete reviewer pairs with replacement for 10,000 draws of 300 rows each. The intervals condition on the supplied pairs and do not verify independence or label correctness. Full label prevalence and per-label disagreement are saved in [agreement_before_adjudication.json](agreement_before_adjudication.json).

## Review provenance and disagreement resolution

The user confirms Manish began independently from a blank page, was assigned the entire already frozen sample, and started on 1 November. This retrospective user confirmation and human attestation support the full 300-ID overlap; the assignment chronology and blinding are not independently verified. The 50-ID assignment recorded on 2 November was later than his reported start and is not used as prospective registration for his review.

Both complete exported review arrays, including all labels and notes, are identical. This observation is retained rather than treated as independent proof of correctness. Both reviewer IDs and supplied export timestamps are preserved; no per-row annotation timestamps were supplied.

With 0/300 disagreements, all 300/300 matching labels are accepted by agreement. There are no individual adjudication decisions to make, and none are invented. See the [decision trail](adjudication/decision_trail.json), [gate interpretation](reliability_gate.json), and [user confirmation](second_review/manish/user_confirmation.json).

## Per-label precision, recall and F1

Support and predicted counts are shown against all 300 evaluation rows. Precision is TP/predicted, recall is TP/support, and F1 is 2TP/(2TP+FP+FN). An undefined zero-denominator ratio is marked unavailable. Per-label intervals appear in [accuracy.json](accuracy.json).

| Label | Human support | Predicted | Precision (TP/predicted) | Recall (TP/support) | F1 (2TP/denominator) | F1 95% interval |
|---|---:|---:|---|---|---|---|
| other_unclear | 193/300 | 198/300 | 175/198 = 88.4% | 175/193 = 90.7% | 350/391 = 0.895 | 0.869–0.920 |
| electric_power_assist_system_loss_of_control | 11/300 | 9/300 | 9/9 = 100.0% | 9/11 = 81.8% | 18/20 = 0.900 | 0.706–1.000 |
| wiring_electrical | 11/300 | 9/300 | 8/9 = 88.9% | 8/11 = 72.7% | 16/20 = 0.800 | 0.588–0.952 |
| engine_and_engine_cooling_leak | 10/300 | 11/300 | 9/11 = 81.8% | 9/10 = 90.0% | 18/21 = 0.857 | 0.696–1.000 |
| antilock_traction_control_electronic_limited_slip_software | 5/300 | 6/300 | 3/6 = 50.0% | 3/5 = 60.0% | 6/11 = 0.545 | 0.200–0.889 |
| instrument_cluster_panel_compliance_or_label | 5/300 | 6/300 | 5/6 = 83.3% | 5/5 = 100.0% | 10/11 = 0.909 | 0.769–1.000 |
| air_bag_restraint_control_module_failure | 5/300 | 5/300 | 5/5 = 100.0% | 5/5 = 100.0% | 10/10 = 1.000 | 1.000–1.000 |
| camera_software | 4/300 | 4/300 | 4/4 = 100.0% | 4/4 = 100.0% | 8/8 = 1.000 | 1.000–1.000 |
| engine_and_engine_cooling_engine_missing_or_wrong_part | 4/300 | 3/300 | 0/3 = 0.0% | 0/4 = 0.0% | 0/7 = 0.000 | 0.000–0.000 |
| belts_and_associated_pulleys_detachment | 4/300 | 2/300 | 2/2 = 100.0% | 2/4 = 50.0% | 4/6 = 0.667 | 0.000–1.000 |
| electrical_system_software_software | 4/300 | 2/300 | 1/2 = 50.0% | 1/4 = 25.0% | 2/6 = 0.333 | 0.000–0.750 |
| hinge_and_attachments_detachment | 3/300 | 3/300 | 2/3 = 66.7% | 2/3 = 66.7% | 4/6 = 0.667 | 0.000–1.000 |
| hoses_lines_piping_and_fittings_missing_or_wrong_part | 3/300 | 3/300 | 3/3 = 100.0% | 3/3 = 100.0% | 6/6 = 1.000 | 1.000–1.000 |
| relay_stall | 3/300 | 3/300 | 2/3 = 66.7% | 2/3 = 66.7% | 4/6 = 0.667 | 0.000–1.000 |
| tires_compliance_or_label | 3/300 | 1/300 | 1/1 = 100.0% | 1/3 = 33.3% | 2/4 = 0.500 | 0.000–1.000 |
| body_control_module_software_software | 2/300 | 2/300 | 1/2 = 50.0% | 1/2 = 50.0% | 2/4 = 0.500 | 0.000–1.000 |
| service_brakes_compliance_or_label | 2/300 | 2/300 | 1/2 = 50.0% | 1/2 = 50.0% | 2/4 = 0.500 | 0.000–1.000 |
| hybrid_propulsion_system_electrical | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| roof_and_pillars_failure | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| structure_body_compliance_or_label | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| door_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| electronic_stability_control_esc_compliance_or_label | 2/300 | 0/300 | 0/0 = unavailable | 0/2 = 0.0% | 0/2 = 0.000 | 0.000–0.000 |
| tie_rod_assembly_loss_of_control | 1/300 | 4/300 | 1/4 = 25.0% | 1/1 = 100.0% | 2/5 = 0.400 | 0.222–1.000 |
| inverter_stall | 1/300 | 2/300 | 1/2 = 50.0% | 1/1 = 100.0% | 2/3 = 0.667 | 0.500–1.000 |
| brake_lights_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| control_module_tcm_pcm_tecm_software | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| electrical_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| fuel_pump_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| ignition_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| master_cylinder_leak | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| occupant_classification_software | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| recliner_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| seats_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| sun_moon_roof_assembly_detachment | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| automatic_transmission_detachment | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| canister_failure | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| lower_arm_crack_or_fracture | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| lugs_nuts_bolts_studs_crack_or_fracture | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| seat_belts_compliance_or_label | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| visibility_wiper_software | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| gear_position_indication_prndl_failure | 0/300 | 3/300 | 0/3 = 0.0% | 0/0 = unavailable | 0/3 = 0.000 | 0.000–0.000 |
| parking_brake_compliance_or_label | 0/300 | 3/300 | 0/3 = 0.0% | 0/0 = unavailable | 0/3 = 0.000 | 0.000–0.000 |
| equipment_adaptive_mobility_failure | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| headlights_compliance_or_label | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| hoses_lines_piping_and_fittings_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| steering_wheel_handle_bar_detachment | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| tail_lights_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| tank_assembly_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |

## Confusion and frozen inputs

The full confusion matrix is in [accuracy.json](accuracy.json), with human labels as rows and model labels plus `__missing_prediction__` as columns. Its total is 300/300 records; its diagonal is 246/300 records. No rows are excluded for missing predictions.

Classifier: `meta-models/muse-spark-open-1026`; prompt `defect-cls-v2`. Saved repaired predictions: `reports/defect/repair/classifications.parquet`; SHA-256 `ce3977cbe22e410775a9527cabfb5acb5191a4bc5134371369f98d5fddbd739b`.

Frozen sample SHA-256: `7b0bf958b8756b51e3a3d550b8611f8182b56839b20e922b35abcc67e3aba1a4`. Final labels SHA-256: `4bfd3545a0e028eb2607797eb88487326f090285ffeed841d43b5edff461348b`.

These labels and the synthetic fixtures remain evaluation-only. No fitting, calibration, feature selection, dashboard accuracy update, or new model inference was performed. This is an opened historical evaluation, not a fresh prospective result.

The [README](README.md) records artifact locations and the reproduction command.
