# External timestamp verification

The frozen manifest records pending human verification. A calendar receipt, if
obtained in Phase 4, is committed separately; it is not a verified Bitcoin timestamp.
Only the hash of FREEZE_HASHES.sha256 is submitted, never outcome data or secrets.
Do not change the frozen hash index or tagged receipt. Use a copy for upgrades.

```sh
python3 -m venv /private/tmp/rca-ots-human
/private/tmp/rca-ots-human/bin/python -m pip install opentimestamps-client==0.8.0
shasum -a 256 -c reports/improvement/phase1/FREEZE_HASHES.sha256
shasum -a 256 -c reports/improvement/phase1/freeze_manifest.sha256
```

If no receipt exists, create one with the following command and record it in an
append-only timestamp addendum without moving the freeze tag:

```sh
/private/tmp/rca-ots-human/bin/ots --no-cache stamp reports/improvement/phase1/FREEZE_HASHES.sha256
```

To verify later, copy FREEZE_HASHES.sha256 and its .ots receipt into a temporary
folder, then run `ots upgrade <copy>.ots` and `ots verify <copy>.ots`. Verification
requires a trusted Bitcoin node or a documented independent verification method.
Commit the verification transcript and proof hash as an addendum. A pending
calendar attestation alone is not evidence of a confirmed external timestamp.
No remote push is authorized by this runbook.
