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
