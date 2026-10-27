# Claims audit — Skew AI / hackathon submission

Audit date: 2026-10-26 (IST). Repo: `/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool`.
Branch: `hackathon/ai-layer`. HEAD at audit start (the pre-event feature head):
`4b70a8019ef96fb689bcb21a714f723951e787b0` (120 commits; it equals
`origin/hackathon/ai-layer`). Six cleanup commits were made before this report:
`4dd4271`, `7fb9b79`, `701f01a`, `f99111b`, `83bf89d`, `af07e89` (126 commits
total at that point); the report commit that contains this file makes it 127 /
seven commits ahead. No push and no history rewrite were performed; all cleanup
commits are local only.

Method: every claim below was checked against the cited file, JSON key, source
constant or a command actually run on 2026-10-26. Nothing was estimated or
rounded by the auditor. Where a claim could not be executed, it is marked
**NOT RUN** or **UNVERIFIABLE**; no number was invented to fill a gap.

Status legend:

- **VERIFIED** — current text matches the source/command.
- **CORRECTED** — the prior text was false or misleading; the current text was
  changed and is listed in the corrections section.
- **NOT RUN** — the text says it was not executed, and that is accurate.
- **UNVERIFIABLE** — the underlying artifact is not in the checkout.
- **PARTIAL** — some sub-claims verified, some not; details in the row.

## 1. Repository and timeline claims

| # | Claim (current text) | Location | Evidence / check | Status |
|---|---|---|---|---|
| 1 | Pre-event head `4b70a80`, 120 commits, equal to `origin/hackathon/ai-layer`; four local cleanup commits afterwards | `HACKATHON.md` §8; audit header | `git rev-parse --abbrev-ref HEAD`; `git rev-parse 4b70a80 origin/hackathon/ai-layer`; `git rev-list --count 4b70a80` = 120; `git rev-list --left-right --count origin/hackathon/ai-layer...HEAD` = `0 6` before the report commit (`0 7` after it; run 2026-10-26) | VERIFIED |
| 2 | Event window 2026-10-26 to 2026-11-04; every commit through `4b70a80` is pre-event | `HACKATHON.md` §8 | `git log -1 --format='%aI' 4b70a80` → `2026-10-21T17:21:43+05:30`; `git log --since='2026-10-26 00:00:00'` returned no commits. The **start** date is consistent with git; the 2026-11-04 end date is not derivable from the repo | PARTIAL |
| 3 | Initial pilot commit `8be66ab` dated 2026-08-16 | `HACKATHON.md` §8 | `git log -1 --format='%h %aI %s' 8be66ab` → `2026-08-16T14:56:11+05:30` | VERIFIED |
| 4 | Phase 1 `020f81e` 2026-09-06; SLM/voice `ad14248` 2026-09-26 | `HACKATHON.md` §8 | `git log -1 --format='%h %aI %s' 020f81e ad14248` | VERIFIED |
| 5 | Meta client `fc114d2`, safety backtest `07bdb30`, `#demo` `ba2e881`, eval set `e16d267`, fresh set `791d65d`, lexicon `ce1268e`, OOS `e0e51db`, OBD `66a87bf` all on 2026-10-20/21 | `HACKATHON.md` §8 | `git log -1 --format='%h %aI %s'` on each hash (run 2026-10-26) | VERIFIED |
| 6 | Pre-event head contains "39 review fixes" | `HACKATHON.md` §8 | `git log -1 --format='%s%n%b' 4b70a80` → `fix(ai-layer): resolve all 39 findings from code review (F01-F39)`; body lists F01–F39 | VERIFIED |
| 7 | "Built during the event" lists only the 2026-10-26 honesty cleanup, no product feature | `HACKATHON.md` §8 | `git log --since='2026-10-26 00:00:00'` shows only the cleanup commits (`4dd4271`, `7fb9b79`, `701f01a`, `f99111b`, `83bf89d`, `af07e89`); no threshold/regex/lexicon/test change | VERIFIED |

## 2. NHTSA backtest numbers

All figures below are from the committed JSON produced by the recorded run.
They were **not** re-run from raw data at audit start because the ZIPs were not
present; see §7 and `reports/oos/BASELINES.md`.

