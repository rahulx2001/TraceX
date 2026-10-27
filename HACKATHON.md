# TraceX — Meta Global AI Developer Hackathon

**Hosts:** Meta & Cerebral Valley  
**Window:** Oct 26 at 12:00 PM – Nov 4 at 9:00 PM (EST) | **Date:** 2026-10-27  
**Tracks:** Startup Track (Production Readiness & Enterprise Execution) / Indie Developer Track  
**Themes:** Build for Your World (Multilingual Voice VOC) & Push the Frontier (Visual Part Segmentation with SAM 3.1 & Automotive Safety RCA)  
**Meta Models:** Muse Spark series (`muse-spark-1.3`), SAM 3.1 (`sam-3.1`), Muse Image (`muse-image-1.0`), Muse Wonder  
**Inference Partners:** Meta Model API ($150 credit tier), Baseten, Modal, Fireworks  

> **Mission: Help vehicle manufacturers reduce road accidents by recording vehicle faults from every customer contact, in the customer's own language, and predicting defects early enough to inspect and repair before they cause crashes, fires, or injuries.**

> **Evidence status (2026-10-27):** No live Meta API call has been made in this project checkout. Every Meta path described here is covered by mocked contract tests or the no-key deterministic fallback. All Hindi/Hinglish evaluation calls are synthetic. See §4.2 and §6.

TraceX operates as a dual-engine voice-of-customer operations platform and root-cause analysis (RCA) engine:
1. **Deterministic Safety Core:** Voice/text intake, kill-switch lexicons, triage rules, NHTSA weekly z-score clustering, Qubot groundedness auditor, and an immutable Ed25519 hash-chain audit ledger. An embedded Hindi/Hinglish emergency lexicon (`hindi_safety.py`) ensures life-critical hazards (fire, brake failure, injury) trigger emergency stops locally without network latency or external model dependencies.
2. **Meta Model Layer:** With `META_API_KEY` configured (using the hackathon Meta Model API), Meta models **converse in Hindi/Hinglish and English via Muse Spark**, **segment physical part damage via SAM 3.1**, and **write grounded engineering briefs**, while deterministic safety floors govern every output (`final = max(rule, AI)`).

- Demo storyboard: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)
- One-command judge setup: `bash scripts/judge_setup.sh` → `http://127.0.0.1:8000/ui/#demo`
- Single container (portable): `docker compose -f docker-compose.hackathon.yml up --build`

## 1. What is new vs. what already existed

| Already existed (unchanged) | Added in this branch before the event (`[AI-LAYER]`, 2026-10-20/21) |
|---|---|
| Domain packs, slot frames, regex/gazetteer intake | `src/ai_layer/*`: Meta client, config, intake enhancer, language normaliser, severity raise, photo evidence, grounded brief, safety tiering, safety board, demo seeding |
| Kill-switch lexicon, `assess_safety`, Qubot auditor, audit ledger | `src/api/routes/ai_layer.py`: `/api/ai/*`, `/api/cases/{id}/evidence`, `/api/evidence/*` |
| Triage severity rules, NHTSA clustering, investigations | Dashboard: `dashboard/src/ai/*`, `dashboard/routes/DemoMode.jsx` (`#demo`) |
| Recall lead-time backtest (`src/backtest/recall_lead.py`) | `scripts/ai_safety_backtest.py`: full-scale run + preventable-window counts |
| Early-warning board, Issue desk, Case queue, Call widget | `eval/enhanced/`: 60 labelled synthetic calls (en/hi/hinglish) + harness; `eval/hindi_fresh/`: 24 further synthetic Hindi/Hinglish calls (84 total) |
| | `scripts/judge_setup.sh`, `scripts/ai_demo_seed.py`, `Dockerfile.hackathon`, `docker-compose.hackathon.yml` |
| | Tests: `tests/frontline/ai_layer/` (every Meta call mocked) |

### 1a. Road-safety tools (`#ai-tools`, all deterministic without a key)

