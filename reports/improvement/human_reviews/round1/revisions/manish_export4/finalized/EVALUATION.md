# Finalized export4 evaluation

Current classifier: **255/300 = 85.0%**, 95% Wilson interval **80.5%–88.6%**. All **31/31** disputed labels have supplied human adjudication decisions; all **300/300** records across **29 components** remain in the evaluation.

The experimental grounded candidate scores **238/300 = 79.3%**, 95% interval **74.4%–83.5%**. Its **6/300** missing predictions count as wrong. The current classifier remains the stronger recorded result; no deployment change is made.

These are rescored, unchanged saved predictions. The earlier current-model score was **246/300 = 82.0%** under the original labels; the difference is **9/300** correct decisions because the human labels changed. This is not evidence of a newly trained or improved model.

| Metric | Current classifier | Grounded candidate |
|---|---|---|
| Overall accuracy | 255/300 = 85.0%; CI 80.5%–88.6% | 238/300 = 79.3%; CI 74.4%–83.5% |
| Specific-label accuracy | 62/77 = 80.5%; CI 70.3%–87.8% | 21/77 = 27.3%; CI 18.6%–38.1% |
| Common-label macro F1 | 23.628447 summed F1 / 43 labels = 0.549499; CI 0.511–0.586 | 9.834495 summed F1 / 43 labels = 0.228709; CI 0.206–0.241 |
| Candidate own-union macro F1 | — | 9.834495 summed F1 / 34 labels = 0.289250; CI 0.261–0.305 |
| Missing predictions | 0/300 | 6/300 |
| Human label prevalence | 223/300 other_unclear; 77/300 specific | Same adjudicated labels |

The candidate-minus-current paired difference is **−17/300 = −5.67 percentage points**, with a 95% paired-bootstrap interval of **−11.00 to −0.33 percentage points**. It improves **25/300**, worsens **42/300**, and ties **233/300** records. A 90% point estimate requires **270/300** correct; the current model is **15/300** correct decisions short.

## Adjudication provenance

The earlier pre-adjudication comparison is preserved: raw agreement **269/300 = 89.7%**, paired-bootstrap interval **86.0%–93.0%**; kappa **0.802502 over 300 paired rows**, interval **0.733394–0.864478**. This comparison is descriptive because the revised Manish export reused prior labels and script-generated notes. The user confirmed that Manish personally checked every final label.

Rahul supplied the finalized adjudication export and confirmed all issues were resolved. The **31/31** decisions accept the presented assistant source-only drafts. Their quotes, reasoning, reviewer IDs and supplied timestamps are preserved verbatim. All decisions share the single supplied timestamp; this does not independently establish distinct per-row review times. The **269/300** matching labels are retained by agreement, with both original reviews preserved.

The original blinding/prior-assignment limitations remain in the round1 reliability gate. This is an opened historical benchmark with human-approved assisted adjudication, not fresh prospective validation. No reviewer expertise, independence or label correctness is independently proved by the attestation.

No evaluation labels, paraphrases or synthetic_review_v1 fixtures enter fitting, calibration, feature selection or dashboard accuracy. No new model calls or training were performed. Historical reviews, scores, predictions, draft packet and pending status remain preserved.

## Metrics and intervals

Accuracy, precision and recall use 95% Wilson intervals. F1 uses 10,000 human-label-stratified paired-row bootstrap draws, with 300 rows per draw and fixed observed supports. The paired accuracy difference uses 10,000 whole-pair resamples of 300 rows. The candidate common 43-label macro interval scales its own 34-label interval by 34/43, because the nine added labels have no human support or candidate predictions. Full per-label metrics and intervals are in both accuracy JSON files.

The current-model confusion matrix totals **300/300** records and has **255/300** on its diagonal. The candidate matrix totals **300/300**, has **238/300** on its diagonal, and **6/300** in its missing-prediction column.

## Current classifier per-label results

Precision is TP/predicted, recall is TP/human support, and F1 is 2TP/(support+predicted). Counts of support and predictions use the full 300-row denominator. Zero-denominator precision/recall is unavailable.