| # | Claim | Location | Source key / check | Status |
|---|---|---|---|---|
| 8 | 219,510 complaints; 5 makes; MY 2015–2024 | `HACKATHON.md` L88 | `reports/nhtsa/backtest_safety.json` → `precision.records` = 219510; `meta.makes`; `meta.year_min/max` | VERIFIED |
| 9 | 4,393 recall scope rows = 1,172 campaigns | `HACKATHON.md` L89 | `summary.recalls_scored` = 4393; `summary.campaign_level.campaigns` = 1172 | VERIFIED |
| 10 | 535 / 1,172 campaigns flagged early = 45.6% | `HACKATHON.md` L122; `README.md` L281; `DEMO_SCRIPT.md` L110 | `summary.campaign_level.hits` = 535; `.recall_rate` = 0.456 | VERIFIED |
| 11 | 2,090 / 4,393 scope rows flagged = 47.6% | `HACKATHON.md` L122 | `summary.hits` = 2090; `summary.recall_rate` = 0.476 | VERIFIED |
| 12 | 637 campaign misses; 2,303 scope-row misses | `HACKATHON.md` L123 | `summary.campaign_level.misses` = 637; `summary.misses` = 2303 | VERIFIED |
| 13 | Median / mean lead 11 / 15.9 weeks (campaigns); 10 / 14.8 (scope rows); IQR 3–23 | `HACKATHON.md` L124 | `summary.campaign_level.lead_weeks_median` = 11, `..._mean` = 15.9; `summary.lead_weeks_median` = 10.0, `..._mean` = 14.8; `reports/nhtsa/backtest_safety_2015_2024.md` L29 IQR 3.0–23.0 | VERIFIED |
| 14 | 1,540 flag episodes; 985 confirmed; precision 0.64 | `HACKATHON.md` L128–129 | `precision.flag_episodes` = 1540; `precision.confirmed_episodes` = 985; `precision.precision_episodes` = 0.64 | VERIFIED |
| 15 | 555 false-alarm episodes | `HACKATHON.md` L130 | arithmetic on the JSON: 1540 − 985 = 555 (`python3` run 2026-10-26) | VERIFIED |
| 16 | Slice-weeks 2,409 / 1,619 / 790; precision 0.672 | `HACKATHON.md` L131 | `precision.flagged_slice_weeks`, `confirmed_slice_weeks`, `false_alarm_slice_weeks`, `precision_slice_weeks` | VERIFIED |
| 17 | Preventable window 1,379 crash / 712 fire / 882 injury (1,266 persons) / 19 deaths (29 reported) / 2,331 any | `HACKATHON.md` L137; `DEMO_SCRIPT.md` L115 | `reports/nhtsa/backtest_safety_2015_2024.md` L42–46; `reports/nhtsa/backtest_safety.json` → `headline.preventable_window_*` / `summary.preventable_window_totals_dedup` | VERIFIED |
| 18 | First-ever flag 735 / 1,172 = 62.7%, median 214 weeks, explicitly inflated | `HACKATHON.md` L139 | `reports/nhtsa/backtest_safety_2015_2024.md` L59–66 ("First-ever flag vs official recall") | VERIFIED (label is a caveat, not a production claim) |
| 19 | Tuned OOS `z2.0_q0.05_abs3_rel0.5`: 62.7% campaign recall, median 8 weeks | `HACKATHON.md` L142–144; `README.md` L282; `DEMO_SCRIPT.md` L116–117 | `reports/oos/oos_test_results.json` → `actionable_52w.campaign_level.recall_rate` = 0.627, `.lead_weeks_median` = 8, `.campaigns` = 477, `.hits` = 299 | VERIFIED (tuned config only) |
| 20 | Production `abs5` was NOT RUN on 2021–2024; its in-sample 2015–2020 score is 33.6% recall / 0.61 episode precision | `HACKATHON.md` L145–149; `README.md` L283–284; `DEMO_SCRIPT.md` L117 | `reports/oos/oos_tune_results.json` → `production` = `z2.0_q0.05_abs5_rel0.5`; `in_sample_production.actionable_52w.campaign_level.recall_rate` = 0.336, `.hits` = 159, `.campaigns` = 473; `in_sample_production.precision.precision_episodes` = 0.61; test JSON `config_id` = `z2.0_q0.05_abs3_rel0.5` | VERIFIED |
| 21 | Detector constants z ≥ 2.0, BH q ≤ 0.05, abs lift ≥ 5, relative lift ≥ 0.5 | `HACKATHON.md` L91–93 | `src/ml_runtime/anomalies.py` L53–54 (`ANOMALY_Z = 2.0`, `FDR_Q = 0.05`); `reports/oos/oos_config.json` body `production_thresholds` = {z 2.0, q 0.05, abs_lift 5, rel_lift 0.5} | VERIFIED |
| 22 | Full window / OOS split: train 2015–2020, test 2021–2024, 52-week actionable window | `HACKATHON.md` L122; `reports/oos/OOS_BACKTEST.md` L1 | `reports/oos/oos_config.json` body `train_window` / `test_window`; `oos_test_results.json` `actionable_52w.window_weeks` = 52 | VERIFIED |
| 23 | The committed OOS input was `FLAT_CMPL.zip`, 374,664,687 bytes, SHA-256 `c00707bd…` | `reports/oos/oos_config.json` body `data.flat_cmpl` | JSON fields read 2026-10-26 | VERIFIED as a record; the live file no longer matches (see §7) |
| 24 | The report re-renderer says production was NOT RUN on OOS | `reports/oos/OOS_BACKTEST.md` L39; `scripts/ai_oos_backtest.py` renderer text | Read both files; text explicitly says "NOT RUN" and "tuned config only" | VERIFIED |
| 25 | 2,258,118 FLAT_CMPL lines read and 9,198 "trusted" rows are unverifiable here | `HACKATHON.md` L158 | No raw ZIP/ingest log in checkout at audit start; text itself labels them unverifiable | UNVERIFIABLE (correctly labelled) |

