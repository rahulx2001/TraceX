# Fixed logistic challenger versus baseline: prospective 2027–2028 comparison

## 1. Identity and registration

Version 1; 2026-11-01. Author/custodian: Rahul Kumar Singh; implementation by
the ML improvement engineer. Repository: `v2_ai_rca_tool`; branch:
`ml-score-improvement`. Study ID: `fixed-logistic-comparison-v1`.
The first commit containing this document and `protocol.json` is the local
pre-registration event. The annotated tag
`ml-logistic-comparison-freeze-2026-v1` identifies the fixed implementation.
The source parent is recorded in `protocol.json`. No external registry entry
or independent timestamp is claimed.

## 2. Relationship to the existing study

This is a separately registered, fixed-challenger research comparison on the
same future cohort as the original Mode B baseline-replication study. It is
not a second independent dataset or an independent replication. Both results
must be reported; neither may be selected because its conclusion is favorable.
The original protocol, Phase 2 decision, artifacts and
`ml-prospective-freeze-2026` tag remain unchanged. This comparison cannot
retroactively satisfy the original development selector or authorize promotion.
The additional research is authorized by DEV-20261101-04.

## 3. Historical background, not selection evidence

Historical-opened context; these values are unchanged and are not challenger
results. Label source: model categories plus official recall dates, not human
semantic truth. Scope: the existing five-make, MY2015–2024 fuel-system task.

| Metric | Numerator / denominator | Value | Wilson 95% CI |
| --- | --- | --- | --- |
| Repair campaign recall | 22/41 | 53.7% | 38.7–67.9% |
| Repair mature-alert precision | 14/31 | 45.2% | 29.2–62.2% |
| Sensitivity recall | 14/41 | 34.1% | 21.6–49.5% |
| Sensitivity precision | 7/13 | 53.8% | 29.1–76.8% |
| 2025 fuel holdout recall | 5/8 | 62.5% | 30.6–86.3% |
| 2025 fuel holdout precision | 6/18 | 33.3% | 16.3–56.3% |

Exact historical commands, source/data/config hashes, code provenance and
splits remain in `../phase1/phase0_recheck.json`. Authored category diagnostics
are non-acceptance-eligible context in `../pipeline_recheck.json`; they are not
human accuracy or a model-selection signal. Human semantic labels remain 0/300.

## 4. Fixed models

Baseline: the original Gamma-Poisson/count rule, 13-week window, minimum count
2, tail threshold 0.2, 91-day cooldown. Challenger: exactly the existing
`logistic_prototype_v1/model.json`, SHA-256
`7a4a2607822e792d46cef5aeb4ca79d0c1a44164534e27cb9f87840351ecda2d`.
It has four standardized count features and a fixed 0.5 threshold. No fitting,
calibration, feature choice, model substitution or threshold change is allowed
in this study. Uncalibrated outputs are not physical-defect probabilities.

Development-only evidence; not a candidate result and not a prospective estimate.
The challenger was fitted on 12 mature 2015–2020 rows, including 4 positives
across only 2 campaigns. Both original training folds were unsupported. Its
original ineligibility for the first study is preserved; this new study
explicitly tests the fixed, unvalidated research challenger.

## 5. Scope and untouched-data boundary

Ford, Honda, Hyundai, Kia, Toyota; MY2015–2024; vehicle recalls; repaired
`FUEL SYSTEM` and the existing taxonomy. `FUEL/PROPULSION SYSTEM` is not silently
added. Campaign IDs are deduplicated across vehicles/model years; IDs do not
prove that physical causes are independent. Unknown labels and misses remain
in the eligible campaign denominator; unknown labels never establish matches.

All 2015–2020 development data have been opened. The 2021–2024 OOS analysis,
2025 fuel holdout and 2026 backtest are opened history, descriptive only.
No historical subset is redesignated as untouched. No 2027+ outcomes are
collected or inspected during development. All final outcome campaign IDs
must be disjoint from the development campaign inventory; overlap is an error,
not permission to remove a difficult campaign.

## 6. Window and sample rule

Flag dates: 2027-01-01 through 2028-12-31. Eligible campaign issue dates: the
same two years. Precision confirmation outcomes extend through 2029-12-31.
The minimum is 25 distinct eligible campaigns, preferably 30. Count campaigns
before loading labels or calculating any performance metric. Below 25, write
`INCONCLUSIVE_SAMPLE`, counts only, and stop with a nonzero exit status.
Never lower this threshold after seeing data. Any extension requires a new
pre-registration before further outcome access; there is no automatic extension.

At least 25 eligible-campaign-linked components are additionally required for
improvement confirmation. Report that count. A smaller count prevents a
confirmation claim even when there are at least 25 campaign IDs. This is a
conservative dependence check, not proof of physical independence.

## 7. Primary metrics and temporal availability

Campaign recall is unique eligible campaigns detected divided by all eligible
campaigns. Mature-alert precision is confirmed full-follow-up alert episodes
divided by all full-follow-up alert episodes. Reuse the original evaluator and
`estimate` function. Preserve the 7–364-day matching horizon and 91-day cooldown.
Censored alerts are separate; no imputation, cherry-picking or denominator
reduction is permitted.

Counts use only complaints received strictly before alert availability in the
trailing 30/90/365 days, plus same-make counts over 365 days. Both models use
the same completed-week candidate universe and initial 17-week support rule.
Input history starts in 2027; there is no 2026 warm-up. The new prospective
feature adapter must reproduce the frozen development count recipe on
synthetic fixtures. Recall text, future complaints and outcome-derived numeric
features are forbidden.

## 8. Hypotheses and decisions

H1: challenger improves recall over concurrent baseline. H2: challenger improves
mature-alert precision over concurrent baseline. H3: positive differences in
both metrics persist after excluding explicit recall mentions.

