# Measure usefulness with actual service professionals

The historical classifier review is published. **There are zero completed
real-participant investigation tasks and no measured time-saving result.**
This plan uses the existing live-study recorder; it does not generate participant
identities, reference answers or timing data.

## A small first pilot

Recruit automotive service or quality professionals who understand the chosen
records. Four to six people can reveal usability problems, but do not justify a
population productivity or road-safety claim. Use consented fictional tasks or
appropriately de-identified real records, with installation evidence and source
reports that each participant can inspect.

Prepare at least three tasks covering missing, contradictory and irrelevant
records. An independent domain reviewer defines acceptable material facts,
consequential errors and legitimate uncertainties **before** seeing participant
answers. Leave that rubric blank until the reviewer completes and attests to it.

Compare the full existing manual/deterministic workflow, extraction-only
assistance and full Muse Spark investigation using the same task sources.
The existing recorder counterbalances tasks and conditions; each participant
sees each task once. Start timing before the task is revealed and include model
waiting, record lookup, corrections and final review.

## Use the existing recorder

Create actual task candidates from the chosen campaign/vehicle and its durable
source references. Fields and examples are described in
[evaluation-readiness.md](evaluation-readiness.md#two-distinct-human-studies).

```bash
python3 -m scripts.investigation_study prepare --tasks /path/to/task-candidates.json --out /path/to/preparation
python3 -m scripts.investigation_study freeze --tasks /path/to/task-candidates.json --rubric /path/to/independent-rubric.json --out /path/to/live-study
```

Open the generated `study.html`. Participants enter their own identity,
expertise and attestation, perform the assigned work and export their actual
sessions. Keep failed/incomplete tasks, deviations and the original live run
IDs. A recorded replay cannot stand in for a new live-assisted task.

```bash
python3 -m scripts.investigation_study analyze --study /path/to/live-study/study.json --rubric /path/to/independent-rubric.json --sessions /path/to/actual-session.json --artifacts /path/to/exported-packet.json --out /path/to/analysis
```

Give the generated blinded grading files to independent graders. Keep the
private mappings separate. Attach completed grades using the same analysis
command with `--grading primary.json secondary-subset.json`.

## Publish the actual evidence

Report participant expertise and count, all attempted tasks, acceptable packet
counts, material omissions, unsupported claims, failures and end-to-end time
by condition. Preserve grading disagreements and deviations. Time matters only
alongside packet quality; a quicker incorrect packet is not a success.

Retain anonymized raw sessions, source/version hashes, graders' attestations and
the analysis output. Keep personal contact details and private mappings out of
the public repository. Until those files exist, leave the study's participant
counts at zero and productivity/quality fields null. Model or synthetic test
outputs must never be entered as independent human work.
