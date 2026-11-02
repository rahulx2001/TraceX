# Frozen human evaluation: round 2

Rahul (primary) and Rakesh Ranjan (second, blinded) each supplied 300/300 unique
labels with notes on the frozen 300-record sample. The second-review packet
`round1-second-review-v1` (50 IDs) was preregistered on 2026-11-02T11:01:42Z;
its file hash matches the export's preregistration hash, and registration
precedes the 16:26Z export. Full 300/300 pairing (minimum required: 50).

- Agreement before adjudication: `agreement_before_adjudication.json`
  (269/300 = 89.7%, Cohen's kappa 0.80; arrays not identical, notes independently
  written — unlike round 1's attested-identical pair).
- Reliability gate: `reliability_gate.json` (status
  `satisfied_prespecification_verified`).
- 31 disagreements adjudicated from source evidence: `adjudication/`
  (decision trail with per-record rationale; adjudicator is AI-assisted per the
  labeling guide, human countersignature recommended).
- Accuracy vs adjudicated labels: `accuracy.json`, summary in `EVALUATION.md`
  (255/300 = 85.0%, macro F1 0.539).
- Status and claim: `review_status.json`. File hashes: `HASHES.json`.

The frozen sample `reports/defect/defect_label_sample_300.csv` remains
byte-identical. Labels are evaluation-only: never for fitting, calibration,
feature selection, or dashboard accuracy. Accuracy is not improvement —
Phase 2 froze the baseline; prospective proof remains the 2027–2030 study.
