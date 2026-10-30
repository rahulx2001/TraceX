# TraceX: stronger prediction evidence and hackathon submission

Historical plan, superseded for this pass by the owner's investigation-first
instructions and [current readiness status](READINESS_STATUS_2026-10-30.md).
Its threshold targets and video schedule are not current tasks. Video work is
outside this pass and remains the owner's later task.

Prepared 30 October 2026 after the owner chose to prioritize both objectives.
This is an implementation and evaluation plan. Proposed capabilities, targets,
participant counts and future measurements below are not completed results.

**Implementation update:** the sourced Meta investigation, review packs,
comparison gates, participant-study workflow and narrated three-minute demo
have now been built. See [the implementation report](../../docs/sourced-investigation.md).
Human labels, user-study outcomes and a new independent prediction score remain
pending. The original plan below is preserved as the intended sequence.

## Starting evidence

- Expanded-fuel 2025 holdout: **5/8 campaign recall (62.5%)**, **6/18
  mature-alert precision (33.3%)**, identical to the count baseline. None of
  40 development candidates passed the precision gate. See the
  [frozen report](../defect/fuel_holdout/README.md).
- Human defect evaluation: **0/300** completed. The existing blind review
  page is ready, but it assesses the earlier classifier and broader component
  sample; it does not establish accuracy on the new propulsion inputs.
- Live Meta integration is recorded for Hindi intake and Hinglish campaign
  symptom extraction. Single synthetic integration examples do not establish
  accuracy, usefulness across users or autonomous investigation ability.
- The safety-campaign walkthrough connects traceability, reviewed repair,
  follow-up and evidence export. Its records are synthetic and outreach is
  simulated. See [the implemented scope](../../docs/safety-campaigns.md).

## Priorities tied to the actual rubric

| Priority | Work | Judging criterion | Evidence required to claim completion |
|---|---|---|---|
| 1 | Demonstrate one complete quality-engineer task and measure the work it saves | Impact, 30% | Recorded operator sessions with the same tasks and an explicit manual baseline; task quality and elapsed time both reported |
| 2 | Let Meta choose the next evidence-gathering step, explain supported hypotheses and ask a useful follow-up | Meta tooling, 25% | Actual tool-call logs, cited source evidence, changed result after the new information, and measured comparison with the full existing rules |
| 3 | Improve complaint extraction and independent evaluation | Technical execution, 20%; also impact | Human-reviewed labels, disjoint evaluation data, fixed workload, retained misses, precision/recall and uncertainty |
| 4 | Record one coherent three-minute story | Demo, 25% | Timed recording of the working build; live and recorded/synthetic steps labelled accurately |
| Required | Public repo and clear event-work provenance | Initial eligibility | Accessible source, new-work diff, reused foundation disclosed, accessible video and team list |

Meta tooling and demo together account for half the score. Prediction research
helps, but the rubric does not require an 86% prediction threshold. No point
gain or finalist probability can be estimated reliably without judges and the
other submissions.

## Prediction work: improve the signal before adding more threshold searches

**First, create trustworthy labels.** Complete the existing
[blind review](../defect/repair/human_review.html) with real human reviewers and
record disagreements. Also define a dedicated review set for fuel and propulsion
complaints and recall descriptions, including negations, uncertain causes,
unrelated propulsion issues and reports after a known recall. Record who
reviewed which examples. Model suggestions must not be imported as human labels.
Human review improves measurement; it does not itself increase detector recall.

Before model development, separate the dedicated data by time and related
complaint/campaign groups. Deduplicate repeated narratives across partitions.
Keep new evaluation examples out of student training, prompt examples and
threshold selection. Reserve an independent cohort that has not already been
examined locally, or collect a prospective cohort. The opened 2025 holdout and
its 2026 outcome follow-up cannot be repurposed as a fresh blind test.

**Then compare a richer Meta extractor with the current student.** Proposed
fields are vehicle identity as stated, part, reported symptom, failure mode,
event timing, negation, uncertainty and exact supporting text spans. Missing
information stays unknown. Quoted evidence supports a report's interpretation;
it does not establish mechanical cause or installed-part identity. No recall
description, campaign outcome or later record enters a prediction input.