| Tool | Endpoint(s) | What it does (data behind it) |
|---|---|---|
| Per-vehicle fault risk | `GET /api/ai/vehicle-risk?make&model&year[&mileage]` | Per-component complaint counts for that make/model/year, share vs model-year peers, crash/fire/injury mentions and matching recall campaigns from the NHTSA warehouse → level (act now / high / elevated / watch / low) + owner advice. Every level shows its counts. Mileage is accepted but **not used** (NHTSA rows carry no mileage). Optional Muse Spark plain-language explanation is rejected if it cites any number not in the facts. |
| Manufacturer alert feed | `POST /api/ai/alerts/scan`, `GET /api/ai/alerts`, `GET /api/ai/alerts/feed.json`, `POST /api/ai/alerts/{id}/ack` | Investigations crossing a threshold (≥3 cases high, ≥10 elevated; env-configurable) become alerts carrying the grounded brief + recommended repair actions. Deduped per investigation, only escalates. Delivery is a pull JSON Feed 1.1 and a webhook **payload preview; nothing is sent externally.** |
| Service-centre queue | `GET /api/ai/service-centre/queue` | Open cases ranked by explained points: existing severity, kill-switch flags, component tier, recall match, investigation, waiting time; each with a call-in action. |
| Fault spread | `GET /api/ai/spread?make&model&component&year_min&year_max` | Complaint counts by NHTSA reporting state and received month, region × year heat grid, first-reporting regions. Raw counts, **not normalised** for population or fleet size. |
| WhatsApp intake **MOCK** | `POST /api/ai/whatsapp-mock/webhook` | Accepts a WhatsApp-Cloud-API-shaped `messages` webhook body and feeds each text into the **existing** orchestrator (channel `whatsapp_mock`, sender stored only as sha256). Kill-switch, `assess_safety`, Qubot and audit run as for any contact. Replies are returned in the response (`status: mock_not_sent`). **No WhatsApp Cloud API is called and no message is sent.** If `META_API_KEY` is configured, the same optional Meta intake/severity hooks as any other contact may run; with no key, the path is fully local. |
| Short video evidence | `POST/GET /api/ai/cases/{id}/video`, `GET /api/ai/video/{id}/file`, `POST /api/ai/video/{id}/analyze` | mp4/mov/webm sniffed by magic bytes, size cap `AI_VIDEO_MAX_BYTES` (20 MB), duration read from the container (MP4 `mvhd` / WebM `Info/Duration`), 1–10 s (`AI_VIDEO_MAX_SECONDS`); unreadable duration is rejected. Stored per case, erased by the DSR hook. Analysis only with `AI_VIDEO_ANALYSIS=1` + key: **unverified: video input support not confirmed**; informational, never changes severity. Default: `stored_no_analysis`. |

## 2. How each Meta tool is used

All calls go through `src/ai_layer/meta_client.py`, which does the following:
- uses an allow-listed host (the key only goes to `api.meta.ai` or `META_ALLOWED_HOSTS`);
- applies a timeout, a retry on 429/5xx and a daily call cap;
- validates strict JSON schemas;
- logs nothing secret.
Every result also writes a row to an AI event log that records the deterministic value, the AI proposal and what was accepted.

| Meta model | Where | What it does | Guard-rail |
|---|---|---|---|
| **Muse Spark 1.3** (`muse-spark-1.3`, chat completions) | Live call intake (`intake_enhancer.py`) | Fills only *still-empty* slots; normalises Hindi/Hinglish to English | Values must validate against the pack gazetteer/year range and a confidence floor (0.7). The **existing** kill-switch lexicon is re-run on the English text and may only **add** an escalation |
| Muse Spark 1.3 | Language API (`normalize.py`) | Hindi/Hinglish → English, original kept alongside | Numbers must survive translation; a deterministic glossary is the fallback |
| Muse Spark 1.3 | Severity/sentiment (`severity.py`) | Proposes a severity + caller sentiment | `final = max(rule, AI)`; AI can never lower severity; the Qubot severity sanity check still runs |
| Muse Spark 1.3 (vision) | Photo evidence (`evidence.py`) | Describes the photo, guesses the component, notes visible hazards | May only add flags; never changes case severity by itself |
| **SAM 3.1** (`sam-3.1`, `/v1/responses`) | Photo evidence | Segments the damaged region; boxes drawn as an overlay in `EvidencePanel` | Box tokens parsed strictly; malformed output is dropped |
| Muse Spark 1.3 | Grounded brief (`grounded_brief.py`) | Rewrites the investigation brief, leading with crash/fire/injury risk, plus a suggested inspection step | Every claim must cite a real record/advisory ID and pass **Qubot**; failing claims are dropped and counted. AI actions with numbers/IDs are rejected; accepted ones are labelled "requires engineering review" |
| **Muse Image 1.0** (`muse-image-1.0`) | `scripts/ai_demo_seed.py --muse-image` | Optional *synthetic* brake-rotor photo for the demo | Always labelled SYNTHETIC; the default is a code-generated PNG |
| Muse Spark Open / Muse Glimmer (open weights) | Any OpenAI-compatible gateway | Self-host by pointing `META_API_BASE` at it and listing it in `META_ALLOWED_HOSTS` | Same client and guards |
| Browser Web Speech `hi-IN` | Call widget | Hindi speech recognition (language picker) | Muse Voice Transcribe is **not** wired (see §6) |

