# Sourced investigations, independent reviews and the demo

The **Meta investigation** tab in Safety campaigns now runs a bounded,
source-cited investigation. Human labels and reviewer-study results remain
pending; no new prediction-accuracy claim is made.

## Run the feature

The current judge entry is `#demo`: Report → Investigate → Review → Evidence.
On an authenticated server, use Sign in with the configured operator key or a
signed supervisor session. Open mode retains the agent role; it does not grant
supervisor permission. Real campaign reviews still require the existing
supervisor authority.

After a voice or typed contact ends, **Investigate this report** opens its
server-stored customer turns. Select the campaign vehicle, review the stored
report and explicitly confirm the vehicle association. Opening the handoff
makes no inference or campaign action. **Use latest recorded report** also
resolves the original reply on the server instead of copying its text.

Interaction sources retain the interaction and turn IDs, speaker, UTC
timestamps, source version and hashes; citations link to the original stored
record. Personal information is redacted before model input and packet storage.
Recorded owner replies retain author/date/vehicle lineage and are labelled as
operator transcriptions. Separately typed text is labelled manual and has no
original-record claim. A changed, erased, active or unavailable source is
refused, and an oversized report is rejected without silently dropping turns.
This bounded path supports up to 8,000 characters per stored interaction and
16,000 report characters across at most three investigation turns.

Observation and claim decisions are **Accept**, **Correct** or **Reject**.
Accepting a draft requires an explicit acceptance of every displayed model
interpretation. Corrections and their
original claims remain in the recorded review. A linked revision receives that
review and earlier evidence as historical context, rechecks stored report
references and performs current lookups. A corrected draft requires a new
revision before acceptance. This does not establish semantic accuracy: an
engineer still needs to inspect each interpretation.

Targeted guards withhold unsupported numbers/identifiers and selected
English/Hindi/Hinglish denial reversals. They are deliberately narrower than
semantic entailment and can withhold a valid interpretation whose citation is
incomplete. The rejected interpretation, original quotation and reason remain
inspectable. Actual unsupported-claim and omission rates require human grading.

CSV `trace_status=verified` is a source assertion, not an independent review.
Imports keep file/row hashes and importing actor/time. A trace review requires
inspectable installation-record text, records its hash and reviewer identity,
and binds the review to the vehicle/supplier/part/lot. Existing unsupported
verified assertions are displayed as unverified. The new ready demo records
explicit fictional installation documents and simulated seed reviews; these
are never counted as human study participation.

The current request stage is stored as Reading report, Checking records,
Drafting or Ready for review. A single-worker restart or a ten-minute expired
reservation becomes **Interrupted** on history refresh. Retrying that same
request ID returns the saved state and never repeats inference. Starting a new
request is explicit, requires renewed source review and retains any prior
provider spend. This is conservative recovery, not an exactly-once guarantee
at the external provider. The existing model budget is unchanged.
An interrupted call count is labelled uncertain. Workers check their saved
reservation before continuing to another stage. The existing contact-erasure
workflow now removes linked report snapshots, claims and correction context
from investigation history; an in-flight worker cannot restore those copies.

Each observed HTTP attempt records model/host, timestamps, prompt/schema/request
hashes, code fingerprints, token usage, validation result and fallback. Stage
and total durations are measured separately. Reservation amounts and configured
token-rate estimates are not provider invoices; billed cost remains unknown.
The global AI badge describes server configuration. Saved results identify
their own operation mode and original timestamp.

Owner and workshop history expose record counts and omitted older records;
scoped pagination opens those older sources. Truncated lookup snapshots show
omitted character counts and link to the complete original record. No evidence
retrieved is not a claim that no evidence exists.

Focused validation (isolated fixtures and fake inference, no API credit):

```bash
.venv/bin/python -m pytest tests/frontline/ai_layer/test_report_handoff.py \
  tests/frontline/ai_layer/test_campaign_investigator.py \
  tests/frontline/ai_layer/test_safety_campaigns.py \
  tests/frontline/test_pii_token_integrity.py -q
cd dashboard
PLAYWRIGHT_CHANNEL=chrome npm run test:signin
```

The browser check builds current assets and starts isolated real backends for
entry/auth and a text/WebSocket report → stored source → manual investigation
→ supervisor review → downloaded packet check. Separate UI fixtures check
correction controls and voice behavior. UI transport simulations do not measure real speech quality,
multilingual accuracy, live Meta reliability or reviewer usefulness. The
historical three-minute recording below predates this handoff; a final video
still needs to be recorded and external links checked.

Build the dashboard and restart the normal API using its existing server-side
Meta configuration. The established API budgets and daily cap still apply.

```bash
.venv-hackathon/bin/python -m scripts.prepare_review_assets
cd dashboard
npm run build
```

