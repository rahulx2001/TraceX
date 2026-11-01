# Prospective deviations and amendments

This log is append-only. Preserve the pre-registration, original run records,
frozen files, and `ml-prospective-freeze-2026` tag. A deviation does not erase an
earlier action or establish an improved score. No prospective outcomes have
been collected or inspected in this work.

## DEV-20261101-01 — historical preparation read acknowledged

- Date: 2026-11-01.
- Approver: Rahul Kumar Singh, through the conversation approving the displayed
  “Approve this narrow amendment” option with “complete this that you have asked”.
  This records conversational approval, not a cryptographic signature.
- Reason: `prepare_v1` read the repaired 2015–2024 complaint and recall files
  into pandas before filtering. Source metadata reaches 2024-12-31 and
  2024-12-20, respectively. The original no-read acceptance gate cannot be
  asserted retrospectively for that preparation step.
- Amendment: acknowledge that historical preparation read as a deviation.
  Retain the strict 2015-01-01 through 2020-12-31 row boundary for the
  pre-registered Phase 2 experiment. Its two hashed inputs contain 263
  complaints and 136 recall scope rows covering 36 campaigns, all pre-2021.
  Do not re-run preparation, tune on opened history, or use any 2021+ row for
  fitting, calibration, evaluation, feature choice, or selection in Phase 2.
- Evidence: `reports/improvement/runs/prepare_v1/started.json` and
  `finished.json`; `scripts/ml_improvement.py` preparation reader;
  `reports/improvement/development_manifest.json`;
  `reports/improvement/runs/phase1_development_v1/started.json`.
- Files affected: this append-only log, Phase 5 reports/claims and validation
  metadata, and the resumability record. Original preparation records,
  pre-registration, protocol, Phase 2 decision, frozen models/code and tag
  remain unchanged.
- Effect on claims: Phase 2 is accepted only under this explicit amendment.
  There is no claim that all historical preparation avoided opened rows.
  Mode B remains baseline replication; no improvement, semantic accuracy,
  independent historical holdout, or prospective performance is claimed.

## DEV-20261101-02 — post-freeze reporting and operations documentation

- Date: 2026-11-01.
- Approver: Rahul Kumar Singh, via the authorized Phase 5–6 task.
- Reason: finish reporting, dashboard reservation/custody notices, validation,
  and human operations runbooks after the freeze.
- Files affected: `reports/improvement/phase1/` reporting and validation files,
  `reports/CLAIMS_AUDIT.md` (append only), dashboard evidence JSON/component/test,
  `scripts/ml_improvement_report.py`, its reporting test,
  `reports/improvement/prospective/` runbooks/templates/log, and
  `data/prospective/README.md`. The exact committed paths are in the Phase 5
  and Phase 6 commits and validation input manifest.
- Effect on claims: metadata and presentation only; numerical evidence,
  matching rules, windows, denominators, thresholds and frozen artifacts are
  unchanged. Validation counts describe engineering tests, not ML accuracy.
  The final analysis must run code from the immutable freeze tag.


### DEV-20261101-02 completion — Phase 6

Date: 2026-11-01. Approver: Rahul Kumar Singh via the Phase 6 instruction.
Phase 5 was committed as `3a50479260598d48891aa883006d6fcbf61226e5`. Phase 6 adds the human runbook and blank
attestation template, appends links to `data/prospective/README.md`, and updates
phase/verification metadata. Five shell examples and their embedded Python
snippets were syntax-checked without execution. Frozen files/tag, source
windows, sample floor, metrics and denominators remain unchanged. No real
2027+ data was accessed. No future attestation was made on the human's behalf.

## DEV-20261101-03 — separate unvalidated trained prototype

- Date: 2026-11-01.
- Approver: Rahul Kumar Singh, via the follow-up request for better modeling
  work ("please make it best"). This authorizes exploratory work within the
  existing data limits, not a change to the frozen selection or test.
- Reason: both original fit folds lacked mature outcomes; the full 2015–2020
  development period supports fitting one small model, without a permitted
  untouched validation set. Record that distinction and a fixed recipe.
- Files affected: new `scripts/ml_candidate_research.py`, its tests,
  `reports/improvement/research_v2/`, a new immutable Run directory and an
  append-only `reports/improvement/experiments.csv` row.
- Effect on claims: trained but unvalidated prototype only. No training score
  is presented as validation. Frozen artifacts/tag, original decision/results,
  dashboard scores and human-only Phase 7 state remain unchanged. The prototype
  is excluded from the existing Mode B prospective test and from production.
- Data boundary: use only the two pinned prepared pre-2021 files; do not rerun
  preparation or access opened-period/prospective outcomes. The historical
  preparation limitation remains recorded in DEV-20261101-01.
- Human labels: the ID-only review queue is blank. Review remains deferred;
  human semantic validation remains 0/300.

## DEV-20261101-04 — campaign census and a separate fixed comparison

- Date: 2026-11-01.
- Approver: Rahul Kumar Singh, through the request to complete more independent
  campaigns with full follow-up and a separately pre-registered comparison.
- Reason: establish whether uncounted pre-2021 campaigns are available within
  the unchanged scope, and reserve a separate comparison of the already fitted
  logistic prototype against the original baseline before future outcomes exist.
- Files affected: new census/comparison scripts, tests and
  `reports/improvement/comparison_v1/`; this append-only log.
- Data boundary: the census inspects date headers of the pinned local recall
  archive, retaining only 2015–2020 identity/scope fields. It never parses recall
  descriptions or constructs a post-2020 development frame. It does not create
  new campaign observations or make previously opened history untouched.
- Effect on claims: the separate study is a fixed research comparison, not
  retroactive qualification under the original Phase 2 selector. The original
  Mode B protocol, decision, freeze/tag, dashboard and 0/300 human label count
  remain unchanged. The new comparison shares the reserved future cohort;
  it is not a second independent dataset or an independent replication of
  results from that cohort. No future collection or final analysis is authorized
  for execution now. No improvement or promotion is claimed.

## DEV-20261101-05 — synthetic label-workflow fixtures

- Date: 2026-11-01.
- Approver: Rahul Kumar Singh, through the request to generate testing data
  because 300 people were unavailable.
- Interpretation: 300 is a record count, not a participant count. Generate
  clearly fictional software fixtures; do not invent human labels, reviewers
  or attestations and do not claim human validation is complete.
- Files affected: new `scripts/synthetic_label_checks.py`, its tests and
  `reports/improvement/synthetic_review_v1/`; this append-only log.
- Effect on claims: 300 template variants, zero real independent observations,
  zero new human labels and no classifier inference or accuracy estimate.
  Fixtures are excluded from fitting, selection, human review, dashboard
  metrics and both prospective studies. Existing second-reviewer/50-record
  overlap requirements remain unchanged; no review protocol is waived.
- Integrity: preserve both freeze tags/artifact sets, the original 300-row
  blank sample, all real score values, `main` and the original checkout.
