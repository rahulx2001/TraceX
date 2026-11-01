# Reproduce the engineering checks

Run from the `ml-score-improvement` worktree. Do not alter the original checkout,
the shared `.venv-hackathon`, or either freeze tag. No provider key is needed.
Use a new output directory on every run; the commands refuse existing logs or
replay output. These commands do not collect prospective outcomes.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-hackathon/bin/python -B \
  reports/improvement/final_handover/validate.py \
  --out /tmp/rca-handover-new-run \
  --step replay --step frozen_replay --step dashboard_build --step full_tests \
  --step eval_frontline --step dashboard_source --step pipeline \
  --step compileall --step browser
```

The browser needs permission to launch local Chromium and isolated local API
servers. It blocks requests outside each local test server and clears provider
keys. `pipeline` uses the existing 76-row category diagnostic; those are separate
fixtures and must not be represented as predictions for the supplied 300 rows.
`eval_frontline` uses existing functional scenarios, not a held-out model dataset.

`dashboard/node_modules` links into the original checkout. The runner therefore
uses `npm run build -- --configLoader native`, then `make test -o dashboard-build`
with that verified build. Python setup and all `tests/frontline/` tests still run.
For the browser, it executes the existing `assert-signin-reachable.mjs` harness
from its original directory via stdin, changing only the Vite `configLoader`
option in memory. All original assertions, including the imported ML evidence
desktop/mobile checks, execute. The adapted input and its hash are recorded.
This is not reported as a bare `node --test` invocation. Frozen source files
and the shared dependency directory are not edited.

Bytecode is disabled except for `compileall`, which writes to a disposable
external `PYTHONPYCACHEPREFIX`. Test and evaluation databases are temporary.
`make eval-frontline` also writes its ordinary dated functional report under
`reports/qubot/eval/`; inspect that output before committing a later run.

The exact saved pack can also be replayed separately:

```sh
FRONTLINE_TEST_ISOLATION=1 PYTHONDONTWRITEBYTECODE=1 \
  .venv-hackathon/bin/python -B -m scripts.synthetic_project_smoke \
  --out /tmp/rca-synthetic-replay-new-run
```

This reads the supplied `synthetic_cases.jsonl` and `PROJECT_CLOSEOUT.md`, verifies
their pinned hashes, verifies both registered model freezes, injects the authored
labels and runs the unchanged count-feature, baseline and logistic inference
code. It does not run the narrative classifier or train/select a model.

The fixed fictional schedule has one observation per make/label at week 0,
followed by observations at weeks 26, 27, 28 and 29 in 2019. It is a software
stimulus, not reconstructed history. All 300 fixture IDs are retained; 150
`other_unclear` rows stay in the input but cannot become specific-defect
candidates. No campaign outcomes are invented. The report leaves performance
metrics and confidence intervals null because no performance is estimated.

Verify the preserved real evidence and both freezes:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-hackathon/bin/python -B \
  reports/improvement/final_handover/check_integrity.py
```

The original human sample and review workflow remain unchanged. Three hundred
means records, not people. Human review, the reserved prospective collection,
the cutoff and the separate human merge decision remain outside this software
replay. Follow the existing prospective runbook when those activities are due.
