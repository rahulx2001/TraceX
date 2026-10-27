# TraceX — Real Hindi / Hinglish / English complaint eval

This pipeline is deliberately separate from every synthetic eval. It collects **real, consenting** stories, asks you to label them by hand, and scores three modes on that set:

1. rules-only (existing `IntakeAgent` → `TriageAgent`),
2. rules + `hindi_safety` (the deterministic lexicon),
3. rules + Meta (the existing `maybe_enhance_intake` / `maybe_raise_severity` path).

The synthetic sets under `eval/enhanced/`, `eval/hindi_fresh/`, `reports/hindi_safety/` and `reports/eval_modes/` are **not** inputs and their numbers are **not** combined with real numbers.

## Status

No real records, human labels or real-eval numbers are committed. All 84 existing Hindi/Hinglish eval calls are synthetic. Meta mode is **NOT RUN** until a key is configured; the runner never invents a Meta number.

## 1. Collect

```bash
python -m scripts.real_hindi_collect serve
```

- Binds to `127.0.0.1:8765` by default, with no access log and no analytics.
- Requires the consent checkbox and the no-identifiers confirmation.
- Accepts typed text, a voice recording, or both, in Hindi, Hinglish, English or mixed.
- Turns voice uploads into a metadata-free 16 kHz mono WAV. The original filename and container metadata are discarded.
- Stores one JSON record and (if present) one WAV under the gitignored `data/real_hindi/`.
- The page never asks for a name, phone number or number plate.

Share [`docs/real_hindi/PARTICIPANT_INSTRUCTIONS.md`](../../docs/real_hindi/PARTICIPANT_INSTRUCTIONS.md) with participants. It contains no example complaints.

If a voice-only record has no transcript:

```bash
python -m scripts.real_hindi_collect transcribe --next
```

Transcription is manual and local. No AI call is made, and the audio never leaves the machine.

Useful local commands:

```bash
python -m scripts.real_hindi_collect list        # ids and counts, never stories
python -m scripts.real_hindi_collect consent     # exact consent text, version and hash
python -m scripts.real_hindi_collect delete <id> # delete one record and its audio
```

## 2. Export and fill the label sheet

```bash
python -m eval.real_hindi.labels export
```

This writes `data/real_hindi/labels.csv` with the story text and **blank** `language`, `is_safety_critical`, `component` and `notes` cells. Nothing is pre-filled. The committed [`labels_template.csv`](labels_template.csv) is the header-only schema:

```text
id,language,is_safety_critical,component,notes
```

Fill every row yourself:

| Column | Allowed values | Meaning |
| --- | --- | --- |
| `language` | `hindi`, `hinglish`, `english`, `mixed` | The language you judge the story to be in. Aliases `hi`, `en`, `hing`, `mix` are accepted and canonicalised. |
| `is_safety_critical` | `yes` / `no` | Your judgment: could this problem cause injury or death if ignored? This is the reference for the kill-switch metrics. |
| `component` | one value from `domains/automotive_nhtsa/gazetteers/categories.csv` | The main vehicle system involved. Case and extra spaces are normalised; a value outside the 29-category gazetteer is refused. |
| `notes` | free text | Your notes. Not used as a metric and not written into reports. |

Do not let an assistant pre-fill labels. The runner refuses missing, invalid or duplicate labels, and stale ids that are not in the collection.

If the sheet already has labels, `export` refuses to overwrite it. If you truly need a fresh sheet, back it up and pass `--force`; a timestamped backup is made first.

Check the filled sheet without printing stories:

```bash
python -m eval.real_hindi.labels check
```

## 3. Run the real eval

```bash
python -m eval.real_hindi.run_eval
```

Outputs:

- `reports/real_hindi/runs/<run-id>/REAL_HINDI_EVAL.md` — aggregate report.
- `reports/real_hindi/runs/<run-id>/real_hindi_eval.json` — per-call ids, labels and outputs, no story text.
- `reports/real_hindi/runs/<run-id>/run.json` — run summary used by the history index.
- `reports/real_hindi/RUNS.md` — every real run, held-out status, approvals and before/after metrics.

Default paths can be changed with `--data-dir`, `--labels` and `--out-dir`. The report always stays under the chosen report directory.

### What the runner refuses

