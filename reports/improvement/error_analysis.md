# Development error inventory

Source: `reports/improvement/runs/audit_v1/results.json`. All unique errors are listed, including sparse and unknown-label cases. False positive means no qualifying later recall match; it does not establish absence of a physical defect.

Cause taxonomy: wrong category, recall mention, duplicate, weak evidence, wrong scope, timing/leakage, label ambiguity. Observations are flags for review, not human cause labels.

## all_reports

Unique mature false positives available: 2; unique campaign misses available: 33.
This is a machine evidence audit on pre-2021 development data. Human causal adjudication is unperformed. The requested 50+50 quota cannot be met within this corpus; rows are not duplicated and the scope is not expanded.

| Error | Identity | Observed evidence |
|---|---|---|
| FP | 2018-06-18 / FORD / FUEL SYSTEM / fuel_pump_failure | {"recall_mention": 0, "weak_evidence": true, "duplicate": false}; evidence IDs 11100320, 11101818 |
| FP | 2019-08-26 / FORD / FUEL SYSTEM / fuel_pump_failure | {"recall_mention": 1, "weak_evidence": true, "duplicate": false}; evidence IDs 11244955, 11245636 |
| FN | 15V005000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V339000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V475000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V605000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": true, "matching_label_gap": false} |
| FN | 15V618000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 16V417000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 16V618000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": true, "matching_label_gap": true} |
| FN | 16V621000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V661000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V778000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V945000 | prior fuel complaints: 8; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 17V170000 | prior fuel complaints: 10; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V219000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V269000 | prior fuel complaints: 10; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V442000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V681000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V805000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V108000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 18V392000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V735000 | prior fuel complaints: 5; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V807000 | prior fuel complaints: 5; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V907000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V053000 | prior fuel complaints: 14; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V060000 | prior fuel complaints: 14; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V097000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V569000 | prior fuel complaints: 14; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V859000 | prior fuel complaints: 23; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V012000 | prior fuel complaints: 3; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V162000 | prior fuel complaints: 3; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V314000 | prior fuel complaints: 7; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V560000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V700000 | prior fuel complaints: 103; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V797000 | prior fuel complaints: 13; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": true, "matching_label_gap": true} |

## excluding_explicit_recall_reports

Unique mature false positives available: 1; unique campaign misses available: 35.
This is a machine evidence audit on pre-2021 development data. Human causal adjudication is unperformed. The requested 50+50 quota cannot be met within this corpus; rows are not duplicated and the scope is not expanded.

| Error | Identity | Observed evidence |
|---|---|---|
| FP | 2018-06-18 / FORD / FUEL SYSTEM / fuel_pump_failure | {"recall_mention": 0, "weak_evidence": true, "duplicate": false}; evidence IDs 11100320, 11101818 |
| FN | 15V005000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V339000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V475000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 15V605000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": true, "matching_label_gap": false} |
| FN | 15V618000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 16V417000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 16V618000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": true, "matching_label_gap": true} |
| FN | 16V621000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V661000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V778000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 16V945000 | prior fuel complaints: 7; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 17V170000 | prior fuel complaints: 9; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V219000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V269000 | prior fuel complaints: 9; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V442000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V681000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 17V805000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V108000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 18V392000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V735000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V807000 | prior fuel complaints: 5; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 18V907000 | prior fuel complaints: 1; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V053000 | prior fuel complaints: 14; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V060000 | prior fuel complaints: 14; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V097000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V515000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V569000 | prior fuel complaints: 13; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 19V859000 | prior fuel complaints: 9; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V012000 | prior fuel complaints: 2; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V162000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V314000 | prior fuel complaints: 5; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V560000 | prior fuel complaints: 0; matching-label complaints: 0; {"no_prior_evidence": true, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V700000 | prior fuel complaints: 4; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": true} |
| FN | 20V730000 | prior fuel complaints: 15; matching-label complaints: 1; {"no_prior_evidence": false, "label_ambiguity": false, "matching_label_gap": false} |
| FN | 20V797000 | prior fuel complaints: 7; matching-label complaints: 0; {"no_prior_evidence": false, "label_ambiguity": true, "matching_label_gap": true} |
