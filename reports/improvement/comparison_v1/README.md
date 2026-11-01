# More campaign evidence and a separate comparison

The fixed logistic-versus-baseline comparison is registered here for the future
2027–2028 cohort, with outcome cutoff 2029-12-31. It does not replace or alter the
original Mode B study. The two studies share a cohort and are not independent
replications. No real future data has been collected or evaluated.

[PREREGISTRATION.md](PREREGISTRATION.md) specifies the hypotheses, denominators,
sample/dependence rules and decision criteria. [protocol.json](protocol.json)
is the machine-readable version. [RUNBOOK.md](RUNBOOK.md) covers future human
operations. The separate comparison freeze tag is
`ml-logistic-comparison-freeze-2026-v1`.

Development-only evidence; not a candidate result and not a prospective estimate.
The [campaign census](campaign_census.json) checked the pinned official recall
archive using only 2015–2020 identity/scope fields. It found **36 distinct
campaigns**, all already present in the prepared dataset: **0 additional
campaign IDs**, **0 new campaigns acquired**. Model/year scope rows were not
counted as independent campaigns. No recall descriptions were parsed and no
post-2020 development frame was created.

This establishes coverage of the pinned source, not every possible later
revision or every real-world defect. The current restrictions do not supply
an additional untouched historical dataset. Already opened data cannot be
made untouched by splitting it again. More independent prospective campaigns
and their completed follow-up remain future evidence, not completed work.

The prospective sample needs at least 25 distinct eligible campaigns,
preferably 30. Below 25 the harness returns counts only. Confirmation also
requires at least 25 campaign-linked components; distinct IDs alone do not
establish independence. The fixed MY2015–2024 cohort may not accumulate enough
cases. The threshold is never reduced after inspecting results.

The original baseline, logistic coefficients, dashboard scores and 0/300 human
labels are unchanged. No improved-score claim, merge or promotion is made.
The comparison pre-registration is recorded locally in Git; no independent
external timestamp or public registry entry is claimed.
