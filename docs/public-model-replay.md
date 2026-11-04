# Reproduce the saved model-to-alert result

This replay runs the frozen local student's predictions from the original
cached MiniLM embeddings, then repeats temporal feature construction, alert
selection, campaign matching and all 100 random-reference runs. It compares
the complete recomputed results with the saved 29 October experiment. It makes
**zero Meta API calls** and creates no human results.

The [download descriptor](../reports/defect/fuel_holdout/public_replay_release.json)
pins the public archive's URL, size and SHA-256. The [file manifest](../reports/defect/fuel_holdout/public_replay_manifest.json)
pins all nine payloads and the evaluator source files.

## Run

Use the project's installed environment, or create a small replay environment:

```bash
python3.12 -m venv .venv-replay
.venv-replay/bin/python -m pip install -r requirements-replay.txt -c requirements-lock.txt
.venv-replay/bin/python -m scripts.public_model_replay verify --download
```

With NumPy and pandas already installed:

```bash
python3 -m scripts.public_model_replay verify --download
```

The first run downloads approximately 20.5 MB and validates every file before
creating `data/public_replay/fuel-v1`. Later runs use that checked local cache.
The command refuses changed files, unexpected archive entries or replacement
of an existing destination. It never calls `prepare`, `develop` or `test` on
the historical experiment and never overwrites its results.

For an already downloaded archive, extract its files to a separate directory
and pass that directory explicitly:

```bash
python3 -m scripts.public_model_replay verify --inputs /path/to/replay-files --out /tmp/tracex-replay-result.json
```

The output report path must be new. Successful verification means the selected
method, count baseline, opportunity diagnostic and all random references match
the saved result, including **5/8 campaign matches and 6/18 mature-alert matches**.
Those are scoped historical results; the candidate was not promoted.

## Public payload and original inputs

| Payload | Retained information |
|---|---|
| Development and holdout CSVs | Date, public complaint ID, make, component and original inclusion/exclusion flag |
| Teacher CSV | Original dated model labels in the same row order |
| Two recall-reference CSVs | Campaign ID, component, recall date, make and model-assigned label |
| Three `.npy` arrays | Byte-identical original cached embeddings; they were generated from redacted text |
| `final_student.npz` | Byte-identical fitted local-student weights and classes; no Meta foundation-model weights |

Original complaint narratives contain contact/VIN-like patterns. The public
projection removes **all free-text columns**, retaining the already recorded
text-filter decision instead of distributing the narratives. Dates, row order,
embedding arrays and fitted coefficients are preserved; the saved result is
not retuned. Public files have their own hashes and are explicitly distinct
from the original Parquet files. Export metadata was created after the historical
experiment and does not pretend to be a new preregistration.

This makes the prediction-and-alert replay publicly reproducible. Rebuilding raw
ingestion, regenerating embeddings, retraining/selection or repeating Meta
classification still requires the original source snapshots and environment
described in [the frozen experiment README](../reports/defect/fuel_holdout/README.md).
A fresh NHTSA download may differ. Human correctness, field usefulness and
accident prevention are not established by a successful replay.

NHTSA source data, Meta API outputs and the MiniLM model retain their publisher
terms; see [NOTICE](../NOTICE). The repository's MIT license covers application
code, not a relicensing of external data or models.
