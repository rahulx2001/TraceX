# Synthetic label-workflow test pack

These are fictional software fixtures. Their expected labels are authored by
the agent and are not human judgments, verified diagnoses, real complaints or
prospective outcomes. Human semantic validation remains 0/300.

The generated pack contains 300 distinct fixture IDs from 12 scenario families,
each with 25 make/context variants. These are not 300 independent observations.
Cases cover six explicit fuel-system diagnoses, vague symptoms, an unidentified
odor source, recall mentions without diagnosis, negated diagnoses, unresolved
alternatives and a report with the wrong component selected.

The data uses `expected_label` and explicit synthetic provenance. It provides
no human-review attestation and leaves `human_label` blank. Never import it as
real human review or use it for fitting, calibration, selection, dashboard
accuracy, the prospective studies or replacement of the frozen sample.

Generate once in a new directory:

```sh
FRONTLINE_TEST_ISOLATION=1 PYTHONDONTWRITEBYTECODE=1 .venv-hackathon/bin/python -B -m scripts.synthetic_label_checks --out reports/improvement/synthetic_review_v1/fixtures
```

Outputs are `fixtures/synthetic_cases.jsonl`, `fixtures/manifest.json` and
`fixtures/software_checks.json`. Checks exercise schema/provenance, taxonomy
label parsing and a deliberately authored denominator control. No ML classifier
is called. A passing software check does not establish that a classifier
understands these narratives or performs accurately on real records.

## You need records reviewed, not 300 people

The existing [blind review page](../../defect/repair/human_review.html) contains
the actual frozen 300-record sample and hides model predictions. One primary
reviewer can review these records over multiple sessions, for example 12 batches
of 25, exporting a backup after each session. The person must read the narrative
and make each choice; do not substitute generated expected labels or accept
model suggestions as independent human judgments.

The existing [labeling protocol](../labeling_guide.md) additionally calls for
a second blinded reviewer on at least 50 pre-registered IDs and adjudication of
disagreements. That means two reviewers with different workloads, not 300
participants. Use separate browser profiles so saved choices are not exposed
to the second reviewer. Pre-register the overlap IDs before review starts.
The synthetic work does not waive this requirement or lower the sample target.

The real sample covers 29 components; only 5 records are in FUEL SYSTEM.
It supports review of the broader classifier, not a 300-case fuel-only
performance claim. Its 2021–2024 narratives and any resulting labels remain
evaluation-only and must not enter development fitting or feature selection.

After genuine human review, import an actual exported JSON into a fresh
destination, preserving the blank source sample:

```sh
.venv-hackathon/bin/python -B - <<'PY'
from pathlib import Path
from scripts.defect_review import import_review
import_review(
    Path("<ACTUAL_HUMAN_EXPORTED_REVIEW_JSON>"),
    destination=Path("reports/improvement/human_reviews/round1"),
)
PY
```

Do not execute this example with synthetic data. The importer requires the
correct sample hash, a reviewer name and an explicit human-review attestation.
Those checks record claimed provenance; they cannot prove a person actually
reviewed the cases. A smaller completed subset is partial review, not 300/300
validation. Agreement/adjudication and model-versus-human evaluation follow
the original protocol; no accuracy result is produced by this test pack.
