# Human prospective operations runbook

Owner/custodian: Rahul Kumar Singh. Written 2026-11-01. This document does not
authorize or execute collection now. Phases 0–6 are engineering/documentation;
Phase 7 is human-run collection/final analysis and Phase 8 is a separate human
merge decision. Neither future phase is marked complete.

Frozen mode: **Mode B baseline replication**, tag `ml-prospective-freeze-2026`,
commit `e96338df3cce113a182b0cf1be5bf760abc00b31`. No improved score is demonstrated.
Human semantic labels remain 0/300. No paid model call is authorized here.

## Invariants and schedule

- Flags: 2027-01-01 through 2028-12-31; outcomes through 2029-12-31.
- Scope: Ford, Honda, Hyundai, Kia, Toyota; MY2015–2024; repaired FUEL SYSTEM.
  Preserve the existing labels/matching rules, 91-day cooldown, 7–364-day
  horizon, unknown-label treatment and full-follow-up precision denominator.
- Quarterly source snapshots are preferred, annual snapshots are the minimum
  for 2027 and 2028. A final snapshot on or after 2029-12-31 is also necessary
  to establish the outcome cutoff. Do not freeze the data manifest prematurely.
- Minimum 25 evaluable campaigns; prefer 30. One final analysis by 2030-06-30.
  Never lower the sample floor or extend the window after inspecting metrics.
- Use the frozen code/model; do not re-run development selection. Opened
  2021–2026 history is descriptive only. DEV-20261101-01 acknowledges the
  historical preparation read; it is not permission for new development reads.
- No merge, promotion, push, paid call, or signing-key creation follows from
  this runbook. Any remote publication or production decision needs separate
  human authorization. The freeze tag must never move.

## Custody is procedural

The human manages an encrypted APFS disk image outside every repository
worktree, with volume label `RCA-PROSPECTIVE`. Hold the passphrase personally;
never place it in repository files, environment variables, shell commands or
history, logs, or an agent-accessible keychain. Mount/unmount through macOS's
interactive facilities and verify encryption there. The collector itself does
not encrypt or prove encryption. A marker proves identity, not access control.

Public NHTSA records can be re-fetched. No-peeking is honor-system. Tamper
evidence relies on pre-registration, the frozen artifacts, published hashes,
the committed manifest chain, and a human attestation. Do not leave the volume
mounted during agent work. Raw ZIPs, classifications, keys and disk images stay
outside the repository; only metadata/hashes and the eventual reviewed final
reports belong in Git.

## Collection in 2027 and 2028

Use a clean human-maintained checkout of `ml-score-improvement`. The tag and
all commits must be available locally. Replace angle-bracket placeholders with
actual values; do not paste the examples unchanged. Use a fresh separate
environment built from `reports/improvement/phase1/requirements-prospective.txt`.
Never install into the original shared `.venv-hackathon`.

1. Mount the encrypted image through macOS; verify it is writable and is
   outside every worktree, with no symlink in its path.
2. Verify `.rca-custody` contains this exact UUID, also recorded in
   `data/prospective/custody.json`:
   `770b71da-b9f2-4624-af9e-25c6e3d4e7ac`.
   On initial human provisioning, create the marker on the intended encrypted
   image only after confirming its identity. A missing marker on later runs is
   an error; do not recreate it merely to bypass a refusal.
3. Verify the freeze and prior committed manifest, then collect the completed
   period. The collector rejects future periods, dates outside 2027–2028,
   missing flags, symlinks, invalid markers and duplicate snapshot IDs.

```sh
git status --porcelain
git rev-parse ml-prospective-freeze-2026^{commit}
shasum -a 256 -c reports/improvement/phase1/FREEZE_HASHES.sha256
shasum -a 256 -c reports/improvement/phase1/freeze_manifest.sha256
'<FRESH_VENV>/bin/python' -B -c 'from pathlib import Path; from src.eval.prospective_io import verify_freeze; verify_freeze(Path.cwd())'
cat '<CUSTODY_ROOT>/.rca-custody'
'<FRESH_VENV>/bin/python' -B -m scripts.seal_prospective \
  --seal --confirm-public-data \
  --custody-root '<CUSTODY_ROOT>' \
  --start 2027-01-01 --end 2027-03-31 \
  --snapshot-id '<UNIQUE_SNAPSHOT_ID>'
```

