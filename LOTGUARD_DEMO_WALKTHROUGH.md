# LotGuard EPS B14 walkthrough

Open **http://127.0.0.1:8770/ui/#cases** and select **LOT ALERT · STEERING**, or click **Load LotGuard demo**. The isolated server uses separate demo warehouses. No access key is needed for this local fictional walkthrough.

All records are fictional; your saved changes are preserved. Email delivery, owner responses, workshop bookings and findings are simulated. The prepared campaign records scripted reviewer decisions; AI does not approve it. The server enables configured AI providers from the local `.env`, plus background jobs. The initial canonical seed remains offline for reproducibility. The local AI-layer reservation allowance was increased from $30 to $50 with the owner's approval; prior reservations remain in the same ledger.

| Show | What the audience can inspect |
| --- | --- |
| Cases → LOT ALERT | Eleven actual cases created through normal simulated intake and CaseAgent, not case-table fixture inserts. One detailed 2021 Honda City hero, ten thin 2021–22 siblings. |
| Known now | Stored steering complaint, linked investigation, mock advisory matched through Sentinel, and actual parent records. High review priority inherits from two scoped severe reports; expand the inner explanation to see the caller's own Medium severity. |
| Still needed | Green photo, codes, assessment and follow-up indicators, backed by saved records. Missing/unavailable evidence on other cases retains normal request/retry actions. |
| Photos & scan codes | A real stored PNG labelled fictional: EPS batch-label illustration. C0035 captured from the original customer turn, with its ABS/wheel-speed meaning and category mismatch visible. The image does not establish a crack. |
| Follow-up draft | Collected fictional email destination and consent. Click **Send demo follow-up**; the persisted outbox and audit show simulated delivery. Repeating the same draft does not create another send. |
| Lot risk | 213 reviewed installation records; 11 inbound owners; 202 initially silent owners warned in simulation. Separate previous-week source history gives the complaint ramp **1 → 3 → 6 → 11/week**. This measures reports, not confirmed failure incidence. |
| Stored source investigation | Follow **Read the stored source investigation and review its draft**. The prepared run reads the real saved hero turns, their IDs/hashes and reviewed vehicle association. Review installation, owner history and workshop records through existing investigation tools. The prepared run is labelled manual; new AI-assisted drafts use the configured provider and remain subject to review. |
| Owner outreach | Approved English/Hindi notice with Honda City/B14 scope, symptoms and YES inspection CTA. **68** opened/routed, **41** appointments. Select **EPS-CITY-011** to see YES → slot → saved confirmation and its complete simulated delivery/open/book/inspect/resolve history. A new YES response can be scheduled through the existing appointment form. |
| Workshop & repair | Nine fictional EPS housing cracks found after warnings. Each has a reviewed exact replacement specification, work order, verification, symptom-free follow-up and reviewer resolution. Supplier B14 containment remains open; the campaign does not declare every other vehicle safe. |
| Evidence & close-out | Original installation document text/hash, append-only campaign actions, inspection/repair references, investigation source provenance, and downloadable campaign JSON. The nine source vehicles are linked directly from the case result. |
| Published evaluation | **246/300 = 82.0% accuracy; macro-F1 0.514 over 46 labels**. Challenger **238/300 = 79.3%**, rejected. Frozen artifact hashes and evaluation replay gate these displays. All 43 Round 4 AI-assisted adjudications were human-countersigned by Rahul Kumar Singh on 3 November 2026; reviewer blinding remains unconfirmed. This measures historical classification. |

The result metric `vehicles_warned_before_failure = 9` counts fictional vehicles with a simulated warning before a recorded finding, verified repair and resolution, with no earlier failure reported. The demo does not measure accidents prevented or recalls avoided. Its useful capability is tracing an emerging complaint to installed parts, reaching owners before they call, and recording a specific inspection/repair decision with evidence.

Suggested stage narration:

> “One owner's bad morning links eleven current-week reports. We trace the installed batch and warn the 202 owners who never called. In this fictional walkthrough, nine vehicles are inspected and fixed before reported failure. The result is backed by owner, workshop and repair records. Our published historical classifier evaluation is 82.0% accuracy and macro-F1 0.514; the challenger was tested and rejected.”

Start again without deleting saved work:

```sh
.venv-hackathon/bin/python scripts/run_lotguard_demo.py
```

The server writes stable case/campaign links to `data/hackathon/eps-b14/scenario.json`, uses `data/hackathon/eps-b14/ops.duckdb` and `data/hackathon/eps-b14/domains/`, and stores the synthetic PNG under `data/evidence/eps-b14/`. The existing app on port 8000 uses its own data.

For the original offline replay, run `scripts/run_lotguard_demo.py --offline` with the same virtual environment. Browser microphone capture and browser speech replies remain available. Server speech requires a separate `DEEPGRAM_API_KEY` in the local `.env`; the launcher enables Deepgram automatically when that credential is present. The configured Baseten backend supports text and vision; SAM segmentation and image generation require the official Meta backend and are not supplied by Baseten.

Verification commands:

```sh
.venv-hackathon/bin/python -m pytest tests/frontline/ai_layer/test_eps_demo.py tests/frontline/ai_layer/test_safety_campaigns.py tests/frontline/test_case_completeness.py
cd dashboard
npm run build
npm run test:signin
```

The browser suite includes the canonical seed → hero → evidence → simulated follow-up → Hindi outreach → workshop confirmation → packet export. It uses isolated test data and no model/provider calls.

Saved demo captures: [green case readiness](reports/hackathon/lotguard_demo/lotguard-hero-readiness.png), [lot results](reports/hackathon/lotguard_demo/lotguard-risk-results.png), [stored photo and codes](reports/hackathon/lotguard_demo/lotguard-hero-evidence.png), and [workshop confirmation](reports/hackathon/lotguard_demo/lotguard-outreach-confirmation.png).

After enabling providers, [the live service check](reports/hackathon/lotguard_demo/services_live_check.json) records successful Hindi normalization and real vision analysis of the fictional label. The model reports no visible defect in that illustration. [The report screen with AI on](reports/hackathon/lotguard_demo/lotguard-ai-enabled.png) shows the enabled runtime. These checks do not establish microphone/audio quality or live owner delivery.
