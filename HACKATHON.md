# TraceX — Meta Global AI Developer Hackathon

**Track: Indie developer.** Primary theme: **Build for Your World**; automotive quality investigation also fits **Push the Frontier**.

TraceX helps automotive quality engineers turn scattered owner complaints into an auditable investigation. Browser speech recognition supplies text. Muse Spark normalizes difficult Hindi/Hinglish complaints; deterministic safety rules retain authority and a human reviews the result.

## What works and what has been verified

- Live Muse Spark text intake is recorded in [`reports/hackathon/meta_live_smoke.json`](reports/hackathon/meta_live_smoke.json). The artifact records the endpoint, model, accepted output, event ID, ledger verification and spend accounting. A configured key alone never counts as verification.
- Deterministic automotive and finance evaluation: 23 offline gates passed during the initial review. Final regression results — 1,794 backend tests with no deselection and 54 browser/API end-to-end tests — are recorded in [`reports/HACKATHON_FIX_RESULTS_2026-10-28.md`](reports/HACKATHON_FIX_RESULTS_2026-10-28.md).
- Voice/text intake, case creation, human takeover, complaint clustering, early warning and audit export are the reused foundation. Browser Web Speech performs recognition and speech synthesis; **Muse Spark does not transcribe audio in this implementation**.
- Photo upload, validation and storage work locally. SAM 3.1 output is parsed into **region boxes**, which the dashboard overlays. Polygon masks are not rendered. Live vision/SAM/image verification is reported separately; a text success does not verify these models.
- Video clips are validated and stored for **human review only**. Raw video model analysis is disabled because the API support and pricing contract are unverified.
- WhatsApp is an intake **mock**; no WhatsApp message is sent. Manufacturer alert feeds are pull feeds/payload previews, not demonstrated external delivery.

## Run the judge demo

Requirements: **Python 3.12**, Node **20.19+ or 22.12+**, and Chrome for optional microphone recognition.

```bash
bash scripts/judge_setup.sh
```

This creates an isolated `.venv-hackathon`, builds the dashboard and seeds `data/hackathon/judge-v2/`. Seeding never spends Meta credits. Open `http://127.0.0.1:8000/ui/#demo`.

Use **Have an operator API key?** for the local operator credential printed by setup. It authenticates a service principal with its permitted operations. For named supervisor takeover/release and review, use **Have a supervisor session?** and paste the separately issued supervisor session. The browser stores that session as an HttpOnly cookie.

Keep `META_API_KEY` / `BASETEN_API_KEY` in the server-side `.env`; never paste them into the dashboard key fields. With `BASETEN_API_KEY` set, every AI-layer call (intake, normalisation, severity, briefs, photo vision) and Tier-2 narration runs on Baseten-hosted Muse Spark Open (`meta-models/muse-spark-open-1026`, pinned host/model); `META_BACKEND=meta` pins the Meta API instead. SAM segmentation and image generation are Meta-API-only and report as skipped errors on Baseten; photo vision still runs via chat. Without a Meta key the deterministic demo still works, and **View recorded live proof** shows the saved synthetic API run with its timestamp. **Run Meta complaint** creates a new synthetic contact through the real intake, shows the accepted translation/fallback, and links it to the event/ledger evidence. The separate India emergency seed demonstrates the existing local safety layer. If port 8000 is occupied, use `API_PORT=8765 bash scripts/judge_setup.sh`.

Docker option:

```bash
docker compose -f docker-compose.hackathon.yml up --build
```

The container requires an operator API key and a distinct session secret in your environment or local `.env`. CI includes a separate hackathon-image smoke job. Docker is unavailable on the reviewed machine; its next CI run remains to be checked. Local verification status is in the results report.

## Reproduce verification

```bash
make test                    # builds dashboard, provisions/checks pinned MiniLM, isolated test DBs
make eval-frontline          # isolated deterministic evaluation
.venv-hackathon/bin/python -m scripts.ai_meta_smoke
# Optional individual capabilities:
.venv-hackathon/bin/python -m scripts.ai_meta_smoke --vision --sam --image
```

