# Evaluation: round 4 (three new reviewers + adjudicated gold v2)

ARYAN (107), Kaushal (130), Ram (100); 183 unique IDs combined with Rahul primary.
All three passed fraud checks (imperfect agreement 79-82% vs Rahul, zero copied notes,
cross-reviewer convergence on disputed IDs).

## Pairwise agreement (before adjudication)

| pair | agree | n | kappa |
|---|---|---:|---:|
| rahul_vs_aryan | 87 | 107 | 0.724 |
| rahul_vs_kaushal | 103 | 130 | 0.672 |
| rahul_vs_ram | 82 | 100 | 0.477 |
| aryan_vs_kaushal | 86 | 106 | 0.686 |
| aryan_vs_ram | 34 | 47 | 0.413 |
| kaushal_vs_ram | 40 | 48 | 0.598 |

Inter-reviewer kappas vary (0.41-0.69): genuine threshold variation between independent
reviewers, consistent with honest disagreement rather than copying.

## Adjudication

43 unique disputes adjudicated from source evidence per the labeling guide
(`adjudication/decision_trail.json`; AI-assisted draft, countersignature pending).
Notable: S108 overturned to tail_lights_leak on unanimous reviewer agreement;
several 2v2 majorities overridden by the evidence rule, each cited.

## Accuracy (gold v2)

- Baseline: **246/300 = 82.0%** (95% CI 77.3%-85.9%); macro F1 0.514
- Candidate: 238/300 = 79.3%; paired difference -2.7pp, 95% CI [-8.0, +2.7] — includes zero:
  **rejected** (below baseline, 90% target unmet), but no longer significantly worse on v2 gold.

## Largest supports

| label | support | P | R | F1 |
|---|---:|---:|---:|---:|
| other_unclear | 222 | 0.94 | 0.84 | 0.89 |
| engine_and_engine_cooling_leak | 11 | 0.91 | 0.91 | 0.91 |
| electric_power_assist_system_loss_of_control | 9 | 0.78 | 0.78 | 0.78 |
| antilock_traction_control_electronic_limited_slip_software | 5 | 0.50 | 0.60 | 0.55 |
| air_bag_restraint_control_module_failure | 5 | 1.00 | 1.00 | 1.00 |
| instrument_cluster_panel_compliance_or_label | 4 | 0.67 | 1.00 | 0.80 |

## Weakest F1 (support >= 3)

| label | support | P | R | F1 |
|---|---:|---:|---:|---:|
| antilock_traction_control_electronic_limited_slip_software | 5 | 0.50 | 0.60 | 0.55 |
| hinge_and_attachments_detachment | 3 | 0.67 | 0.67 | 0.67 |
| electric_power_assist_system_loss_of_control | 9 | 0.78 | 0.78 | 0.78 |
| instrument_cluster_panel_compliance_or_label | 4 | 0.67 | 1.00 | 0.80 |
| other_unclear | 222 | 0.94 | 0.84 | 0.89 |
| engine_and_engine_cooling_leak | 11 | 0.91 | 0.91 | 0.91 |

Full tables: `accuracy_v2.json`. Limits: see `review_status.json`.
Reproduce: `python3 -m scripts.defect_accuracy --csv reports/improvement/human_reviews/round4/adjudication/adjudicated_labels_v2.csv --classifications reports/defect/repair/classifications.parquet --manifest reports/defect/repair/review_manifest.json --out /tmp/r4-replay.json --require-complete`
