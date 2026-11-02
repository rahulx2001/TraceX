# Repaired defect prediction experiment

**Retrospective reanalysis, not a new holdout or validated physical-defect prediction.**

Scope: Ford, Honda, Hyundai, Kia and Toyota; model years 2015–2024; FUEL SYSTEM; vehicle recalls. The original 6/269 result is preserved in its original files. These denominators differ and must not be compared as a percentage-point improvement.

Complete model coverage: 2203 complaints and 360 recall scope rows. Human labels remain a separate requirement.

Frozen training-selected configuration: `{'window': 13, 'min_count': 2, 'max_tail': 0.2}`.

## All reports

| Strategy | Campaigns detected | Recall | Alert episodes | Mature episode precision | Median lead (weeks) |
|---|---:|---:|---:|---:|---:|
| rolling_defect | 22/41 | 53.7% | 47 | 45.2% (14/31) | 33.1 |
| count_reference | 15/41 | 36.6% | 47 | 35.5% (11/31) | 32.4 |
| original_weekly_on_repaired_data | 5/41 | 12.2% | 10 | 25.0% (1/4) | 39.0 |

Equal-budget random reference: mean recall 40.7%; 95% empirical percentile interval [0.3042682926829268, 0.4878048780487805]. Fraction of 100 seeded draws with recall at least the detector: 0.00. This is a reference distribution, not a confidence interval for prospective effectiveness.

## Excluding explicit recall reports

| Strategy | Campaigns detected | Recall | Alert episodes | Mature episode precision | Median lead (weeks) |
|---|---:|---:|---:|---:|---:|
| rolling_defect | 14/41 | 34.1% | 27 | 53.8% (7/13) | 31.4 |
| count_reference | 10/41 | 24.4% | 27 | 46.2% (6/13) | 31.3 |
| original_weekly_on_repaired_data | 0/41 | 0.0% | 1 | n/a | n/a |

Equal-budget random reference: mean recall 26.2%; 95% empirical percentile interval [0.17073170731707318, 0.36585365853658536]. Fraction of 100 seeded draws with recall at least the detector: 0.07. This is a reference distribution, not a confidence interval for prospective effectiveness.

## Interpretation

- Count each recall campaign once, retain misses, and never match `other_unclear` as a defect.
- A week's counts are available the following Monday. Matching requires 7–364 days of lead.
- Primary precision uses only alerts with the entire 364-day follow-up, including known positives under the same rule; late alerts are censored, not assumed false.
- All training choices are frozen before reanalysis. The 2021–2024 window was previously inspected; independent future validation is still required.
- The recall/campaign-mention sensitivity removes obvious post-recall reporting, but cannot eliminate model pretraining leakage or all reporting bias.
- The same model labels complaints and recalls; a make/component/defect match does not prove identical physical defects or vehicle applicability.
- No accident-reduction, real-customer accuracy, or production superiority claim follows from this experiment.