| Label | Human support | Predicted | Precision | Recall | F1 | F1 95% interval |
|---|---:|---:|---|---|---|---|
| other_unclear | 223/300 | 198/300 | 193/198 = 97.5% | 193/223 = 86.5% | 386/421 = 0.917 | 0.889–0.942 |
| engine_and_engine_cooling_leak | 11/300 | 11/300 | 10/11 = 90.9% | 10/11 = 90.9% | 20/22 = 0.909 | 0.762–1.000 |
| electric_power_assist_system_loss_of_control | 10/300 | 9/300 | 9/9 = 100.0% | 9/10 = 90.0% | 18/19 = 0.947 | 0.824–1.000 |
| wiring_electrical | 6/300 | 9/300 | 5/9 = 55.6% | 5/6 = 83.3% | 10/15 = 0.667 | 0.429–0.923 |
| instrument_cluster_panel_compliance_or_label | 5/300 | 6/300 | 5/6 = 83.3% | 5/5 = 100.0% | 10/11 = 0.909 | 0.769–1.000 |
| antilock_traction_control_electronic_limited_slip_software | 4/300 | 6/300 | 2/6 = 33.3% | 2/4 = 50.0% | 4/10 = 0.400 | 0.000–0.750 |
| air_bag_restraint_control_module_failure | 4/300 | 5/300 | 4/5 = 80.0% | 4/4 = 100.0% | 8/9 = 0.889 | 0.727–1.000 |
| belts_and_associated_pulleys_detachment | 4/300 | 2/300 | 2/2 = 100.0% | 2/4 = 50.0% | 4/6 = 0.667 | 0.000–1.000 |
| electrical_system_software_software | 4/300 | 2/300 | 1/2 = 50.0% | 1/4 = 25.0% | 2/6 = 0.333 | 0.000–0.750 |
| camera_software | 3/300 | 4/300 | 3/4 = 75.0% | 3/3 = 100.0% | 6/7 = 0.857 | 0.667–1.000 |
| hoses_lines_piping_and_fittings_missing_or_wrong_part | 3/300 | 3/300 | 3/3 = 100.0% | 3/3 = 100.0% | 6/6 = 1.000 | 1.000–1.000 |
| hinge_and_attachments_detachment | 2/300 | 3/300 | 2/3 = 66.7% | 2/2 = 100.0% | 4/5 = 0.800 | 0.571–1.000 |
| body_control_module_software_software | 2/300 | 2/300 | 1/2 = 50.0% | 1/2 = 50.0% | 2/4 = 0.500 | 0.000–1.000 |
| hybrid_propulsion_system_electrical | 2/300 | 1/300 | 1/1 = 100.0% | 1/2 = 50.0% | 2/3 = 0.667 | 0.000–1.000 |
| relay_stall | 1/300 | 3/300 | 1/3 = 33.3% | 1/1 = 100.0% | 2/4 = 0.500 | 0.286–1.000 |
| inverter_stall | 1/300 | 2/300 | 1/2 = 50.0% | 1/1 = 100.0% | 2/3 = 0.667 | 0.500–1.000 |
| brake_lights_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| control_module_tcm_pcm_tecm_software | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| electrical_electrical | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| fuel_pump_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| ignition_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| master_cylinder_leak | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| occupant_classification_software | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| recliner_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| roof_and_pillars_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| seats_failure | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| structure_body_compliance_or_label | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| sun_moon_roof_assembly_detachment | 1/300 | 1/300 | 1/1 = 100.0% | 1/1 = 100.0% | 2/2 = 1.000 | 1.000–1.000 |
| automatic_transmission_detachment | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| canister_failure | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| lower_arm_crack_or_fracture | 1/300 | 0/300 | 0/0 = unavailable | 0/1 = 0.0% | 0/1 = 0.000 | 0.000–0.000 |
| tie_rod_assembly_loss_of_control | 0/300 | 4/300 | 0/4 = 0.0% | 0/0 = unavailable | 0/4 = 0.000 | 0.000–0.000 |
| engine_and_engine_cooling_engine_missing_or_wrong_part | 0/300 | 3/300 | 0/3 = 0.0% | 0/0 = unavailable | 0/3 = 0.000 | 0.000–0.000 |
| gear_position_indication_prndl_failure | 0/300 | 3/300 | 0/3 = 0.0% | 0/0 = unavailable | 0/3 = 0.000 | 0.000–0.000 |
| parking_brake_compliance_or_label | 0/300 | 3/300 | 0/3 = 0.0% | 0/0 = unavailable | 0/3 = 0.000 | 0.000–0.000 |
| service_brakes_compliance_or_label | 0/300 | 2/300 | 0/2 = 0.0% | 0/0 = unavailable | 0/2 = 0.000 | 0.000–0.000 |
| equipment_adaptive_mobility_failure | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| headlights_compliance_or_label | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| hoses_lines_piping_and_fittings_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| steering_wheel_handle_bar_detachment | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| tail_lights_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| tank_assembly_leak | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |
| tires_compliance_or_label | 0/300 | 1/300 | 0/1 = 0.0% | 0/0 = unavailable | 0/1 = 0.000 | 0.000–0.000 |

## Saved artifacts

- [Current-model scores](accuracy_baseline.json)
- [Grounded-candidate scores](accuracy_candidate.json)
- [Paired comparison](comparison.json)
- [Full decision trail](decision_trail.json)
- [Supplied adjudication export](adjudication_export.json)
- [Validation completed before scoring](validation_before_scoring.json)
- [Independent arithmetic checks](verification.json)

Frozen sample SHA-256: `7b0bf958b8756b51e3a3d550b8611f8182b56839b20e922b35abcc67e3aba1a4`. Final labels SHA-256: `f2ab4c28c2f8f6edb5907c426ccfe78ec2d04490a708739753b8f63164380a93`. Current saved predictions SHA-256: `ce3977cbe22e410775a9527cabfb5acb5191a4bc5134371369f98d5fddbd739b`.
