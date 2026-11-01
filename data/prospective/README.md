# Prospective metadata only

Raw data belongs on the human-mounted encrypted APFS image outside this repository.
The UUID in custody.json must match .rca-custody on that image. No passphrase is
stored here. The collector does not encrypt; the human verifies APFS encryption.
Procedural custody is tamper-evident, not access-control; no-peeking is honor-system.
No real prospective data has been collected.

The manifest is a committed hash chain. Commit each update before collecting
again. Never copy raw files, labels, disk images or keys into this directory.
A missing classification input at final analysis is a hard failure, not a reason
to impute labels. See the human runbook added in Phase 6.


## Human operations runbooks — added 2026-11-01

Use [RUNBOOK.md](../../reports/improvement/prospective/RUNBOOK.md) for collection
in 2027–2028, the final outcome snapshot after 2029-12-31, metadata freezing,
human attestation and one final frozen-code analysis. The
[attestation template](../../reports/improvement/prospective/UNTOUCHED_ATTESTATION_TEMPLATE.md)
is not a completed attestation. Preserve the append-only
[deviations log](../../reports/improvement/prospective/DEVIATIONS.md).

The frozen mode is baseline replication. No improved score is demonstrated;
human semantic validation remains 0/300. No real prospective data was fetched
or inspected by the engineering task. The collection log is empty. Phases 7–8
remain future human-only work; no collection, final analysis, merge or promotion
was executed. Keep the encrypted image unmounted during agent work.

The Phase 2 acceptance gate includes the explicitly approved historical
preparation amendment DEV-20261101-01. It does not authorize future-outcome
peeking, historical-data tuning, or changes to the immutable freeze tag.