Evaluate the existing student, the full current deterministic pipeline and
direct Meta extraction on the same development examples. Score fields separately
and include difficult/unknown cases, cost, latency and abstention coverage.
Do not weaken the baseline to English keywords alone: the existing system also
has deterministic Hindi handling. Select the method on development results;
more prompts, agents or a larger model are not automatically improvements.

**Finally evaluate alerts.** Keep complaint receipt time and completed-week
availability causal. Compare policies under the same alert budget and cooldown.
Report campaign recall, mature-alert precision, lead time and missed campaigns.
Measure exact vehicle/part association separately from broad make/defect matching.
Any richer taxonomy must be designed using development data, with unknowns and
unreachable campaigns retained in the final denominator.

For a new experiment, predeclare the above-86% recall objective, precision gate,
workload and selection rules before opening its holdout. Retain at least the
current 50% development precision requirement; increasing alerts until most
campaigns match is not a useful improvement. If the target fails, publish the
failure. Without earlier evidence for some defects, public complaints alone
may never support this recall target.

## Product work: a bounded Meta-assisted investigation

The current campaign feature already has the useful action workflow. Add a
small evidence-gathering loop to it, rather than unrelated dashboards:

1. Meta extracts the owner's report into sourced observations and unknowns.
2. It chooses a read-only lookup of complaint evidence or installed-part records,
   or drafts one follow-up question that would distinguish competing explanations.
3. The next reply or referenced record updates an investigation brief: supporting
   evidence, contradictory evidence, remaining unknowns and suggested next step.
4. The engineer reviews the brief and uses the existing campaign/repair controls.

The visible trace should contain tool requests/results and evidence citations,
not a claim to expose the model's private reasoning. Bound tool calls, record
latency and cost, and retain the current fallback behavior. Safety escalation,
part approval, outreach authorization and vehicle clearance keep their existing
review requirements. Do not add a second model merely to call it a verifier;
check references and outcomes independently.

Show a meaningful change caused by Meta on a reviewed example, such as resolving
an ambiguous Hinglish symptom after a follow-up. If authoritative lot records
are absent, preserve unknown traceability. Any real external contact or delivery
integration needs the owner's explicit authorization; the local demo stays
simulated unless that integration is actually implemented and verified.

## Evidence that can improve the submission before the deadline

Run a small, explicitly described operator study on fixed quality-investigation
tasks. Recruit actual reviewers through the owner; none have been contacted by
this plan. Counterbalance manual and assisted task order where practical so
learning the same example does not create artificial time savings. Measure:

- Time to a correct, reviewable evidence packet.
- Correctly supported facts and citation errors.
- Task completion, necessary corrections and unresolved information.
- Number of human interactions, model latency, fallback rate and cost per task.

Report every session and the sample size, including failed tasks. A small study
supports a limited usability finding, not a general productivity percentage.
Synthetic scenarios can test software behavior and the demo; they cannot replace
human-labelled prediction validation or actual user evidence.

## Proposed remaining schedule

| Date | Deliverable | Stop condition |
|---|---|---|
| 30 October | Agree on the single investigation task; prepare independent labels and benchmark protocol | No human-accuracy claim while review is empty |
| 31 October–1 November | Implement the sourced extractor and bounded follow-up/lookup flow; compare development baselines | Keep the simpler method if the new one has no measured benefit |
| 2 November | Run independent evaluation if data/review are ready; conduct operator sessions | Report unavailable evidence as unavailable; do not rush labels or reuse the opened holdout |
| 3 November | Freeze the demo path, rehearse and record three minutes | Fix broken steps; exclude unverified capabilities from the story |
| 4 November | Verify source/video accessibility, event-work inventory and submit through the portal | Submission by 9 PM Eastern; no fabricated completion claims |

The building window and deadline come from the participant guide supplied in
this conversation. The schedule is a proposal, not an autonomous background job
or a promise that independent reviewers will be available.

## Changes completed while preparing this plan

Corrected the local submission documentation to reflect the supplied public-repo,
three-minute-video and new-work rules. Added a three-minute campaign storyboard,
removed an unsupported fixed inspection-saving line, and documented the current
holdout limitation and recorded Baseten integration proof. These are documentation
improvements; no new predictive result, benchmark, live model call or autonomous
investigation has been produced by this planning pass.