For later quarters/years, choose the relevant dates within 2027–2028 and a new
ID. Both configured NHTSA sources are downloaded: `FLAT_CMPL.zip` and
`FLAT_RCL_POST_2010.zip`. ZIP row counts count source records; they are not the
in-scope eligible campaign denominator. The command fetches full source
snapshots; the final frozen parser applies the registered scope/windows.

4. Independently verify each external ZIP's SHA-256 and source row count against
   `<CUSTODY_ROOT>/<SNAPSHOT_ID>/snapshot.json`. Verify that file's SHA-256
   against the new entry in the repository manifest. Do not print raw records.

```sh
shasum -a 256 '<CUSTODY_ROOT>/<SNAPSHOT_ID>/complaints.zip' \
  '<CUSTODY_ROOT>/<SNAPSHOT_ID>/recalls.zip' \
  '<CUSTODY_ROOT>/<SNAPSHOT_ID>/snapshot.json'
'<FRESH_VENV>/bin/python' -B -c 'from pathlib import Path; from scripts.seal_prospective import row_count; p=Path("<CUSTODY_ROOT>/<SNAPSHOT_ID>"); print({n:row_count(p/n) for n in ("complaints.zip","recalls.zip")})'
git diff -- data/prospective/manifest.json reports/improvement/prospective/collection_log.jsonl
```

Confirm exactly one snapshot/log record was appended, all prior entries remain,
`prev_sha256` equals the previous committed manifest's SHA-256, and no raw rows,
passphrase or absolute custody path entered Git. The manifest is replaced
atomically, but the manifest/log pair is not a transactional database. If a
write/fetch was interrupted, preserve the partial snapshot and log the failure;
never reuse its ID or silently discard evidence. Reconcile metadata under a
documented deviation before continuing.

5. Commit only the new metadata and log on `ml-score-improvement`:

```sh
git add data/prospective/manifest.json reports/improvement/prospective/collection_log.jsonl
git commit -m 'Prospective collection: <SNAPSHOT_ID>'
'<FRESH_VENV>/bin/python' -B -c 'from pathlib import Path; from src.eval.prospective_io import manifest_chain; manifest_chain(Path.cwd(),"HEAD"); print("Manifest chain verified")'
```

6. Unmount/eject the encrypted image through macOS. Verify it is unmounted
   before resuming any agent work.

## Outcome-cutoff snapshot and final data manifest

After 2029-12-31, take a last source snapshot using the same collector with
`--start 2027-01-01 --end 2028-12-31` and a new outcome-cutoff snapshot ID.
The start/end arguments remain flag dates, not the collection date. Verify and
commit that snapshot exactly as above. Require complete follow-up through
2029-12-31, including source-publication lag checks documented by the custodian.
A snapshot taken too early cannot establish complete outcomes.

Final classification inputs must be complete external Parquet artifacts for
complaints and recall scopes, pinned to the model, prompt and taxonomy in
`phase1/protocol.json`. The final harness does not generate labels, make paid
calls, substitute a classifier or impute missing labels. See `apply_labels`
in the tagged final-analysis script and `join_labels` for the exact columns and
coverage contract. These are model labels, not human semantic ground truth.
If complete compatible artifacts are unavailable, stop and record the blocker;
do not consume a one-shot analysis attempt to discover known missing inputs.

Without computing performance metrics, the human verifies external files and
prepares their relative paths and SHA-256 hashes. Add to the manifest:

