# TraceX — Meta Global AI Developer Hackathon

**Track: Indie developer.** Primary theme: **Build for Your World**; automotive quality investigation also fits **Push the Frontier**.

TraceX helps an automotive quality or service engineer turn a multilingual owner report into a source-cited investigation, review missing installation evidence, and document action and repair verification. Browser Web Speech or optional Deepgram supplies the transcript. Muse Spark can select bounded evidence lookups and draft supported claims; the engineer reviews the result.

The required customer data is an owner report linked to an operator-confirmed vehicle, installation records with part/lot provenance, and workshop/repair evidence. A credible first pilot is one service team's review of a small, consented batch, measuring acceptable packets, corrections and completion time against its existing process. No pilot results or accident reduction are claimed.

## What works and what has been verified

- Live Muse Spark text intake is recorded in [`reports/hackathon/meta_live_smoke.json`](reports/hackathon/meta_live_smoke.json). The artifact records the endpoint, model, accepted output, event ID, ledger verification and spend accounting. A configured key alone never counts as verification.
- Deterministic automotive and finance evaluation: 23 offline gates passed during the initial review. Final regression results — 1,794 backend tests with no deselection and 54 browser/API end-to-end tests — are recorded in [`reports/HACKATHON_FIX_RESULTS_2026-10-28.md`](reports/HACKATHON_FIX_RESULTS_2026-10-28.md).
- Voice/text intake, case creation, human takeover, complaint clustering, early warning and audit export are the reused foundation. Browser Web Speech performs recognition and speech synthesis; **Muse Spark does not transcribe audio in this implementation**.
- Photo upload, validation and storage work locally. SAM 3.1 output is parsed into **region boxes**, which the dashboard overlays. Polygon masks are not rendered. Live vision/SAM/image verification is reported separately; a text success does not verify these models.
- Video clips are validated and stored for **human review only**. Raw video model analysis is disabled because the API support and pricing contract are unverified.
- WhatsApp is an intake **mock**; no WhatsApp message is sent. Manufacturer alert feeds are pull feeds/payload previews, not demonstrated external delivery.
- Safety campaigns connect component-lot records, owner reports, reviewed repairs, follow-up and evidence export. The synthetic walkthrough and a live Baseten-hosted Muse Spark Open symptom-extraction call are recorded in [`reports/hackathon/safety_campaign_smoke.json`](reports/hackathon/safety_campaign_smoke.json). This is integration evidence, not a measured field outcome. See [`docs/safety-campaigns.md`](docs/safety-campaigns.md).
- The new **Meta investigation** tab performs sourced extraction, model-selected read-only evidence lookups, a cited brief and linked follow-up. Live synthetic runs are recorded in [`investigation_live_smoke.json`](reports/hackathon/investigation_live_smoke.json) and [`investigation_followup_smoke.json`](reports/hackathon/investigation_followup_smoke.json). Blind review packs, a gated comparison and the real-participant study are ready; human results remain pending. See [`docs/sourced-investigation.md`](docs/sourced-investigation.md).

## Run the judge demo

Requirements: **Python 3.12**, Node **20.19+ or 22.12+**, and Chrome for optional microphone recognition.

```bash
bash scripts/judge_setup.sh
```

This creates an isolated `.venv-hackathon`, prepares the review assets, builds the dashboard and seeds `data/hackathon/judge-v3/`. It preserves older judge datasets. Seeding never spends Meta credits. Open `http://127.0.0.1:8000/ui/#demo` for **Report → Investigate → Review → Evidence**. An authenticated server opens Sign in first, then returns to the requested page. Credential entry remains directly reachable at `/ui/#signin`, including in open local mode. The earlier intake/LotGuard tour is at `/ui/#legacy-demo`.

Use **Have an operator API key?** for the local operator credential printed by setup. It authenticates a service principal with its permitted operations. For named supervisor takeover/release and review, use **Have a supervisor session?** and paste the separately issued supervisor session. The browser stores that session as an HttpOnly cookie.

