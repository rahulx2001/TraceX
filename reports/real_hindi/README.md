# Real complaint eval reports

**Status: no real eval has been run.** There are no real records or human labels yet, so there are no real numbers in this directory.

`RUNS.md` and `runs/<run-id>/` are created by:

```bash
python -m eval.real_hindi.run_eval
```

These reports contain aggregate metrics and per-call ids/labels/outputs only. They never contain story text. Raw stories and audio stay in the gitignored `data/real_hindi/`.

Synthetic Hindi/Hinglish results are separate and live under `reports/hindi_safety/` and `reports/eval_modes/`.
