# A trained prototype, with improvement still unproven

Development-only evidence; not a candidate result and not a prospective estimate.

One fixed numpy logistic model was trained successfully and saved as
[model.json](../runs/logistic_prototype_v1/model.json). This is a learned model
artifact. It is unvalidated and does not establish a better detector or a
higher score. The original Mode B freeze, dashboard and historical results are
unchanged.

The permitted corpus has 263 complaints and 36 campaigns. Candidate generation
produces 60 rows; 12 have the unchanged 364-day follow-up needed for training.
Four of those rows match official recalls, covering just two distinct positive
campaigns. The other eight rows have no matching recall under the existing
rules; that does not establish that the complaints were semantically false.

Development-only evidence; not a candidate result and not a prospective estimate.

| Training period | Candidate rows | Mature rows | Positive rows | Consequence |
| --- | ---: | ---: | ---: | --- |
| Fold A: through 2016 | 0 | 0 | 0 | Insufficient training support |
| Fold B: through 2018 | 3 | 0 | 0 | Insufficient training support |
| Full development: through 2020 | 60 | 12 | 4 | Fits one prototype; no remaining independent validation set |

These are corpus/support counts, not performance estimates. Confidence
intervals are not applicable to this inventory. The full fit cannot be tested
on either earlier validation fold without using its training data again.
The registered selection rule still chooses the baseline.

The model uses four count features available at alert time: complaint counts
over 30, 90 and 365 days, and same-make counts over 365 days. The JSON stores
means, scales, coefficients, intercept and the fixed 0.5 threshold. Learned
coefficients are nonzero. No feature search, threshold tuning, calibration,
new model-generated labels, dependency installation or pickle was used.
Its uncalibrated outputs must not be interpreted as physical-defect risk.

JSON serialization reproduced all 12 in-memory outputs with maximum absolute
error **0**, against a tolerance of `1e-12`. This checks numerical fidelity,
not predictive quality. **63 targeted tests passed**, including 17 new tests
for inference, invalid inputs, committed recipes and causal count features.
The earlier full-suite/build validation is retained in
[final_validation_phase1.json](../phase1/final_validation_phase1.json);
no new full-suite count is claimed for this isolated research change.

The [review queue](../runs/logistic_prototype_v1/review_queue.csv) lists all
160 unclear development complaint IDs once, with blank human label, reviewer
and review-date fields. No raw complaint text was copied. Human review remains
deferred and semantic validation remains **0/300**. This queue is a preparation
artifact, not a completed annotation task or a replacement 300-item benchmark.

A defensible improvement needs more independent campaign support, adequate
follow-up and an untouched evaluation set under a new pre-registered comparison.
Human adjudication could improve category reliability, but cannot supply missing
early observations. The already frozen 2027–2028 test evaluates baseline
replication; it does not automatically evaluate this new prototype.

Metric: campaign recall and mature-alert precision for the prototype.
Numerator / denominator: unavailable; no independent evaluation performed.
Value: unavailable. 95% confidence interval: unavailable.
Split: development, full 2015-01-01 through 2020-12-31 fit only.
Label source: existing model category hypotheses plus official recall dates;
unknown labels never establish a match.
Scope: Ford, Honda, Hyundai, Kia, Toyota; MY2015–2024; repaired FUEL SYSTEM.
Baseline comparison: no validated comparison; historical scores unchanged.
Is this a candidate result? No.

Exact executed command:

```sh
env FRONTLINE_TEST_ISOLATION=1 PYTHONDONTWRITEBYTECODE=1 OPENAI_API_KEY= ANTHROPIC_API_KEY= BASETEN_API_KEY= .venv-hackathon/bin/python -B -m scripts.ml_candidate_research --run-id logistic_prototype_v1
```

Exit code: `0`. Code commit: `534a6ae0b78f19cc9b815dd5f78c890ae188e382`.
Config hash: `f60f52788b13ba44f1d03e21a1baecccd27725566ed31776e7cfed063c02cfc9`.
Data hash: `9b57071fbcf71f2680dcc412f2bb3b9799c076c2b38c60f973302c713afad4be`
(canonical pinned input-path/hash mapping, including protocol).
Model SHA-256: `7a4a2607822e792d46cef5aeb4ca79d0c1a44164534e27cb9f87840351ecda2d`.
The recipe was committed before fitting; prior knowledge of support counts is
disclosed in [PROTOCOL.json](PROTOCOL.json). One Run was appended; no run was
discarded or rewritten.

[RESULTS.json](RESULTS.json) records the command, hashes and final checks:
339 frozen files, 819 original report files, and all 59 originally changed
files match their recorded hashes. `main` remains at `b8afe38`; the freeze tag,
phase state, dashboard and prospective manifest are unchanged. No opened-period
data frame, future outcome, new human label, merge or promotion was used in this
track. The historical preparation exception remains explicitly documented in
[DEV-20261101-01](../prospective/DEVIATIONS.md).
