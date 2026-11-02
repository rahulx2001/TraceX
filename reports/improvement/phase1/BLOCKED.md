# Phase 1 custody gate

Status: stopped after the starting-state audit. Phase 1 is not complete, and the
prospective test has not been declared preregistered, sealed or frozen.

The human already approved the 2027-01-01–2028-12-31 flag window, 2029-12-31
outcome cutoff, minimum 25 evaluable campaigns (preferably 30), development on
2015–2020 only, and no merge. Those decisions do not need approval again.
The verified branch state, baseline values, confidence intervals, source hashes,
development limits and command logs are in `starting_state.json`.

## Triggered stop condition

The user requires that the sealed directory be unreadable by development code
and that this restriction cannot be bypassed. The current development process
runs as UID 501, which owns the workspace data directories. No independent
prospective collector, custody account, external vault or custodian public-key
configuration has been supplied or configured for this workflow.

A Python path validator or `--final-analysis` flag can prevent accidental use
through one API. It cannot prevent direct `open`, pandas/pyarrow reads or a
subprocess running as the same account. Owner-only or zero-read permissions are
also insufficient: the owner can restore access. Keeping a decryption key in
this account's files or environment would leave the same problem. No such
mechanism is being presented as an enforced seal.

The applicable instruction is: **“Stop and report if: The sealed-data guard
cannot be enforced.”** This is the user's requirement, not a new approval rule.

## What is needed to resume

Supply the public configuration of an independent collector/custodian boundary:

- A separate service or OS/storage identity collects the raw prospective data;
  development has no raw-read credentials or permissions.
- Alternatively, an external collector produces encrypted snapshots for this
  workspace using a custodian public key. The corresponding private key stays
  outside the development identity and is not released before final analysis.
- The independent identity also protects collection code and release policy
  from modification by the development account. Final execution verifies the
  committed protocol/freeze hashes and cutoff before accessing outcomes. The
  sample-size check occurs within that authorized final execution.

Once that boundary is specified, the implementation can be wired to it and
tested with synthetic fixtures and a real cross-identity denial test. A toy
same-process path-check test alone would not satisfy the acceptance gate.

The known small development corpus still limits defensible fitting. The user's
explicit baseline-freeze fallback remains available; no complex model will be
forced and no development result will be described as an improvement.

## Work preserved

The required existing files were read, the branch was clean at `c602bdd`, and
the original checkout, `main`, protected reports and dashboard evidence were
checked without modification. Only this blocker report, the starting-state
record, its hashes and command logs were added. No prospective data was fetched,
no labels were filled, and no model experiments or paid calls were run. The
full test suite was not rerun because implementation stopped at this gate;
previous passing tests are not a Phase 1 completion claim.

## Resolution — 2026-10-31T15:10:06.484940+00:00

The human amended the custody requirement to procedural custody. The former
independent-identity requirement no longer blocks this task. Public outcomes
cannot be made inaccessible to a determined process; no-peeking is explicitly
honor-system. CUSTODY.md and protocol.json record the replacement model.