From `dashboard/`, `npm run test:signin` builds the current production UI into temporary storage and tests real operator/session authentication, refused unauthorized review, permitted supervisor review and open-mode entry against isolated local API servers. Install Playwright Chromium first, or use `PLAYWRIGHT_CHANNEL=chrome` with installed Chrome. The test disables model calls and uses fictional fixtures. See [entry validation](docs/entry-auth-validation.md) for prerequisites and the missing-route negative control.

Keep `META_API_KEY` / `BASETEN_API_KEY` in the server-side `.env`; never paste them into the dashboard key fields. `BASETEN_API_KEY` selects the pinned Baseten-hosted Muse Spark Open model (`meta-models/muse-spark-open-1026`); `META_BACKEND=meta` pins the Meta API instead. Without a model key, the deterministic report/review path remains available. Each investigation operation identifies live inference, deterministic handling, fallback or saved output. A replay server never makes a new model call. If port 8000 is occupied, use `API_PORT=8765 bash scripts/judge_setup.sh`.

For a credit-free isolated rehearsal, run `.venv-hackathon/bin/python -m scripts.investigation_demo_server --without-recorded-proof`. Omit that flag only to inspect the historical 29 October proof: it retains its original source IDs and is labelled display-only historical replay; it cannot be accepted as a new review of the current campaign. This server is open local mode, not the authenticated judge setup.

Docker option:

```bash
docker compose -f docker-compose.hackathon.yml up --build
```

The container requires an operator API key and a distinct session secret in your environment or local `.env`. It seeds the current campaign and includes all advertised review pages. CI includes a current-image smoke job. Docker is unavailable on the reviewed machine, so this change has not been locally built/run in Docker and its release CI result remains pending.

The current no-proof local server passed `python -m scripts.submission_smoke --base-url http://127.0.0.1:18068 --open`: campaign seed, inspectable installation records, five review pages and their JavaScript assets. This read-only check made zero model calls. It is separate from the production authentication/browser check.

## Reproduce verification

Start with the small public replay. It checks saved arithmetic, source hashes and quotation citations using only Python's standard library, with no network, weights or API credit:

```bash
python -m scripts.public_replay
python -m scripts.package_public_replay
```

The generated `reports/hackathon/public_replay/TraceX-public-replay.zip` is a lightweight standalone replay. The [claim-to-artifact index](reports/hackathon/CLAIM_INDEX.md) states every result's scope, date, model/version and denominator, plus the separate full-data requirements. Replaying a saved result does not validate new model behavior.

```bash
make test                    # builds dashboard, provisions/checks pinned MiniLM, isolated test DBs
make eval-frontline          # isolated deterministic evaluation
.venv-hackathon/bin/python -m scripts.ai_meta_smoke
# Optional individual capabilities:
.venv-hackathon/bin/python -m scripts.ai_meta_smoke --vision --sam --image
```

The smoke command runs only synthetic input on a fresh fixture warehouse and writes the actual artifact schema consumed by `/api/ai/status`. Missing keys, rejected output, or failed ledger verification never produce a successful marker. Each feature is matched to its endpoint and model ID.

All Meta attempts go through the allow-listed client with bounded timeouts/retries, schema validation, a daily call cap, and the cross-process lifetime **$30 maximum** reservation ledger. The tested text intake default is 20 seconds, configurable through `META_INTAKE_TIMEOUT_S` up to 30 seconds; a timeout falls back. Spending in a proof artifact is a snapshot at that artifact's timestamp, not current account usage. This budget covers this client, not unrelated account activity. Baseten-hosted Muse Spark Open has the recorded 29 October safety-campaign integration proof linked above. Modal and Fireworks remain **unverified**; only explicitly priced model IDs can run. Muse Wonder is not implemented in this submission.

## Event contributions and reused work

See [`ELIGIBLE_WORK.md`](ELIGIBLE_WORK.md) for the actual baseline, original source commits and current contribution range. The TraceX initial commit imported an existing product; its date does not make every imported feature event-built. No published history is rewritten.

