# Account-free local demo — 2026-11-01

Open <http://127.0.0.1:60861/ui/#command>. The API is healthy and the local demo
does not require sign-in. Its isolated database contains 15 completed simulated
contacts, 15 open/follow-up cases and three issue groups. The command center
includes test traffic; zero active contacts is correct when no report is live.
The fictional records are software demonstrations, not evaluation observations.

The old “Server: offline / deterministic” label conflated server availability
with hosted inference configuration. The badge now says “AI: local rules” when
the responding server has inference disabled. A failed configuration request
instead says “AI status unavailable”; a configured provider is labelled as
configuration, without implying an actual model call. The demo introduction
describes the available local/manual workflow and labels historical replays.

Seeding now enables the test-traffic filter, so generated cases become visible.
The same preference carries into the case queue and survives reloads. Simulator
errors and abandoned contacts are reported. Eleven live localhost endpoints,
including operations analytics, were checked successfully; see
`runtime_snapshot.json` for the observed state and timestamp.

## Supported demonstration

Use **Report → Type instead**, enter a fictional report and any corrections,
then end the contact. **Investigate this report** preserves the stored turns.
Select a vehicle in the prepared fictional campaign and confirm the source and
vehicle association. A run with hosted AI disabled saves a manual fallback and
its source evidence with zero model calls. Review the draft, inspect installation
records and export the evidence packet. Synthetic campaign review is available
to the local operator without granting supervisor privileges over real records.

Hosted model interpretation, photo analysis and external messaging are not
enabled by this change. Voice capture also depends on browser microphone/speech
support; the real workflow check uses text. Synthetic browser voice tests do not
establish real-audio accuracy. Human semantic labels remain 0/300. Baseline
scores and both prospective freeze sets remain unchanged.

## Restart the same demo

From this worktree, after the existing process has stopped:

```sh
PYTHONDONTWRITEBYTECODE=1 FRONTLINE_TEST_ISOLATION=1 \
OPENAI_API_KEY= ANTHROPIC_API_KEY= BASETEN_API_KEY= META_API_KEY= \
.venv-hackathon/bin/python -B -m scripts.investigation_demo_server \
  --port 60861 \
  --state-directory /private/tmp/rca-ml-handover-local-20261101 \
  --without-recorded-proof --existing-state-only
```

This reuses the isolated rehearsal database. If temporary files have been
removed, use a new empty rehearsal directory without `--existing-state-only`,
then use **Seed demo traffic** once. That action runs real local orchestration
and can take about two minutes for 15 contacts. It makes no hosted model call.
The unrelated server on port 8768 and original checkout are untouched.

## Validation evidence

`validation.json` records the final check results and input hashes.
`final/` holds build and auth checks. Browser checks use temporary servers,
real local API/WebSocket transport, fictional campaigns and the existing
report-handoff regression; AI configuration display failure tests use explicit
mocks. Logs include prior failures rather than overwriting them.

- Initial browser run: the default 30-second event timeout expired while the
  real 15-contact simulator was running; increased to 120 seconds.
- First retry: test compared the open-only case view against an unfiltered API
  query; corrected the test query and waited for case-page navigation.

No full-suite count is claimed for this UI change. The earlier 2,039-test
handover is a historical result, not a newly executed run. No model fitting,
prospective outcomes, paid calls, external delivery, merge or promotion occurred.
