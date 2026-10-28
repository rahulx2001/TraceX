# TraceX submission review — 28 October 2026

**Historical review snapshot.** The subsequent repairs and current verification
are in [HACKATHON_FIX_RESULTS_2026-10-28.md](HACKATHON_FIX_RESULTS_2026-10-28.md).

**Verdict: strong fit for the Indie developer track, but not ready to submit as-is.**

The automotive problem fits **Build for Your World**. Evidence-based component investigation also fits **Push the Frontier**, provided the demo proves what Meta adds. The existing intake, safety rules, human takeover, complaint warehouse, and audit trail give the project a substantial foundation.

This is a review of the local working source and the public repository, not a certification of eligibility or production readiness. No live model call, deployment, message, or submission was made during this review. Credentials were not printed. Application source was not changed.

## Rules that were actually checked

The public [event page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) confirms:

- Each project enters **one** track. The owner selected **Indie developer** during this review.
- Indie projects are judged on creativity, technical ambition, and whether they work.
- Both advertised themes are relevant to TraceX.
- The advertised submission deadline is **4 November 2026, 9 PM Eastern** — **5 November, 7:30 AM IST** if the portal uses Eastern standard time on that date. Verify the portal's displayed deadline before submitting.

The owner says the official rules have been accepted. The public `/details` page returned a loading shell without the participant-only rules. The actual clauses governing reused code, eligible development dates, required Meta usage, video length, deliverables, and intellectual property were **not available for independent verification**. The application-selection criteria on the public page are not the full project-submission rules. This review does not infer a ban on existing projects or a mandatory three-minute video from that page.

## Changes needed before submission

| Priority | Finding | Evidence | Required result |
|---|---|---|---|
| Blocking | No recorded, verified live Meta workflow | `reports/hackathon/meta_live_smoke.json` is absent; `HACKATHON.md` and `DEMO_SCRIPT.md` label Meta paths unrun. A Meta key is configured locally, but a configured key is not execution evidence. | Show one useful, successful Meta step in the actual application, with the model, endpoint, output, accepted/rejected result, fallback status, and audit trail recorded. |
| Blocking | Public submission snapshot omits the local fixes | Public `rahulx2001/TraceX` has only commit `de3c483946`, dated 27 October. The working tree has many uncommitted changes. `ELIGIBLE_WORK.md`, `LICENSE`, `NOTICE`, and `src/ai_layer/budget.py` are untracked. GitHub reports no detected license for the public snapshot. | After verification, publish the intended changes to **TraceX** and test the exact submitted revision. |
| Blocking | Reused foundation and event contributions cannot be verified from the published history | `HACKATHON.md` and `ELIGIBLE_WORK.md` say the Meta adapter and major functionality existed on 20–21 October. The current public repo contains one initial commit and does not contain that earlier history or commit IDs. | Check the accepted rules' reuse clause. Document the actual starting snapshot and dated event contributions, with provenance for the reused foundation. Preserve truthful dates. |
| High | Tests are not all passing | Independent clean-source checks reproduce failures in video analysis and medical-pack lint. Full-suite results are recorded below. | Resolve each genuine failure or documented contract mismatch, then obtain a passing run on the supported Python 3.12 environment. |
| High | Documentation enters two tracks | `README.md:6` says the project is competing in both tracks; `HACKATHON.md` repeats dual-track framing. | State **Indie developer track** consistently in the README, hackathon document, video, and submission form. |
| High | Smoke command cannot create the evidence its status check expects | `src/ai_layer/config.py` reads a top-level `ok` and `api_host` from `reports/hackathon/meta_live_smoke.json`. `scripts/ai_meta_smoke.py` only prints `all_ok` and nests the host under `status`; it has no artifact-writing option. Simply redirecting its output will not satisfy the status contract. | Have the live workflow produce the agreed artifact schema. Make verification specific to the model/feature and endpoint tested. Do not hand-edit an unrun success marker. |
| High | No completed demo video is available in the inspected repo | Only a planned storyboard exists. `ELIGIBLE_WORK.md` explicitly says the video is unfinished. Browser and complete judge-setup verification are also missing. | Record and time a concise demo. Confirm the actual portal's format and length requirement, and test the exact judge steps before recording. |

`origin` currently points to `rahulx2001/SkewAi.git`; the named `tracex` remote points to `rahulx2001/TraceX.git`. A routine push to `origin` would publish to a different project. No remotes or published history were changed during this review.