## 3. Hindi/Hinglish evaluation claims

| # | Claim | Location | Source key / check | Status |
|---|---|---|---|---|
| 26 | 84 eval calls, all synthetic; every row marked `"synthetic": true` | `HACKATHON.md` L164–165; `README.md` L239; `DEMO_SCRIPT.md` L133 | `python3` loop over `eval/enhanced/calls.jsonl` (60 rows) and `eval/hindi_fresh/fresh_calls.jsonl` (24 rows): all `synthetic is True`; `reports/hindi_safety/hindi_eval.json` `sets` keys `original_60`, `fresh_24` | VERIFIED |
| 27 | 60-call set committed 2026-10-20 21:45 UTC; 24-call set 2026-10-21 07:58 UTC; lexicon 2026-10-21 08:01 UTC | `HACKATHON.md` L164–172; `reports/hindi_safety/HINDI_EVAL.md` | `git log --diff-filter=A --format='%H %aI' -- <file>` for `eval/enhanced/calls.jsonl` (`e16d267`), `eval/hindi_fresh/fresh_calls.jsonl` (`791d65d`), `src/ai_layer/hindi_safety.py` (`ce1268e`) | VERIFIED |
| 28 | Rules-only 6/24 kill-switch hits; rules + `hindi_safety` 24/24; 1 false alarm (`fr_hl_11`) | `HACKATHON.md` L186; `DEMO_SCRIPT.md` L137–138 | `reports/hindi_safety/hindi_eval.json` → `sets.original_60.rules_only.all` (6/12), `.rules_plus_hindi.all` (12/12), `sets.fresh_24.rules_only.all` (0/12), `.rules_plus_hindi.all` (12/12, false alarms 1) | VERIFIED |
| 29 | Per-language breakdown: Hindi 0/4 → 4/4; Hinglish 2/4 → 4/4; fresh Hindi 0/6 → 6/6; fresh Hinglish 0/6 → 6/6; fresh false alarm 1 | `HACKATHON.md` L177–186; `DEMO_SCRIPT.md` L136–138 | `reports/hindi_safety/HINDI_EVAL.md` tables; JSON per-language keys | VERIFIED |
| 30 | Meta-enhanced column NOT RUN; no live Meta call | `HACKATHON.md` L194–196; `DEMO_SCRIPT.md` L61, L138 | `reports/eval_modes/EVAL_MODES.md` states no `META_API_KEY`; no key in environment (`env` check); `src/ai_layer/config.py` hardcodes `"verified_against_live_api": False` | VERIFIED as NOT RUN; no accuracy number exists |
| 31 | The eval sets were "added on 2026-10-21 IST, the same day as the lexicon" | `DEMO_SCRIPT.md` L20; `reports/hindi_safety/HINDI_EVAL.md` synthetic/timeline note | UTC→IST conversion: 2026-10-20 21:45 UTC = 2026-10-21 03:15 IST; 2026-10-21 07:58 UTC = 13:28 IST; 08:01 UTC = 13:31 IST | VERIFIED |

## 4. Product / UI claims