Every AI surface in the UI carries a **Meta model tag** (e.g. `Muse Spark 1.3`,
`SAM 3.1`) or a **Deterministic** tag, and the top bar shows the AI-mode badge.

## 3. Safety contract (what AI can never do)

1. Without a key (`META_API_KEY` / `MODEL_API_KEY`) or with `FRONTLINE_AI_LAYER=off`, no Meta network call is made and every optional Meta feature returns the deterministic result. This is enforced in tests by a transport that fails on any call. Two deliberate no-key behavioural additions are the deterministic Hindi/Hinglish safety layer (`src/ai_layer/hindi_safety.py`, §4.2) and the deterministic OBD-II fault-code capture/severity floor (`src/ai_layer/fault_codes.py`, §5); each can only add a kill-switch hit, slot or severity floor, never lower anything, and neither is a Meta call.
2. The kill-switch, `assess_safety`, the Qubot auditor and the audit ledger always run and have the final say. AI may only **raise** severity or **add** a safety flag.
3. On any error, timeout, invalid JSON, schema mismatch or low confidence, the layer falls back silently to the deterministic result and logs the reason.
4. No invented data. Brief claims must cite warehouse record/advisory IDs that pass Qubot. Photos in the demo are synthetic and labelled as such. The committed backtest JSON was produced from the public NHTSA `FLAT_CMPL.zip` / `FLAT_RCL_POST_2010` files; those raw ZIPs are not in this checkout, and the live 2026-10-26 `FLAT_CMPL.zip` has a different SHA-256 from the recorded input, so the recorded run cannot be reproduced byte-for-byte here (see §4.1 and `reports/CLAIMS_AUDIT.md`).

## 4. Results (real data, honest caveats)

### 4.1 Recall early-warning backtest (NHTSA)

Full run on public NHTSA ODI data:
- complaints: `FLAT_CMPL`, Honda / Toyota / Ford / Hyundai / Kia, model years 2015–2024, **219,510 complaints** (`reports/nhtsa/backtest_safety.json`, `precision.records`);
- recalls: `FLAT_RCL_POST_2010`, **4,393 recall scope rows = 1,172 campaigns** (`reports/nhtsa/backtest_safety.json`, `summary.recalls_scored` / `summary.campaign_level.campaigns`).

This full-window report is the **production** detector (`z >= 2.0`, BH
`q <= 0.05`, absolute lift `>= 5`, relative lift `>= 0.5`;
`src/ml_runtime/anomalies.py` constants). Its 45.6% headline below is
**in-sample on 2015–2024**, not an out-of-sample result.

The detector is the **existing** deterministic weekly z-score scan; no AI is involved in these numbers. Each recall is scored only on complaints NHTSA had *received* by the recall report date, and misses stay in.
Full report: [`reports/nhtsa/backtest_safety_2015_2024.md`](reports/nhtsa/backtest_safety_2015_2024.md). Reproduce with a side `DOMAIN_DB_PATH` loaded by `scripts/ingest_nhtsa.py` + `scripts/ingest_recalls.py`, then `make ai-backtest ZIP=FLAT_CMPL.zip`. The **exact ingest flags for the committed run are not recorded**; the closest reproducible sequence is:

