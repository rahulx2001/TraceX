# Defect-level label sample

This folder holds the frozen inputs and outputs for the defect-level recall
experiment. Nothing in this folder is model ground truth.

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
