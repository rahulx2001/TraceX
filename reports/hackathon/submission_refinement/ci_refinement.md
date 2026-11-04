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
