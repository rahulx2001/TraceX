# Hackathon fix prompts

Repo: https://github.com/rahulx2001/TraceX
Clone it fresh, or use a local checkout whose `git remote -v` origin is that URL. If origin is still `https://github.com/rahulx2001/SkewAi`, do not push there. The product name is TraceX. Old docs may still say SkewAi; do not treat SkewAi as the submission remote.

Paste one prompt per chat. Run them in the order below. Later prompts assume earlier ones are merged in this same checkout.

Shared rules, already inside every prompt:

- Do not weaken, delete, skip, or xfail tests.
- Do not rewrite or rebase published git history.
- Do not print, log, or send the Meta API key to the browser.
- Live Meta spend for the whole submission is capped at 30 USD. Only prompts 11 and 12 may call the live API, and only inside the budget those prompts state.
- The Meta key is already configured by the owner. Use it. Do not ask them to create another key.

Order:

1. Prompt 03 — `.env` actually configures the server
2. Prompt 04 — classifier export matches the accuracy evaluator
3. Prompt 05 — grounding rejects unsupported claims
4. Prompt 06 — translation cannot drop or invent facts
5. Prompt 07 — four failing contracts
6. Prompt 10 — portable defect paths and a budget plan (no live calls)
7. Prompt 11 — blocking routes and SIGTERM shutdown
8. Prompt 12 — clean-checkout judge setup
9. Prompt 09 — backtest wording and reproducibility (no threshold changes)
10. Prompt 01 — eligible-work record
11. Prompt 02 — one live Meta workflow (budget slice: at most 8 USD)
12. Prompt 08 — evaluation only for claims you will make (budget slice: at most 22 USD, and only what remains under the 30 USD total)
13. Prompt 13 — submission snapshot, license, three-minute story

---

## Prompt 01 — Eligible work record

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Preserve the actual Git history. Do not rebase, squash, or amend published commits. Do not spend any Meta API money.

This is an eligibility fix for a hackathon submission whose strongest fit is Push the Frontier, focused on automotive quality investigation and defect evidence.

HACKATHON.md at DeveloperFolder/Code/v2_ai_rca_tool/HACKATHON.md:240 records that the optional Meta integration, Hindi safety lexicon, original dashboard demo, OOS backtest, and synthetic evaluation sets existed before the event.

The same document contradicts itself: it says no product feature was built during the event, then describes newer defect and complaint-collection tooling.

The organizer guide says the building period begins October 27. HACKATHON.md uses October 26. Some October 26 work occurred after kickoff, so its eligibility needs organizer clarification. Do not silently relabel October 26 work as eligible. Mark it "needs organizer clarification" and keep the dates that git actually shows.

Fix this by recording, in HACKATHON.md, three separate lists a judge can read without interpreting git log themselves:

1. Reused foundation (existed before the event): optional Meta integration, Hindi safety lexicon, original dashboard demo, OOS backtest, synthetic evaluation sets. Name the pre-event commits.
2. Accepted event starting point: the commit or tree the eligible work starts from, and the clock you are using (October 27 per the guide). State that October 26 work is listed apart and needs organizer clarification.
3. Exact subsequent contributions: each feature, file, and commit made after that starting point, including the newer defect and complaint-collection tooling. Remove the sentence that says no product feature was built during the event, because it conflicts with those tools. Replace it with the contribution list.

Rewrite the demo section of HACKATHON.md so the three-minute story is about those subsequent contributions, not the pre-event foundation. Label pre-event pieces as reused. Do not claim a feature is event-built unless git history supports it.

Acceptance criterion: a judge can identify exactly what was built during the eligible period without interpreting the repository history themselves.

