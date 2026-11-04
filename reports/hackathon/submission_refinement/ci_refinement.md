# Full-suite CI follow-up

The earlier main run [41881156977](https://github.com/rahulx2001/TraceX/actions/runs/41881156977)
had test failures before the 25-minute job timeout. That execution is not a
successful full-suite result. The initial submission PR’s first run repeats
the existing suite; it must not be described as fully passing.

The synthetic comparison fixtures copied the real study’s pinned runtime,
then ran in a different CI environment, causing runtime refusal before the
intended cutoff, custody and provenance checks. Disposable synthetic test
registrations now pin the executing environment. The wrong-runtime negative
test still verifies refusal. The real study protocol, hash index, runtime gate
and source freeze remain unchanged.

The metadata/smoke regressions now use disposable synthetic freeze repositories
instead of incorrectly treating current application source as an older research
freeze. The multi-case demo and returning-customer tests have integration-sized
timeouts, and enrichment concurrency is verified by actual overlap rather than
an absolute host-dependent 750ms disk/ledger bound. No user-performance claim
is produced by these software tests.

The planned workflow partitions all 232 Frontline test files into four disjoint
58-file jobs, with fail-fast diagnostics within each job and all shards retained.
It uses the project’s existing optional research requirements in an isolated
`.ml-deps` folder. It does not add them to the application environment or install
anything on the owner’s Mac. The owner approved installation on GitHub CI only; no local installation is authorized or required.

[Focused execution](ci_fixture_verification.json): 42 synthetic/evaluation
regressions and three integration tests passed using already installed local
packages. The YAML parses and the four file partitions have complete, unique
coverage. Public model replay and historical scores are unchanged. Full new CI
status will be established by the actual GitHub run after the workflow is pushed.

The first partitioned run passed shards 1 and 3 and both container jobs. It exposed a missing Pillow runtime declaration in the canonical EPS demo, a demo-service fixture environment leak, and a 120-second browser timeout for fifteen simulated contacts. Pillow is now declared as an application requirement; no package was installed on the owner’s Mac. Launcher tests explicitly restore initially absent variables, the health check explicitly tests offline mode, and the multi-record integration/browser checks use bounded batch-sized timeouts. No production model or research metric changes were made.

At [ef3424d](frontline_shards_ef3424d.json), all four complete unit/contract partitions passed. The browser workflow progressed through the fifteen-contact simulation and report/review/export checks, then timed out while loading the full 213-owner canonical campaign. Browser checks now have their own bounded CI job with retained failure artifacts; the canonical batch gets an eight-minute limit. Unit correctness assertions and all fictional campaign outcomes remain intact.

At [2524c84](ci_2524c84.json), all four complete Frontline partitions, the
production browser/report/canonical-demo job, dashboard build and both Docker
jobs passed. The overall workflow failed in the public model replay. A subsequent
strict diagnostic run at `f659c54852ec1d8120a75017b4a7c05e3e35e44a` identified
98 floating-point differences; the first twelve were tail probabilities at
approximately `1e-15` absolute scale. Linux and macOS use different platform
math implementations.

The public replay comparison now permits at most `1e-12` absolute difference
only for `tail_4`, `tail_13` and `tail_26` diagnostic fields in selected/baseline
alert details. Counts, metrics, alert identities, campaign matches, configuration
and all 100 random references still require exact equality. Changed input hashes,
frozen source or outcome choices remain failures. The report exposes accepted
roundoff counts and maximum difference. Seventeen standalone regression checks
passed locally, including rejection of metric/configuration/reference changes,
nonfinite values and larger tail differences. The local model replay also
passed with zero accepted roundoff differences and zero provider calls.

The final workflow conclusion must be read from the PR's current-head checks;
the linked earlier receipts retain their actual failures and source commits.

The portable replay passed in run
[41910318848](https://github.com/rahulx2001/TraceX/actions/runs/41910318848),
accepting 98 diagnostic tail differences with maximum absolute difference
`4.773959005888173e-15`; all other fields matched exactly. Public evidence,
17 standalone regressions, SLM probes, dual-pack evaluation, production browser,
dashboard and Docker jobs passed. Two Frontline partitions exposed timing
flakiness: the no-provider-call test imposed an unrelated 100ms whole-turn bound
(observed 110ms), and the complete five-drill staging test had only a 30-second
outer timeout.

The no-provider-call test retains its trapped narration function and requires
both concurrent turns to return slot questions. Latency benchmarks and
over-deadline model-refusal tests remain separate and unchanged. The five-drill
integration test now has a 120-second outer limit; all five outcomes and the
production drill's 60-second evacuation assertion remain unchanged. No
production deadline, routing guard or inference behavior was altered.
