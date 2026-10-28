# TraceX demo — concise recorded workflow

Target length: approximately three minutes. Confirm the actual submission portal's video format/length before upload; the supplied event page does not specify one.

## Prepare

Run `bash scripts/judge_setup.sh`. Open `http://127.0.0.1:8000/ui/#demo`. For supervisor actions, sign in with **Have a supervisor session?** using the local session from setup. Keep all credentials out of the recording. Meta's key stays only on the server.

Run `.venv-hackathon/bin/python -m scripts.ai_meta_smoke` beforehand. Use the artifact's actual endpoint/model/accepted output; do not substitute planned results. The central demonstration is text intake. SAM, image generation, WhatsApp and video analysis are not needed for this story.

A local captioned draft is available at `reports/hackathon/demo-draft.mp4` (2:58, silent). It shows **recorded** live synthetic Meta evidence and separate simulated supervisor actions. Add narration using this script if desired and review the portal's upload requirements. Without a Meta key, use **View recorded live proof** and describe its displayed timestamp.

## 0:00–0:25 — Problem and provenance

“Automotive quality teams receive scattered owner complaints, often in different languages. TraceX turns a complaint into reviewable facts and an audit trail. The frontline platform existed before this event. This submission adds verified Meta intake, stricter grounding and translation checks, and a reproducible judge path.”

Show Indie developer / Build for Your World, and label the example **synthetic**.

## 0:25–1:15 — Useful Meta step

Open **Meta complaint intake** and click **Run Meta complaint**. Show the original Hindi complaint, the deterministic language result, and the accepted Muse Spark translation. Read the actual result rather than promising a particular field. Show any facts requiring confirmation and the fallback status. Browser speech recognition supplies text; do not call this Meta audio transcription.

“No new vehicle identity or changed numbers are accepted. A failed or unsupported model output falls back.”

## 1:15–2:00 — Human decision and safety

Review the original complaint beside accepted facts. Show the completed case if this run created one, then the case queue. Explain that an engineer must decide what inspection/action to take. The separate synthetic brake-emergency seed demonstrates local safety escalation, which works without Meta; do not attribute that existing emergency detection to this new model run.

Use the issued supervisor browser session for any takeover/release demonstration. Operator API-key sign-in is a service role, not a supervisor.

## 2:00–2:40 — Actual audit evidence

Show the intake event ID, accepted/rejected fields and chain verification. The live proof records model, endpoint, completion status and spend accounting. Describe the chain as tamper-evident. An intact chain proves integrity of these recorded actions, not truth of every customer statement.

## 2:40–3:00 — Contribution and limitations

“This is an Indie prototype for multilingual automotive quality intake. We reuse the earlier operations platform. Today's submission proves a live Meta text workflow and makes its review and setup reproducible. The historical recall statistics are deterministic component-level results, not Meta accuracy or lives saved. The multilingual evaluation sets are synthetic; the human defect-label study is unfinished.”

Keep the last screen on the accepted model output and audit row. Show a repo/demo link, with credentials hidden.
