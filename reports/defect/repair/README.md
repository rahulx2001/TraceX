# Prediction evidence repair — 29 October 2026

The data/evaluation repair and bounded model run are complete. Human validation
is prepared but **not completed**. Read [PREDICTION_REPAIR.md](PREDICTION_REPAIR.md)
for the measured results and limitations.

## What changed

- Restored the documented five makes and model years 2015–2024. The prior run
  had ingested all makes/model years and then silently retained whichever
  complaint rows had labels.
- Recovered every affected vehicle scope from the **same hashed NHTSA ZIP**.
  Deduplicated descriptions are model inputs; they cannot substitute for the
  full make/model/year recall scope. There are 360 scope rows and 77 campaigns
  in the repaired 2015–2024 fuel-system corpus, including 41 evaluation campaigns.
- Completed 1,281 missing classifications in 98 successful live Muse Spark Open
  batches. All 2,203 scoped complaints and all 300 frozen review examples now
  have model output (2,498 distinct complaints in the union). Existing model,
  prompt and taxonomy versions were retained.
- Added an experimental rolling Gamma-Poisson score for sparse repeated
  complaints. Its 27 candidate configurations were evaluated on 2015–2020;
  the selected 13-week window, minimum two complaints and 0.2 tail threshold
  were frozen before reanalysis. This tail threshold is a scoring heuristic,
  not a probability of a defect. The production alert policy is unchanged.
- Compare complete-week alert episodes using the same 13-week cooldown and
  equal alert budgets for count/random references. Never match two
  `other_unclear` labels as a physical defect. Apply a 7–364-day match horizon
  and report precision only on alerts with complete follow-up.
- Include a predeclared sensitivity excluding explicit recall/campaign mentions;
  1,698 of 2,203 complaints contain such language. This matters: many complaints
  concern an already announced recall or unavailable replacement parts.
- Preserve the original 6/269 result and its baselines. The new scope,
  denominators, detector and matching rules differ; this is **not** a direct
  improvement from 2.2% to 53.7% on the same benchmark.

## Results

| Same-scope strategy | All reports | Excluding recall/campaign mentions |
|---|---:|---:|
| Rolling detector | 22/41 (53.7%) | 14/41 (34.1%) |
| Count reference | 15/41 (36.6%) | 10/41 (24.4%) |
| Random reference, mean of 100 draws | 40.7% | 26.2% |

Each strategy receives 47 alerts in the all-report comparison and 27 in the
sensitivity. Detector mature-episode precision is 14/31 (45.2%) and 7/13
(53.8%), respectively. Seven percent of random draws match or exceed detector
recall in the sensitivity: the advantage is exploratory, not conclusive.

## Reproduce without model calls

Use Python 3.12 with the existing project dependencies. From the repository root:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.defect_verify
```

This replays the **recorded** comparison, checks code/input/configuration hashes
and compares both results including all 200 random draws. It does not retune,
overwrite reports or claim a second independent test. The pinned derived inputs
are in `data/defect/repair/` (gitignored). To reconstruct them on another machine,
use the original source ZIPs identified by `protocol.json` and the original
`data/defect/defect_input_manifest.json`; do not silently substitute a newer
NHTSA download. The input preparation code writes `recall_scopes.parquet`
separately from deduplicated classifier descriptions.

The original repair sequence was `scripts.defect_repair prepare`, the bounded
`scripts.defect_classify` run on `pending_complaints.parquet`,
`scripts.defect_repair assemble`, then `scripts.defect_prediction_eval tune`
and `test`. Preparation, tuning and evaluation refuse to silently overwrite
their existing protocol/configuration/test reservation. The live classifier
used the existing cache and existing budget ledger; neither cap was reset.

The dashboard summary is regenerated from saved results:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.defect_publish
cd dashboard
npm run build
```

## Complete the human evaluation

1. Open [human_review.html](human_review.html) locally. It shows the 300 frozen
   complaints with allowed labels and **no model answers**. A human reviewer
   selects labels, adds notes and exports `defect-review.json`. No choice is
   preselected. Progress is stored locally where browser storage is available.
2. Import the export; the importer checks sample identity, allowed labels,
   duplicates, named reviewer and human-review attestation. It writes a separate
   CSV and provenance record; the original blank sample is preserved.
3. Score using the complete model output and frozen review manifest:

```bash
.venv-hackathon/bin/python -m scripts.defect_review import --review /path/to/defect-review.json
.venv-hackathon/bin/python -m scripts.defect_accuracy \
  --csv reports/defect/repair/human_labelled.csv \
  --classifications reports/defect/repair/classifications.parquet \
  --manifest reports/defect/repair/review_manifest.json \
  --out reports/defect/repair/accuracy.json --require-complete
```

The scorer checks immutable sample fields, reports per-label metrics, macro F1,
specific-defect accuracy and an always-`other_unclear` baseline. With zero human
labels it exits without writing an accuracy score. Human-reviewed recall labels
and an independent future evaluation are still needed before stronger claims.

## Validation and spending

Targeted regressions cover complete-week availability, prior-only scoring,
multi-vehicle recall scope, unknown labels, campaign deduplication, censoring,
equal alert budgets, missing classification failures and blind-review import.
Both experiment variants replay exactly from the frozen inputs. The dashboard
build and existing analytics tests pass.

The live run added about $0.82 to the client's token-cost estimate and $3.57 to
its conservative reservations. Reservations total $23.41 of the unchanged $30
cap. Baseten rates in this ledger are estimates, not a provider invoice.

All results are retrospective. The 2021–2024 window was already examined and
the 2026 model may have learned historical recall information. Model-labelled
recall matching does not establish identical physical defects, crash prevention
or prospective production performance.