The smoke command runs only synthetic input on a fresh fixture warehouse and writes the actual artifact schema consumed by `/api/ai/status`. Missing keys, rejected output, or failed ledger verification never produce a successful marker. Each feature is matched to its endpoint and model ID.

All Meta attempts go through the allow-listed client with bounded timeouts/retries, schema validation, a daily call cap, and the cross-process lifetime **$30 maximum** reservation ledger. The tested text intake default is 20 seconds, configurable through `META_INTAKE_TIMEOUT_S` up to 30 seconds; a timeout falls back. Current observed/reserved spending is recorded in the proof artifact. This budget covers this client, not unrelated account activity. Baseten/Modal/Fireworks integration is **planned/unverified**; only explicitly priced model IDs can run. Muse Wonder is not implemented in this submission.

## Event contributions and reused work

See [`ELIGIBLE_WORK.md`](ELIGIBLE_WORK.md) for the actual baseline, original source commits and current contribution range. The TraceX initial commit imported an existing product; its date does not make every imported feature event-built. No published history is rewritten.

The supplied event page starts the hackathon on 26 October and advertises the 4 November, 9 PM Eastern submission deadline. The changes in this submission repair pass are dated 28 October. The supplied text contains no detailed existing-code clause or video-format requirement; do not invent one or treat application selection criteria as the complete submission contract. The owner has accepted the event rules.

## Historical results — context, not Meta prediction accuracy

The deterministic NHTSA report used five makes and 219,510 complaint records. Its in-sample production detector matched **535/1,172 campaigns (45.6%)**, with an **11-week median** actionable lead. Episode precision was **0.64** under the chosen matching rules.

A different tuned `abs3` configuration reported **62.7% campaign recall, 8-week median lead** on a later window. Production `abs5` was **not run** on that window. Matching is at make/component grain, not verified physical-defect identity. The original raw-file hash and exact ingest arguments are not fully reproducible from this checkout. These figures do not establish Meta improving prediction or accidents prevented. See [`reports/CLAIMS_AUDIT.md`](reports/CLAIMS_AUDIT.md) and [`reports/nhtsa/backtest_safety_2015_2024.md`](reports/nhtsa/backtest_safety_2015_2024.md).

The 84 Hindi/Hinglish examples are **synthetic**. Their prior local Hindi safety result is not real-customer accuracy. The 300-row defect label sample has no completed human labels; no defect-classification accuracy claim is made.

## Safety and audit boundaries

The original kill-switch, severity rules and ledger always run. AI may add supported facts or raise a severity/sentiment floor, never lower safety. Invalid/low-confidence/unsupported outputs fall back. Grounded brief claims require source sentences, citation scope and number checks. Source complaints themselves are not independently verified facts.

The database action chain is **tamper-evident**. Evidence exports have separate Ed25519 signatures. These controls are not a SOC 2 certification and do not make a mutable database absolutely immutable.

## Demo story

Use [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md): one difficult complaint, the accepted live Meta translation, the operator's review, and the actual audit trail. Label synthetic inputs and reused foundation. Keep the broader optional feature list out of the central story until its live behavior is verified.

The local `reports/hackathon/demo-draft.mp4` is a captioned, silent screen recording for review. It shows saved live Meta evidence and separate simulated supervisor actions. Add narration and check the portal's accepted format before uploading. Video binaries are gitignored.

To record again against a running isolated judge server:

```bash
cd dashboard
TRACEX_JUDGE_DATA=../data/hackathon/judge-v2 PLAYWRIGHT_CHANNEL=chrome \
  node scripts/record-hackathon-demo.mjs
```

Playwright video capture needs `npx playwright install ffmpeg`. Browser verification is available with `TRACEX_JUDGE_DATA=../data/hackathon/judge-v2 PLAYWRIGHT_CHANNEL=chrome npm run test:e2e -- e2e/judge.workflow.spec.js`. Supply `BASE_URL` when using another port.