Do not change product behavior in this task. Docs only, plus a short "How to read the history" section that names the commands a judge can run (git log, git show) to confirm the lists.
```

---

## Prompt 02 — One live Meta workflow, at most 8 USD

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. The Meta API key is already configured by the owner. Never print it, log it, or let the browser accept it. The browser may receive only configuration status.

Hard budget: this task may spend at most 8 USD of Meta API. The whole submission cap is 30 USD. Stop before the eighth dollar. Record token counts and estimated cost for every live call. If a call fails, keep the failure visible. Do not retry in a loop.

Meaningful live Meta use has not been demonstrated. HACKATHON.md (HACKATHON.md:220) lists text, vision, and SAM integrations as unverified against the live API. The document says the Meta request formats have only been tested with mocks. Integration code and an Enhanced badge do not establish that Meta performed a meaningful task.

Complete and verify ONE existing workflow that materially uses Meta. Do not integrate every model listed in the guide. Prefer a workflow already in the product (grounded brief, intake enhancement, or defect classification of a tiny fixture). Record:

- the model id that answered
- a successful execution
- the resulting artifact on disk (path and hash)
- the fallback behavior when the call is forced to fail (deterministic fallback must still run, and the UI or report must say the model did not run)

The seeded Hindi safety example already becomes Critical through the deterministic pipeline. Do not use that example as the proof of Meta capability. Pick an input where the deterministic path and the model path produce different, checkable outputs, and show what the model supplied.

Keep failures and unavailable results visible. Do not relabel a mock as live. Update HACKATHON.md so this workflow is described as executed, with the artifact path, model, cost, and what was still not verified (leave vision and SAM unverified if you did not call them).

Acceptance criterion: the demo shows an executed Meta-dependent contribution, with evidence of what the model supplied. You do not need to integrate every model listed in the guide.

Depends on Prompt 03: the documented server launch must actually load the key before you call the API.
```

---

## Prompt 03 — .env must configure the documented server

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Do not print secrets. The browser must never accept the Meta key; it may receive only status (configured / missing).

The Settings panel tells users to edit .env and restart. config.py (src/ai_layer/config.py:69) reads process environment variables. There is no application dotenv loader and no --env-file in the documented plain uvicorn launch.

Editing .env and restarting that documented command can leave the server unconfigured. Docker Compose loads env files differently, which adds confusion.

Choose ONE tested server configuration path and use it everywhere:

- either load .env at process startup inside the application, or
- document a launch command that loads the file (for example uvicorn --env-file), and make Settings, README, and judge setup use that exact command.

Apply the same instructions to README, the Settings panel, HACKATHON.md judge setup, and scripts/judge_setup.sh. Remove the other path so a judge is not offered two conflicting launches.

Test it. Start the server with the documented command against a temporary env file that sets a non-secret status flag (or a dummy key in a temp file). Hit the status endpoint. Confirm the status changed. Restart with the flag absent and confirm the status changed back. Confirm the HTTP response does not contain the key.

Acceptance criterion: the documented procedure changes the server’s configuration status after restart. The browser continues to receive only status information and never accepts the Meta key.
```

---

## Prompt 04 — Classifier export must load in the accuracy evaluator

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not call the live Meta API. Do not spend credits. Fix the schema before any classification run.

Reproduced pipeline bug:

scripts/defect_classify.py at scripts/defect_classify.py:462 exports classifications without three provenance columns required by scripts/defect_accuracy.py at scripts/defect_accuracy.py:120.

An offline exporter-to-evaluator check failed with:

classifications parquet is missing columns:
['model', 'prompt_version', 'taxonomy_sha256']

Fix the export schema so every classification artifact, including the empty-output case (zero rows), contains model, prompt_version, and taxonomy_sha256. Empty output must still have those columns and the right dtypes so the evaluator can open it.

Add a round-trip test that uses the actual exporter function and the actual consumer in defect_accuracy.py. Build a small temporary classification artifact locally, load it through defect_accuracy.py, and assert model, prompt version, and taxonomy provenance survived. Do not mock away the schema check.

Acceptance criterion: a locally constructed temporary classification artifact loads successfully and preserves its model, prompt version, and taxonomy provenance.
```

---

## Prompt 05 — Grounding must reject unsupported claims

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Add or extend offline tests. Do not weaken existing grounding tests.

src/ai_layer/grounded_brief.py at src/ai_layer/grounded_brief.py:153 checks citation existence, scope, numbers, and some prohibited narration. It does not establish that the cited record supports the claim’s meaning.

Reproduced offline with a committed braking-noise fixture: an adversarial claim asserting an engine fire and airbag failure cited that real record, and the validator returned:

(True, 'ok')

The UI labels accepted model claims “Muse Spark, Qubot-verified.” That label overstates the check.

Strengthen the evidence contract:

