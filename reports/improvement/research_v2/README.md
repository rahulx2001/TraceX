# Exploratory trained prototype

Development-only evidence; not a candidate result and not a prospective estimate.

This track fits one small logistic model using the already prepared, hash-pinned
2015–2020 files. It responds to the request for actual modeling work. It does not
replace the immutable baseline, amend the original selection result, or enter
the existing Mode B prospective test.

The completed run, observed support counts, numerical checks and limitations
are recorded in [RESULTS.md](RESULTS.md) and [RESULTS.json](RESULTS.json).

The support audit found zero mature training rows in both registered folds.
The full development period has 12 mature candidate rows, including 4 positive
rows. That meets the existing fitting minimum but leaves no untouched permitted
evaluation set. Several rows may share a campaign, so row count overstates
independent support. These counts were known before the recipe was committed;
this is an exploratory fit, not a new confirmatory pre-registration.

[PROTOCOL.json](PROTOCOL.json) specifies one fixed numpy L2 logistic fit using
prior complaint counts over 30/90/365 days and same-make counts over 365 days.
Counts retain the existing frozen detector's category grouping; no recall text
or label text is a numeric feature. Existing model labels remain hypotheses,
not human truth. The script refuses uncommitted recipe changes and verifies
both input hashes and the original freeze before fitting.

Run after committing the recipe and code:

```sh
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -B -m scripts.ml_candidate_research --run-id logistic_prototype_v1
```

The append-only Run records code, configuration and input hashes. Outputs are
JSON coefficients, a support audit, an inference serialization check, a model
card and a blank queue of existing unclear development complaint IDs. No
human labels are supplied or inferred. No additional dependency is installed.

An improved-score claim still requires independent evaluation and adequate
campaign support. This full-development fit cannot be evaluated on the earlier
folds without leakage. Human adjudication could resolve ambiguous categories,
but cannot create absent early complaints or completed outcome follow-up.
The original 2027–2028 test evaluates baseline replication only; evaluating
this prototype would require a separate pre-registered comparison. Human
review remains deferred, and the label count remains 0/300.
