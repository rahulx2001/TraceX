# REJECTED: machine-generated "human" review rounds (round 2, round 3)

Status: withdrawn. This file records what happened, how it was detected, and
what stands, so the withdrawal itself is auditable. No history was rewritten;
the removal commit sits on top of the pushed record.

## What was withdrawn

- `round2/` (Rakesh Ranjan second review, agreement kappa 0.80, adjudication,
  85.0% accuracy, revision rev1) — entire directory.
- `round3/` (Gaurav timed replication, 47/50, kappa 0.88) — entire directory.
- `overlap_round2_ids.json` (stratification for the withdrawn round).
- All claim text derived from the above (accuracy 85%, kappa values,
  "prespecification-verified second review" language).

## How the fabrication was established

The following untracked helper scripts in `scripts/` write the exact review
files that were presented as human work (all paths absolute to Downloads;
all read other reviewers' exports as input):

- `scripts/build_rakesh_ranjan_reviews.py` — reads Rahul's export plus a
  hard-coded disputed-labels dict and WRITES the Rakesh p50/p300/default
  review files. The kappa-0.80 "independent" agreement was script output.
- `scripts/build_gaurav_review_5.py` — reads Rahul/Manish/Rakesh exports plus
  hard-coded labels and notes and WRITES `defect-review (5).json` (300 records).
- `scripts/build_gaurav_outsider_50.py` — WRITES the same path with 50 records,
  generating `first_shown_at`, `labeled_at`, and `dwell_before_label_ms` from
  `random.Random(20261102)`. The "median dwell ~63s" timing evidence was
  random-number output.
- `scripts/generate_manish_full_review.py` — builds Manish's review from
  Rahul's export and a hard-coded disagreements dict (that round was already
  deprecated for byte-identical arrays).

No generator was found for Rahul's original export (`defect-review (2).json`);
it stands as attested single-reviewer labels — weak evidence, not disproven.

## Detection notes (for future controls)

- Statistical checks (agreement, kappa, note-text comparison) PASSED the
  fabricated rounds: the fabrication was designed to look independent
  (kappa 0.80, paraphrased notes). Statistics cannot detect provenance fraud.
- What caught it: (1) full-300 export 3 minutes after packet registration —
  physically impossible pace; (2) 300/300 label identity with the source file;
  (3) the generator scripts present in the working tree.
- Lesson recorded: provenance must rest on observed process (timed pages,
  outsiders, packet discipline), never on the statistical shape of the labels.

## What stands after withdrawal

- Rahul 300/300 attested labels and the real accuracy computation against them
  (246/300 = 82.0%, single-reviewer, unvalidated).
- The registered grounded-candidate comparison (round-1 labels): candidate
  209/300 rejected at -12.3pp. Real computation, unchanged.
- Per-record timing instrumentation on the review page; the outsider packet
  (reusable for a genuine future review); the Manish-round deprecation.
- These generator scripts were never committed. They are preserved on disk as
  evidence and must never be presented as review tooling.
