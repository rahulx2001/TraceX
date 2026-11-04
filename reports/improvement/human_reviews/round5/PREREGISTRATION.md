# Round 5: preregistered blinded validation (registered, not collected)

Status: REGISTERED BEFORE LABELS. No round-5 labels, scores, or claims exist.
This registration is the only route to strong ML evidence; the opened
300-record benchmark must not be used to tailor a candidate to its answers
(see defect_grounded_v1 EVALUATION.md).

## Design (frozen by this commit)

- Sample: NEW 300 complaints, disjoint by odino from S001-S300, drawn from the
  same pre-2021 NHTSA pool with the defect_sample method. The sample CSV and
  its immutable hash are frozen in a follow-up commit BEFORE any label exists.
- Reviewers: at least 2 humans, blinded to model predictions and to each
  other, using the timed review page. Exports must carry human attestation,
  per-record timing, and the frozen sample hash. No script-generated labels.
- Candidate: prediction code, prompt, taxonomy, and thresholds frozen by hash
  BEFORE scoring. Baseline is the committed repair classifier.
- Scoring: scripts.defect_accuracy --require-complete on adjudicated labels.
  Missing predictions count as wrong. All results published, favorable or not.

## Success criteria (fixed in advance)

Strong evidence requires ALL of: candidate accuracy >= baseline on round-5
gold, paired difference 95% CI excluding zero in the candidate's favor, and
two-reviewer kappa reported before adjudication. Accuracy >= 90% (270/300)
is the product target; falling short is reported as target unmet.

## Prohibitions

No fitting, calibration, feature or threshold selection on round-5 labels.
No label generation by script. No selective reporting of a favorable subset.
Human labeling is human-only work; an agent must not supply it.