| # | Claim | Location | Source / check | Status |
|---|---|---|---|---|
| 32 | Two shipped packs have 10 records, 2 advisories, 3 clusters each | `README.md` L10 | Isolated seed run: `FRONTLINE_DB_PATH=/tmp/skewai-fixture-count/frontline.duckdb DOMAIN_DB_PATH=/tmp/skewai-fixture-count/domains python3 -m scripts.seed_frontline_fixtures`; DuckDB `count(*)` → automotive 10/2/3, finance 10/2/3 | VERIFIED |
| 33 | Second supervisor claim returns 409 | `README.md` L72 | `src/api/routes/interactions.py` `takeover()`: `lost = bool(already and claimed_by and claimed_by != actor)`; `raise HTTPException(status_code=409, detail=body)` | VERIFIED |
| 34 | Dropped socket resume grace default 120 s | `README.md` L78 | `src/api/routes/interactions.py` `_reconnect_grace_s()` returns 120.0 default; env `FRONTLINE_WS_RECONNECT_GRACE_S` | VERIFIED |
| 35 | Alert thresholds: high ≥ 3 cases, elevated ≥ 10 cases | `HACKATHON.md` L46; `dashboard/src/ai/tools/Alerts.jsx` L39 | `src/ai_layer/alerts.py` `thresholds()` defaults `AI_ALERT_MIN_CASES=3`, `AI_ALERT_ELEVATED_CASES=10`; `_RANK`/`qualifies` gate by safety-risk level | VERIFIED |
| 36 | Alerts are a pull JSON Feed 1.1 + webhook payload preview; nothing sent externally | `HACKATHON.md` L46; `dashboard/src/ai/tools/Alerts.jsx` L1, L61 | `src/ai_layer/alerts.py` L195 "Pull feed. Nothing is pushed externally."; payload key `"delivery": "not sent"`; no external send call in the file | VERIFIED |
| 37 | Video: mp4/mov/webm, 20 MB cap, 1–10 s, duration read from container, analysis flag-gated/unverified | `HACKATHON.md` L50; `README.md` L241; `dashboard/src/ai/tools/VideoEvidence.jsx` L53 | `src/ai_layer/video_evidence.py` L33 `MIN_SECONDS = 1.0`, L60–65 `max_bytes` default 20 MiB / `max_seconds` default 10; L172–185 size/duration checks; `AI_VIDEO_ANALYSIS` gate in route | VERIFIED |
| 38 | Photo cap ≤ 8 MB | `dashboard/src/ai/EvidencePanel.jsx` L178 | `src/ai_layer/config.py` `evidence_max_bytes()` default `8 * 1024 * 1024`; `src/ai_layer/evidence.py` L114 applies it | VERIFIED |
| 39 | Meta slot/category confidence floor 0.7 | `HACKATHON.md` L63 | `src/ai_layer/config.py` `min_confidence()` default 0.7 (`META_MIN_CONFIDENCE`); `src/ai_layer/intake_enhancer.py` L234–238/L297 rejects below floor | VERIFIED |
| 40 | Seeded India scenario finishes Critical with flags `["brakes failed","escalation"]` | `DEMO_SCRIPT.md` L55–60; `dashboard/routes/DemoMode.jsx` L184 | Isolated end-to-end run recorded in `reports/demo_seed_check.txt`: seed exit 0, `severity: "Critical"`, `state: "DONE"`, flags exactly those two | VERIFIED (synthetic scenario) |
| 41 | Pack lexicon alone does **not** match the Hinglish seed sentence (`original_kill_switch: null`) | `DEMO_SCRIPT.md` L51–54; `dashboard/routes/DemoMode.jsx` L84–85, L104 | `reports/demo_seed_check.txt` records `safety_contrast(...)` output: `lang: hinglish`, `original_kill_switch: null`, `normalization_method: identity`, `final_kill_switch: null` | VERIFIED |
| 42 | Two no-key deterministic additions: `hindi_safety.py` (default on, `AI_HINDI_SAFETY=0` disables) catches the seed sentence; `fault_codes.py` captures/raises on OBD-II codes | `README.md` L245–254; `HACKATHON.md` L78 | `src/ai_layer/hindi_safety.py` `enabled()` / `maybe_apply_hindi_intake`; `docs/HINDI_SAFETY.md` L3; orchestrator hooks `maybe_raise_severity_hi`, `maybe_capture_fault_codes`, `maybe_raise_severity_dtc`; seed result above | VERIFIED |
| 43 | No live Meta API call; no Meta network call without a key; Meta paths mocked only | `README.md` L237–239, L245; `HACKATHON.md` L8–11, L78; `dashboard/routes/AiTools.jsx` L28 | `tests/frontline/ai_layer/conftest.py` installs a transport that fails on any call; no `META_API_KEY`/`MODEL_API_KEY` in env; `config.py` hardcodes `verified_against_live_api: False`; `reports/eval_modes/EVAL_MODES.md` NOT RUN | VERIFIED |
| 44 | WhatsApp intake is a **mock**; no WhatsApp Cloud API call/message | `HACKATHON.md` L49; `dashboard/src/ai/tools/WhatsAppMock.jsx` L2, L35 | `src/ai_layer/whatsapp_mock.py` / route shape; UI says "MOCK — simulated WhatsApp, no message is sent"; response `status: mock_not_sent` | VERIFIED |
| 45 | With a Meta key, WhatsApp mock may run the same optional Meta intake/severity hooks | `HACKATHON.md` L49 | WhatsApp route calls the existing orchestrator; `src/agents/orchestrator.py` hooks `maybe_enhance_intake` / `maybe_raise_severity` are key-gated | VERIFIED by code; NOT RUN live |
| 46 | Video/photo analysis never changes case category/severity | `HACKATHON.md` L50, L66; `dashboard/src/ai/EvidencePanel.jsx` L88 | `src/ai_layer/evidence.py` only adds flags; route advisory-only; UI text "Advisory only" | VERIFIED by code/tests; live model behaviour NOT RUN |
| 47 | Mileage is accepted but not used (no mileage field in NHTSA data) | `HACKATHON.md` L45 | `src/ai_layer/vehicle_risk.py` L19, L125–127: `"mileage_used": False`, note says warehouse has no mileage field | VERIFIED |
| 48 | Every AI surface carries a Meta/Deterministic tag | `HACKATHON.md` L73–74 | `dashboard/src/ai/MetaTag.jsx`; panels import/use `MetaTag` (VehicleRisk, EvidencePanel, Alerts, SafetyRiskBoard, DemoMode) | PARTIAL — tag component and usages verified; not every historical AI surface was enumerated |
| 49 | One-command judge setup `bash scripts/judge_setup.sh` | `HACKATHON.md` L26; `DEMO_SCRIPT.md` L13 | Script exists and its seed steps were run individually (`reports/demo_seed_check.txt`); the full script (venv + npm build + serve) was **not** run end-to-end | NOT RUN |
| 50 | `python -m scripts.ai_meta_smoke` makes one small live call each to text/vision/SAM with a key, skips without a key | `HACKATHON.md` L227; `README.md` L273 | Script exists; no key on this box; script was **not** run | NOT RUN (correctly labelled) |
| 51 | Single container, not deployed | `HACKATHON.md` L27 | `docker-compose.hackathon.yml` has one service `skewai`; no deployment pipeline run | VERIFIED (not deployed) |