```json
{
  "status": "data_frozen",
  "prev_sha256": "<SHA256_OF_PREVIOUS_COMMITTED_MANIFEST>",
  "updated_at": "<UTC_TIMESTAMP>",
  "outcomes_complete_through": "2029-12-31",
  "analysis_inputs": {
    "complaint_labels": {"file": "analysis/complaint_labels.parquet", "sha256": "<SHA256>"},
    "recall_labels": {"file": "analysis/recall_labels.parquet", "sha256": "<SHA256>"}
  },
  "untouched_attestation": {
    "custodian": "Rahul Kumar Singh",
    "type": "self-attestation",
    "attested_at": "<UTC_TIMESTAMP>",
    "no_outcomes_inspected_during_development": true,
    "document_path": "reports/improvement/prospective/UNTOUCHED_ATTESTATION_<DATE>.md",
    "sha256": "<SHA256_OF_COMPLETED_ATTESTATION>"
  }
}
```

This is a field-update example, not a replacement manifest. Preserve all
existing schema, source, window, sample-floor and snapshot fields. Derive
`prev_sha256` from the previously committed manifest, not from a partially
edited file. Verify the current file equals `git show HEAD:data/prospective/manifest.json`
before editing, then record `shasum -a 256 data/prospective/manifest.json`.
Use the frozen `atomic_json` helper to replace the complete updated manifest
from a temporary metadata JSON file in the repository. Remove that temporary
file before committing; it must contain no secrets, rows or absolute paths.
Commit the updated manifest and completed attestation together. Verify the
manifest chain and `check_collection_log` against that commit. Do not change
`final_analysis` from null until an actual final report is committed.

## Human attestation

Copy `UNTOUCHED_ATTESTATION_TEMPLATE.md` to a new dated document, fill all fields
truthfully, and commit it before final analysis. Never sign the blank template.
State custodian, date, reserved window and that no 2027+ outcomes were inspected
during development. Acknowledge any deviation; the historical 2021–2024
preparation amendment does not waive the future-outcome no-peeking condition.
If the statement cannot be made truthfully, stop and record that fact.

Use a signing key only if already available and human-controlled. A signed
document/commit needs independent signature verification by the human; the
harness checks committed attestation content/hash and metadata, not signer
identity cryptographically. Without a key, label both the document and manifest
`self-attestation`. Do not imply that a self-attestation is an independent proof.

## One final analysis after the cutoff

1. Obtain a fresh clone from a human-approved source containing the immutable
   freeze tag and the complete committed metadata branch. The tag is local
   today; do not assume a remote has it. Publishing it requires separate human
   authorization. A local repository source with the required commits is valid.
2. Check out the freeze tag detached and create a fresh venv outside the clone
   from the frozen requirements. Verify the Python version (3.12.13), dependency
   lock hash and frozen files. Do not silently substitute missing package/model
   versions. Preserve any installation failure as a reproducibility blocker.

```sh
git clone --no-hardlinks --branch ml-prospective-freeze-2026 \
  '<REPOSITORY_URL_OR_LOCAL_PATH_WITH_TAG_AND_METADATA>' '<FRESH_CLONE>'
cd '<FRESH_CLONE>'
git checkout --detach ml-prospective-freeze-2026
git rev-parse HEAD
git rev-parse refs/remotes/origin/ml-score-improvement
'<PYTHON_3_12_13>' -m venv '<FRESH_VENV>'
'<FRESH_VENV>/bin/python' -m pip install -r reports/improvement/phase1/requirements-prospective.txt
shasum -a 256 reports/improvement/phase1/requirements-prospective.txt
shasum -a 256 -c reports/improvement/phase1/FREEZE_HASHES.sha256
shasum -a 256 -c reports/improvement/phase1/freeze_manifest.sha256
'<FRESH_VENV>/bin/python' -B -c 'from pathlib import Path; from src.eval.prospective_io import verify_freeze; verify_freeze(Path.cwd())'
git status --porcelain
```

Expected HEAD: `e96338df3cce113a182b0cf1be5bf760abc00b31`. Expected requirements
SHA-256: `5a38a83520a9ddc12eabcbe5fc6b2b4d7185404a9452873aca60b368adca57b5`.
The final `git status` output must be empty. The final script permits identical
frozen-file hashes at later commits, but this procedure deliberately runs from
the tag. `--manifest-ref` selects only the separately committed data metadata.
Confirm that ref contains `data_frozen`, the full chain, collection log and
truthful attestation; pin its commit hash in the human execution record.

