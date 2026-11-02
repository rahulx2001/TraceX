# Monitoring and investigation operations

This is a proposed monitoring contract with tested offline aggregation. It has
not been deployed, and no automatic production action is authorized.

Each prediction record must include received time, normalized make/model/year,
component, model/config/data versions, assigned label, abstention reason,
ranking score, probability only when validated calibration exists, and evidence
complaint IDs. Capture severity-source completeness and explicit recall mentions.
Keep immutable prediction-time values so future reprocessing cannot rewrite history.

Weekly, report complaint/alert counts per complete calendar week (including
zero-volume weeks), abstention, latency, failed/missing predictions, duplicate
rates and severity-field completeness. Compare make/component/year/label
distributions against a frozen training reference. The offline monitor reports
total-variation distance and unseen values; >=0.20 triggers investigation, not
automatic model replacement. This is a prespecified operational heuristic, not a
validated drift-to-performance relationship.

Monthly, join official outcomes and label provenance without changing prediction
records. Report all eligible campaign hits/misses. Compute precision only after
the full 364-day follow-up; show censored and unresolved mature outcomes separately.
Never silently omit unresolved mature rows from a deployment gate. Show Wilson
intervals alongside support. With at least 30 resolved mature alerts, an upper
precision bound below the approved target triggers human review. Fewer observations
are reported as insufficient evidence, not success. Monitor recall after campaign
outcomes become observable; don't infer it from alert traffic.

Report each measure by make, component, model year and label, using distinct
campaign-date and alert-date year cohorts. Where one campaign spans strata,
explain that slice totals are not additive. Calibration monitoring uses fixed
validation-defined bins, Brier score and the original training-prevalence reference.
Do not refit bins, calibrators or thresholds on monitoring outcomes without a new
versioned development protocol and independent future evaluation.

An investigator sees alert timing, supporting complaint IDs/text, available
severity evidence, the matching scope, and uncertainty. A reviewer records
confirmed/refuted/insufficient-evidence separately from official recall matching.
Route high-severity evidence through the existing safety workflow. Monitoring
does not suppress existing safety escalation, change severity floors, or claim
that an alert prevented an accident.

Every deployment requires an owner, audit trail, rollback version and explicit
human approval. The current branch performs none of those deployment actions.