- Require supporting source spans for each critical assertion (fault, component, injury, deployment, fire, airbag, and similar safety claims).
- Check that those assertions follow from the spans. A citation that merely exists is not support.
- Reject unsupported claims. The braking-noise record must reject an engine-fire and airbag-failure claim.
- Apply the same scrutiny to generated headlines, not only body claims.
- Until the check actually verifies meaning, change the UI label so it names the checks performed (citation exists, in scope, numbers match, narration rules) instead of “Qubot-verified.” After the span check exists, the label may say the claim is supported by a cited span, and must still name the checker.

Add a regression test that feeds the committed braking-noise fixture and the adversarial engine-fire / airbag claim and expects rejection.

Acceptance criterion: a valid citation attached to an unsupported fault claim is rejected. The same scrutiny applies to generated headlines.
```

---

## Prompt 06 — Translation must not drop or invent facts

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Offline tests only.

src/ai_layer/language.py at src/ai_layer/language.py:66 rejects numbers introduced by a translation, but does not require original numbers to survive.

Reproduced:

- An offline check accepted a translation that dropped the caller’s 2019 vehicle year.
- Another accepted check introduced a make, model, and brake failure absent from the original utterance.

src/ai_layer/intake_enhancer.py at src/ai_layer/intake_enhancer.py:154 permits slot evidence from the model’s own translated text. That lets model-generated details look grounded.

Change the contract:

- Original numbers must survive (a dropped 2019 year is rejected or flagged, not silently accepted).
- Uncertainty and negation must survive. Reversing a negation is rejected.
- Introducing a make, model, or fault that is absent from the original utterance is rejected.
- Critical slots bind to the original utterance. Where support is uncertain, require confirmation instead of accepting the slot.
- Keep the existing safety rules that prevent the model from lowering severity. Do not relax them.

Add regression tests for: dropped year, reversed negation, invented make/model/brake failure, and a slot that cites only the translation.

Acceptance criterion: dropping a year, reversing negation, or introducing a vehicle identity cannot silently become accepted contact data.
```

---

## Prompt 07 — Four failing contracts

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Do not delete, skip, weaken, or xfail these tests. Fix the implementation or, where the test encodes the real contract, fix the implementation to match that contract. If a test’s expected value is the bug, state the intended contract in the test docstring and make the code match the safer contract. Do not change an assertion just to go green.

A targeted offline run produced 164 passed and 4 failed. reports/TEST_RESULTS.md at reports/TEST_RESULTS.md:25 also records four failures, and a clustering test exceeding 600 seconds. Do not describe the suite as green. You do not have to rerun the whole suite or fix the 600-second clustering test in this task. Do rerun the four failing tests until they pass, and update TEST_RESULTS.md only if you actually rerun and record the new counts honestly.

The four failures:

1. Correction rejection and diagnostic answer. Confirmation metadata disagrees with the expected correction behavior. Make the stored confirmation metadata match the correction that was accepted or rejected. The diagnostic answer and the metadata must describe the same outcome.

2. Disabled investigator. The investigator continues when recording its disabled outcome raises an exception. This is an implementation bug: the disabled return sits inside a broad exception handler in src/agents/investigator.py at src/agents/investigator.py:181. Logging failure must not enable a disabled agent. A disabled investigator returns the disabled outcome even if the audit write throws. Test that.

3. Scheduled speech and playback. A helper returns "No!" where the test expects True. Decide the intended return value from the existing caller contract (the test is the contract unless it contradicts a safety rule). Make the helper return that value. Do not special-case the test string.

4. Malformed WebSocket frame. The test receives a readiness frame before the expected response. Fix frame ordering so a malformed frame produces the expected error response in the order the test asserts, while a normal connection may still send readiness first. Document the order in the handler if it is not already documented.