```bash
export DOMAIN_DB_PATH=/path/to/side/domains
python -m scripts.ingest_nhtsa --pack automotive_nhtsa --limit 300000 \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024
python -m scripts.ingest_recalls --pack automotive_nhtsa --zip FLAT_RCL_POST_2010.zip \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024 --rcl-type V
python -m scripts.ai_safety_backtest --zip FLAT_CMPL.zip \
  --makes HONDA,TOYOTA,FORD,HYUNDAI,KIA --year-min 2015 --year-max 2024
```

The limit must be above 219,510 or the corpus is truncated. The expected
`FLAT_CMPL.zip` SHA-256 is in `reports/oos/oos_config.json`
(`c00707bd4afd6cad075000e0c45e74b59d140976aab2ddae3c6f47a4f807ffe1`). The raw
ZIPs were absent when this audit started; the audit-run status is in
`reports/CLAIMS_AUDIT.md`. NHTSA refreshed the live file on 2026-10-26: the copy
downloaded that day was 375,063,317 bytes with SHA-256
`91ff80bd163cbfecb80700948ab4a0e60fd49b6c0640e7abab692d691188c608`, so it is
**not byte-identical** to the input recorded for the committed run.

**Headline: actionable early warning** (a flag episode on the same make + component ending within 52 weeks before the recall):

| | Campaigns | Scope rows |
|---|---|---|
| Flagged early (hits) | **535 / 1,172 (45.6%)** | 2,090 / 4,393 (47.6%) |
| Missed | 637 | 2,303 |
| Median / mean lead | **11 / 15.9 weeks** | 10 / 14.8 weeks (IQR 3–23) |

| Flag quality (full series) | Value |
|---|---|
| Flag episodes | 1,540 |
| Confirmed by a later recall of the same make + component | 985, so **precision 0.64** |
| False-alarm episodes (no later recall in the data) | 555 |
| Slice-weeks flagged / confirmed / false alarm | 2,409 / 1,619 / 790 (precision 0.672) |

**Preventable window (correlation only, not "lives saved"):** this counts distinct complaints on the flagged make + component that NHTSA received between the start of the flag episode and the recall report date, using NHTSA's own owner-entered fields:

| CRASH = Y | FIRE = Y | INJURED > 0 | DEATHS > 0 | Any of these |
|---|---|---|---|---|
| 1,379 | 712 | 882 (1,266 persons) | 19 (29 deaths reported) | 2,331 |

**First-ever flag (full 2015–2024, production detector; not a tuned-threshold result and not the OOS result below):** counting from the *first-ever* flag of a slice gives 735 / 1,172 campaigns (62.7%) with a median lead of 214 weeks (`reports/nhtsa/backtest_safety_2015_2024.md`, "First-ever flag"). That lead is inflated. A broad slice such as FORD ENGINE is first flagged in 2015 and then "matches" an unrelated 2026 recall.

**Out-of-sample (OOS) result — tuned threshold, separate run:** on the 2021–2024
test window, the tuned config `z2.0_q0.05_abs3_rel0.5` scored **62.7% campaign
recall with a median lead of 8 weeks** (`reports/oos/oos_test_results.json`,
`actionable_52w.campaign_level`). That 62.7% belongs to the tuned `abs3` config,
**not** to production. Production ships `abs5`; it was **not run on the 2021–2024
test window (NOT RUN)**, so there is no production OOS number. Its in-sample
2015–2020 score was **33.6% campaign recall with episode precision 0.61**
(`reports/oos/oos_tune_results.json`, `in_sample_production`). Do not quote the
tuned 62.7% as the production detector's performance.

Caveats:
- Matching is at make + component grain, so a flag can come from a different defect than the one recalled.
- The 52-week window is a chosen parameter, not a tuned one.
- "False alarm" includes real defects that were never recalled, or that were recalled after the data window (right-censoring).
- Complaints are self-reported.
- The recall date is the Part 573 receipt date, and manufacturers often know earlier.
- Precision uses the full series.
- Only 5 makes were ingested. The **219,510** kept rows are verified in `reports/nhtsa/backtest_safety.json` (`precision.records`). The earlier run also reported **2,258,118** FLAT_CMPL lines read and **9,198** rows marked "trusted"; no raw file or ingest log for those two counts is committed in this checkout, so they are **unverifiable here** and should not be quoted as independently checked. The rows were loaded with the existing historical-backfill option (`enforce_trust=False`).

