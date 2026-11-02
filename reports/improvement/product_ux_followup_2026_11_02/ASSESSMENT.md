# Product, UX and readiness follow-up — 2 November 2026

The earlier review describes several conditions that have changed. The completed
historical label review now supports a measured benchmark, the private local
configuration contains a Baseten key, and the primary running API returned
HTTP 200 with `status: ok` and readiness true during this audit. The remaining
opportunity is evidence of understandable workflows, reproducible operation
and usefulness to actual quality/service engineers. No new rubric score is
assigned by this audit.

## UX repairs completed

- A missing recall link is explained and does not count as missing case evidence.
- Failed code, photo and note reads are reported as unavailable, with unknown
  counts; they are not presented as confirmed empty collections.
- Photo loading, successful empty results and outages have separate states.
  List/preview failures offer retries, and successful retries clear the error.
- Suggested next steps lead directly to photo upload, scan-code entry,
  follow-up drafting and the assessment note. Customer evidence is optional
  and photos should only be taken when safe.
- Uploads, code additions, notes and patches refresh the case evidence status
  while preserving unsaved note/follow-up text. Case reads reject stale responses.
- Case action confirmations and errors appear inside the drawer.
- Photo-analysis copy describes availability without assuming a Meta key or
  claiming that both vision and segmentation ran.

These extend existing work: conversation-supplied codes are already captured,
follow-up drafts already request evidence, optional photo intake already exists,
and advanced navigation is already collapsed. The five-field intake is not
inherently a flaw; the handoff must explain what is optional, what was captured,
and how to obtain the rest.

## Verified evidence

- Python completeness regressions: **5/5 passed**, using isolated fixtures.
- Production dashboard build passed. Vite still reports a large shared bundle;
  startup performance on a slow device has not been measured here.
- `PLAYWRIGHT_CHANNEL=chrome npm run test:signin` passed on the final code.
  The real isolated API checks cover authentication, a typed report, source
  handoff, correction, revision, review and export. The added case evidence
  checks use explicitly fictional route fixtures for outages, retries, focus
  actions, refreshed status and unsaved-input preservation. No hosted inference
  or real audio was exercised by these checks.
- [Suggested next steps screenshot](case-evidence-next-steps.png) and
  [recorded evidence screenshot](case-evidence-recorded.png) were rendered and
  visually inspected. Both contain fictional data.
- Frozen sample, candidate recipe dependencies and finalized evaluation
  artifacts: **25/25 hash checks passed** in
  [preservation_checks.json](preservation_checks.json).

## ML evidence: established scope and remaining limits

The [finalized evaluation](../human_reviews/round1/revisions/manish_export4/finalized/EVALUATION.md)
reports current-classifier accuracy **255/300 = 85.0%**, 95% Wilson interval
**80.5%–88.6%**. Specific-label accuracy is **62/77 = 80.5%**, interval
**70.3%–87.8%**. The sample spans 29 components; **223/300** final labels are
`other_unclear`, so overall accuracy does not establish uniform component quality.

All **31/31** disputed labels have supplied adjudication, while **269/300**
matching labels are retained by agreement. The provenance retains the
script-assisted revision, human attestations, assistant-drafted adjudication
and original reliability limitations. This is a historical benchmark, with
unchanged saved predictions rescored against revised labels. It is not fresh
prospective validation or proof of independent human review quality.

The grounded candidate is weaker: **238/300 = 79.3%**, interval
**74.4%–83.5%**, including **6/300** missing predictions counted as wrong.
The README's current paragraph now links the finalized evidence and removes
the stale unmeasured-human-accuracy statement. Historical artifacts and dashboard
accuracy remain separate.

All these human labels, paraphrases and `synthetic_review_v1` fixtures remain
evaluation-only. Future fitting, calibration and feature selection require
separate development data; fresh testing requires independently sealed labels
and a candidate freeze before access.

## Readiness: credit existing work and close the deployment gap

The current local `.env` contains a Baseten key; no key value is published here.
The effective default `DOMAIN_DB_PATH` for this worktree is `data/domains`, which
does not exist here. The sibling `../v2_ai_rca_tool/data/domains` does exist.
This is a worktree configuration/reproduction gap, not evidence that the user's
running installation lacks a warehouse. No sibling database was changed or
silently connected to this writable app.

The repository already contains [clean container, Compose and restart evidence](../../hackathon/container_validation/README.md)
for earlier source revisions. It includes preservation of the campaign and
trust identity after restart. Credit that work, then repeat the existing checks
against the final release with its intended database path and configuration.
HTTP 200 and key presence alone do not prove model responses, source entailment,
persisted evidence or recovery under that configuration.

## Highest-value next work

| Priority | Work | Evidence to retain |
|---|---|---|
| 1 | Observe relevant quality/service engineers completing report → investigation → review → export. Start with a small usability cohort; this is distinct from defect-label review. | Each attempted task, completed/attempted denominator, elapsed time including waits, corrections, failures and unacceptable conclusions. Compare assistance conditions only under the existing frozen study protocol. |
| 2 | Package one supported pilot path with explicit data ownership, `DOMAIN_DB_PATH`, startup and backup settings. Keep advanced services outside the default workflow. | Clean-start and restart results against the actual release; a backup/restore drill showing saved cases, notes, evidence and exports survive. |
| 3 | Exercise provider timeout, malformed output, unavailable database and interrupted upload on an isolated installation. | Visible fallback/retry states, retained original attempts, no fabricated evidence, and latency/cost records including failures. |
| 4 | Complete the separate development/evidence review and independently sealed validation workflow. Do not tune against this opened historical sample. | Frozen candidate, reference labels and independent field grading; accuracy, omissions and critical source/negation/identifier errors with denominators and intervals. |
| 5 | Validate each audio/video capability actually offered by the app, after integrating it. | Consented real recordings, rejected/unsupported inputs, source preservation and failure handling. Provider support for a modality is not proof that this app implements it. |

Use the existing [evaluation/study workflow](../../../docs/evaluation-readiness.md)
and [container verification commands](../../../docs/container-validation.md).
Do not add speculative features just to expand the demo surface. A concise
source-cited demo of the core task, supported by real usability observations and
reproducible release checks, directly addresses the remaining review concerns.

This pass changes local UX and documentation. It does not deploy a release,
train a model, run paid inference or establish a new judge score.
