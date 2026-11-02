# First non-author usability task

This is a product usability session, separate from defect-label review. Use
fictional data on the isolated test installation. Do not use an actual customer
or vehicle. No model inference is needed for this task.

The isolated installation is running at
[Start here](http://127.0.0.1:8766/ui/#demo) on the owner's computer. Its database
and outbox live under `/private/tmp/tracex-usability-20261102-ux1`. It has no
customer-delivery connection and model calls are disabled.

## Give only this task to the participant

You are handling a fictional owner report:

> My 2019 Honda CR-V makes a grinding noise when braking at low speed. I am
> parked safely. There has been no fire, injury, crash or loss of control.
> I do not have a photo or scan report with me. This is a demonstration.

Record the report using typed input. Find its saved case. Prepare a message
asking for a safely available photo and any existing scan codes. Save an
assessment that identifies what you know, what is uncertain and your next
action. Set the case to Pending follow-up, save it, then undo that status change.
Finally save the case packet and tell the observer whether the customer has
received a message. This is administrative record handling; do not approve a
repair or release a vehicle.

Try to complete the task without instructions about where to click. Stop if
you are stuck or uncomfortable. Asking for help is a valid session outcome.

## Observer instructions — do not give these to the participant

1. Open the start page in a clean browser session. Record the actual participant
   name/alias, relevant experience, device/browser, build, installation URL and
   whether they previously saw the app. Do not present them as a service advisor
   unless that is true. Explain that you are testing the product, not them.
2. Start the timer before giving the task. Watch silently. Do not point, name
   routes, correct an answer or take the mouse. Record any intervention verbatim.
   An intervention prevents an unassisted-success claim.
3. Let the participant answer the intake questions using only the fictional
   facts. Missing evidence stays missing. Record unclear instructions, wrong
   destinations, errors, retries, backtracking and requested help.
4. Stop when they say they have finished, withdraw, or reach the session limit
   you recorded before starting. Do not turn a timeout into a success.
5. Inspect saved records after they finish: case ID, follow-up text, assessment
   note, status history and packet reference. Confirm that Undo restored Open
   and the packet contains the saved draft, note and evidence references.
6. Ask: “What would you do next?”, “Was anything unclear?”, and “Did this send
   a message to the owner?” The correct delivery understanding is that the
   packet was saved locally; the customer was not contacted.
7. Fill a copy of [observation_template.json](observation_template.json) with
   actual observations and timestamps. Preserve failures and original answers.

The first planned cohort is **1 non-author participant / 1 task**. No session
has been supplied yet; completion and unassisted success are unmeasured. This
can identify usability problems, not establish population productivity or
clinical/mechanical correctness. Retain every attempted task in the denominator.