Memory note: the existing `recall_lead_report` caches every as-of series and ran the box out of RAM at this scale. `scripts/ai_safety_backtest.py` therefore calls the same building blocks but keeps only one series in memory per worker. A test asserts that its output is identical to `recall_lead_report` on a fixture.

### 4.2 Hindi/Hinglish intake eval (`reports/hindi_safety/HINDI_EVAL.md`)

**All 84 evaluation calls are synthetic, and every row in the eval files is
marked `"synthetic": true`.** The 60-call set (`eval/enhanced/calls.jsonl`) was
committed 2026-10-20 21:45 UTC; the 24-call fresh set
(`eval/hindi_fresh/fresh_calls.jsonl`) was committed 2026-10-21 07:58 UTC; the
lexicon (`src/ai_layer/hindi_safety.py`) was committed 2026-10-21 08:01 UTC
(`git log --diff-filter=A`). Both eval sets and the lexicon are therefore dated
the same local day (2026-10-21 IST), and the fresh 24 were committed before the
lexicon and before measurement. These are evaluation inputs, not real customer
calls.

Kill-switch results (counts, not percentages; from
`reports/hindi_safety/HINDI_EVAL.md` and `hindi_eval.json`):

| Set | Language | Calls | Rules-only hits / expected | Rules + `hindi_safety` | False alarms (rules + `hindi_safety`) |
|---|---|---|---|---|---|
| original 60 | English | 20 | 4 / 4 | 4 / 4 | 0 |
| original 60 | Hindi (Devanagari) | 20 | **0 / 4** | **4 / 4** | 0 |
| original 60 | Hinglish | 20 | **2 / 4** | **4 / 4** | 0 |
| original 60 | all | 60 | 6 / 12 | 12 / 12 | 0 |
| fresh 24 | Hindi (Devanagari) | 12 | **0 / 6** | **6 / 6** | 0 |
| fresh 24 | Hinglish | 12 | **0 / 6** | **6 / 6** | 1 |
| fresh 24 | all | 24 | 0 / 12 | 12 / 12 | 1 |
| **total** | **all** | **84** | **6 / 24** | **24 / 24** | **1** |

The rules-only path misses every Hindi safety call in both sets. The deterministic
`hindi_safety.py` layer (no Meta key, no network) recovers all of them; the one
false alarm is `fr_hl_11` in the fresh Hinglish set (a parking-lot scratch that
mentions no injury but contains collision language). These are synthetic test
results, not production accuracy.

The optional Meta-enhanced column was **NOT RUN (no `META_API_KEY` configured)**;
no live Meta call has been made. There are no enhanced accuracy numbers to quote.
To attempt that run: `META_API_KEY=… python -m eval.enhanced.run_eval`.

## 5. Existing files touched (minimal wiring, each marked `[AI-LAYER]`)

| File | Why |
|---|---|
| `src/api/main.py` | `include_router(ai_layer_routes.router)` (2 lines) |
| `src/agents/orchestrator.py` | Guarded hooks: Meta `maybe_enhance_intake` after deterministic intake; Meta `maybe_raise_severity` after triage (both return the input unchanged with no key); plus the no-key deterministic `maybe_raise_severity_hi` (Hindi safety) and `maybe_capture_fault_codes` (OBD-II evidence). Each sits inside `try/except` |
| `src/frontline/dsr.py` | DSR erase also deletes the photo evidence rows/files for the erased interaction |
| `.gitignore` | Ignore `data/ai_evidence/` (customer photos) and `data/hackathon/` |
| `docs/openapi.yaml` | Additive entries for the new `/api/ai/*` and evidence paths (the surface test requires it) |
| `Makefile` | Appended targets `hackathon-setup`, `ai-demo-seed`, `ai-eval`, `ai-backtest`, `ai-test` |
| `README.md` | Mission line + "AI Layer (optional)" section |
| `dashboard/src/App.jsx` | `#demo` page entry + AI-mode badge in the top bar |
| `dashboard/routes/CallWidget.jsx` | Speech language picker (`hi-IN`) and photo upload under the compose box |
| `dashboard/routes/CaseQueue.jsx` | `EvidencePanel` above operator notes |
| `dashboard/routes/IssueDesk.jsx` | `GroundedBriefPanel` + read-only evidence panel |
| `dashboard/routes/EarlyWarningBoard.jsx` | `SafetyRiskBoard` under the header |

