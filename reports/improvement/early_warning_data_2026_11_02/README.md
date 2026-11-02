# Early-warning count check — 2 November 2026

The screenshot was taken on port **8766**, the isolated usability installation.
Its operational database has no cases, investigations or contacts. The four
Honda brake records shown in its complaint-trend table come from the separate
domain corpus. They are not four operational cases. No records were deleted.

The regular installation on [port 8000](http://127.0.0.1:8000/ui/#warning)
still contains operational data. It currently serves an older sibling UI
build; this check did not replace its build, restart it or change its database.

| Current queue | Simulated contacts included | Simulated contacts excluded |
|---|---:|---:|
| Cases in Open status | 2 | 0 |
| Cases pending follow-up | 36 | 8 |
| Critical cases in any unclosed status | 24 | 4 |
| Open investigations | 4 | 4 |
| Active calls | 0 | 0 |

The case and investigation tiles are current queue counts. Contact activity
uses the last seven days. Complaint trends use the latest displayed corpus
week, which can differ from the current calendar week. The two sources should
not be expected to agree. The investigation endpoint's count is not filtered
by simulated traffic.

In the current project's UI, Refresh now uses the checkbox value instead of
mistaking the click event for an enabled filter. Simulation refreshes use the
new filter value, and late responses cannot overwrite counts for a later
selection. A failed metrics request clears stale values and displays an
unavailable message and dashes. The page identifies operational activity and
complaint trends separately and includes the pending-follow-up count.

The production build and **7/7** focused browser checks passed. See
[verification.json](verification.json). [isolated.png](isolated.png) shows the
real empty usability installation. [regular.png](regular.png) previews the
current UI against the regular installation's real GET responses, forwarded
only inside the read-only browser check. This does not connect the running
usability installation to the regular database. Filter, race and outage
checks use browser-only display fixtures; no records are seeded by this test.

The frozen 300-record sample still has SHA-256
`7b0bf958b8756b51e3a3d550b8611f8182b56839b20e922b35abcc67e3aba1a4`.
No human labels, predictions, model configuration or evaluation results changed.
