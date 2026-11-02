# Frozen human evaluation: round 1

Rahul and Manish each supplied 300/300 unique labels with notes. Both original
exports, imported CSVs, reviewer IDs, supplied export timestamps, and importer
provenance records are preserved. Neither export supplies per-record annotation
timestamps.

- [Rahul's original export](primary_review_export.json) and [provenance](human_review_provenance.json)
- [Manish's original export](second_review/manish/original_review_export.json) and [provenance](second_review/manish/human_review_provenance.json)
- [User confirmation of independence and prior full-sample assignment](second_review/manish/user_confirmation.json)
- [Reliability gate and evidence limits](reliability_gate.json)
- [Agreement before adjudication](agreement_before_adjudication.json)
- [Disagreement-resolution trail](adjudication/decision_trail.json) and [final evaluation labels](adjudication/adjudicated_labels.csv)
- [Evaluation report](EVALUATION.md), [complete accuracy metrics](accuracy.json), and [current status](review_status.json)

All 300/300 labels and notes match between the two exports. The user confirms
Manish independently reviewed a blank page and was assigned all 300 records
before beginning on 1 November. The gate uses that reported prior assignment
and the already frozen full 300-ID list; it does not characterize the 50-ID
packet created on 2 November as prospective for Manish. Review independence
and assignment chronology remain human-attested rather than independently
verified. Agreement does not establish correctness by itself.

There are 0/300 label disagreements, so the trail accepts the matching labels
without inventing individual human adjudication judgments. Both original
reviews remain unchanged.

Scoring uses the saved repaired classifier output prescribed by the repair
runbook, covering the full sample. Missing predictions count as wrong and
remain in accuracy, support, recall, F1, and confusion denominators. The score
is an evaluation of this opened historical sample, not a new holdout result.

To reproduce the saved accuracy into a separate file, run from the repository:

```sh
python3 -m scripts.defect_accuracy \
  --csv reports/improvement/human_reviews/round1/adjudication/adjudicated_labels.csv \
  --classifications reports/defect/repair/classifications.parquet \
  --manifest reports/defect/repair/review_manifest.json \
  --out /tmp/round1-accuracy-replay.json --require-complete
```

The original `reports/defect/defect_label_sample_300.csv` remains byte-identical
to its frozen manifest. These labels and the synthetic fixtures in
`reports/improvement/synthetic_review_v1/` are evaluation-only. Never use them
for fitting, calibration, feature selection, or dashboard accuracy.