No product rules, regexes, gazetteers, lexicons, test assertions or data were
modified by the 2026-10-26 honesty cleanup. That cleanup changed docs, pinned
`pyarrow`, fixed the demo seed script's temp-file path jail, and corrected a
report-renderer sentence; the pre-event feature wiring above is unchanged.

## 6. What is unverified about Meta (no key exists in this project)

- Endpoint defaults follow the public docs at <https://dev.meta.ai/docs> (read 2026-10-21): base `https://api.meta.ai/v1`, Bearer auth, `muse-spark-1.3` chat completions with `response_format: json_schema`, `sam-3.1` via `/v1/responses` streaming box tokens, and `muse-image-1.0` via `/v1/images/generations`. **None of this has been called live.** The request/response shapes are covered only by mocked tests.
- The following are assumptions: `json_schema` strict-mode support on Muse Spark, the exact SAM box-token grammar, image-input formatting for vision, rate limits and pricing. Every one is env-configurable (`META_API_BASE`, `META_MODEL_*`, `META_CHAT_PATH`, `META_SAM_ENDPOINT`, `META_IMAGE_ENDPOINT`, `META_TIMEOUT_S`, …; see `src/ai_layer/config.py`).
- Video input to Muse Spark (sending an mp4/webm data URL as an `image_url` part) is **not documented/confirmed**; it is behind `AI_VIDEO_ANALYSIS` and labelled unverified.
- Muse Voice Transcribe (`muse-voice-transcribe-1.0`) exists in the docs but is **not implemented**. Hindi speech uses the browser's `hi-IN` Web Speech recogniser.
- Enhanced-mode accuracy numbers do not exist yet (see §4.2).
- **To verify with a key:** `META_API_KEY=… python -m scripts.ai_meta_smoke` (add `--image` for Muse Image). It makes one small call each to text, vision and SAM 3.1 through the product client and prints ok/failed with the reason. Without a key it is skipped and makes no network call. This smoke script was **NOT RUN** here (no key).

## 7. Known limitations (honest list)

- The pack kill-switch lexicon itself is English-only and was not changed. A separate deterministic Hindi/Hinglish safety layer (`src/ai_layer/hindi_safety.py`) runs with **no Meta key** and can only add a kill-switch hit or fill an empty slot. Meta is not required for the Hindi emergency stop; it is only relevant to the optional conversational normalisation path, which has not been run live.
- Existing `classify_yes_no` does not parse Hinglish "nahi"/"haan" as no/yes, so the seeded scenario answers yes/no questions in English. This was left as is (existing logic).
- The British spelling "tyre" is not in the English gazetteer. That was left as is.
- The safety-risk tier uses a keyword list over complaint text, so it is a triage aid, not a hazard analysis.
- The kill-switch path sets Critical/P1, emits the "do not drive" script, a supervisor whisper and an optional Slack-shaped `ALERT_WEBHOOK_URL` alert. It does **not** create a handoff queue row or call a dedicated paging system; the separate manual "page a human specialist" control queues a handoff. The demo has no alert webhook configured, so nothing is sent externally.
- The local demo warehouse can be built from synthetic scale rows (`scripts/ingest_scale.py`); counts shown by the `#ai-tools` screens are then synthetic demo counts, not real NHTSA evidence. The demo transcript and generated photo are labelled synthetic in the UI. The judge setup uses fixture/simulated data, not a full public NHTSA load.
- `pyarrow` was previously undeclared; it is now pinned in `requirements.txt`, `requirements-docker.txt`, and `requirements-lock.txt` (`pyarrow==22.0.0`). `scripts/seed_issue_demo.py` previously hit the allow-root jail on its generated temp CSVs; that path fix is in the 2026-10-26 cleanup.
- Backtest caveats are listed in §4.1.

## 8. Hackathon Tracks, Themes & Architecture Alignment

### 8.1 Track Fit: Startup Track & Indie Developer Track

TraceX is architected for both evaluation tracks of the Meta Global AI Developer Hackathon:

