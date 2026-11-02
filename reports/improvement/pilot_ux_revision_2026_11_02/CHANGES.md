# Pilot UX revision — 2 November 2026

The software fixes are implemented and verified. The non-author usability task
is prepared and an isolated installation is running; actual human results have
not yet been received. English/Hindi input is explicitly distinguished from the
English-only interface and replies. No new rubric score is claimed.

| Review finding | Result |
|---|---|
| 1. Case drawer | “Known now” contains the report, vehicle details, safety status and recall link. “Still needed” offers photo/code requests, evidence entry and an assessment draft. Empty editors stay collapsed. Optional evidence does not block manual review. Missing vehicle fields are called out. |
| 2. Navigation | The pilot workflow stays at the top. Following the owner's correction, direct links to the full operations, intelligence, trust/platform and additional tools are restored in a scrollable sidebar. The earlier tour is accessible again. The owner prefers retaining these links instead of moving them all under Platform. |
| 3. Internal language | Assistance availability and useful outcomes replace vendor labels. Raw model IDs, latency percentiles, error details and usage remain inspectable in closed diagnostics/provenance sections. |
| 4. Defensive entry | Start here leads with the operator's job. Fictional-data and evidence limits remain in a details section, with fictional records labelled in their workspaces. The stale generic pending-human-accuracy sentence is removed; historical classification evidence remains separate from product/source-field validation. |
| 5. Draft delivery | The drawer says Save case packet. The audited local packet now includes the saved follow-up draft, note identities/timestamps and evidence references. The outcome explicitly says the customer was not contacted. Unsaved follow-up edits are saved first; unsaved notes/status must be saved before packet creation. No email/CRM integration is implied. |
| 6. Small failures | Permission errors give recovery steps. Missing vehicle models are identified in new follow-up drafts. Manual status changes require Save and offer Undo; automated safety severity stays read-only. Shared account authors are labelled honestly. Notes disable duplicate submission and reuse an idempotency key when retried. A note-store failure preserves the readable case and marks notes unavailable. |
| 7. Load cost | Routes are lazy-loaded with visible loading and error recovery. The entry JavaScript is about 178.45 kB, compared with the previous 739.75 kB entry. The large-chunk warning is gone. This is a build/route-loading result, not a measured tablet-speed benefit. |
| 8. Language scope | Entry, report setup and guide state English interface/replies with English or Hindi input. Full UI/reply localization remains deferred. Real Hindi/Hinglish recognition quality remains unmeasured. |
| 9. Human success | A short unassisted task and blank observation record are ready for the available non-author tester. Planned: one participant with one task. Actual completion, unassisted success and timings remain unmeasured until their session is supplied. |

## Verification

- Focused Python regressions: **21/21 passed**. This includes the packet's
  draft/note/evidence contents, missing-model follow-up and readable-case behavior
  during a note-store outage. One existing Starlette deprecation warning remains.
- Final production build, browser suite and copy gate passed. The browser suite
  checks a real isolated typed report, source handoff, correction, revision,
  review and export. Fictional route fixtures check permission errors, saved
  drafts, note retry identity, status Undo, packet wording, hidden engineering
  metrics and a narrow-screen case drawer. No paid inference or real audio ran.
- The frozen sample, candidate dependencies and finalized evaluation artifacts
  passed **25/25** preservation checks. No evaluation labels or fixtures were
  used for fitting, calibration, feature selection or dashboard accuracy.
- [Verification and source hashes](verification.json) and
  [preservation details](preservation_checks.json) retain the scopes and limits.

Rendered fictional screenshots were visually inspected:

- [Start here and the single navigation](judge-entry.png)
- [New case workspace, with no open empty editors](case-workspace-initial.png)
- [Saved evidence and packet outcome](case-evidence-recorded.png)
- [Narrow-screen workspace](case-workspace-mobile.png)

## Ready for the non-author session

Open [the isolated app](http://127.0.0.1:8766/ui/#demo) on this computer and give
the participant only [the task](usability/TASK.md). The observer watches silently
and fills [a copy of the blank observation record](usability/observation_template.json)
with actual times, outcomes, errors and interventions. This is separate from
defect-label review. Preserve failed attempts and the participant's own answers.

The test installation owns its database and outbox under
`/private/tmp/tracex-usability-20261102-ux1`; model calls and customer delivery
are disabled. It does not change the running production installation or connect
to the sibling project's warehouse. The server remains running for this test.