The participant guide supplied by the owner gives kickoff as 26 October, the building period as **27 October–4 November**, and the deadline as **4 November at 9 PM Eastern**. It explicitly requires a **public repository** and a **three-minute demo video** highlighting the features, code and functionality built during the event. Existing codebases may be used, but new contributions must be clearly identified; failure to identify them can disqualify a submission. Reused foundation must be disclosed as context, and the demo must highlight event-built work. Check the portal for its accepted video container and upload details.

The published rubric is Impact **30%**, Use of Meta AI Tooling **25%**, Technical Depth & Execution **20%**, and Demo **25%**. The next work is prioritized in [`reports/hackathon/IMPROVEMENT_PLAN_2026-10-30.md`](reports/hackathon/IMPROVEMENT_PLAN_2026-10-30.md); that plan contains proposed work and acceptance criteria, not claimed results.

## Historical results — context, not Meta prediction accuracy

The deterministic NHTSA report used five makes and 219,510 complaint records. Its in-sample production detector matched **535/1,172 campaigns (45.6%)**, with an **11-week median** actionable lead. Episode precision was **0.64** under the chosen matching rules.

A different tuned `abs3` configuration reported **62.7% campaign recall, 8-week median lead** on a later window. Production `abs5` was **not run** on that window. Matching is at make/component grain, not verified physical-defect identity. The original raw-file hash and exact ingest arguments are not fully reproducible from this checkout. These figures do not establish Meta improving prediction or accidents prevented. See [`reports/CLAIMS_AUDIT.md`](reports/CLAIMS_AUDIT.md) and [`reports/nhtsa/backtest_safety_2015_2024.md`](reports/nhtsa/backtest_safety_2015_2024.md).

The 84 Hindi/Hinglish examples are **synthetic**. Their prior local Hindi safety result is not real-customer accuracy. The 300-row defect label sample has no completed human labels; no defect-classification accuracy claim is made.

The separate expanded-fuel 2025 holdout measured **5/8 campaigns (62.5%)** and **6/18 mature-alert matches (33.3%)**, equalling the count baseline. None of 40 development candidates met the precision gate. The above-86% target was not achieved. This scope differs from the earlier historical reports; it is not a direct improvement on their benchmarks. See the [frozen result and replay instructions](reports/defect/fuel_holdout/README.md).

## Safety and audit boundaries

The original kill-switch, severity rules and ledger always run. AI may add supported facts or raise a severity/sentiment floor, never lower safety. Invalid/low-confidence/unsupported outputs fall back. Grounded brief claims require source sentences, citation scope and number checks. Source complaints themselves are not independently verified facts.

The reused contact action chain is **tamper-evident**, and its contact exports have separate Ed25519 signatures. The campaign packet records sources, actor/time/history, revisions and model fingerprints; it is not automatically covered by those older contact-export signatures. A file hash detects a difference from a known copy; it does not independently authenticate the truth of a complaint or an engineer's decision.

## Demo story

Use [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md): one difficult owner report becomes a cited investigation, a missing record changes the reviewed association, and the same vehicle reaches documented action and separate repair verification. The older narrated 180-second recording at `reports/hackathon/investigation_demo/TraceX-investigation-demo.mp4` and its [media verification](reports/hackathon/investigation_demo/video_verification.json) are historical evidence, not verification of the current build. Preserve its fictional/replay labels. Human effectiveness measurements remain pending.

Public submission state is in [`submission_links.json`](reports/hackathon/submission_links.json). The repository opened successfully in a fresh anonymous Chrome context on 30 October; [the result](reports/hackathon/link_checks/results.json) retains the check. The final submitted source commit, public three-minute video, portal entry and actual team list still need verification. A hosted demo is optional; the local fallback must remain reproducible. Video binaries are gitignored and need an accessible upload.

After filling actual links, run `PLAYWRIGHT_CHANNEL=chrome node scripts/check-public-links.mjs` from `dashboard/`. The checker uses a fresh browser context and does not submit the portal form. Confirm the final links/team in the portal separately and record the submitted commit. Do not mark an empty URL or a developer-only local file as publicly accessible.