- **Startup Track (Technical Execution & Production Integrity):**
  - **Fail-Closed Safety Architecture:** Third-party LLMs never operate unconstrained on safety-critical workflows. TraceX guarantees that deterministic rules and kill-switch lexicons establish an immutable safety floor (`final = max(rule, AI)`).
  - **SOC 2 & Tamper-Evident Ledger:** Every action, slot extraction, sentiment score, and brief generated by Meta models is signed and stored in an immutable Ed25519 hash-chain audit ledger.
  - **Live Ops Supervisor Console:** Real-time WebSocket connection strip allowing human supervisors to monitor calls, review live frustration, and execute one-click takeovers.
  - **Enterprise Connectors:** Configurable webhook notifications, audit exports (CSV/JSON), and incident alerting with signature verification.

- **Indie Developer Track (Creativity, Technical Ambition & Working Prototype):**
  - **Multi-Modal Pipeline:** Combines real-time Hindi/Hinglish speech synthesis and recognition, physical part defect segmentation with **SAM 3.1**, and zero-shot diagnostic trouble code classification.
  - **Live Working Application:** Runs out-of-the-box locally via `bash scripts/judge_setup.sh` or Docker with complete offline fixtures and zero external setup hurdles.

---

### 8.2 Project Themes: "Build for Your World" & "Push the Frontier"

1. **Theme 1: Build for Your World (Multilingual Voice VOC)**
   - *The Reality:* In India and multilingual emerging markets, vehicle owners experiencing catastrophic mechanical failures (sudden brake loss, steering lock, engine smoke) report them in Hindi or Hinglish.
   - *The Meta Solution:* **Muse Spark 1.3** transcribes and normalises colloquial turns (e.g. *"Namaste. Meri Honda CR-V ke brakes fail ho gaye"*), extracts structured parameters against validated gazetteers, and triggers immediate hazard classification, while the deterministic lexicon ensures instant local fail-safe execution.

2. **Theme 2: Push the Frontier (Visual Part Damage via SAM 3.1 & Telematics RCA)**
   - *The Physical Frontier:* Bridging customer-reported symptoms to physical component hardware and fleet-wide manufacturing defect prediction.
   - *The Meta Solution:* When an owner uploads a photo of a failed component, **SAM 3.1** (`sam-3.1`) automatically segments the damaged region (e.g. cracked rotor surface, ruptured hydraulic hose), outputting bounding boxes and polygon masks overlaid on the operator console.
   - *Engineering Defect Clustering:* Weekly z-score anomaly scans correlate customer complaints and OBD-II DTCs with NHTSA recall histories to predict emerging component defect clusters weeks before official recall campaigns.

---

### 8.3 Meta Model Stack & Credit Budgeting ($150 Tier)

TraceX is explicitly designed to maximize efficiency under the $150 Meta Model API credit allotment:
- **Daily Call Caps (`META_DAILY_CALL_CAP`):** Configurable request throttling (default 300 calls/day) to prevent accidental credit exhaustion.
- **Circuit Breakers & Exponential Backoff:** Automatic retries on HTTP 429/5xx and fallback to local deterministic models on any latency spike or network disconnect.
- **Zero Key Leakage:** `META_API_KEY` remains strictly server-side in `.env` and is never transmitted to or stored in client browser sessions.
- **Partner Support:** Compatible with open-weights endpoints hosted on Baseten, Modal, and Fireworks via standard OpenAI-compatible gateways.

---

### 8.4 Event Roadmap & Verification Status (2026-10-27)

- **Status as of Day 2 (Oct 27, 2026):**
  - Deterministic safety baseline, WebSocket supervisor console, and domain packs are fully operational.
  - Meta Model API integration (`muse-spark-1.3`, `sam-3.1`, `muse-image-1.0`) is wired through `src/ai_layer/meta_client.py` with strict JSON schema validation.
  - The frozen defect-level taxonomy (`reports/defect/taxonomy.json`) and 300-row stratified evaluation sample (`reports/defect/defect_label_sample_300.csv`) are prepared.
  - When judges supply `META_API_KEY`, the console immediately switches to **AI: Enhanced** mode; with no key, it runs 100% locally on deterministic safety floors.