## 5. Dashboard claims

| # | Claim | Location | Evidence | Status |
|---|---|---|---|---|
| 52 | `#ai-tools` numbers come from the active warehouse; offline seed may be synthetic; demo counts are not real-world evidence | `dashboard/routes/AiTools.jsx` L28; `README.md` L241 | UI banner text; seed commands in `scripts/judge_setup.sh` use `seed_frontline_fixtures` + `ai_demo_seed`, not a full public dump; local warehouse is 11,924 records / 2 advisories, mostly `synthetic_scale` | VERIFIED |
| 53 | Demo seed transcript/photo are labelled SYNTHETIC | `dashboard/routes/DemoMode.jsx` L156–160, L177; `DEMO_SCRIPT.md` L60, L67–68 | `reports/demo_seed_check.txt` label `"synthetic demo contact (India, Hinglish + Hindi)"`; seed photo is code-generated PNG | VERIFIED |
| 54 | The "Rules only" panel is labelled "Pack lexicon only" and explicitly "not the full no-key pipeline" | `dashboard/routes/DemoMode.jsx` L84–85, L104 | Current text; `reports/demo_seed_check.txt` shows the full pipeline catches the sentence via `hindi_safety.py` | CORRECTED |
| 55 | Seeded kill-switch produces Critical/P1 escalation and the "do not drive" script; no claim that a specialist was paged | `dashboard/routes/DemoMode.jsx` L184 | `reports/demo_seed_check.txt` flags/severity; `src/agents/orchestrator.py` `_complete_safety_escalation` sets `severity = "Critical"`, `priority = 1`, state `SAFETY_ESCALATION`, emits the script and a supervisor whisper, and calls `alert_safety_escalation`. That alert posts only to an optional Slack-shaped `ALERT_WEBHOOK_URL`; it does not create a handoff queue row and no dedicated paging system exists. The demo run had no webhook configured, so nothing was sent externally. | CORRECTED |
| 56 | Backtest hero is the production detector, in-sample, 5 makes; 1,379/712/882 preventable-window counts | `dashboard/src/ai/SafetyRiskBoard.jsx` L13–18 | `src/ai_layer/safety_board.py` `backtest_headline()` reads `reports/nhtsa/backtest_safety.json`; `headline.campaign_level.hits/campaigns` = 535/1172; `headline.preventable_window_*` = 1379/712/882; hero = `26V582000|2024|FORD|MUSTANG MACH E|ELECTRICAL SYSTEM`, lead 52 | VERIFIED |
| 57 | Largest window text: FORD ELECTRICAL SYSTEM, 2025-W37, 52 weeks, recall 26V582000 | `dashboard/src/ai/SafetyRiskBoard.jsx` L21 | `reports/nhtsa/backtest_safety_2015_2024.md` L48–50; JSON `headline.hero` | VERIFIED |
| 58 | Alerts payload is a preview, not sent | `dashboard/src/ai/tools/Alerts.jsx` L61 | See row 36 | VERIFIED |
| 59 | Video UI says 1–10 s (aim 5–10), analysis "unverified" | `dashboard/src/ai/tools/VideoEvidence.jsx` L53, L86 | Code constants above; button label `Analyze (unverified)` only when analysis enabled | VERIFIED |
| 60 | MetaTag says "claims are validated before display; no live Meta API call has been verified" | `dashboard/src/ai/MetaTag.jsx` L7 | Current title text; matches no-live-call status | CORRECTED (prior title claimed "verified before display") |