Target met means challenger recall ≥70% and precision ≥80%; report this
separately from statistical confirmation. Improvement is confirmed only when
both primary candidate-minus-baseline lower 95% bootstrap bounds exceed zero
for every registered seed and the component-count requirement is met. Either
primary point estimate below baseline is failure. Otherwise unresolved or
undefined comparisons are inconclusive. No improvement language is permitted
for an inconclusive result. No result automatically authorizes deployment.

## 9. Uncertainty and dependence

Use existing Wilson 95% intervals for rates, with their correlation limitation.
For paired differences, use 2,000 component-bootstrap draws for every seed
17, 29, 43, 71, 101; retain all results. Build joint connected components across
both models, connecting each alert to every matched campaign. Identical alerts
are shared between methods; unmatched alerts retain their denominator mass.
Precision-only 2029 campaigns connect related alerts but contribute zero
campaign-recall denominator mass. Component totals must equal the original
evaluator's numerators/denominators. Do not replace invalid draws; intervals
are unavailable if fewer than 95% of draws have defined denominators.

The confirmatory claim is the conjunction of H1 and H2 for one fixed challenger;
there is no model/seed search. Separate campaigns may still share suppliers,
platforms or causes beyond observed matching links. All inference is limited
by the tiny training corpus and uncertain effective sample size.

## 10. Secondary analyses

Apply the existing explicit-recall regex to complaints and regenerate both
models' alerts, retaining every campaign. H3 is supported only when both
sensitivity lower bounds exceed zero for every seed. Otherwise a dependence
on recall mentions has not been ruled out.

Report median campaign lead, total/mature/censored alerts and per-make
descriptive rates. For the uncalibrated logistic outputs, report descriptive
ECE and Brier on every mature candidate row, with 10 equal-width bins and
fixed reference prevalence 4/12. Reuse the existing calibration diagnostics:
seed 17, 1,000 row-bootstrap ECE draws and 2,000 Brier draws. These are weak-label
diagnostics with row-dependence limitations, not calibration fitting, semantic
accuracy, acceptance gates or physical-defect risk validation.

## 11. Complete follow-up and source coverage

Quarterly NHTSA complaint/recall snapshots are preferred; annual is the minimum
in 2027–2028. A final snapshot on or after 2029-12-31 and a committed
`outcomes_complete_through` attestation are mandatory. The calendar reaching
the cutoff is insufficient by itself: the human checks publication lag and
snapshot coverage. Official recalls are outcome proxies, not complete truth
about every actual defect.

## 12. Custody and attestation

Custodian Rahul Kumar Singh holds the encrypted APFS volume outside the repo.
The passphrase remains human-held, outside repo/environment/history/keychain
access by the agent. Reuse the marker UUID, metadata-only collection log and
committed manifest hash chain. Before final access, the human commits the
untouched attestation and authorizes this study's exact protocol hash in the
manifest. No attestation is made on the human's behalf now.

Custody is procedural and tamper-evident, not enforced access control. No-peeking
is honor-system: public outcomes can be re-fetched and same-account processes
can bypass local checks. Tests prove refusal paths and integrity checks only.

## 13. Label availability

Use the original frozen taxonomy, classifier model and prompt identifiers.
Complete, hash-verified, version-consistent classification files must be
supplied externally under the existing input contract. Missing labels or an
unavailable pinned classifier block analysis; no imputation, replacement model,
new LLM-generated training labels, paid call or human-label claim is authorized
by this harness. This is a material future dependency, not a completed label
collection task. Provider version identifiers alone do not establish immutable
model weights; provenance uncertainty limits claims.

## 14. Single analysis and complete reporting

Run the frozen comparison once after all gates pass. The fixed repository
execution record is reserved before raw parsing; failures remain recorded.
Changing `--out` does not authorize another attempt in that checkout. The
committed manifest also records completed comparisons. Fresh clones and
deleted local state can bypass local guards; committed history and human
attestation remain essential. There is no automatic rerun.

Report both studies together without pooling their shared cohort as independent
evidence. Export every eligible campaign, every miss and every emitted alert,
all rate denominators, CIs, paired draws/seeds, model/data/config/code hashes,
split and label provenance. Review output does not retrospectively relabel
outcomes to improve results.

## 15. Freeze and reproducibility

Freeze by 2026-12-31. `REGISTERED_HASHES.json` pins this document, protocol,
comparison code, model artifacts, tests and environment lock. The original
339-file freeze is verified independently. The comparison index and each file
must match the new annotated tag as well as working-tree bytes. No original
freeze file or tag is changed. No external timestamp has yet been obtained;
the new registration is local Git evidence only.

## 16. Operations

Follow `RUNBOOK.md` and the existing human collection runbook. Use separate
fresh checkouts at the two freeze tags for their respective analyses; bring in
only committed manifest metadata through a ref. Keep the volume unmounted
during agent development and read-only for final evaluation. Never execute
collection, label production or real final analysis during this task.

## 17. Timeline and outstanding evidence

Register/freeze by 2026-12-31; collect during 2027–2028; outcome cutoff
2029-12-31; final analyses by 2030-06-30. The historical census found no
additional campaigns in the pinned, in-scope source. Future campaigns and
their completed follow-up cannot be supplied today. The fixed model-year
cohort will be older and may never reach the sample target; report that
honestly rather than expanding scope after seeing outcomes.

## 18. Deviations and claim limits

Every amendment is append-only, with date, reason, approver, files affected and
effect on claims. Preserve all earlier records and both tags. The existing
historical preparation deviation remains visible. Changed models, windows,
thresholds, sources, taxonomy or metric definitions require a new registration
and explicit disclosure. No improved score, semantic accuracy, production
eligibility, merge or promotion has been demonstrated or performed here.
