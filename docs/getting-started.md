# First run: report to evidence

Use the [README offline quickstart](../README.md#try-the-offline-demo) to install
the Python dependencies, build the dashboard and start the demo. It requires
Python 3.12, Node 20.19+ or 22.12+, and npm. The terminal must stay open while
you use the app. Installation needs network access; the offline application
does not call an AI provider.

Open **http://127.0.0.1:8770/ui/#demo**. No account, `.env` file, model download
or provider key is needed for this fictional walkthrough. The interface says
**AI assistance is off**. Reports and manual review still work; offline mode
does not generate model observations or interpretations.

## Complete the workflow

1. Choose **Start a report →**, then **Type instead**. Answer the consent
   question. For a report that matches the prepared fictional vehicle, type
   **My 2021 Honda City knocks over bumps**. You can add **No fire** or a
   correction as a separate reply. Wait for each reply to be sent before
   continuing. The original turns are retained.
2. Choose **End call**, then **Investigate this report →**. Select the
   LotGuard EPS B14 campaign and the matching **EPS-CITY-001** vehicle. Inspect
   the stored turns and confirm both the source review and vehicle association.
   For your own records, select only a vehicle the report actually concerns.
3. Choose **Run sourced investigation**. In offline mode the result is a
   manual investigation with the report and its source references. AI-created
   claims and model-selected lookups remain unavailable. Original report IDs
   and source hashes carry into the saved result without retyping.
4. Inspect the source. Under **Draft decision**, choose **needs correction**
   when further work is needed, enter an **Evidence review note**, confirm
   that you reviewed the evidence, and choose **Record draft review**.
   Choose **Create revised investigation** to retain that review in a linked
   revision. The original draft and decision remain available in history.
5. Review the revision. **accepted for investigation** records acceptance of
   the investigation draft; it does not approve a repair or release a vehicle.
   In offline mode, your note records the manual assessment. When AI is
   configured, its observations and claims also require individual review.
6. Choose **Export evidence ↗**. The downloaded JSON includes the campaign,
   stored source turns, original investigation, review, and linked revision.
   Reopening **Recorded investigations** restores saved work. Refreshing the
   page does not start another investigation.

The campaign, installation records, owners and repair outcomes are fictional.
The local demo permits review of its synthetic campaign with the `agent` role.
An authenticated installation requires the appropriate authorized reviewer for
a real campaign; see [entry and authentication](entry-auth-validation.md).

## Inspect the prepared case

Open **http://127.0.0.1:8770/ui/#cases** and select **LOT ALERT**. This provides
the existing eleven-report walkthrough, fictional batch trace, simulated
outreach and repair evidence. Follow the [LotGuard guide](../LOTGUARD_DEMO_WALKTHROUGH.md)
for exact screens and denominators. The historical classifier evaluation is
[Round 4: 82.0% accuracy, macro-F1 0.514](../reports/improvement/human_reviews/round4/EVALUATION.md).
That historical evaluation is separate from the fictional campaign outcomes.

## Stop, resume or use a separate demo

Stop the server with **Ctrl-C**, then rerun this command from the repo root:

```bash
.venv/bin/python scripts/run_lotguard_demo.py --offline
```

The launcher preserves the demo's stored records in `data/hackathon/eps-b14`.
An active call cannot survive a server restart; its persisted turns remain.
To keep another independent set of demo records, choose a new state directory:

```bash
.venv/bin/python scripts/run_lotguard_demo.py --offline --state /tmp/tracex-second-demo --port 8771
```

Open `http://127.0.0.1:8771/ui/#demo` for that instance. Use a different port
when the original server is still running.

## Troubleshooting

| Symptom | Action |
|---|---|
| `python3.12` is missing | Install Python 3.12 and rerun the virtual-environment step. |
| A package cannot be imported | Run `.venv/bin/python -m pip install -r requirements.txt -c requirements-lock.txt` from the repo root. Use the same `.venv/bin/python` to launch. |
| `Dashboard build missing` | Run `npm ci --prefix dashboard`, then `npm run build --prefix dashboard`. Restart the launcher. |
| Port 8770 is already in use | Choose `--port 8771` and open the corresponding URL. |
| The page cannot connect | Wait for the terminal's **Start here** URL. Keep that process running and include `/ui/` in the browser address. |
| No AI interpretations appear | Expected with `--offline`. Manual report review and export remain available. Live providers need separate configuration and credits. |
| A saved investigation seems absent after refresh | Select the same campaign and its entry in **Recorded investigations** before starting another request. |
| Microphone is unavailable | Choose **Type instead**. Browser speech needs separate permission and a supported Chrome-family browser. Typed checks do not validate microphone quality. |

## Recheck this path

After installing the application and dashboard dependencies, install the test
browser once and run:

```bash
npm exec --prefix dashboard -- playwright install chromium
npm run test:demo --prefix dashboard
```

This builds `dashboard/dist`, launches `scripts/run_lotguard_demo.py --offline`
with temporary state, enters a matching fictional Honda City report through
the browser, records a correction and linked revision, reloads the saved
history and checks the downloaded evidence. It makes no provider calls and
creates no participant or model-performance results.

The runner uses `.venv`, then `.venv-hackathon`, then `python3` from PATH.
Set `E2E_PYTHON=/path/to/python` to use a different installed environment.
`npm run test:signin --prefix dashboard` checks authenticated roles and the
broader existing UI scenarios. See the [finishing verification record](finishing-verification-2026-11-05.md)
for the environment and results of the recorded run.