Open `#safety-campaigns`, select **Meta investigation**, choose a registered
vehicle, and enter an owner report or load its latest recorded report. **Run
sourced investigation** makes at most two logical model calls (transport
retries remain bounded by the existing adapter). No call is made just by
opening the tab.

The first model call extracts the reported vehicle/part, symptom, failure mode,
timing, negation and uncertainty. It selects up to two read-only tools from
installed-part records, workshop history and prior owner reports. Availability
metadata helps it avoid empty or repetitive lookups. The second call drafts a
cited brief and selects the next information need. The application renders a
safe question for that need. A follow-up creates a linked new draft; at most
three turns are supported.

All quotations are attached from server-owned, redacted source sentences;
unknown citations are rejected. This checks source fidelity, not semantic
correctness or mechanical cause. A model can still misinterpret a sentence,
which is why observations and briefs retain an explicit review requirement.
The tools cannot run arbitrary queries, fetch arbitrary URLs, send messages,
approve an action, choose a replacement part or clear a vehicle.

Drafts persist in `safety_investigation_runs`, separately from campaign state.
Input hashes and request IDs prevent changed or duplicate requests from being
silently replayed. Each run records its actor, source snapshot, campaign
revision, tool choices, model ID, duration and parent. The original campaign
revision is not changed by investigation. A stale draft cannot receive a new
review; repeat the investigation against the updated evidence. Real draft
review requires the existing signed-supervisor authority. Demo review remains
explicitly synthetic and is never counted as a participant study or human label.

Evidence export now includes the investigation drafts and reviews. Ordinary
campaign approvals, remedies, verification and closure keep their existing
controls. A missing key or rejected model output leaves source evidence and a
manual-review fallback; it does not produce a success score.
This campaign packet records actors, time, source hashes and history. It is
**not** a signed or hash-chained export; the older contact export's tamper-evident
claim does not apply to the entire campaign packet.

The current synthetic live proof is
[`investigation_current_live_smoke.json`](../reports/hackathon/investigation_current_live_smoke.json).
Its four real HTTP calls selected installed-part lookup before and after the
scripted installation review. The initial draft kept traceability unknown;
the revised brief cited the newly attached fictional record. One revised
observation was withheld because its citation omitted the earlier year it
mentioned. Both that failure and the accepted brief remain recorded. The
source turns are typed fixtures, not a microphone recording or human study.
The initial sandbox DNS failure is separately retained with zero calls.

## Independent label review

Open **Independent review and measurement** inside the investigation tab. The
authenticated buttons open these prepared documents:

| Review | Current work prepared | Result status |
|---|---:|---|
| Original classifier sample | 300 complaints | 0 human labels |
| New development sample | 32 complaints | Human review pending |
| Reserved cohort sample | 100 fuel/propulsion complaints | Human review pending |
| New recall reference set | 5 distinct descriptions | Human review pending |

Model predictions are hidden; no answer is preselected. Supporting quotations
must occur in the original text. Reviewer identity, sample hash and personal
attestation are checked on import. Multiple review exports remain separate;
the code does not invent consensus or automatically adjudicate disagreements.

For the original 300 use the existing instructions in
[`reports/defect/repair/README.md`](../reports/defect/repair/README.md).
For a new exported review:

```bash
.venv-hackathon/bin/python -m scripts.evidence_benchmark import-review \
  --review /path/to/fuel_complaint_review-human.json
```

The standalone HTML files also work locally. In the app, their scripts are
served as static assets; the global `script-src 'self'` policy is unchanged.

## Comparison and the reserved cohort

The separate cohort covers Chevrolet, GMC and Nissan, model years 2015–2024,
with 2025 fuel/propulsion complaints and recall follow-up through 2026-09-30.
There are **621** deduplicated complaints after excluding explicit recall
mentions. These makes were outside the prior five-make 2025 evaluation. This is
locally unused evaluation data, not a guarantee against model pretraining or
revised historical narratives. The reservation and source/input hashes are in
[`reports/defect/evidence_v1/protocol.json`](../reports/defect/evidence_v1/protocol.json).

Eight development complaints were compared through the frozen lightweight
student and direct Meta extraction. After fixing required JSON fields, eight
calls returned schema-valid extraction; four defect labels agreed. **That is
model agreement, not accuracy.** The earlier eight rejected-output attempts are
preserved separately. The model-labelled development outputs and the study's
recorded assistance identify their actual extractor version; later planning
context refinements are not retroactively attributed to them.

The reserved cohort has not been scored. Freeze the candidate from complete,
attested development review **before** reserved gold is attached. Keep the
independent complaint/recall labels sealed from builders during candidate
selection. The separate gold attachment records its custodian and order:

