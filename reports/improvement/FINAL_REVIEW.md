# ML improvement review

The research and evaluation infrastructure is implemented. The approved ML
targets have **not been demonstrated**, and no candidate has been trained,
selected, merged or promoted. Human annotation was deferred at the user's
request. An untouched same-scope test window has not been verified or frozen.

Work is on `ml-score-improvement` in the sibling worktree
`v2_ai_rca_tool_ml-score-improvement`. The original dirty checkout and `main`
were left alone. Historical reports remain preserved; claims-audit changes are
append-only. The final implementation commit and checks are recorded in
`final_validation.json`.

## Measured results and limits

See [before_after.md](before_after.md) for the unchanged baseline comparison,
[baseline.json](baseline.json) for every historical metric and its provenance,
and [results.json](results.json) for the unpromoted research result. A baseline
replay is not a new candidate result. The authored category diagnostics, repaired
experiment, broader fuel holdout, safety backtest and OOS test have distinct
denominators and must remain separate.

The permitted pre-2021 same-scope development corpus contains 263 complaints
and 36 campaigns. Under the existing specific labels, only 7/36 campaigns have
preceding matching evidence, or 4/36 after excluding recall mentions. These are
observed input-opportunity counts, not achieved recalls or estimates of the
universal model ceiling. A same-make fuel complaint exists before 29/36 campaigns
(27/36 in sensitivity), but that weaker signal does not establish a matching
defect and cannot replace the original matcher.

All available development errors are listed in [error_analysis.md](error_analysis.md):
2 mature false positives and 33 campaign misses in the all-report variant;
1 and 35 respectively in sensitivity. The variants overlap. Neither supports
50 unique false positives plus 50 unique false negatives; no rows were invented
or repeated to meet that quota. Cause flags are machine observations, not human
causal adjudication. Counts above describe the complete audited corpus; they are
not statistical accuracy estimates.

Calibration diagnostics use 9 mature candidate weeks, including 4 positives,
in 2019–2020. Treating the frozen `1 - predictive_tail` heuristic as a probability
gives ECE 0.338 (row-bootstrap 95% interval 0.211–0.512) and Brier 0.187
(0.055–0.374). This demonstrates unreliability, not calibrated defect risk.
These candidate-week units differ from mature-alert episodes. The sensitivity
diagnostic has only 2 candidates and no positives. No pre-2019 mature training
reference exists, so Brier superiority and calibrated effectiveness remain
unavailable. Exact numerators, denominators, curves and bootstrap settings are
in `runs/baseline_calibration_v1/results.json` and its `started.json`.

## Disposition of every reported problem

| Original problem | Delivered evidence or control | Remaining limit |
|---|---|---|
| 1. Human ground truth | Complete taxonomy labeling guide; frozen review sample preserved; accuracy command reports unavailable | Annotation and double-review deferred; 0/300 human labels |
| 2. Circular labels | Model/recall label sources visible in metrics, model card and dashboard | No physical-defect truth or human accuracy claim |
| 3. Category labels | Supervised text/embedding adapters, per-label/confusion metrics and split guards tested | No independently labeled pre-2021 training set; no candidate evaluation |
| 4. Category descriptions | Precision/coverage curves and abstention evaluator implemented | Higher accuracy and coverage unproven |
| 5. Retrieval | Mixed-candidate query evaluator rejects missing positive/negative controls and preserves k | Old novel-true fixture has zero positives; independent benchmark and stronger embedding comparison pending |
| 6. Defect precision | Causal features and count/logistic/boosting/Gamma-Poisson comparison tooling | No tuning or achieved precision gain |
| 7. Recall mentions | Mandatory exclusion variant, explicit mention features, separate error inventory | Sensitivity gains unproven |
| 8. Recent performance | Recent and first-ever metrics retain separate source fields and units | No substitution of headline bounds for recent performance |
| 9. Random advantage | All preregistered random seeds retained; equal-budget count/random comparison and paired campaign difference tools | No candidate advantage established |
| 10. Tiny holdout | Wilson intervals and support displayed; existing holdout preserved | New same-scope, untouched data needed |
| 11. Missed precision gate | Failed target remains visible; no automatic promotion or fallback claim | Target still not demonstrated |
| 12. Narrow scope | Five makes, model years 2015–2024 and repaired fuel definition preserved | Generalization beyond this scope unproven |
| 13. Metric confusion | Unified baseline inventory and source-checked dashboard with denominators | Distinct benchmarks remain incomparable as one aggregate |
| 14. Lead-time confusion | Historical full-window and recent lead fields remain explicitly separated | No first-ever bound presented as recent lead |
| 15. Calibration | ECE/Brier/reliability and PR diagnostic; Platt/isotonic adapters; unique-row/split/support guards | No calibrated candidate or validation-selected operating point |
| 16. Error analysis | All available development errors; make/component/label and separate alert/campaign-year slices | Requested review quota unavailable; human cause labels absent |
| 17. Monitoring | Offline volume, drift, abstention, maturity and delayed precision/recall aggregation; monitoring plan | Live deployment and owner assignment require separate review |
| 18. Report/dashboard drift | JSON generated from results with source-hash and value checks; tampering tests | No hand-edited metric values |
| 19. Browser tests | Chromium/headless shell installed; sign-in and evidence-panel browser checks; desktop/mobile visual review | Synthetic voice transport does not establish real audio quality |
| 20. Fragmented evaluation | Immutable run directories, protocol/seeds/hashes, exact commands, baseline and verification ledgers | Unknown historical provenance is reported as unavailable |

## Evidence required before continuing

The revised 80% mature-alert precision / 70% campaign recall ambition is already
approved. The separate pending decision is whether to reserve calendar 2027
for prospective same-scope testing and explicitly authorize development-only
experiments now, leaving final scores pending accrual and complete follow-up.
This is an exception to starting only after an available test dataset is frozen;
silence is not approval. The user's original untouched-test rule requires this
decision. An independently attested unused existing same-scope window is another
option. The inspected 2021–2024, 2025 and 2026 outcomes cannot be relabeled as new.

Even with development authorization, the early training folds have inadequate
mature outcomes for reliable supervised fitting/calibration. More informative
same-scope development data and independent labels remain the substantive path
to stronger models. Waiving annotation does not supply those labels. No claim
of a universal achievable ceiling is possible from the current evidence.

Review this report before any merge. Production promotion additionally requires
new untouched results, per-slice/error analysis and explicit human sign-off.
