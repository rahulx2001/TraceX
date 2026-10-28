# TraceX repair results — 28 October 2026

**Known source and judge-flow blockers from the review are repaired locally.**
TraceX is a suitable Indie / Build for Your World prototype. This is evidence
of the checks below, not a certification that every possible issue is absent.
The original review is a historical snapshot; this report supersedes its
runtime, test and demo status.

## Verified results

| Check | Result |
|---|---|
| Complete backend suite, Python 3.12.13, isolated warehouses and provider state | **1,794 passed**, 575.27 seconds, **no tests deselected or skipped**; one Starlette TestClient deprecation warning |
| Documented `make test` target (dashboard build + MiniLM verify + `tests/frontline/`, 30-second per-test timeout) | **1,755 passed**, 759.59 seconds, `EXIT:0`; the 39 tests outside `tests/frontline/` are in the full-suite row |
| Full Playwright suite against a clean-checkout judge server (real Chrome) | **54 passed**: API auth/SSRF/export specs, all UI routes and operator loops, and the judge sign-in/takeover workflow |
| Affected AI/UI/session tests (earlier targeted run, superseded by the full suite above) | **173 passed**, 37.49 seconds |
| Dashboard production build, theme and QA-label checks | Passed; existing bundle-size and ineffective-dynamic-import warnings remain |
| Pinned MiniLM model/tokenizer hashes and runtime initialization | Passed |
| Automotive + finance offline evaluation | **23 gates passed** (12 automotive, 11 finance) |
| Real sockets during deliberately slow analytics | Health 200 and console WebSocket handshake complete before the slow request finishes |
| SIGTERM with a held active contact | Begins draining, reaches the short deadline, exits and logs completed application shutdown |
| Fresh judge setup | Passed in a temporary source copy without `.env`, node_modules, venv, credentials or runtime data; dependencies installed independently |
| Real Chrome judge workflow | Passed operator-key login, recorded-proof display, supervisor-cookie login, takeover and release; no page exceptions |
| YAML and embedded shell syntax | GitHub Actions and hackathon Compose parse; all workflow shell steps pass `bash -n` |
| Local dependency consistency and compilation | `pip check`, `compileall` and shell syntax checks pass |
| Demo draft | **178.24 seconds**, 1280×900, MP4; silent with captions. Frames from the translation, takeover and final evidence screens inspected |
| Docker image execution | **Not run locally**: Docker CLI unavailable. Separate hackathon-image CI smoke job added; its next run must be checked |

The full suite above is the final run on the current tree and includes every
repair listed below. The previously deselected 5,005-record cluster test now
passes in about 1.8 seconds, so the reported total has no exclusions. The
browser suite was updated only where old specs contradicted the current
security model (sanitized `/health`, admin-only `ops:write`, simulated-case
filtering); every assertion still exercises the same product behavior.

## Live Meta proof

[`hackathon/meta_live_smoke.json`](hackathon/meta_live_smoke.json) records a
real **muse-spark-1.3** request to **https://api.meta.ai/v1**. The synthetic
Hindi complaint becomes:

> My 2019 Honda CR-V makes a grinding-like sound when pressing the brake while moving slowly.

The final complete workflow creates **case_01m611b8w1wh1whqzs4s2hc0yy**, ends
in **DONE**, and has **37 verified ledger actions** with no emergency flag
invented by the scripted replies. The accepted intake event and original
source text are in the artifact. Exported ledger actions verify independently
of the temporary runtime database:

```bash
FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python - <<'PY'
import json
from pathlib import Path
from src.ledger.chain import verify_chain
p = json.loads(Path('reports/hackathon/meta_live_smoke.json').read_text())
r = p['checks'][0]['result']
print(verify_chain(r['ledger_actions'], allow_partial=True))
PY
```

`allow_partial=True` checks the exported rows without asking the current
database for a newer tail. It does not claim that complaint statements are
independently true.

The lifetime client ledger reports **$0.06529575 observed token cost** and
**$2.373128 conservative reservations**, against the **$8 proof-run cap**.
Reservations retain failed attempts and include earlier client use. The
client's maximum configurable total is $30; unrelated account activity is
outside this ledger.