```bash
.venv-hackathon/bin/python -m scripts.evidence_benchmark freeze \
  --review /path/to/development_review-human.json
.venv-hackathon/bin/python -m scripts.evidence_benchmark attach-reviews \
  --complaint-review /path/to/fuel_complaint_review-human.json \
  --recall-review /path/to/recall_review-human.json \
  --custodian 'Actual independent custodian' --attest-sealed

# Estimate full warm-up/cohort and batch cost without making calls.
.venv-hackathon/bin/python -m scripts.evidence_benchmark preflight --limit 8
# Only after freeze and budget inspection; bounded, cached, unchanged cap.
.venv-hackathon/bin/python -m scripts.evidence_benchmark predict-holdout --limit 8
.venv-hackathon/bin/python -m scripts.evidence_benchmark evaluate
```

The final command refuses partial prediction coverage and mismatched inputs,
code, model or labels. It applies the same 13-week count policy, minimum two
complaints, completed weeks, 91-day cooldown and 7–364-day lead horizon to both
classifiers. Actual monthly alert quotas are matched by keeping the earliest
common count of alerts, without using recall outcomes. That conditional
comparison is retrospective, not an online policy. Both original and matched
alert rows, zero-alert months, precision/recall and lead times are retained.
Failures are abstentions; misses and unknown labels stay in the denominator.
Campaign matching remains make/component/defect association,
not proven physical-part identity. A numerical target result does not promote
the model; development precision qualification and broader validation remain
separate.

The complete cohort and warm-up require more calls than the eight-row
development probe. Bounded batches cannot override the existing cap. No budget
or daily counter was reset, and no claim is made that remaining credit covers
the full experiment.

## Actual reviewer study

The prepared-draft [study page](../reports/hackathon/reviewer_study/study.html) contains eight
distinct public-report tasks, each reviewed once by a participant. Manual tasks
show source text; assisted tasks also show a saved, real Meta extraction.
Participant-based assignment counterbalances conditions and order. The task
is preparation of a complaint evidence packet with saved assistance. Its timer
does not include live inference waiting. It is not a full field repair or OEM
deployment study.

The browser records elapsed time, source/assignment identity, submitted answer,
and hidden-tab events. Timings include time spent elsewhere. A participant must
attest that they personally performed the tasks. Export before closing. Failed
tasks should be completed with an explanation, not silently omitted.

```bash
.venv-hackathon/bin/python -m scripts.reviewer_study analyze \
  --sessions /path/to/reviewer-1.json /path/to/reviewer-2.json \
  --rubric /path/to/independent-material-fact-rubric.json
```

This validates assignment, timing and attestations, reports incomplete work,
and produces a grading pack that hides the experimental condition and timing.
An independent human grader assesses source-supported facts, unsupported claims,
required corrections and whether the packet is acceptable. Enter the actual
grades and use `--grading /path/to/completed-grading-pack.json` with the same
command. Every recorded task, including failures, needs a grade. Small samples
and task difficulty limit interpretation; the code does not invent a single
productivity percentage. **Current participants: 0. No time-saving or quality
result exists.**

The separate `scripts.investigation_study` workflow measures the complete
deterministic workflow, extraction-only assistance and full live investigation
on the same original sources. It starts timing before task reveal, retains
failed attempts, verifies live run IDs and supports independent grading with a
double-graded subset. It requires an actual independent task rubric before
freeze; no participants have been created. See
[evaluation-readiness.md](evaluation-readiness.md) for the per-point status,
field scoring, sealed-gold procedure and both study commands.

## Three-minute recorded workflow

The video uses real UI actions on an isolated local dataset and saved live Meta
outputs. Fictional inputs, simulated engineering/workshop actions and recorded
model outputs are labelled on screen and in the narration. The standard macOS
Samantha text-to-speech voice supplies the narration; it is not a human reviewer
or the owner's voice.

```bash
.venv-hackathon/bin/python -m scripts.investigation_demo_server --port 8768 --scenario recording
# In another terminal:
cd dashboard
node scripts/record-investigation-demo.mjs --check
node scripts/record-investigation-demo.mjs
cd ..
.venv-hackathon/bin/python -m scripts.render_investigation_demo
```

The demo server uses only its dedicated `data/hackathon/investigation-demo-*`
database. It seeds the existing automotive fixtures and makes no model calls.
Replaying recorded output adds source-artifact provenance and does not count as
a new independent test. A completed recording mutates only its own fictional
campaign. Use a separate scenario for a fresh rehearsal rather than resetting
the normal pilot warehouse.

The live integration proofs are
[`investigation_live_smoke.json`](../reports/hackathon/investigation_live_smoke.json)
and [`investigation_followup_smoke.json`](../reports/hackathon/investigation_followup_smoke.json).
Neither proof is human diagnostic validation. The original **5/8 (62.5%)**
holdout remains unchanged; prediction above 86% and accident reduction have
not been established.
