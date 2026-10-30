# TraceX contribution provenance

## Starting snapshot

The event repair work starts from TraceX commit [`de3c483946`](https://github.com/rahulx2001/TraceX/commit/de3c483946), committed **27 October 2026, 16:08:25 UTC**. This commit imported an existing application. Its timestamp is not evidence that every imported feature was built during the hackathon.

The owner's supplied participant guide gives kickoff as 26 October, the building period as **27 October–4 November**, and submissions due **4 November at 9 PM Eastern**. The initial repair pass is dated 28 October. Later changes must be recorded separately; this document does not relabel or backdate earlier work.

## Reused foundation: actual original commits

Earlier history is available in the local `origin/hackathon/ai-layer` and `bundle-ai-layer` references and original SkewAi source repository:

| Source commit | UTC date | Reused contribution |
|---|---|---|
| [`fc114d2`](https://github.com/rahulx2001/SkewAi/commit/fc114d2) | 20 Oct 2026, 21:08:19 | Optional Meta adapter, status route, decision store |
| [`e16d267`](https://github.com/rahulx2001/SkewAi/commit/e16d267) | 20 Oct 2026, 21:45:32 | 60 synthetic multilingual examples and evaluation harness |
| [`ce1268e`](https://github.com/rahulx2001/SkewAi/commit/ce1268e) | 21 Oct 2026, 08:01:32 | Deterministic Hindi/Hinglish safety and slot layer |
| [`349077c`](https://github.com/rahulx2001/SkewAi/commit/349077c) | 21 Oct 2026, 08:37:34 | Existing AI-layer bundle/test reports |

The frontline agents, domain packs, human takeover, NHTSA statistics and early-warning backtests, synthetic demo and ledger are also reused. No claim is made that these were newly built on 28 October.

## Current event contributions

The committed contribution range is **`de3c483946..HEAD`** in TraceX. Working-tree changes and untracked files are not part of that range until committed. The initial repair scope includes:

- Loading server `.env` settings while isolating tests from local credentials and spend ledgers.
- Resource-host binding/recovery, lifetime spend reservations, translation sanity checks and extractive brief grounding from the local repair work.
- A live synthetic Meta complaint workflow, feature-specific proof artifact and dashboard review surface. The artifact records actual acceptance and ledger verification; key presence is not proof.
- Valid medical/consumer pack YAML; bounded clustering model selection and batch writes; an efficient 5,005-record test fixture retaining every assignment assertion.
- A browser exchange of an **already issued** supervisor session into an HttpOnly cookie, with signature/expiry/role tests. It does not mint extra privileges.
- Python 3.12 judge setup, dashboard/model test prerequisites, versioned isolated demo data and credential handling.
- Honest Indie-only submission wording, bounded feature claims, MIT application license and third-party notice.
- Regressions and recorded verification results in `reports/HACKATHON_FIX_RESULTS_2026-10-28.md`.

Readiness implementation was committed in `b8afe38` before this follow-up pass.
The following inventory is part of that committed foundation for the candidate:

| Local addition | Source and evidence |
|---|---|
| Component-lot safety campaign, reviewed repair/follow-up and evidence packet | `src/ai_layer/safety_campaigns.py`, `src/api/routes/safety_campaigns.py`, `dashboard/routes/SafetyCampaigns.jsx`, `docs/safety-campaigns.md`, `reports/hackathon/safety_campaign_smoke.json` |
| Scoped prediction repair and blind human-review workflow | `scripts/defect_repair.py`, `scripts/defect_review.py`, `src/eval/defect_prediction.py`, `reports/defect/repair/README.md` |
| Expanded-source temporal experiment and failed above-86% test | `scripts/fuel_holdout.py`, `src/eval/fuel_detection.py`, `reports/defect/fuel_holdout/README.md` |
| Sourced Meta investigation, independent review/comparison tools, timed participant study and narrated demonstration | `src/ai_layer/complaint_evidence.py`, `src/ai_layer/campaign_investigator.py`, `dashboard/src/ai/CampaignInvestigation.jsx`, `scripts/evidence_benchmark.py`, `scripts/reviewer_study.py`, `docs/sourced-investigation.md` |
| Current route/authentication, reviewed report handoff, inspectable trace sources, claim corrections and bounded run recovery | `dashboard/routes/JudgeEntry.jsx`, `dashboard/routes/CallWidget.jsx`, `src/ai_layer/report_sources.py`, `src/ai_layer/claim_support.py`, `src/ai_layer/operation_trace.py`, `dashboard/scripts/assert-signin-reachable.mjs`, `docs/entry-auth-validation.md` |
| Current seed/container review assets, credit-free replay, claim index and public-link checks | `scripts/submission_smoke.py`, `scripts/public_replay.py`, `scripts/submission_manifest.py`, `scripts/package_public_replay.py`, `reports/hackathon/CLAIM_INDEX.md`, `reports/hackathon/link_checks/results.json` |

This inventory does not replace a review of history against the imported
baseline. The current `reports/hackathon/source_manifest.json` must identify the
packaged source commit; older manifests remain in Git history. Video work is
outside this readiness pass and belongs to the owner.

## Package the final source

Review the intended working-tree delta first, preserving unrelated local changes.
Commit the selected source and permitted lightweight artifacts to the submission
branch without rewriting the original history. Exclude credentials, runtime
databases, cached datasets/weights and generated video/audio. A locally untracked
feature is not present in a fresh checkout.

After the source commit, regenerate the manifest from that exact commit:

```bash
python -m scripts.submission_manifest create --commit HEAD
python -m scripts.submission_manifest verify --worktree
```

Commit the manifest separately. It deliberately excludes itself and pins
`source_commit`, `source_tree`, file hashes and the event delta from the imported
baseline, avoiding a recursive self-hash. Preserve the older manifest in Git
history. A subsequent implementation change requires a new source manifest.

Verify a fresh checkout of the pinned source commit with the public replay,
production authentication/browser path and current container CI. Record the
candidate source commit separately from the actual submitted commit in
[`submission_links.json`](reports/hackathon/submission_links.json). Its empty
values and pending verification must not be interpreted as a completed release.
The current link check covers public source and hosted demo, with portal/team
inspection recorded separately. A missing video does not gate this pass.

## Verify the dates and delta

```bash
git show -s --format=fuller de3c483946
git log --format=fuller de3c483946..HEAD
git diff --stat de3c483946..HEAD
git diff --stat
git ls-files --others --exclude-standard
# The original source history is separately linked above:
git show -s --format=fuller fc114d2 e16d267 ce1268e 349077c
```

The supplied guide explicitly permits building on existing products or codebases
when the new event work is clearly identified. It requires the demo to highlight
event-built features and warns that unclear contributions can result in
disqualification. This record supports that disclosure; judges determine
eligibility. Historical backtests stay historical, synthetic cases stay
synthetic, and unrun human evaluations stay unrun.