Failed/intermediate artifacts are preserved alongside the successful proof.
The four-second default timed out; the tested, bounded default is now 20
seconds. A prior successful translation did not complete a case because the
script supplied ambiguous safety replies. The final script answers each
actual safety/confirmation question separately and the final proof requires
a created case. No success marker was fabricated.

Only text intake is live verified. Vision, SAM, image generation and inference
partners remain optional/unverified; video clips are stored for human review.

## Repairs

- Server `.env` loading respects exported values; tests isolate local keys,
  provider transports, databases and accounting files.
- Meta requests use allow-listed hosts, host-bound remote-ID recovery,
  bounded retries and transactional lifetime budget reservations.
- Translation checks preserve numeric occurrences, recognized identities,
  critical concepts, negation, uncertainty and clause polarity. Unsupported
  slot values remain proposals for confirmation.
- Grounded brief claims must copy full cited source sentences. Unsupported
  paraphrases and headlines cannot gain authority by attaching record IDs.
- Malformed medical/consumer YAML is repaired. Large cluster rebuilding uses
  bounded scoring and batch database writes; all 5,005 fixture assignments
  remain asserted.
- The defect classifier exports the provenance required by its evaluator;
  its paths are portable, pandas is declared, and live runs require a bounded
  batch limit. The 18,998-batch plan is explicitly outside this demo.
- Blocking analytics and usage accounting leave the event loop. SIGTERM
  forwards shutdown after a bounded drain.
- Dashboard sign-in routes are restored instead of redirecting judges into
  an unauthenticated console. Issued supervisor credentials exchange into
  HttpOnly cookies without role elevation. Nested API-key forms are removed.
- Judge setup fails on dependency-install failures, verifies/renews signed
  supervisor tokens, preserves versioned fixture data, supports an alternate
  local port and seeds without Meta spend. Token-creation errors now fail the
  setup instead of being hidden by an `export` command.
- Container seeding disables models. Compose requires a distinct session
  secret and stores budget/cap/resource state in its persistent data volume.
  The image includes the synthetic proof and excludes local venvs/videos.
- Indie-only documents distinguish reused foundation from event repairs,
  identify the actual original commits, and qualify historical/synthetic
  results. MIT application license and third-party notices are present.

## Demo and remaining submission actions

Local video: `reports/hackathon/demo-draft.mp4` (gitignored). It is a silent,
captioned draft showing recorded live synthetic Meta evidence, fixture case
review, and a separate simulated supervisor contact. It shows the final
complete saved Meta proof throughout. The video does not pretend the saved
complaint and separate supervisor contact are one live call. Use
[`../DEMO_SCRIPT.md`](../DEMO_SCRIPT.md) when adding narration.

The verified fresh setup was:

```bash
bash scripts/judge_setup.sh --no-serve
API_PORT=8765 bash scripts/judge_setup.sh
# port 8000 was already occupied by another local process
```

The browser check ran against that server with `PLAYWRIGHT_CHANNEL=chrome`,
`TRACEX_JUDGE_DATA` set to its isolated `judge-v2` directory and
`BASE_URL=http://127.0.0.1:8765`. Credentials are intentionally omitted.

| Submission item | Status |
|---|---|
| One selected track and clear problem | Indie / Build for Your World documented |
| Working Meta contribution | Live text-to-case proof verified |
| Local judge workflow and regression checks | Passed as recorded above |
| Reused-code provenance | Original commits linked; imported foundation identified honestly |
| Independent operator impact, real Hindi accuracy, human defect labels | Not established; no unsupported accuracy/impact claim made |
| Video | Local draft prepared; review narration and portal format before upload |
| Public submission revision | **Pending**: changes are local and uncommitted; no push or submission made |
| Official existing-code and deliverable clauses | Not present in the supplied page; owner has accepted rules. No additional eligibility ruling inferred |

Publish only the intended verified snapshot to **rahulx2001/TraceX**. The
`tracex` remote points there; `origin` still points to **SkewAi**. Preserve the
history and confirm the newly published CI results. The supplied deadline is
4 November 2026, 9 PM Eastern (5 November, 7:30 AM IST).
