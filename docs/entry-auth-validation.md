# Judge entry and authentication validation

Start at `/ui/#demo`. An authenticated server opens credential entry, then returns to the requested page. The operator API key shown by `scripts/judge_setup.sh` permits operator work; it does not grant supervisor authority. Use **Have a supervisor session?** on `/ui/#signin` for the separately issued supervisor token. The server validates that token and exchanges it for an HttpOnly cookie. Sign-in remains available in open local mode, where anonymous access retains the `agent` role.

The main judge entry is Report → Investigate → Review → Evidence. The earlier intake/LotGuard tour remains at `/ui/#legacy-demo`. Prepared campaign records are fictional; saved Meta output is explicitly replayed and is not a new inference.

Run the current production-build browser check from `dashboard/`:

```sh
npm run test:signin
```

This requires installed dependencies, a Playwright browser (`npx playwright install chromium`) and the local `.venv-hackathon` Python environment. `PLAYWRIGHT_CHANNEL=chrome` selects an installed Chrome; `E2E_PYTHON=/path/to/python` selects another environment with the project dependencies.

The check builds into a new temporary directory and starts the actual API with temporary databases, an automotive mini-fixture, fresh test credentials and all model calls disabled. It verifies:

- A clean browser reaches rendered sign-in when opening a protected route.
- An invalid API key stays refused; a valid operator key is accepted without disk persistence unless selected.
- An operator sees the server's refusal when attempting a real-campaign draft review.
- An issued supervisor token becomes an HttpOnly cookie and permits a review whose saved actor matches the authenticated supervisor.
- A real local text contact sends consent, a punctuation-free report, a denial and a year correction over WebSocket. Every turn remains citable. A recorded correction review becomes a linked revision without retyping, and the downloaded packet retains both reviews and the original turn IDs. This exercises manual fallback with model calls disabled; it does not establish model obedience to a correction.
- Open local mode needs no credential, still exposes sign-in and retains `agent` authority.

No developer credentials, running demo server, external service, model credit or human evaluation result is used. These are UI/authentication regressions, not speech-quality or productivity measurements. Temporary fixture records are explicitly fictional even though the permission test exercises the non-demo campaign policy.

The same command also runs the current voice-control and investigation-handoff UI contracts. Those additional checks use explicitly synthetic browser-intercepted transport/source responses to exercise keyboard start, text-only operation, correction history, review/vehicle gates, original-record citations, linked revisions, truthful feedback failures and trace-review navigation. They are separate from the real-backend authentication checks above; they do not measure transcription quality, claim accuracy or live inference latency.

To verify that a missing registry entry is detected, run:

```sh
npm run test:signin -- --missing-route-control
```

This negative control omits only the sign-in registry entry from its temporary build and must exit nonzero at the rendered sign-in assertion. It never edits `App.jsx` or the submitted build.
