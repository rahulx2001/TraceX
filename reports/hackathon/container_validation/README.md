# Container execution — 30 October 2026

The current investigation container passes its real browser and API workflow
with **zero model calls**. The image was built from a clean checkout of
`edfda13e616314480c3501ba9b1a600c1e42ff88` using `--pull --no-cache`.
This is fictional text/software evidence, not a real-audio, participant,
mechanical-defect, hosted-demo or productivity result.

| Execution | Evidence | Result |
|---|---|---|
| Linux arm64, Docker 29.5.2 in isolated Colima, bare image | [result](edfda13-arm64-attempt1.json), [browser log](edfda13-arm64-attempt1.browser.log), [container log](edfda13-arm64-attempt1.container.log), [build](edfda13.build.log) | Passed |
| Same image through documented Compose service, Compose 5.6.1, new isolated data volume | [result](edfda13-compose-arm64-attempt1.json), [browser log](edfda13-compose-arm64-attempt1.browser.log), [container log](edfda13-compose-arm64-attempt1.container.log) | Passed |
| Compose with an added visible forbidden-action check | [result](edfda13-compose-arm64-attempt2.json), [browser log](edfda13-compose-arm64-attempt2.browser.log), [container log](edfda13-compose-arm64-attempt2.container.log) | Passed; operator campaign creation returned 403 and showed a permission error |
| GitHub Ubuntu runner, clean image and Chromium browser | [public CI run](https://github.com/rahulx2001/TraceX/actions/runs/41035375574), [retrieved job/step results](ci-edfda13.json) | Passed |
| Packaged candidate `db6c7ba`: clean Compose image, Chromium and visible operator 403 | [public CI run](https://github.com/rahulx2001/TraceX/actions/runs/41036898751), [job/step results](ci-db6c7ba.json) | Passed |
| Public repository and exact packaged candidate in a fresh signed-out browser | [anonymous source check](public-source-db6c7ba.json) | Both HTTP 200; no saved user cookies or account |
| Trust bootstrap, legacy migration, existing-row preservation and voice software contracts | [60 focused Python tests](focused-tests.log) | Passed; one Starlette deprecation warning |

All local browser executions verified visible sign-in, refused invalid key,
accepted operator key and supervisor session, then a typed report containing
“No fire” and a corrected model year. Original punctuation-free turns remained
citable exactly once. The review handoff used stored source references without
retyping, the correction note reached a linked revision, the supervisor review
recorded its actor, and export contained the original and revised packets.
This uses manual/deterministic fallback; it does not test a new Meta result.

The API checks verified anonymous refusal, the current campaign, inspectable
fictional installation evidence with simulated trace reviews, all five review
pages and their JavaScript. Restart preserved the campaign and local trust
identity. The key file was mode `0600`. No local media or host data was mounted.
The Compose run used a unique disposable project/volume, excluded local `.env`
and disabled inference. Its override selected the already-built image, random
loopback port and test container name; it did not replace the shipped service's
entrypoint or data-volume setup. All test containers/volumes were removed.

The Compose result fingerprints the extended verification runner separately
from the image commit. CI now uses that Compose route on every readiness-branch
commit, including packaging commits. The latest public workflow result identifies
the exact checked SHA; the saved run above remains evidence for its own SHA.
The clean checkout of `db6c7ba` also passed the standard-library public replay
and the source manifest's working-tree verification (1,170 files). Subsequent
evidence/manifest commits package these records; they do not change runtime code.

## Failures retained and fixes

| Attempt | Observed failure | Repair |
|---|---|---|
| [8edc0fd, attempt 1](8edc0fd-arm64-attempt1.json) | Fresh image refused startup: no configured trust root | Unique local pilot key creation; existing and production trust stay operator-owned |
| [e240143, attempt 1](e240143-arm64-attempt1.json) | First report returned 500: legacy `agent_actions` lacked `ts` and other runtime columns | Additive migration 004 completes ledger/case columns, preserves existing rows/hashes and converts the original timestamp to UTC |
| [e240143, attempt 2](e240143-arm64-attempt2.json) | Restart test timed out while the container was healthy on a newly allocated port | Runner rereads Docker's assigned port after restart |
| [41f7d87, attempt 1](41f7d87-arm64-attempt1.json) | Saved transcript returned 500: DuckDB TIMESTAMPTZ decoding needed absent `pytz` | Add the existing lockfile-pinned timezone dependency to the Docker runtime |

The initial CI runs [41033514683](https://github.com/rahulx2001/TraceX/actions/runs/41033514683)
and [41035097675](https://github.com/rahulx2001/TraceX/actions/runs/41035097675)
failed. Public job metadata was readable; unauthenticated log download returned
403. The specific failure diagnoses above come from the retained local container
logs, not an assumption about hidden CI logs. The 41f7d87 build was initially
labelled with the short SHA, then [relabeled using cached identical source
layers](41f7d87.full-revision-label.log) with its full SHA before testing.

Reproduce with [the container setup and verification commands](../../../docs/container-validation.md).
The generated trust key belongs to the older contact evidence-locker path;
the campaign packet remains unsigned. Real reviewers and consented multilingual
audio remain pending. The owner confirmed one team member and deferred portal
upload until checks are complete. Hosted demo and video are outside this pass.