Acceptance criterion: those four tests pass without being weakened. The disabled-investigator test fails if a logging exception lets the agent run.
```

---

## Prompt 08 — Evaluation evidence, remaining budget only

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Live Meta spend for the whole submission is capped at 30 USD. Prompt 02 may already have used up to 8 USD. This task may spend only what remains under 30 USD, and at most 22 USD. Stop when the running total reaches 30 USD. Record every call’s model, tokens, and estimated cost. Prefer a small frozen sample over a full 300-call run. If the remaining budget cannot finish a meaningful labeled run, do not start it. Leave the report at Not run.

The defect experiment remains Not run, with 0/300 human labels filled. The real Hindi collection/evaluation tooling has no collected real records and no completed human labels. The existing 84 Hindi/Hinglish examples are synthetic, and their Meta-enhanced evaluation was not run.

These are separate evidence gaps. Do not mix them in one accuracy number:

- Synthetic examples test known scenarios.
- Real held-out complaints test generalization.
- Human labels provide independent reference judgments.
- Model execution provides evidence about Meta behavior.

Before any accuracy or improvement claim, complete the evaluation that matches the claim, with frozen prompts, recorded inputs, human labels, and unsuccessful cases included. Do not invent labels. If humans have not labeled rows, those rows stay unlabeled and the metric stays unpublished.

Keep reports/oos/DEFECT_LEVEL.md (reports/oos/DEFECT_LEVEL.md:3) and the dashboard saying Not run until genuine artifacts exist. A partial run must be labeled partial, with the sample size, and must not be written as the 300-row result.

Do not raise the daily call cap to finish faster. The client default is 300 calls per day. Stay inside that cap and inside the dollar cap.

Depends on Prompt 04: the exporter must already emit model, prompt_version, and taxonomy_sha256, or this run will not load in defect_accuracy.py.
```

---

## Prompt 09 — Backtest interpretation and reproducibility

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Do not change shipped thresholds to obtain a headline number. Do not retune abs3 or abs5.

The submission must keep these results distinct. Update HACKATHON.md, reports/oos/BASELINES.md, and any dashboard copy that blends them:

| Existing result | Valid interpretation |
|---|---|
| 45.6% campaign recall, median 11 weeks | Historical full-window, in-sample production result. |
| 62.7% campaign recall, median 8 weeks | Separate tuned abs3 configuration on the OOS window. |
| Production abs5 on that OOS window | Not run. |

Broad make-and-component matching does not establish that a warning identified the same defect or root cause as a later recall. Say that next to both recall figures.

reports/oos/BASELINES.md at reports/oos/BASELINES.md:3 records unrun baselines. Leave them as Not run until you actually run them on the same data as the reported configuration.

The original input snapshot is absent, and the refreshed download has a different hash. Record both hashes, which file is missing, and which ingest settings produced the refreshed file. Do not pretend the hashes match.

For a credible comparison, preserve source manifests and ingest settings, evaluate baselines on the same data, and distinguish historical associations from causal defect identification. Independently audit model-generated recall labels as well as complaint labels: add a checklist or script that separates those label sources. Do not overwrite historical numbers.

Acceptance criterion: a reader can see which number is in-sample, which is tuned abs3 on OOS, and which is not run, and can see the input hash mismatch.
```

---

## Prompt 10 — Portable defect workflow and a budget plan (no live calls)

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not call the live API. Do not increase the 300-calls-per-day cap. Do not spend money.

Classifier defaults (scripts/defect_classify.py:606) and backtest defaults point into a private macOS temporary directory. Those paths will not exist on a judge’s machine.

Provide portable preparation commands, explicit input paths, source hashes, and clear missing-input errors. A missing file must name the path and the command that prepares it. Defaults must be relative to the repo or passed as flags, not a user-specific /var/folders or /tmp path from one laptop.

The dry-run estimate (reports/defect/classification_estimate.json:7) contains 18,998 estimated batches, while the client defaults to 300 calls per day. The full plan therefore needs a deliberate scope, rate-limit, retry, and budget decision. Write that decision into the defect report and the script help text:

- default judge/demo scope is a small explicit sample, not 18,998 batches
- 300 calls per day remains the cap
- retries are bounded
- estimated tokens and cost stay labeled as estimates
- a live full run is out of scope for this submission unless a later prompt authorizes a tiny sample under the 30 USD submission cap

Verify the estimate’s assumptions against the current prompt and a local token count of one real batch (local count only, no API). Correct the written assumptions if they disagree. Do not blindly increase the cap.

Depends on Prompt 04 for the export columns. This prompt does not run classification against Meta.
```

---

## Prompt 11 — Blocking routes and SIGTERM shutdown

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money.

WebSocket readiness improved, but other backend routes can still block it. A limited read-only probe measured WebSocket connection at approximately 14 ms, and eight concurrent dashboard snapshots completed within approximately 424 ms. Those measurements do not cover every endpoint. Do not cite them as proof that every route is non-blocking.

