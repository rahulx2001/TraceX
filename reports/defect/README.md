# Defect-level label sample

**29 October repair:** the explicitly scoped fuel-system experiment now has
complete model coverage, a repaired recall scope, a sparse-count detector and
equal-budget comparisons. All 300 review examples also have model predictions;
human labels remain unfilled. See [the repair report and blind-review workflow](repair/README.md).
The JSON files in this directory remain the original partial experiment;
`repair/` contains the separately identified retrospective reanalysis.

**Above-86% follow-up:** the separate, frozen 2025 holdout detected **5/8
campaigns (62.5%)**, matching the count policy. Mature-alert precision was
**6/18 (33.3%)**. None of 40 development candidates passed the precision gate;
the target was not achieved. See [the holdout report](fuel_holdout/README.md)
for the protocol, all campaigns, uncertainty and exact replay instructions.

This folder holds the frozen inputs and outputs for the defect-level recall
experiment. Nothing in this folder is model ground truth.

## Preparing the inputs

The classifier, taxonomy builder and sample exporter read two parquet files
that are not committed because they are large derived NHTSA extracts. Build
them from the official flat files (no model call, no Meta spend):

```bash
# Downloads FLAT_CMPL.zip and FLAT_RCL_POST_2010.zip, then writes
# data/defect/complaints.parquet, data/defect/recall_descriptions.parquet
# and data/defect/defect_input_manifest.json with source hashes.
python -m scripts.defect_prepare_inputs --out-dir data/defect

# Offline, from ZIPs already downloaded:
python -m scripts.defect_prepare_inputs --out-dir data/defect \
  --complaints-zip /path/FLAT_CMPL.zip \
  --recalls-zip /path/FLAT_RCL_POST_2010.zip

# Small deterministic judge/demo sample:
python -m scripts.defect_prepare_inputs --out-dir data/defect/hackathon \
  --complaints-limit 5000 --recalls-limit 5000
```

A missing file names this command. After preparation, verify the classifier
reads the inputs without a network call:

```bash
python -m scripts.defect_classify --dry-run --limit 1
```

## Hand-label file

`defect_label_sample_300.csv` has 300 complaints drawn from the 2021–2024 test
window, stratified by component with seed `20261026`. The `label` and `notes`
columns are blank in the frozen export. The blank file's SHA-256 is recorded in
`sample_manifest.json`.

To fill it:

1. Read one row's `narrative` and the label definitions in
   `allowed_label_text`.
2. Put exactly one label **ID** from that row's `allowed_label_ids` in `label`.
   For example: `other_unclear`, not `other/unclear`.
3. Use `notes` for anything you want to record. Do not edit the narrative,
   component, or allowed-label columns.
4. Keep the file as UTF-8 CSV.

A partial fill is allowed while you work. The scoring script refuses to write an
accuracy result until at least one valid human label exists, and it reports how
many rows are labelled, invalid, missing model output, or scored.

```bash
python -m scripts.defect_accuracy                 # writes reports/defect/accuracy.json
python -m scripts.defect_accuracy --require-complete   # final run: requires 300/300 and model output
```

The script records both the frozen blank-file hash and the current file hash.
Changing earlier columns invalidates the comparison; if that happens, say so
rather than treating the sample as unchanged.

## What the labels mean

The taxonomy in `taxonomy.json` was built only from recalls issued on or before
2020-12-31. Each specific label is a train-recall leaf part plus its dominant
defect mode. Components without enough train recalls only have
`other/unclear`. A human label can therefore legitimately be `other_unclear`
even when the complaint describes a real defect: the frozen taxonomy may not
have a label for it.

## Files

### Hackathon execution scope

The frozen dry-run estimate covers **18,998 batches / 151,766 records**; it is
not an authorized live run. At the default 300-call daily cap it would require
at least 64 days before retries. The estimate assumes short completions and
does not override the client's conservative reservations or $30 lifetime cap.
The committed estimate records `cl100k_base`; a clean environment without the
optional `tiktoken` package falls back to `chars/4` and labels the estimate
accordingly. Both are local estimates, not a bill. A 3-batch dry run on the
prepared sample estimated 4,516 input tokens (~1,505 per batch), well below the
8,000-input-token bound the live-run guard reserves per batch.

Full multi-component classification and human-label accuracy remain **Not run**.
The repair completes only the declared fuel-system scope and model predictions
for the 300-row sample. The sample contains no completed human labels. The
synthetic intake proof is separate from classification evidence. Do not fill
labels with model output and call them human.

Use repository-relative defaults or explicit portable input paths. Start with
`python -m scripts.defect_classify --dry-run --limit 1`. Any future live run
requires an explicit batch `--limit`, frozen human labels when scoring,
available calls in the daily cap, and remaining Meta budget. Use one worker
and 20 RPM initially. Completed batches are cached before continuing;
failed calls remain charged by the reservation ledger. Retries are bounded
and recorded. The full 18,998-batch plan is outside this demo's scope.

### Artifact list

| File | What it is |
|---|---|
| `taxonomy.json` | Frozen train-only taxonomy. `sha256` covers `body`. |
| `defect_label_sample_300.csv` | Human label sheet; labels are not model output. |
| `sample_manifest.json` | Sampling frame, seed, allocation and blank-CSV hash. |
| `classification_estimate.json` | Calls/tokens/cost estimate from a dry run, before any live call. |
| `component_full_corpus_test.json` | Component-level detector diagnostic on the full corpus; **not** a defect-level result. |
| `cache/classifications.sqlite` | Raw per-batch cache; not a report. |
| `classifications.parquet` | Per-complaint model labels (written by the classifier). |
| `recall_labels.parquet` | Per-recall-description model labels (same classifier). |
| `classification_manifest.json` | Counts, hashes and failures for the classifier outputs. |
| `defect_config.json` | Frozen detector config from the 2015–2020 tune phase. |
| `defect_tune_results.json` | Train-window grid results. |
| `defect_test_results.json` | One-shot 2021–2024 defect-level test result. |
| `component_baseline_results.json` | Component detector on the same labelled subset. |
| `baseline_results.json` | Defect-grain count and random baselines. |
| `example_flags.json` | Five real flags with complaint excerpts and recall matches. |
| `accuracy.json` | Human-label accuracy, per-label metrics and confusion matrix. |
| `run_log.jsonl` | Append-only record of tune/test/refusal events. |
