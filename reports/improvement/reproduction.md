# Reproducing the research tooling

Use Python 3.12 and the repository's pinned application dependencies. Optional
research dependencies are pinned in `requirements-ml-improvement.txt` and can be
installed with:

```bash
.venv-hackathon/bin/python -m pip install --target .ml-deps -r requirements-ml-improvement.txt
```

Research scripts prefer that isolated dependency directory. They make no paid
API calls. Transfer the exact input artifacts named in the existing repair and
holdout manifests; a newer NHTSA download cannot reproduce a frozen run.

The checked baseline and original reports are immutable. Do not rerun a command
that creates the same output. `write_once`, run-directory reservations and input
hash checks refuse replacement. For new attempts use a new run ID and retain
failed attempts. The existing runs are `prepare_v1`, `audit_v1`, and
`baseline_calibration_v1`; all are diagnostics, not candidate selection.

Preparation extracts only pre-2021 records and enriches severity from the same
source ZIP, without adding complaint rows or expanding fuel-source scope:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement prepare --run-id prepare_v1 --source-zip /path/to/the/pinned/FLAT_CMPL.zip
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement audit --run-id audit_v1
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_baseline_calibration
```

The initial prepare/audit started.json records contain the Python script path
and arguments; the exact module invocations above and logs supply the interpreter
and isolation environment. Later run metadata records the complete module command.
The code hash covers uncommitted Python changes as well as the base commit.

Development remains gated. `scripts.ml_improvement develop` refuses without an
explicitly authorized test reservation and verifies protocol/input hashes before
fitting. A prospective calendar reservation does not pass `require_final_test`:
actual frozen data hashes, untouched attestation and completed follow-up are required.

Generated reporting and integrity checks:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement_report check
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.defect_verify
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.fuel_holdout verify
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m pytest -q tests/frontline/ai_layer/test_ml_improvement.py
cd dashboard
npm run build
npm run test:signin
```

Full `make test` and `make eval-frontline` are required. Run the latter from a
disposable working directory with an explicit Makefile/PY/PYTHONPATH so its dated
report cannot overwrite an existing report. Browser/network loopback tests need
OS permission to launch Chromium and bind a local port. Never weaken the tests
to compensate for those environment restrictions.

Changes to old operational tests correct stale UI structure/wording, freeze the
freshness test clock, and isolate both domain fixtures. No historical ML scoring
test, denominator, threshold or frozen scorer was altered. The original failed
full-suite log is retained for comparison.

## Fresh-environment verification addendum

A detached checkout was created at `/private/tmp/ml-score-repro-19bd5cf` and
advanced to the verified implementation commits. It has a fresh Python virtual
environment, not a symlink. Application dependencies were installed with
`pip install -r requirements.txt -c requirements-lock.txt`; research dependencies
were independently installed into `.ml-deps` using the pinned file. Install
attempts and dependency freezes are retained in `logs/clean_*`.

The clean checkout replays the frozen repair and fuel reports, runs the selected
regression tests, checks report/dashboard integrity, and reproduces the development
audit and uncalibrated diagnostic. Numeric equality is recorded in
`clean_reproduction_comparison.json`. Calibration now accepts a fresh run ID:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement audit --run-id audit_clean_replay
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_baseline_calibration --run-id calibration_clean_replay
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.verify_ml_pipeline --records 76 --out reports/improvement/pipeline_clean.json
```

Those example output names now exist; choose new names for another attempt.
No seed, model, matching rule or threshold changes between replays. Calibration
adapters additionally require one unique example ID per calibration row; callers
must still enforce campaign/time-group independence. This guard was checked in
the fresh environment after it was added. The final browser build/sign-in checks
used the existing Node installation; a fresh Node dependency install is not
claimed. Chromium was installed and actual browser tests ran.
