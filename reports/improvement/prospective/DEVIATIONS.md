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