## Confirmed implementation and documentation issues

1. **Invalid optional domain packs:** `domains/medical_maude/pack.yaml:94` contains `pack_# TraceX Medical Devices (MAUDE) Domain Pack`, followed by a new `id` block. `domains/consumer_cpsc/pack.yaml:94` has the equivalent malformed consumer-products line. YAML parsing fails in both. They are outside the automotive demo, but their shipped pack contracts fail and prevent a completely passing suite.
2. **Video-analysis contract mismatch:** `src/ai_layer/budget.py` deliberately rejects unpriced video media. The flagged analysis path in `src/ai_layer/video_evidence.py` sends a video data URL through chat and therefore fails, while `test_flagged_analysis_with_fake_meta` still expects success. Keep the budget guard; decide whether to explicitly disable this undocumented feature or implement and price a supported video path. Do not advertise video analysis as working.
3. **Local configuration affects test behavior:** the first run loaded the project's `.env` through the new `src/config.py` behavior. Its auth/session settings affected tests. That run also used an explicit AI-off switch that several direct client tests did not override. Its raw failure count is not a clean code-quality metric. The subsequent run uses a source copy without `.env`, empty provider keys, and temporary databases/counters. Ensure the documented local test command remains safe and reproducible when a developer has a real `.env`.
4. **Model attribution is overstated:** `HACKATHON.md` says Muse Spark transcribes calls. Audio recognition actually runs through browser Web Speech; Meta receives text for normalization. Credit Meta for the demonstrated text processing.
5. **SAM output is overstated:** `parse_sam_output` stores boxes and a `has_mask` indicator. `EvidencePanel.jsx` draws percentage-positioned boxes. It does not render polygon masks. Describe boxes accurately unless masks are implemented and verified.
6. **Model and partner listings exceed demonstrated support:** Muse Wonder is named without a demonstrated implementation. Baseten/Modal/Fireworks are described as compatible, but no live partner run was found, and the budget module accepts only explicitly priced model IDs. List actual tested models/providers and label planned support separately.
7. **Proof of model value is weak in the current storyboard:** the headline Hindi brake emergency already succeeds through the pre-event deterministic Hindi layer. Demonstrate a Meta step that improves an actual task beyond the deterministic output, such as extracting a difficult complaint or selecting source-supported evidence. Keep the local emergency safety floor.
8. **Judge supervisor access needs verification:** setup prints a supervisor token for HTTP headers, while the browser sign-in documented for judges uses an operator API key, which is a service principal. A printed token is not proof that the supervisor UI steps can be completed. Verify takeover, release, and review using the real browser login flow.

## Claims that should remain qualified

- **45.6% of campaigns and 11-week median:** the reported historical, in-sample component-grain detector result. It is deterministic and is not evidence of Meta improving prediction.
- **62.7% and 8-week median:** a separate tuned configuration's out-of-sample result. Do not label it the shipped production detector's result.
- **Production `abs5` later-window performance:** unrun according to the project reports.
- **84 Hindi/Hinglish examples:** synthetic tests. They are not customer recordings or field accuracy.
- **300-label defect experiment:** the inspected CSV contains 300 rows and **zero filled human labels**. No human-label accuracy is established.
- **Early-warning impact:** make/component matches do not establish detection of the same physical defect, nor accidents prevented or lives saved.
- **WhatsApp:** a mock intake endpoint. It does not send WhatsApp messages.
- **Ledger:** describe the implemented hash chain as tamper-evident and distinguish it from the separately signed evidence export. Avoid suggesting a mutable database is absolutely immutable or that engineering controls constitute SOC 2 certification.

The existing caveats in `reports/CLAIMS_AUDIT.md` and `HACKATHON.md` are useful. Make the short pitch consistent with them.

## Verification performed