## 6. Corrections made in this cleanup

The following prior claims were false or misleading and were changed. Only
documentation/UI text, dependency declarations and the demo-seed path jail were
touched; no product thresholds, regexes, lexicons, tests or data were changed.

| # | Where | Prior claim / problem | Current text / fix |
|---|---|---|---|
| C1 | `README.md` L241 | "5–10 s video evidence" | "1–10 s video evidence (the UI suggests 5–10 s; analysis is flag-gated and unverified)". Code: `MIN_SECONDS = 1.0`, `max_seconds()` default 10. |
| C2 | `README.md` L243–253 | "With no key, nothing changes" | No Meta network call is made, but the deterministic `hindi_safety.py` layer runs by default and can only add a kill-switch hit/slot. Disable with `AI_HINDI_SAFETY=0`. |
| C3 | `README.md` L21 | "Python 3.11+" | "Python 3.12+ (CI, Dockerfiles and `requirements-lock.txt` target 3.12)". CI line 40 and Dockerfiles use 3.12. |
| C4 | `README.md` L237–239 | No evidence-status banner | Added: no live Meta API call; Meta paths mocked/no-key fallback; 84 synthetic eval calls. |
| C5 | `HACKATHON.md` L78 | "output is identical to `main`" with no key | No Meta network call and Meta features return deterministic results, but `hindi_safety.py` and `fault_codes.py` are deliberate no-key additions. |
| C6 | `HACKATHON.md` L215–217 | "Nothing in the existing rules, regex, gazetteers, lexicons, tests or data was modified." | The 2026-10-26 cleanup changed docs, pinned `pyarrow`, fixed the demo seed script's path jail and corrected a report-renderer sentence; product wiring is unchanged. |
| C7 | `HACKATHON.md` L81 | "Brief claims must cite real IDs" (ambiguous on synthetic demo) | "warehouse record/advisory IDs"; demo photos labelled synthetic; backtest raw ZIPs not in checkout, so the recorded run cannot be re-executed here (status in `reports/CLAIMS_AUDIT.md`). |
| C8 | `HACKATHON.md` L227 | "To verify in about 30 seconds with a key" | Removed the unmeasured 30-second claim; smoke script is **NOT RUN** (no key). |
| C9 | `HACKATHON.md` L139 / L142–149 | Two different 62.7% results (first-ever vs tuned OOS) were easy to conflate; production vs tuned was unclear | Added explicit labels: first-ever = inflated full-window upper bound; tuned OOS = `abs3`, 62.7%, median 8 weeks; production `abs5` OOS = **NOT RUN**; production in-sample 2015–2020 = 33.6%, precision 0.61. |
| C10 | `HACKATHON.md` §4.2 | Hindi dates/results lacked a synthetic/timeline note | Added 84-call synthetic note, commit hashes/dates and the rules-only vs rules+hindi table (6/24 → 24/24, 1 false alarm). |
| C11 | `HACKATHON.md` L236 | `pyarrow` was undeclared; ingest tests failed with `ModuleNotFoundError` | Declared `pyarrow>=22.0,<25.0` in `requirements.txt` and `requirements-docker.txt`; pinned `pyarrow==22.0.0` in `requirements-lock.txt`. |
| C12 | `HACKATHON.md` L236 | `scripts/seed_issue_demo.py` failed with `path outside allow-root jail` | Fixed the script by temporarily adding its generated temp directory to `FRONTLINE_INGEST_ROOT`, then restoring it. Small end-to-end seed run now exits 0. |
| C13 | `DEMO_SCRIPT.md` L55–60 | Prior text said the deterministic path opens the case at **Medium** because the English lexicon misses the Hinglish phrase | Corrected: the **pack lexicon alone** returns `original_kill_switch: null`, but the full no-key pipeline (with `hindi_safety.py`) opens the seeded case at **Critical** with `["brakes failed","escalation"]`. Verified in `reports/demo_seed_check.txt`. |
| C14 | `DEMO_SCRIPT.md` L50–66 | "Meta AI enhanced" was presented as the intended Critical path; deterministic Hindi layer was omitted | Added the pack-lexicon-only vs full no-key pipeline vs Meta-enhanced distinction; Meta is **not required** for this example and is **NOT RUN LIVE**. |
| C15 | `DEMO_SCRIPT.md` L128–132 | "without a key the system behaves exactly as before" | Corrected: Meta features return deterministic results; the no-key additions are `hindi_safety.py` and `fault_codes.py`. |
| C16 | `DEMO_SCRIPT.md` L70 | Claimed on-screen `Muse Spark 1.3` tags without noting the no-key mode | Tags are now labelled "when a key is set (intended, NOT RUN LIVE)"; with no key the tags read `Deterministic`. |
| C17 | `DEMO_SCRIPT.md` title/L3 | "2–3 minute demo" implied a measured duration; setup said "30 seconds" | Removed measured-duration claims; added "planned script cues, not measured durations; not timed end to end". |
| C18 | `DEMO_SCRIPT.md` L93–96 | Safety-risk chip used "real records" language in a synthetic demo | Says the warehouse is the synthetic seed, so those counts are synthetic demo counts. |
| C19 | `dashboard/routes/DemoMode.jsx` L84–85, L104 | "Rules only" panel implied the live no-key pipeline; it isolates the English pack lexicon | Renamed "Pack lexicon only"; added "not the full no-key pipeline" and a note that `hindi_safety.py` catches the sentence and opens Critical. |
| C20 | `dashboard/routes/DemoMode.jsx` L184 | "safety specialist paged" overstated the path: the kill-switch sets Critical/P1, emits the script, a supervisor whisper and an optional Slack-shaped `ALERT_WEBHOOK_URL` alert, but creates no handoff queue row and no dedicated paging system. | "Critical/P1 safety escalation and 'do not drive' script". The separate manual "page a human specialist" control queues a handoff; it is not fired by the seeded kill-switch. |
| C21 | `dashboard/routes/AiTools.jsx` L28 | No synthetic-count/no-live-Meta banner | Added: active warehouse, synthetic seed warning, no live Meta call. |
| C22 | `dashboard/src/ai/MetaTag.jsx` L7 | Title said "verified before display" | Title now says claims are validated and **no live Meta API call has been verified**. |
| C23 | `reports/oos/OOS_BACKTEST.md` L39 / `scripts/ai_oos_backtest.py` renderer | Renderer could imply the 62.7% was production | Renderer now says production `abs5` was **NOT RUN** on the test window and the OOS column is the tuned config only. |
| C24 | `reports/hindi_safety/HINDI_EVAL.md` | No synthetic/timeline note | Added the 84-call synthetic note and the three pre-event commit timestamps. |
| C25 | `reports/demo_seed_check.txt` | No reproducible evidence for the seeded Critical claim | Added exact commands/results: seed exits 0, severity Critical, flags `["brakes failed","escalation"]`; pack lexicon returns `null`. |

