# Procedural prospective custody

Custodian: Rahul Kumar Singh. Recorded 2026-10-31T15:10:06.484940+00:00.

Storage is an encrypted APFS image outside the repository, volume label
RCA-PROSPECTIVE. The human holds the passphrase; it is never stored in the
repository, environment, shell history or agent-accessible keychain. The agent
does not create, mount, encrypt or populate the image in this task.

This is **tamper evidence, not access control**. NHTSA complaints and recalls
are public, and a determined process can re-fetch them. No-peeking is an
honor-system limitation. Same-account bypass is acknowledged, not tested away.
Integrity rests on preregistration, the frozen code/model, published hashes,
the committed manifest chain and a committed human attestation. A marker UUID
identifies the intended volume; it does not prove encryption or independence.
The human must verify APFS encryption and unmount the image before agent work.

External timestamp proof is pending until a receipt/proof is actually obtained
and verified. A local git timestamp alone is not independent evidence of time.
