# TraceX — three-minute engineer workflow

TraceX helps an automotive quality or service engineer turn a multilingual owner report into a source-cited investigation and documented action. The customer supplies the vehicle association, installation provenance and workshop records. The model helps decide which evidence is missing; an engineer checks the claims and authorizes the next action.

The final story is **Report → Investigate → Review → Evidence**. Start at `/ui/#demo` after `bash scripts/judge_setup.sh`, sign in with the issued local credential, and keep credentials out of the recording. Use the supervisor session for actions that require a named reviewer. Setup uses `data/hackathon/judge-v3/`; it does not reset earlier datasets or spend model credit.

The existing `reports/hackathon/investigation_demo/TraceX-investigation-demo.mp4` is a verified 180-second **historical** recording. It shows saved 29 October model outputs and the earlier UI. It is not the final-current-build recording. Preserve that file and use `reports/hackathon/final_demo_2026-10-30/` for new media.

## Recording sequence and narration

These are editorial time allocations, not latency or performance claims. Every demonstrated record is fictional. Keep “fictional scenario” and the individual operation's live/recorded/fallback label visible. A recorded model result retains its original source IDs, model version and timestamp; never attach it to a newly created report to imply a new inference.

| Time | Visible action | Narration |
|---|---|---|
| 0:00–0:15 | Guided entry and owner report | “A quality engineer receives an ambiguous owner complaint. TraceX connects it to reviewable evidence and documented action. This scenario is fictional; the operations platform is reused.” |
| 0:15–0:40 | **Start voice report** or **Type instead**, readable transcript, a correction and confirmed vehicle | “The owner can speak or type. The engineer checks what was captured, corrects the report and confirms the vehicle. Investigate this report carries the stored source turns without retyping.” |
| 0:40–1:20 | Report citation, actual Meta-selected lookup/question, uncertainty and missing source | “This saved/live Muse Spark result selected this evidence lookup or question. Here is the exact source and the uncertainty it leaves. A reported symptom is not a confirmed cause.” Say saved or live according to the operation, not server configuration. |
| 1:20–1:50 | Inspectable fictional installation record, source assertion versus engineer review, linked revised brief | “An import can assert a lot, but a reviewer checks the installation evidence. This record changes what we know. The revised brief keeps the earlier claim and explains the correction.” |
| 1:50–2:20 | Same vehicle, reviewed next action, repair and distinct verification | “The application enforces the review and repair prerequisites. These are simulated workshop records, not a real repair. Replacement and repair verification are separate steps.” |
| 2:20–2:45 | Exported packet, original turn, installation source, review and model fingerprint | “The packet preserves source lineage, model decisions and reviewer history. Another engineer can inspect and challenge it. Human usefulness and accuracy measurements are still pending.” |
| 2:45–3:00 | Event contribution list and verified repository/video links | “The event work adds a sourced, correctable investigation and a reproducible review path. The reused platform supplies operations context. The repository and public replay let you inspect the evidence.” |

Show a close view of the current fact or decision, readable captions, and a short pause on the changed evidence. Avoid a tour of unrelated dashboards. If real audio has not been validated on the recording device, use the visible text fallback and describe it as typed intake. Browser Web Speech and optional Deepgram supply transcription; Muse Spark is not the speech recognizer in this path.

If the saved model calls do not demonstrate an improvement on the ambiguous report, show the actual limitation. Do not invent a useful answer, human review, source document or repair to fit the script. A scripted operator action in this fictional recording is not a study participant result.

## Recording and release checks

- Record against an isolated, persisted fixture database. Reuse the original recorded interaction and campaign state for playback; do not remap historical outputs into new evidence.
- Review each claim and observation through the UI before approval. The review records are labelled simulated actions in the fictional scenario.
- Include the source record, exact model ID, recorded timestamp, and failure/fallback state when applicable. Replaying the UI makes zero inference calls.
- Verify 180 seconds, readable captions and audible narration with `ffprobe` plus sampled frame/audio inspection. System text-to-speech narration is synthetic narration, not a participant interview.
- Keep historical statistics in the [claim index](reports/hackathon/CLAIM_INDEX.md). The 5/8 recall equals its count baseline; four model agreements out of eight are not human accuracy. No accident-prevention or productivity result is established.
- Upload the final video, open it signed out, and record the actual URL in [submission links](reports/hackathon/submission_links.json). Check the portal's accepted format, final source commit and actual team members. A local MP4 is not a public submission.

The participant guide requires a three-minute video focused on event-built code/functionality and disclosure of the reused codebase. The final [source manifest](reports/hackathon/source_manifest.json) must point to the submitted source commit; the old snapshot must not be presented as current. See [contribution provenance](ELIGIBLE_WORK.md) for the packaging procedure.