## 7. NOT RUN / UNVERIFIABLE (as of 2026-10-26)

| Item | Status | Why / what would unblock it |
|---|---|---|
| Baseline strategies B0–B3 (`reports/oos/BASELINES.md`) | **NOT RUN** | Raw NHTSA ZIPs and the full 219,510-record warehouse were absent at audit start; `scripts/oos_baselines.py` does not exist. Fixtures were not used because they are a different corpus. Exact unblock commands are in `reports/oos/BASELINES.md`. |
| Exact re-execution of the committed backtest | **NOT RUN** | The committed run's input hash is `c00707bd…` (374,664,687 bytes). The live file downloaded 2026-10-26 is 375,063,317 bytes, SHA-256 `91ff80bd…`, so it is a different snapshot. A fresh run would not be byte-identical. |
| Full `scripts/judge_setup.sh` end-to-end | **NOT RUN** | Individual seed steps were run in an isolated DB; the full script (venv + npm build + server) was not. |
| `python -m scripts.ai_meta_smoke` | **NOT RUN** | No `META_API_KEY`/`MODEL_API_KEY` on this box; invoking it would skip, not make a call. |
| Any live Meta text/vision/SAM/WhatsApp Cloud call | **NOT RUN** | No key; every Meta path is mocked or deterministic. `config.py` hardcodes `verified_against_live_api: False`. |
| `META_API_KEY=… python -m eval.enhanced.run_eval` (Meta column) | **NOT RUN** | No key. Rules-only column is run; Meta column is explicitly "not run". |
| Full test suite at current HEAD | **RUN; NOT GREEN** | `4 failed, 1711 passed, 1 skipped, 1 deselected` in 16:02 on Python 3.14.7 with pyarrow 22.0.0. Exact command, all four failures and their individual reruns are in `reports/TEST_RESULTS.md`; the failure log is `reports/tests_after_cleanup.txt`. The suite must not be described as passing. |
| Four failing tests | **NOT FIXED** | Each fails alone too, so they are not order-dependent. F1 is a correction-semantics mismatch; F2 is a disabled-agent guard bypassed when the ledger call raises; F3 is a stale assertion (helper returns text, not a boolean); F4 reads the first WebSocket frame but the server sends `ready` first. Fixing any of them would change product behavior or test expectations, so they are reported, not patched. |
| `test_rebuild_clusters_assigns_records_beyond_5000` | **NOT RUN TO COMPLETION** | Deselected from the main suite because its pure-Python O(n²) silhouette over 5,005×512 vectors did not finish after ~14 minutes (aborted, `EXIT:143`). Per `reports/slow_test_check.txt`, a dedicated capped run is recorded in `reports/slow_test_dedicated.txt`; a timeout is not a pass. |
| 2,258,118 FLAT_CMPL lines read / 9,198 trusted rows | **UNVERIFIABLE** | No raw ZIP or ingest log from that run is committed. The text says so and does not rely on them for the headline. |
| Full 219,510-record warehouse in this checkout | **ABSENT** | Local `data/domains/automotive_nhtsa.duckdb` has 11,924 records / 2 advisories, mostly `synthetic_scale`; the recorded run used 150,768 records / 1,861 advisories in the OOS window. Do not treat local counts as the backtest corpus. |
| `git` remote push / history rewrite | **NOT DONE** | Out of scope by instruction; all four cleanup commits are local only, and no existing commit was rewritten. |

