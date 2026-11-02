# Development results

Development-only evidence; not a candidate result and not a prospective estimate.

Decision: **mode_b_baseline**. No method satisfies all fold, denominator and bootstrap conditions.

| Variant / fold / method | Recall (95% CI) | Mature precision (95% CI) | Alerts / mature / censored |
|---|---|---|---|
| all_reports / A / gamma_poisson | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| all_reports / A / count_2 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| all_reports / A / count_3 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| all_reports / A / count_5 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 0 / 0 / 0 |
| all_reports / B / gamma_poisson | 3/14 = 21.4% [7.6%, 47.6%] | 1/2 = 50.0% [9.5%, 90.5%] | 9 / 2 / 7 |
| all_reports / B / count_2 | 3/14 = 21.4% [7.6%, 47.6%] | 1/3 = 33.3% [6.1%, 79.2%] | 12 / 3 / 9 |
| all_reports / B / count_3 | 1/14 = 7.1% [1.3%, 31.5%] | 0/0: unavailable | 7 / 0 / 7 |
| all_reports / B / count_5 | 1/14 = 7.1% [1.3%, 31.5%] | 0/0: unavailable | 4 / 0 / 4 |
| excluding_explicit_recall_reports / A / gamma_poisson | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| excluding_explicit_recall_reports / A / count_2 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| excluding_explicit_recall_reports / A / count_3 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 1 / 0 / 1 |
| excluding_explicit_recall_reports / A / count_5 | 0/11 = 0.0% [0.0%, 25.9%] | 0/0: unavailable | 0 / 0 / 0 |
| excluding_explicit_recall_reports / B / gamma_poisson | 1/14 = 7.1% [1.3%, 31.5%] | 0/0: unavailable | 3 / 0 / 3 |
| excluding_explicit_recall_reports / B / count_2 | 1/14 = 7.1% [1.3%, 31.5%] | 0/0: unavailable | 3 / 0 / 3 |
| excluding_explicit_recall_reports / B / count_3 | 0/14 = 0.0% [0.0%, 21.5%] | 0/0: unavailable | 2 / 0 / 2 |
| excluding_explicit_recall_reports / B / count_5 | 0/14 = 0.0% [0.0%, 21.5%] | 0/0: unavailable | 0 / 0 / 0 |

Development-only evidence; not a candidate result and not a prospective estimate.

Both folds have zero mature training outcomes; all five logistic seeds are recorded as insufficient_training_support. No calibrator was fitted. Boosting was excluded before runs to avoid unnecessary complexity. All 100 random references per comparison and the equal-budget count reference, including any failures, are retained in development_results.json. Rates use unchanged evaluators; lead support, per-slice outcomes and every bootstrap draw count are retained there. Undefined precision cannot satisfy selection.

Label source: frozen model labels + official recalls. Scope: five specified makes, MY2015–2024, repaired FUEL SYSTEM, development dates 2015–2020. No human truth or prospective estimate.

Exact command: `FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement prospective-develop --run-id phase1_development_v1`
Config SHA-256: `647a190b6d1284f162a2846f3411b4e2f6e1ba5085b1e4c071012ea26786c266`
Data SHA-256: `08642ba9cff8fff1c27e7a3dc562a89f32757eb4009c66be3dce27e570cf0b1c`
Recorded code commit: `440b90e5452f199dd9cf6e08ae3be640d59b7300`; uncommitted experiment code SHA-256: `e7db03a5bba0f842034e998847073ba64163479f1ab46e47ddb7d0f15e2a6a1e`. The Phase 2 commit contains the implementation.
Result path: `reports/improvement/runs/phase1_development_v1/results.json`.

Development-only evidence; not a candidate result and not a prospective estimate.
