# Human operations for the fixed-challenger comparison

This runbook is prepared in 2026. Do not execute real collection or analysis
now. Owner: Rahul Kumar Singh. All secrets and raw snapshots remain in the
existing encrypted APFS volume, outside repository worktrees. No-peeking is
honor-system; custody is tamper-evident, not access-control enforcement.

1. During 2027–2028, follow
   [the existing collection runbook](../prospective/RUNBOOK.md). There is one
   shared cohort, not two independent collections. Preserve all quarterly
   snapshots (annual minimum), their hashes and committed manifest history.
2. After 2029-12-31, obtain the final outcome snapshot and verify complete
   coverage and publication lag. Mount the volume read-only for analysis.
   Commit the untouched attestation, version-consistent classification input
   hashes and `outcomes_complete_through` metadata as described in that runbook.
   Missing classifier availability or coverage blocks the run; this task
   authorizes no paid label-generation call.
3. On `ml-score-improvement`, update the manifest in a single append-only
   transaction. Set `prev_sha256` to the hash of its previous committed bytes.
   Add `comparison_authorizations` mapping `fixed-logistic-comparison-v1` to
   the exact protocol hash in `REGISTERED_HASHES.json`. Preserve all existing
   snapshots, attestation and other fields; commit this update. This records
   the human's awareness of the second, correlated analysis, not a new dataset.
4. Create a fresh local clone at the comparison freeze tag and a fresh venv
   from the frozen requirements. Use placeholders below literally as values
   to replace; do not put passwords in any command.

```sh
comparison_source="<LOCAL_REPOSITORY_PATH>"
comparison_checkout="<NEW_COMPARISON_CHECKOUT>"
comparison_venv="<NEW_ENVIRONMENT_OUTSIDE_CHECKOUT>"
comparison_volume="<READ_ONLY_ENCRYPTED_VOLUME_PATH>"
comparison_output="<NEW_COMPARISON_OUTPUT_DIRECTORY>"
git clone --no-hardlinks "$comparison_source" "$comparison_checkout"
cd "$comparison_checkout"
git checkout --detach ml-logistic-comparison-freeze-2026-v1
python3.12 -m venv "$comparison_venv"
"$comparison_venv/bin/python" -m pip install -r reports/improvement/phase1/requirements-prospective.txt
"$comparison_venv/bin/python" -B -m scripts.prospective_comparison \
  --final-comparison \
  --custody-root "$comparison_volume" \
  --manifest-ref origin/ml-score-improvement \
  --out "$comparison_output"
```

The runtime requires Python 3.12.13 and the recorded frozen dependency versions.
Verify the `.rca-custody` UUID before running. There is no real-use `--today`
override. Keep the checkout clean before execution. The script verifies both
freezes, the committed manifest chain, attestation, comparison authorization
and full follow-up before parsing outcomes. It counts eligible campaigns before
loading labels or calculating performance.

`INCONCLUSIVE_SAMPLE` (exit 2) means stop with counts only; never compute
performance separately to see whether it looks promising. A pre-registered
extension and human deviation review must precede any additional access.
Fewer than 25 campaign-linked components prevents improvement confirmation
even when 25 campaign IDs are present. Undefined metrics or unresolved intervals
remain inconclusive. A successful process exit indicates that computation
finished, not that the challenger improved.

Review `final_analysis.json`, `final_analysis.md`, all rows of `campaigns.csv`
and `alerts.csv`, plus `run_manifest.json` and `completion.json`. Review
sensitivity results and every bootstrap seed. Do not retry with another output
directory: the fixed `final_execution.json` preserves the attempt. Keep failed
or inconclusive runs. Any rerun requires a documented deviation and human review;
the current harness intentionally provides no automatic retry switch.

Commit the execution record and all output artifacts. Append a manifest update
with the previous committed manifest hash and `comparison_runs` entry under
`fixed-logistic-comparison-v1`, identifying result paths, hashes, date and
status. Preserve the original Mode B final-analysis field separately. Do not
rewrite either tag. Run the original baseline-replication study only from its
own freeze tag, using its existing runbook, and report both studies together.

Unmount the volume. Do not leave it mounted for agent work. No merge or
production promotion is authorized by either result. An independently reviewed
prospective improvement would still leave human semantic validation, monitoring,
security review and a separate human production decision outstanding.
