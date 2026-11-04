# Manish export 4: human-approved revision, adjudication pending

**Historical archive:** this page describes the revision before finalization.
The original 31-decision [adjudication export](finalized/adjudication_export.json)
and [status](finalized/status.json) are preserved. This assisted revision is not
current independent blinded review evidence; see the [withdrawal](../../../REJECTED_fabricated_rounds.md),
[Round 4](../../../round4/EVALUATION.md) and [export inventory](../../../EXPORT_INDEX.md).

The importer accepted 300/300 unique human labels with 300/300 notes from `defect-review (4).json`, naming Manish and containing `annotation_source: human`, `attestation: true`. Its sample hash matches the frozen 300-record sample. Import output is in `human_labelled.csv`; the original JSON and importer provenance are preserved.

The complete array exactly matches the automated `build_full_rephrased_json.py` generator. The user subsequently confirmed: “Manish personally reviewed every final label.” This is recorded as a human-approved assisted revision. It is not described as a new independent blinded review or fresh holdout. The generated notes remain preserved even where the source audit identifies unsupported details.

Before adjudication, Rahul original and this revised Manish review agree on 269/300 labels (89.7%; 95% paired-bootstrap interval 86.0%–93.0%). Cohen’s kappa is 0.802502 over 300 paired rows (95% interval 0.733394–0.864478). There are 31/300 disagreements. These statistics describe this pair and do not verify independent review. Full prevalence and per-label disagreement are in `agreement_before_adjudication.json`.

## Remaining action

Open `adjudication.html`. A named human can resolve the 31/300 disagreements from each source narrative, with both original labels/notes visible. The assistant’s source-only proposals are drafts: 28/31 retain Manish’s revised label; 3/31 suggest other_unclear instead of the revised specific label (S017, S078, S237) because its required part/mode evidence is absent.

Choose the final allowed label, confirm verbatim evidence and reasoning, and mark every record reviewed. Export `defect-adjudication-export4.json`. The page retains original reviews, packet/source hashes, reviewer IDs and per-decision timestamps. Saved progress is isolated to this packet. No model predictions are shown.

Revised accuracy is unavailable until those 31/31 decisions are complete and validated. Historical 246/300 = 82.0% baseline and 209/300 = 69.7% rejected-candidate scores remain preserved under their original labels. No new model score, training, calibration, feature selection or dashboard accuracy update has been performed.

Importer provenance is `human_review_provenance.json`. Script-origin evidence is preserved in `../../../pending/export4/provenance_check.json`; user confirmation is `human_confirmation.json`. The adjudication draft checks passed 31/31 identity, label and exact-source-quote checks; page JavaScript syntax passed.
