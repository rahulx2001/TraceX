# Evaluation: round 2 (adjudicated human labels)

Two independent named reviewers labelled all 300 frozen records: Rahul (primary)
and Rakesh Ranjan (second, blinded; packet `round1-second-review-v1` preregistered
2026-11-02T11:01:42Z, hash-verified against the export, before the 16:26Z export).

- Raw agreement 269/300 = 89.7%, Cohen's kappa 0.80
  (preregistered-50: 45/50, kappa 0.77). Arrays are not identical; notes are independently written.
- 31 disagreements adjudicated from source evidence per the labeling guide
  (specific label requires explicit part and failure-mode evidence; recall mention
  alone insufficient). Adjudicator: Muse (AI-assisted; human countersignature
  recommended). See `adjudication/decision_trail.json`.
- Classifier accuracy vs adjudicated labels: **255/300 = 85.0%**
  (95% CI 80.5%–88.6%); macro F1 0.539;
  specific-label accuracy 79.7%; always-predict-other_unclear baseline 73.7%.
  Adjudicated ground truth is 221/300 other_unclear: most real
  narratives do not support a specific defect label under the guide's evidence rule.

## Best per-label F1 (support ≥ 3)

| label | support | precision | recall | F1 |
|---|---:|---:|---:|---:|
| hoses_lines_piping_and_fittings_missing_or_wrong_part | 3 | 1.00 | 1.00 | 1.00 |
| electric_power_assist_system_loss_of_control | 10 | 1.00 | 0.90 | 0.95 |
| other_unclear | 221 | 0.97 | 0.87 | 0.92 |
| engine_and_engine_cooling_leak | 11 | 0.91 | 0.91 | 0.91 |
| instrument_cluster_panel_compliance_or_label | 5 | 0.83 | 1.00 | 0.91 |
| air_bag_restraint_control_module_failure | 4 | 0.80 | 1.00 | 0.89 |

## Worst per-label F1 (support ≥ 3)

| label | support | precision | recall | F1 |
|---|---:|---:|---:|---:|
| electrical_system_software_software | 4 | 0.50 | 0.25 | 0.33 |
| antilock_traction_control_electronic_limited_slip_software | 4 | 0.33 | 0.50 | 0.40 |
| belts_and_associated_pulleys_detachment | 4 | 1.00 | 0.50 | 0.67 |
| wiring_electrical | 7 | 0.67 | 0.86 | 0.75 |
| camera_software | 3 | 0.75 | 1.00 | 0.86 |
| air_bag_restraint_control_module_failure | 4 | 0.80 | 1.00 | 0.89 |

Full per-label table and confusion matrix: `accuracy.json`.

## Limits (must accompany any quotation)

- Single 300-record historical sample across 29 components; only 5 fuel-system
  records, so no fuel-specific performance claim is supported.
- Accuracy is not improvement: Phase 2 froze the baseline (no challenger beat
  it); prospective improvement proof remains the registered 2027–2030 study.
- Frozen sample `reports/defect/defect_label_sample_300.csv` is byte-identical
  after import (sha256 `7b0bf958b8756b51…`).
- Labels are evaluation-only: never for fitting, calibration, feature selection,
  or dashboard accuracy.

Reproduce: `python3 -m scripts.defect_accuracy --csv reports/improvement/human_reviews/round2/adjudication/adjudicated_labels.csv --classifications reports/defect/repair/classifications.parquet --manifest reports/defect/repair/review_manifest.json --out /tmp/round2-accuracy-replay.json --require-complete`