src/api/routes/platform56.py at src/api/routes/platform56.py:21 still calls synchronous analytics builders inside asynchronous handlers. The AI status route also calls synchronous usage accounting.

Offload that blocking work (thread pool or a non-blocking equivalent already used in this codebase). Add a test or a small harness that starts a slow analytics call and, while it is in flight, checks that a health check and a WebSocket connection still complete. Assert they are not stuck behind the analytics call.

Shutdown: src/ops/drain.py at src/ops/drain.py:89 handles SIGTERM by beginning drain without exiting. Observed: SIGTERM did not stop the running API; SIGINT did. Implement drain followed by a bounded graceful exit, particularly for containers. SIGTERM must eventually terminate the process after the drain deadline. Add a test with a short deadline that sends SIGTERM and expects the process to exit.

Do not remove the drain step. Exit after drain, within a bound.
```

---

## Prompt 12 — Judge setup from a clean checkout

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Do not print secrets.

scripts/judge_setup.sh at scripts/judge_setup.sh:29 has these reliability gaps:

- It continues when npm is absent, although the dashboard build is required. Missing npm must fail the script with a clear message.
- A failed npm ci can fall through to npm install. If npm ci fails, the script must stop. Do not hide the failure with npm install.
- A supervisor token expires after seven days but is reused whenever its file exists. If the token is expired or inside a day of expiry, mint a new one. Record the expiry in the file you already use.
- Existing seed data is reused without checking its version. If the seed version does not match the version this checkout expects, reseed or fail with the expected and found versions.

The operator API key is a service principal. It does not automatically establish a supervisor session. Test the actual browser authorization flow for each demonstrated action (read dashboard, open an investigation, whatever the demo claims). A service-principal key alone must not be documented as sufficient for supervisor actions.

Rehearse from a fresh checkout (a clean temp copy or a documented sequence that does not depend on this machine’s node_modules, seed files, or tokens). The documented commands in README and HACKATHON.md must be the commands you ran.

Depends on Prompt 03: setup must use the same env-loading launch as the rest of the docs.

Acceptance criterion: setup from a fresh checkout produces a usable UI, current credentials, correct roles, and the expected demo data through the documented commands.
```

---

## Prompt 13 — Submission snapshot, license, three-minute story

```
You are working in a checkout of https://github.com/rahulx2001/TraceX. If origin is still SkewAi, clone TraceX and work there. Do not push to SkewAi. Do not spend Meta API money. Do not rewrite git history. Do not force-push. Commit only what the owner asks you to commit; if they already asked to ship the submission, commit the pending submission files with a message that states why, then push the current branch. Push the submission snapshot to https://github.com/rahulx2001/TraceX, not to SkewAi. Judges need an accessible snapshot that contains the intended submission.

There is no root project license, and GitHub reports no detected license. Public visibility does not grant reuse rights. Add a license only after checking ownership in the existing docs and headers. If ownership is unclear, stop and say so instead of picking a license. Preserve dependency, model, and data attribution next to the license (NHTSA or other data sources, Meta model names, third-party packages).

Write a three-minute demo script in HACKATHON.md. One existing workflow only:

1. complaint evidence
2. the event-built Meta contribution (only if Prompt 02 produced a real artifact; otherwise say the live call is not in the video)
3. an operator decision
4. the audit trail

Label simulations and pre-existing components as reused. WhatsApp is a mock. Vision and SAM stay unverified unless Prompt 02 actually called them. Show only demonstrated functionality.

For impact, name the actual user and the operational benefit (investigation time or triage quality) as a target, and state what is not yet shown: US historical records and synthetic Hindi examples do not establish effectiveness for Indian fleets or bikes. Do not claim that effectiveness.

Include the rubric gaps as a checklist the owner can see, without marketing language:

| Criterion | Main gap |
|---|---|
| Impact — 30% | Independent evidence of usefulness to a specific operator. |
| Meta tooling — 25% | Meaningful, successfully executed Meta contribution. |
| Execution — 20% | Correct grounding, compatible artifacts, passing contracts, reproducible setup. |
| Demo — 25% | Reliable three-minute workflow showing eligible work. |

Do not mark a gap closed unless the corresponding prompt’s acceptance criterion is met in this tree.
```
