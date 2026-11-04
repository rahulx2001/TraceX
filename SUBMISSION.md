# TraceX — judge guide

TraceX helps automotive service and quality teams turn multilingual owner
reports into source-cited investigations, inspect installation/workshop
evidence, and retain reviewed action and repair records.

**[Watch the final three-minute demo](https://youtu.be/Uq7_kra8q-M)** · Indie
developer track · Build for Your World. The public video is 180 seconds. Demo
vehicles, notices and repair outcomes are fictional/simulated.

## What Meta contributes

Muse Spark extracts vehicle, part, symptom, timing, denial and uncertainty. It
chooses bounded installation, workshop or owner-history lookups, drafts claims
with exact source citations, and revises the brief when new records arrive.
The application validates citations and keeps Accept, Correct and Reject
decisions attached to the draft. The model cannot approve outreach, choose a
repair part or clear a vehicle.

The [Meta usage guide](docs/meta-api-usage.md) links direct Meta and
Baseten-hosted Muse Spark Open evidence, six recorded investigation runs,
request traces, model versions and historical classification outputs. The
[contribution disclosure](ELIGIBLE_WORK.md) separates the reused foundation
from event-built investigation, integration, validation and evaluation work.

## Verify the public evidence

The first two checks use Python's standard library and make no network calls:

```bash
python3 -m scripts.public_replay
python3 -m scripts.review_evidence_check
```

| Check | What it establishes |
|---|---|
| Saved-artifact replay | Published arithmetic, artifact hashes and exact source quotations |
| Review evidence checker | Five attested review exports, importer CSV/provenance hashes, frozen taxonomy, all 43 Round 4 source votes and adjudicated labels |
| [Model-to-alert replay](docs/public-model-replay.md) | Recomputed frozen student predictions, temporal alerts, campaign matches and all 100 random references from the public release payload |

With NumPy and pandas installed, run the full prediction/alert check:

```bash
python3 -m scripts.public_model_replay verify --download
```

It fetches the checksummed public [replay release](https://github.com/rahulx2001/TraceX/releases/tag/tracex-replay-2026-11-04).
All free-text columns are excluded; original cached embeddings, fitted weights,
row order and filtering decisions are retained. It makes zero provider calls.
See [setup and scope](docs/public-model-replay.md) for minimal dependencies and
the distinction from regenerating raw data or embeddings.

## Run the product

The [README quickstart](README.md#start-a-local-pilot) installs the application
and dashboard. For the isolated fictional LotGuard walkthrough:

```bash
.venv/bin/python scripts/run_lotguard_demo.py --offline
```

Open `http://127.0.0.1:8770/ui/#cases` and select **LOT ALERT**. Follow the
[complete walkthrough](LOTGUARD_DEMO_WALKTHROUGH.md). Offline mode disables
providers. The [authenticated judge setup](HACKATHON.md#run-the-judge-demo)
provides the separate Report → Investigate → Review → Evidence entry.
Live Muse Spark operations require your own server-side provider key and
credits; opening a page alone is not proof of a model call.

Inspect the run's model/host, source quotations, selected lookup and linked
revision. Existing replay proof retains its original timestamp and synthetic
label. A typed report or software check does not demonstrate real microphone
quality, field effectiveness or independent human grading.

## Results and remaining evidence

| Published result | Scope |
|---|---|
| 246/300 = 82.0%, macro-F1 0.514 | Historical classifier result against Round 4 adjudicated gold; reviewer blinding is unconfirmed |
| 238/300 = 79.3%, six missing predictions retained | Grounded challenger against that gold; rejected |
| 5/8 campaign matches; 6/18 mature-alert matches | Historical fuel experiment, equal to the count baseline; not promoted |
| 0 real-participant tasks; time/quality benefit unavailable | The live user study remains pending; [pilot plan](docs/pilot-validation.md) is ready |

The [claim index](reports/hackathon/CLAIM_INDEX.md) is the current source for
scope, denominators and hashes. The [export inventory](reports/improvement/human_reviews/EXPORT_INDEX.md)
maps all supplied review filenames to current, superseded, assisted or
withdrawn evidence. The [owner-supplied packet](reports/hackathon/demo_reference/README.md)
preserves the earlier twelve-vehicle synthetic export separately from the
later EPS walkthrough and live model proofs.

Successful replay establishes reproducibility of the recorded software
result. Real usefulness still requires relevant participants and independent
task grading; no accident-prevention or productivity claim is invented.
