# Export 4: provenance pending

This intake preserves the supplied export for the same frozen 300-record evaluation sample. It passes the structural review checks and contains 300/300 labels with notes, naming Manish.

The complete 300/300 labels and 300/300 notes exactly match reconstruction from `scripts/build_full_rephrased_json.py`. That script reads the previous review, applies 31/300 label changes, generates notes, writes this supplied filename, and stamps `annotation_source: human` and `attestation: true`. Those fields alone do not establish a new independent human review.

The export is preserved pending clarification of any actual human source-evidence review. It has not been imported as a verified human review, adjudicated, scored, used in training/calibration/feature selection, or used for dashboard accuracy. Historical reviews, predictions and claims remain unchanged.

See `provenance_check.json` for identities, timestamps and source hashes. The supplied JSON and exact source generator are preserved separately. Do not execute the archived generator: its top-level code writes review files.
