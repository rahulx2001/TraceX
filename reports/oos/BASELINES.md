# Recall baselines: status

**Status: NOT RUN.** No baseline numbers are reported in this file. This file
records what was attempted, why it could not be completed, and the exact inputs
and commands needed to complete it. Do not treat the empty cells as zero.

Audit date: 2026-10-26. Repo HEAD: `4b70a8019ef96fb689bcb21a714f723951e787b0`.

## What "baseline" means here

The purpose is to put the detector's recall/precision in context on the **same
frozen split** used by `reports/oos/OOS_BACKTEST.md` (train 2015-2020, test
2021-2024, make + component grain, 52-week actionable window). Candidate
reference strategies:

| ID | Baseline | Definition | Recall | Episode precision |
|---|---|---|---|---|
| B0 | Always flag | Flag every slice in every week | NOT RUN | NOT RUN |
| B1 | Random-budget | Flag the same number of slice-weeks as the detector, chosen uniformly at random (fixed seed) | NOT RUN | NOT RUN |
| B2 | Volume-only | Flag the top-N slices by raw weekly complaint count, ignoring z/lift/FDR | NOT RUN | NOT RUN |
| B3 | Persistence / first-ever | Flag a slice in every week after its first flag (the existing "first-ever" upper bound in `reports/nhtsa/backtest_safety_2015_2024.md`) | NOT RUN as a separate baseline; the full-window upper bound is 735 / 1,172 campaigns (62.7%), median 214 weeks, and is explicitly labelled inflated | NOT RUN |
| B4 | Production detector | `z2.0_q0.05_abs5_rel0.5`, the shipped thresholds | NOT RUN on the 2021-2024 test window. In-sample 2015-2020: 0.336 campaign recall, 0.61 episode precision (`reports/oos/oos_tune_results.json`) | see left |
| B5 | Tuned detector | `z2.0_q0.05_abs3_rel0.5` (the OOS-tuned config) | 0.627 campaign recall, test window (`reports/oos/oos_test_results.json`) | 0.598 (`precision.precision_episodes`) |

Only B5's test-window figures and B4's in-sample figures are recorded results.
B0-B3 were **NOT RUN**, so this file deliberately contains no numbers for them.

## Why it is blocked

Computing B0-B3 requires the per-slice, per-week complaint series and the
matched recall labels. Those are derived from the raw NHTSA inputs during ingest
and are not committed:

- `FLAT_CMPL.zip` — not in the checkout at audit start.
- `FLAT_RCL_POST_2010.zip` — not in the checkout at audit start.
- The full ingested `data/domains/automotive_nhtsa.duckdb` (219,510 records /
  4,393 advisory rows) — not in the checkout.
- `scripts/oos_baselines.py` — does not exist. The existing scripts only score
  the detector configs, not reference strategies.

Using the 10-record fixture or the 11,924-record local warehouse would produce
numbers on a different corpus and would not be comparable to the 219,510-record
backtest. Fixtures were therefore not used.

## Inputs fetched on 2026-10-26 (not the recorded snapshot)

Both public ZIPs were downloaded to
`/private/var/folders/3g/45glb5cn1fq5zh7vn28ljmg80000gn/T/opencode/skewai-nhtsa/`:

| File | Bytes | SHA-256 |
|---|---:|---|
| `FLAT_CMPL.zip` | 375,063,317 | `91ff80bd163cbfecb80700948ab4a0e60fd49b6c0640e7abab692d691188c608` |
| `FLAT_RCL_POST_2010.zip` | 15,068,880 | `bcd81f35fae61ece442825a582567a437407e281f9521e05577f304a582b7563` |

`reports/oos/oos_config.json` records the input actually used for the frozen OOS
run as `FLAT_CMPL.zip`, 374,664,687 bytes, SHA-256
`c00707bd4afd6cad075000e0c45e74b59d140976aab2ddae3c6f47a4f807ffe1`. The
downloaded copy **does not match** that hash or size. NHTSA refreshed the live
file on 2026-10-26 (ZIP member `FLAT_CMPL.txt` timestamp 2026-10-26 10:12), so a
fresh run would use a different snapshot and could not be expected to reproduce
the committed numbers exactly. The committed numbers remain tied to the
recorded hash; the raw file behind that hash is not in the repository.

## Exact unblock sequence

Run in a scratch directory; do not point this at `data/` in the checkout.

```bash
cd /path/to/scratch
curl -L -o FLAT_CMPL.zip https://static.nhtsa.gov/odi/ffdd/cmpl/FLAT_CMPL.zip
curl -L -o FLAT_RCL_POST_2010.zip https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip
sha256sum FLAT_CMPL.zip   # compare with reports/oos/oos_config.json

export DOMAIN_DB_PATH="$PWD/domains"
mkdir -p "$DOMAIN_DB_PATH"
python -m scripts.ingest_nhtsa --pack automotive_nhtsa --limit 300000 \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024
python -m scripts.ingest_recalls --pack automotive_nhtsa --zip "$PWD/FLAT_RCL_POST_2010.zip" \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024 --rcl-type V

# Verify the corpus before scoring.
python - <<'PY'
import duckdb, os
p = os.path.join(os.environ["DOMAIN_DB_PATH"], "automotive_nhtsa.duckdb")
con = duckdb.connect(p, read_only=True)
print("records", con.execute("select count(*) from records").fetchone()[0])
print("advisories", con.execute("select count(*) from advisories").fetchone()[0])
PY

# Re-run the production detector on the full window (writes to scratch files).
python -m scripts.ai_safety_backtest --zip "$PWD/FLAT_CMPL.zip" \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024 \
  --out-md "$PWD/backtest.md" --out-json "$PWD/backtest.json"

# Baselines B0-B3 still need a small script over the same per-slice series; no
# such script exists in this checkout. Until it is written and run, they are
# NOT RUN, not zero.
```

## What must not be claimed

- Do not say "baselines were tested" or quote a baseline recall/precision from
  this file. Nothing was measured.
- Do not compare the 10-record fixture or the 11,924-record synthetic-scale
  warehouse with the 219,510-record backtest.
- Do not quote the 62.7% first-ever figure as a baseline or as production
  performance; it is an inflated upper bound from the full-window report.