| Check | Result |
|---|---|
| Installed Python dependencies, `pip check` | Passed |
| Dashboard production build | Passed; bundle-size and ineffective-dynamic-import warnings only |
| Dashboard theme checks | Passed |
| Dashboard QA-label checks | Passed |
| Isolated dashboard build and HTTP `/ui/` test | Passed after building the snapshot; the initial 404 was due to absent generated assets. |
| Clean-source backend suite | Completed: **1,716 passed, 10 failed, 1 skipped**, in 502.30 seconds, with a 30-second per-test timeout. Failure breakdown follows. |
| Offline automotive/finance evaluation | Passed: automotive 12/12 gates, finance 11/11 gates. Missing semantic artifacts triggered fallback, so this does not verify ONNX retrieval. |
| Fixture build, simulator, synthetic India scenario | Passed: 15 simulated contacts created 15 cases and reported 10 investigation openings. The subsequent India scenario reached Critical with `brakes failed`/`escalation` flags and linked to `inv_0001`. |
| In-process HTTP smoke with test credentials | Passed: health 200, unauthenticated AI status 401, authenticated AI status/cases/grounded brief 200. The brief returned two deterministic claims. |
| Targeted clean-source failure reproduction | Video-analysis test and medical-pack lint test both fail |
| Large-cluster diagnostic rerun | Passed in **56.92 seconds** with a 90-second timeout, including assignment of all 5,005 records. The 30-second suite cap remains unmet in this environment. |
| Full documented judge setup | Not verified: dependency installation and the complete serving/login flow were not run |
| Docker build/run | Not verified: Docker CLI is unavailable in this environment |
| Browser voice, photo overlay, takeover, recording | Not verified: no browser automation surface was available |
| Live Meta/API partner behavior | Not run in this review; no API spend |

Tests use the installed Python **3.14.7** interpreter; project CI and Docker target **3.12**. The clean review snapshot includes current local fixes and tracked fixtures, excludes `.env` and runtime databases, and reuses installed dashboard dependencies. It is not a newly installed dependency environment. Invalid YAML and the video/budget mismatch reproduce independently of the first run's local configuration.

The original, interrupted test run reported **743 passed, 32 failed** before stopping. It is recorded for transparency, not used as the final clean-suite count.

### Clean-suite failure breakdown

| Count | Failure | Interpretation |
|---|---|---|
| 1 | `test_video_evidence.py::test_flagged_analysis_with_fake_meta` | Video request rejected by the new unpriced-media budget guard; implementation/test contract mismatch. |
| 2 | `test_features_56.py::test_42_third_fourth_verticals`, `test_pipeline_features.py::test_sandbox_and_pack_builder_and_marketplace` | Invalid medical and consumer YAML respectively; confirmed source defects. |
| 1 | `test_cluster_builds.py::test_rebuild_clusters_assigns_records_beyond_5000` | Large fixture/rebuild exceeded the documented 30-second test cap. **Focused diagnostic rerun passed in 56.92 seconds with a 90-second cap**, including all 5,005 assignments. This establishes a timeout issue here, not incorrect assignments. |
| 1 | `test_dashboard_ops_actions.py::test_command_center_deep_links` | Test asserts literal `fetchOpenP1Cases` occurs in `CommandCenter.jsx`; it does not. Contract drift needs review; this assertion alone does not prove a browser navigation bug. |
| 1 | `test_hygiene.py::test_ui_index_serves_html_body` | The isolated snapshot had no generated `dashboard/dist` at initial app import. **Focused rerun passed after `npm run build`**, confirming this failure was a build prerequisite. |
| 4 | One pinned SLM probe and three SLM-runtime tests | Snapshot excludes gitignored `model.onnx` and `tokenizer.json`; logs explicitly report missing semantic artifacts and fallback. Provision verified artifacts or make the test environment self-contained. This does not establish an automotive deterministic-path failure. |

Do not report all ten as independent production bugs. Conversely, a successful dashboard build and offline evaluation do not establish a completely passing backend suite. CI should provide the build/model prerequisites and run on Python 3.12 before the final submitted revision is declared verified.

## Suggested submission story

> TraceX helps automotive quality engineers turn scattered customer complaints into an auditable fault investigation. Meta processes a difficult multilingual complaint and selects source-supported evidence, while local safety rules preserve urgent escalation and a human reviews the result.

Use the exact Meta behavior that succeeds in the live workflow. Show:

1. One concrete owner complaint and the problem an engineer faces.
2. The Meta request/result and the useful accepted output.
3. The cited source evidence, deterministic safety decision, and human review.
4. The audit record and a short statement identifying reused foundation versus event work.

Use historical backtest results as context with their caveats. Keep the demo focused enough that a judge can see the complete working flow. The strongest next action is to prove one useful Meta workflow and make its judge path reliable, rather than adding more optional features.
