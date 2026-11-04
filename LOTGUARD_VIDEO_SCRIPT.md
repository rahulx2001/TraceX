# LotGuard: three-minute recording script

Use this for the current TraceX/LotGuard build. The participant guide requires a three-minute demo and disclosure of reused code. This script has **307 spoken words**, leaving time for clicks and pauses. The timings are editing targets, not measured system response times.

## Open these tabs before recording

| Tab | Open this |
| --- | --- |
| Report | [Voice or typed report](http://127.0.0.1:8770/ui/#call) |
| Case and result | [LOT ALERT hero case](http://127.0.0.1:8770/ui/#cases?id=case_01m6gz1hgzryh8fjqffkj7zn0t) |
| Original report → investigation | [Same hero's stored source](http://127.0.0.1:8770/ui/#safety-campaigns?campaign=sc_01m6gz1kvs894w47sv2rjzefbj&tab=investigate&vehicle=EPS-CITY-000&interaction=int_01m6gz1efxd9bvr87znfw4bfn7) |
| Reviewed batch | [Installation evidence](http://127.0.0.1:8770/ui/#safety-campaigns?campaign=sc_01m6gz1kvs894w47sv2rjzefbj&tab=trace&vehicle=EPS-CITY-000) |
| Warning and YES reply | [Owner outreach](http://127.0.0.1:8770/ui/#safety-campaigns?campaign=sc_01m6gz1kvs894w47sv2rjzefbj&tab=outreach&vehicle=EPS-CITY-011) |
| Repair and verification | [Workshop records](http://127.0.0.1:8770/ui/#safety-campaigns?campaign=sc_01m6gz1kvs894w47sv2rjzefbj&tab=workshop&vehicle=EPS-CITY-011) |
| Evidence packet | [Evidence and close-out](http://127.0.0.1:8770/ui/#safety-campaigns?campaign=sc_01m6gz1kvs894w47sv2rjzefbj&tab=evidence) |
| Public code | [TraceX on GitHub](https://github.com/rahulx2001/TraceX) |

These links use the current local demo IDs. A fresh warehouse generates different IDs; use the launcher's printed case link and the links inside its Lot risk panel. The canonical seed has already completed its report. Showing it after the Report screen is an explicit switch to the prepared scenario, not the result of a new microphone call.

## Rehearsal: get the screens ready

1. Keep the demo server running. If needed, from the project root run `.venv-hackathon/bin/python scripts/run_lotguard_demo.py`. Refresh the browser and confirm **AI assistance: on**. Your local provider credentials stay in `.env`; they are not in GitHub.
2. In the hero drawer, confirm **Evidence recorded**, photo attached, codes attached, assessment recorded and follow-up drafted. Use the prepared case with green indicators. Do not record a half-complete case and explain away missing widgets.
3. Prepare the actual AI investigation once, before the timed recording. The canonical seed's original investigation is a **manual** run. Opening its history does not convert it to AI output. Open the stored-source investigation tab above; select **EPS-CITY-000**, read the original turns, tick **I reviewed these stored report turns** and **I confirm this report concerns the selected vehicle**, then click **Run sourced investigation**. Wait for the request to finish. Select the saved run whose result shows **AI-assisted observations**. Inspect its citations, unknown fields and **Engineer diagnostics and operation provenance**. Retain the actual model ID and timestamp. This rehearsal action can use your approved AI allowance.
4. Review every observation and claim against its source. For supported interpretations, select Accept; for an unsupported interpretation, choose Correct or Reject and explain it. Save **Record draft review** with the appropriate decision. Corrections require **Needs correction** and a linked revision, not blanket acceptance for the camera. This is a demo review on fictional records.
5. Check that **EPS-CITY-011** has the YES reply, slot confirmation, finding, repair, verification and resolution. The prepared records already contain these; do not create a second set just to record a click.
6. Confirm the downloaded packet opens. Check the nine-vehicle result and the evaluation source before the take. The batch-label image proves neither a crack nor a failed EPS unit; its actual vision result says no visible defect.
7. Use a Chrome window at about 1440×960 or 1920×1080. Close unrelated tabs or use a separate window. Keep notifications off, set the browser zoom so labels are readable, and record a short microphone test. Record your narration, not an AI-generated customer testimonial.

If the rehearsal AI request fails, keep that failure/fallback label. Use the alternate investigation line below. You can still demonstrate source review and the verified live Hindi/photo checks, but must not describe a manual saved draft as a new Meta inference.

## Exact narration and clicks

Read only the quoted narration. The instructions underneath are for your cursor and editing. Pause after a click so the viewer can read the evidence. Cuts between prepared tabs are fine; show saved results as saved results.

### 0:00–0:15 — The problem

> One steering complaint can point to a wider problem. TraceX helps engineers investigate the installed part, contact affected owners, and verify repairs. This walkthrough uses fictional records and an existing operations platform.

**Screen action:** Show the Report screen at `/ui/#call`, with **AI assistance: on** and **Start voice report** visible. Say the opening while the page is still. No new call is needed for this shot.

### 0:15–0:35 — The completed report

> Reports can begin by voice or typed Hindi or English. Here is our completed Honda City case. The photo, diagnostic code and reviewer assessment are stored. C0035 is a wheel-speed clue, so it does not confirm an EPS defect.

**Screen action:** Switch to the prepared **LOT ALERT** case. Show **Known now** and the green **Evidence recorded** indicators. Briefly open **Photos & scan codes** so the stored photo and C0035 are visible. Caption: **Prepared fictional report · real intake/case paths**.

### 0:35–1:00 — Investigation and AI

> Muse Spark can propose cited observations and read-only evidence lookups. We can open the original source, challenge a claim, and create a linked revision. An engineer reviews the interpretation before action. The batch-label image itself shows no confirmed damage.

**Screen action:** Switch to **Investigate** in the same campaign. Select the completed AI-assisted run prepared during rehearsal. Open one **Source …** citation or **Complete source snapshot**, then show **Evidence lookups** and **Investigation brief**. Keep **AI-assisted observations**, its recorded timestamp and the fictional-data label visible. Briefly show the photo result saying no visible defect. Do not start a new provider request during this shot.

### 1:00–1:20 — Verify the installed batch

> Matching the model name is not enough. Installation evidence ties this vehicle to EPS batch B14. Eleven reports share that reviewed scope. The caller's Medium severity inherits High review priority from severe parent reports.

**Screen action:** Switch to **Review installation** for **EPS-CITY-000**. Show **Installation evidence**, B14 and the recorded reviewer. Return briefly to the case and expand **Why High? · inherited review priority** to show the caller's own Medium severity. Caption: **Reviewed installation evidence determines scope**.

### 1:20–1:52 — Warn and schedule

> The campaign identifies 213 owners. Eleven have reported symptoms; the other 202 receive simulated warnings. The English and Hindi notices ask about symptoms and offer inspection. This owner replies YES and receives a workshop confirmation. Sixty-eight owners respond, and forty-one appointments are recorded.

**Screen action:** Switch to **Owner outreach**. Show **One report → fleet action**, the English notice and **Hindi warning · same reviewed scope**. Search for **EPS-CITY-011**, select that row, and scroll to the YES reply and confirmation containing **SYN-SLOT-011**. Show the existing simulated approval; it is a scripted demo reviewer decision.

### 1:52–2:14 — Inspect, repair and verify

> Here are the inspection, approved replacement part, repair, verification and follow-up. They are separate records. Nine fictional vehicles have findings and verified repairs after warnings, before any reported failure. Supplier containment stays open.

**Screen action:** Switch to **Workshop & repair** for **EPS-CITY-011**. Show **Approved replacement and procedure**, **Latest finding**, and expand **Vehicle history**. Point to inspection, part replacement, repair verification and follow-up timestamps. Caption: **Simulated workshop records · repair verification is a separate step**.

### 2:14–2:33 — Export the evidence

> The evidence packet preserves source records, reviewed installation data, actions and timestamps. Another engineer can inspect the reasoning. Recording a repair does not automatically close the campaign or clear every vehicle.

**Screen action:** Switch to **Evidence & close-out**. Show **Supplier corrective action**, the unresolved vehicle count, and **Evidence timeline**. Click **Export complete packet ↓**, or the top **Export evidence ↗** button. Show the downloaded JSON name; the packet contains the saved findings and repair references.

### 2:33–3:00 — The result and submission

> The result is eleven linked reports, 202 warnings, and nine verified repairs in this simulation. Historical classifier accuracy is 82 percent, with macro-F1 0.514. The challenger was rejected; adjudication is human-countersigned. The event work connects these reviewable steps. Code and evidence are public on GitHub. The goal is earlier intervention, with evidence for each decision.

**Screen action:** Return to the case's **Lot risk · EPS B14** panel. Hold on **213 / 11 / 202**, the nine-vehicle result and **82.0% accuracy · macro-F1 0.514**. Expand **Inspect evaluation source and limits** briefly. Finish on the public TraceX repository or a simple end card with its URL.

## If the investigation is still manual

Replace the 0:35–1:00 narration with:

> This saved draft was produced by rules. We can still inspect the original report, installation evidence and review history. Our separate live checks show Muse Spark understanding Hindi and analysing the fictional image. That image shows no visible defect; it does not confirm the reported cause.

Show the **Manual review / rules** label and the [recorded live service check](reports/hackathon/lotguard_demo/services_live_check.json). Do not relabel this run. The main narration file assumes you prepared and inspected a completed AI-assisted investigation.

## Optional clips for a longer walkthrough

These are rehearsal or extended-demo clips; keep the hackathon submission at three minutes.

- **Live voice / Hindi input:** record a separate short owner-input clip. The known working test sentence is: `मेरी 2021 Honda City का स्टीयरिंग भारी हो जाता है। गाड़ी घर पर खड़ी है।` Its verified translation is: “My 2021 Honda City's steering becomes heavy. The car is parked at home.” If typing, call it typed intake. A fresh report is a separate case unless the system actually links it.
- **Consent and destination:** open **Follow-up draft · prepared** in the hero drawer. Show the collected fictional email and consent, then **Send demo follow-up**. The result is simulated delivery, with no real owner contacted.
- **Correction history:** correct a genuinely unsupported draft interpretation, record Needs correction, and show **Create revised investigation**. Both versions retain their source identity and history.
- **Scope uncertainty:** show that an imported lot assertion and a matching model name do not themselves establish an exact part match. The installation record and reviewer disposition supply that evidence.
- **Repair prerequisites:** show the distinction between recording an inspection, approving the replacement specification, recording the repair and verifying it. A resolution requires its own review.
- **Supplier containment:** show the remaining unresolved owners and the open supplier action. Nine resolved vehicles do not establish that the rest of the lot is safe.

## Words and numbers to keep accurate

| Say this | Its meaning |
| --- | --- |
| “213 owners, 11 reports, 202 warnings” | Fictional installation scope, inbound reports and simulated warnings. |
| “68 responses, 41 bookings, nine verified repairs” | Stored simulated replies/bookings/workshop outcomes, not real-world activity. |
| “Warned and repaired before reported failure” | The demo records warning before finding/verified repair and no earlier reported failure. It does not measure accidents prevented. |
| “82.0% accuracy, macro-F1 0.514” | Historical classifier evaluation on 300 records and 46 labels. AI-assisted adjudication, human-countersigned by Rahul Kumar Singh. |
| “Challenger rejected” | Challenger accuracy 238/300 = 79.3%; baseline 246/300 = 82.0%. |
| “C0035 is a wheel-speed clue” | ABS/left-front wheel-speed circuitry; not confirmation of EPS failure. |
| “Meta Muse Spark handles understanding and vision” | Browser speech handles the demonstrated microphone path. Deepgram is not configured here; Baseten does not supply SAM or Muse Image. |
| “Built on an existing operations platform” | Reused foundation is disclosed in [ELIGIBLE_WORK.md](ELIGIBLE_WORK.md); event contributions and source hashes are inspectable in the repository. |

## Final recording checks

- Finish at three minutes; trim tab switching, not evidence labels. Keep narration audible and add captions if helpful.
- Leave “fictional” and “simulated” labels visible. Keep credentials and settings secrets off camera.
- Hold the nine-vehicle result for at least three seconds. Keep the accuracy source and countersign record readable.
- End card: **TraceX / LotGuard** · **From one report to reviewed fleet action** · **github.com/rahulx2001/TraceX** · **Fictional demonstration; accident reduction not yet measured**.
- After upload, open the actual video URL signed out and play it. A local file or an unverified upload URL is not a completed public submission.

For the narration without cursor instructions, use [LOTGUARD_NARRATION.txt](LOTGUARD_NARRATION.txt). For screenshots and the complete product walkthrough, use [LOTGUARD_DEMO_WALKTHROUGH.md](LOTGUARD_DEMO_WALKTHROUGH.md).