## 8. Number cross-check (source of truth)

| Number | Source key / file | Verified value |
|---|---|---|
| Complaints | `reports/nhtsa/backtest_safety.json` → `precision.records` | 219,510 |
| Recall scope rows | `.summary.recalls_scored` | 4,393 |
| Campaigns | `.summary.campaign_level.campaigns` | 1,172 |
| Campaign hits | `.summary.campaign_level.hits` | 535 |
| Campaign recall | `.summary.campaign_level.recall_rate` | 0.456 |
| Scope hits | `.summary.hits` | 2,090 |
| Scope recall | `.summary.recall_rate` | 0.476 |
| Campaign median / mean lead | `.summary.campaign_level.lead_weeks_median` / `_mean` | 11 / 15.9 |
| Episodes / confirmed / precision | `.precision.flag_episodes` / `confirmed_episodes` / `precision_episodes` | 1,540 / 985 / 0.64 |
| Slice-weeks / confirmed / false / precision | `.precision.flagged_slice_weeks` / `confirmed_slice_weeks` / `false_alarm_slice_weeks` / `precision_slice_weeks` | 2,409 / 1,619 / 790 / 0.672 |
| Preventable crash / fire / injury / deaths / any | `.summary.preventable_window_totals_dedup` and `reports/nhtsa/backtest_safety_2015_2024.md` L42–46 | 1,379 / 712 / 882 / 19 / 2,331 |
| Persons injured / deaths reported | report L44–45 | 1,266 / 29 |
| First-ever campaign hits / rate / median | `reports/nhtsa/backtest_safety_2015_2024.md` L59–66 | 735 / 1,172 (62.7%) / 214 |
| Tuned OOS campaign recall / median | `reports/oos/oos_test_results.json` → `actionable_52w.campaign_level` | 0.627 / 8 |
| Tuned OOS scope recall / precision | same JSON → `actionable_52w.recall_rate` / `precision.precision_episodes` | 0.614 / 0.598 |
| Production in-sample recall / precision | `reports/oos/oos_tune_results.json` → `in_sample_production` | 0.336 / 0.61 |
| Hindi rules-only hits | `reports/hindi_safety/hindi_eval.json` → sets.*.rules_only.all | 6 / 24 |
| Hindi rules+hindi hits | same → `.rules_plus_hindi.all` | 24 / 24 (1 false alarm) |

## 9. Audit conclusion

- The headline NHTSA numbers are internally consistent across the JSON, the
  Markdown report, `README.md`, `HACKATHON.md`, `DEMO_SCRIPT.md` and the
  dashboard hero.
- The largest correction was the demo story: the English pack lexicon alone
  misses the Hinglish sentence, but the **full no-key pipeline** catches it via
  `hindi_safety.py` and the seeded case is **Critical**, not Medium. The UI now
  isolates and labels the pack-lexicon-only panel.
- The tuned OOS 62.7% is no longer presented as production performance.
  Production `abs5` has **no OOS number**; its in-sample 2015–2020 score is
  33.6% recall / 0.61 episode precision.
- Baseline strategies are **NOT RUN**, not zero. The raw inputs were absent at
  audit start; the live `FLAT_CMPL.zip` has since changed, so even a fresh run
  would not be byte-identical to the committed one.
- The test suite is **not all green**. At the pre-event head it is
  `4 failed, 1711 passed, 1 skipped, 1 deselected` in 16:02; all four failures
  reproduce individually and were left unmodified. The very slow cluster test
  is not counted as a pass. Details: `reports/TEST_RESULTS.md`.