3. Mount the encrypted custody image **read-only**, through macOS. Verify the
   marker and file hashes. Use an output directory outside the clone and
   custody volume. Clear provider credentials; do not pass `--today` or set
   synthetic-fixture flags for real execution.
4. Run the frozen analysis exactly once:

```sh
env -u FRONTLINE_TEST_ISOLATION -u META_API_KEY -u MODEL_API_KEY -u BASETEN_API_KEY \
  -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u CLAUDE_API_KEY \
  PYTHONDONTWRITEBYTECODE=1 \
  '<FRESH_VENV>/bin/python' -B -m scripts.final_prospective_eval \
  --final-analysis --custody-root '<READ_ONLY_CUSTODY_ROOT>' \
  --manifest-ref '<PINNED_METADATA_COMMIT>' \
  --out '<NEW_EXTERNAL_FINAL_OUTPUT_DIRECTORY>'
```

The harness verifies the freeze/tag/tree, clean working tree, cutoff, custody
marker, committed frozen manifest chain, attestation, collection log and complete
follow-up before parsing/counting. Below 25 campaigns it writes
`INCONCLUSIVE_SAMPLE` with counts and `metrics: null`, and exits 2 without
classification or metric evaluation. A sample-floor stop is not an improvement
failure and must not be reframed as success. Stop; only a new human-approved
pre-registration before any metric access may specify an extension. The frozen
harness's fixed dates cannot be bypassed; an extension needs its own separately
governed protocol/code freeze, without moving this tag.

On successful Mode B execution, expected outputs are `final_analysis.json`,
`final_analysis.md`, `campaigns.csv`, `alerts.csv`, `run_manifest.json`, plus
`completion.json`. Report estimates and Wilson CIs, sensitivity slice, lead
time/support, alert/censoring counts and descriptive per-make results. No
candidate-minus-baseline improvement test or 70/80 improvement gate applies.
Gamma-Poisson tails are not calibrated probabilities; no ECE/Brier claim is
made. Review every campaign (including misses/unknown labels) and every alert.

5. Preserve every output and exit code, including failed attempts. The presence
   of `run_manifest.json` reserves the attempt before parsing. Do not delete it,
   choose a fresh directory to hide a prior attempt, or rerun for a better result.
   Authorized reruns require a separately approved deviation ID and
   `--rerun --deviation-id '<ID>'`; the harness preserves outputs in `reruns/<ID>`
   and appends a deviation marker. Add date, reason, approver, affected files and
   effect on claims to the human deviation record before the attempt. Never
   silently change a denominator, threshold, window or metric definition.
6. After reviewing all outputs, copy only the reviewed final reports to the
   human metadata checkout on `ml-score-improvement`. Record their SHA-256
   hashes, the output status, execution commit and manifest ref in a new
   `final_analysis` manifest entry, preserving the prior hash chain. Commit
   the report files and updated manifest. Keep raw ZIPs/classifications outside
   the repository. Do not merge into main.
7. Unmount/eject the image and verify it is no longer mounted before agent work.

## Phase 8 — separate human merge decision

No merge is necessary for the demo. The branch includes the original 17
unrelated readiness commits plus ML/research and later phase commits. A merge
brings all of them. Main is recorded at `b8afe38`; check its actual state at the
future decision. Review `phase1/merge_readiness.md`. Require independent human
labels, prospective results, monitoring, security review and separate approval
before production. Preserve the frozen commits/tag regardless of the decision.

## Deviations and timestamp evidence

Append to `DEVIATIONS.md`; never rewrite prior entries. Record date, ID, reason,
approver, files, and effect on scientific claims. Operational collection/final
manifest updates follow the registered protocol and must extend its hash chain.
Protocol/model/code changes after freeze need a separately governed release;
do not patch this tagged release or imply its pre-registration covers the change.

The existing OpenTimestamps receipt is a calendar receipt, not yet a verified
Bitcoin timestamp. Follow `phase1/TIMESTAMP_INSTRUCTIONS.md` using copies of the
receipt for upgrade/verification, and commit an addendum. Do not alter tagged
proof/index files or claim an external timestamp before verification succeeds.