- No records, or a label sheet that does not exist.
- A record whose `"synthetic"` value is not exactly `false`.
- A missing/unknown consent version, a consent-text hash mismatch, or a missing AI-processing / no-identifiers confirmation.
- A record not written by the local consent page (`collection != local_consent_page_v1`).
- A record with no story text, a story hash/length mismatch, or audio without a transcript.
- Audio whose file is missing, whose hash does not match, whose format is not the metadata-free 16 kHz mono WAV, or whose metadata-stripped flag is not true.
- Any record without a usable label row, any invalid label, any duplicate label id, or any label id not in the collection.

The runner refuses the whole set rather than silently scoring a convenient subset. Re-export, label the new rows, and rerun.

### Metrics

The metric columns come from `eval.hindi_fresh.run_hindi_eval.summarise`, so they match the synthetic Hindi eval:

- severity counts, triage skipped, pipeline errors,
- safety-critical hits / expected, misses and false alarms (human `is_safety_critical` is the reference),
- component correct / expected and component wrong (human `component` is the reference),
- severity lowers for rules + hindi_safety (must be 0).

There is no human severity label in the sheet, so **no severity accuracy is claimed**. Severity counts are descriptive. The eval also runs intake and triage directly; it does not execute the orchestrator's escalation fast path.

For every language with `n < 30`, the report and the terminal say **“too small to conclude”**. That is a sample-size floor, not a significance test. There is no confidence interval and no claim of production accuracy.

### Meta mode

Meta runs automatically only when `META_API_KEY` or `MODEL_API_KEY` is configured and `FRONTLINE_AI_LAYER` is not `off`. It uses the existing enhanced path, without the deterministic `hindi_safety` layer, so the three modes differ by one addition at a time.

Only the **text** is sent, after the existing regex PII redaction in `src/security/pii.py`. Audio is never sent. If no key is configured, the report says **NOT RUN** and contains no Meta number or estimate.

## 4. Held-out protection

Every run records a SHA-256 fingerprint of the lexicon, prompts, rules, agents, domain pack, PII redactor, eval summariser and model settings. The API key is never included.

- First run for a config: allowed, `held_out=true`.
- Same config: allowed, `held_out` stays as recorded.
- Changed config after a prior run: **refused**.
- Changed config with explicit approval:

```bash
python -m eval.real_hindi.run_eval --approve-change "why the lexicon/prompt/rules changed"
```

The approval is recorded with old/new hashes, the reason, and the run id. All older run directories are kept. From then on the set is marked **no longer held-out**, and `RUNS.md` shows the before and after numbers side by side.

The local state file is `data/real_hindi/eval_state.json` (gitignored). It can be recovered from `reports/real_hindi/runs/` if it is lost. Do not delete the run history.

Changing the **label sheet** does not change the config hash, but it is recorded and flagged: a run whose label hash differs from the previous run is marked “not directly comparable”. Correcting a label is allowed; hiding a label change is not.

## 5. Privacy

- Raw stories and audio live only under `data/real_hindi/` (gitignored, mode 0700/0600).
- Reports contain no story text. Per-call JSON contains ids, human labels and model outputs only.
- The collector's optional in-browser recorder uses the normal file upload; the server transcodes and verifies that no format/stream tags remain.
- The page has no cookies, analytics, external assets or access log.
- Consent text is versioned in `eval/real_hindi/consent.py`. Do not edit an existing version in place; add a new version and keep the old hash so old records remain verifiable.

## 6. Tests

```bash
python -m pytest tests/real_hindi -q
```

The tests cover consent/CSRF refusal, metadata stripping, blank label export and no-overwrite, unknown ids, synthetic-record refusal, the config-change guard, the `n < 30` warning, and the absence of story text from reports.

## Files

| Path | Purpose |
| --- | --- |
| `scripts/real_hindi_collect.py` | Local consent page, WAV stripping, list/transcribe/delete CLI. |
| `eval/real_hindi/consent.py` | Versioned consent text and SHA-256 registry. |
| `eval/real_hindi/labels.py` | Blank sheet export, label validation, unknown-id refusal. |
| `eval/real_hindi/labels_template.csv` | Header-only committed schema. |
| `eval/real_hindi/run_eval.py` | Load, refuse, run three modes, write a run. |
| `eval/real_hindi/guard.py` | Config fingerprint, held-out guard, state recovery. |
| `eval/real_hindi/reporting.py` | Aggregate report and `RUNS.md`; no story text. |
| `eval/real_hindi/common.py` | Shared constants, sample-size warning, formatting. |
| `docs/real_hindi/PARTICIPANT_INSTRUCTIONS.md` | One-page participant sheet, no example complaints. |
