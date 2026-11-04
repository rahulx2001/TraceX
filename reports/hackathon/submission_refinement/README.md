# Submission refinement checks

This follow-up adds the final public 180-second [demo](https://youtu.be/Uq7_kra8q-M),
[judge guide](../../../SUBMISSION.md), [18-file export inventory](../../improvement/human_reviews/EXPORT_INDEX.md),
owner-supplied synthetic packet and downloadable frozen model-to-alert replay.
It does not create new provider outputs, labels or real-participant results.

- [Verification scope, runtime and source hashes](verification.json)
- [Saved-artifact arithmetic, quotations and current claim hashes](public_artifacts.json)
- [Export/import provenance and all 43 Round 4 adjudication checks](review_evidence.json)
- [Local frozen model-to-alert replay](local_model_replay.json)
- [Ten archive and review regression tests](replay_regressions.txt)
- [Fresh anonymous public-source, release replay and video verification](public_download_verification.json)

The local model replay matches the selected method, count baseline, opportunity
diagnostic and all 100 random references: 5/8 campaign hits and 6/18 mature-alert
matches. The source projections remove all free-text columns. Neither historical
scores nor original experiment source files were altered. The reviewer checker
validates structure and hashes; it does not establish independence or correctness.

The focused local runtime is Python 3.14 with existing NumPy/pandas; the project
application, CI and documented fresh environment target Python 3.12. Historical
full application/container checks retain their original commits and dates.
The fresh anonymous download replay passed for implementation commit
`2314f6352f45b97b0d4809161c80b48f5f70c1a5`, and the final video metadata is
public with a duration of 180 seconds. Four existing package/manifest/citation
checks also passed. Later metadata and receipts are separately packaged by the
source manifest; historical container CI is not relabelled as current execution.
The service-professional study remains pending because no
tester is available; [the pilot plan](../../../docs/pilot-validation.md) prepares
collection without inventing participants or outcomes. Portal submission and a
hosted deployment are not verified by these repository checks.
