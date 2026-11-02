"""Create the handover only after recorded checks and preserved hashes verify."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from check_integrity import ROOT, OUT, verify


def sha(path):
    return subprocess.check_output(['shasum', '-a', '256', str(path)], text=True).split()[0]


def load(name):
    return json.loads((OUT / name).read_text())


def main():
    records = [load(name) for name in ['replay.json', 'frozen_replay.json', 'full_unrestricted/dashboard_build.json',
               'full_unrestricted/full_tests.json', 'eval_frontline.json', 'dashboard_source.json',
               'pipeline_report_check.json', 'compileall.json', 'browser_retry/browser.json']]
    for record in records:
        folder = OUT / ('full_unrestricted' if record['step'] in ('full_tests', 'dashboard_build') else
                        'browser_retry' if record['step'] == 'browser' else '')
        if record['exit_code'] != 0 or sha(folder / record['log']) != record['log_sha256']:
            raise ValueError('Check failed or log changed: ' + record['step'])
    full_text = (OUT / 'full_unrestricted/logs/full_tests.txt').read_text()
    matches = re.findall(r'(\d+) passed(?:, \d+ warnings?)? in [^\n]+', full_text)
    if not matches or 'FAILED ' in full_text or 'KeyboardInterrupt' in full_text:
        raise ValueError('No complete passing full-suite summary')
    passed = int(matches[-1])
    evaluation = (OUT / 'logs/eval_frontline.txt').read_text()
    gates = [(int(a), int(b)) for a, b in re.findall(r'(\d+)/(\d+) gates passed', evaluation)]
    if gates != [(12, 12), (11, 11)]:
        raise ValueError('Functional evaluation gates did not all pass')
    replay = load('replay/replay.json')
    if (replay['records_preserved'] != 300 or replay['performance_metrics'] is not None
        or replay['classifier_executed'] or replay['human_validation']['labelled'] != 0):
        raise ValueError('Synthetic replay scope changed')
    integrity = verify()
    original_replay = json.loads((ROOT / 'reports/improvement/phase1/final_validation_phase1.json').read_text())
    expected_replay_hash = next(r['log_sha256'] for r in original_replay['commands'] if r['name'] == 'defect_verify')
    if sha(OUT / 'logs/frozen_replay.txt') != expected_replay_hash:
        raise ValueError('Frozen replay output is not byte-exact')
    now = datetime.now(timezone.utc).isoformat()
    validation = dict(created_at=now, status='passed_after_test_isolation_fix', commands=records,
                      full_suite={'passed': passed, 'failed': 0, 'command': 'make test -o dashboard-build',
                                  'native_dashboard_build_verified_first': True},
                      functional_gates={'passed': 23, 'total': 23},
                      frozen_replay={'exact': True, 'log_sha256': expected_replay_hash},
                      resolved_failures=[
                          {'record': 'full_tests.json', 'reason': 'Dashboard-test sys.path leak caused 11 runtime-metadata failures; run interrupted after diagnosis.',
                           'fix_commit': 'a08010c69876a36fdd1858b9167e8648ead4c09e', 'verified_by': 'full_unrestricted/full_tests.json'},
                          {'record': 'full_retry/full_tests.json', 'reason': '2038 passed; one localhost socket bind denied by sandbox.',
                           'verified_by': 'full_unrestricted/full_tests.json'},
                          {'record': 'browser.json', 'reason': 'Sandbox prevented Chromium startup.', 'verified_by': 'browser_retry/browser.json'}],
                      integrity=integrity)
    status = dict(created_at=now, status='engineering_handover_complete', engineering_complete=True,
                  scientific_validation_complete=False, improved_score_demonstrated=False,
                  human_validation={'labelled': 0, 'total': 300, 'accuracy': None},
                  supplied_synthetic_records=300, scenario_families=12, real_campaigns_added=0,
                  synthetic_classifier_accuracy=None, prospective_data_collected=False,
                  completed_engineering_phases=[0, 1, 2, 3, 4, 5, 6],
                  unexecuted_human_phases={'7': 'Prospective collection/final analysis; 2027–2029 outcomes, analysis by 2030-06-30',
                                           '8': 'Separate human merge decision'},
                  original_mode='baseline_replication', comparison='Fixed logistic comparison registered; not yet evaluated on prospective data',
                  full_suite_passed=passed, functional_gates_passed=23,
                  source_commit=integrity['code_commit'], main=integrity['main'],
                  branch_commits_ahead_at_source_commit=int(subprocess.check_output(['git', 'rev-list', '--count', 'main..HEAD'], cwd=ROOT, text=True)),
                  topology_note='Includes the original 17 readiness commits. The closeout report is one additional commit; merging includes the whole branch.',
                  merge_performed=False, promotion_performed=False, paid_calls=False,
                  custody='Procedural, tamper-evident; no-peeking remains honor-system for public outcomes.',
                  limitations=['Authored labels bypass the text classifier.', 'The 300 fixtures repeat 12 scenario families.',
                               'No independent campaigns or complete follow-up are created by synthetic fixtures.',
                               'All historical scores, original protocols and existing deviations remain unchanged.'])
    for name, value in [('VALIDATION.json', validation), ('STATUS.json', status)]:
        with (OUT / name).open('x') as stream:
            stream.write(json.dumps(value, indent=2)+'\n')
    text = f'''# Project closeout — engineering prototype

Engineering implementation, synthetic testing and handover are complete. Human
semantic validation and prospective model validation remain incomplete. This
closeout does not claim an improved model score or production readiness.

The supplied [300-case JSONL](../synthetic_review_v1/fixtures/synthetic_cases.jsonl)
and [earlier closeout](../synthetic_review_v1/PROJECT_CLOSEOUT.md) are unchanged.
Their SHA-256 hashes are recorded in [replay provenance](replay/replay.json).
The 300 records are variants of 12 authored scenarios, with zero human labels
and zero additional independent campaigns.

The new replay reads those exact records and injects their expected labels into
the frozen count-feature builder, baseline detector and fixed logistic model.
It bypasses narrative classification. On a fixed fictional 2019 timeline:

| Software observation | Count / relevant input total | Interpretation |
|---|---:|---|
| Fixture records retained | 300/300 | Includes all unclear rows |
| Specific authored labels | 150/300 | Test inputs, not verified truth |
| Unclear authored labels | 150/300 | Cannot become specific-defect candidates |
| Finite logistic scores | {replay['finite_logistic_scores']}/{replay['count_feature_candidates']} candidate rows | Inference executed |
| Baseline alert episodes | {replay['baseline_alert_episodes']}/{replay['count_feature_candidates']} candidate rows | Software count, not precision |
| Logistic alert episodes | {replay['logistic_alert_episodes']}/{replay['count_feature_candidates']} candidate rows | Software count, not recall |

Split: `synthetic_software_test`. Label source: agent-authored fixture expectations.
Scope: fictional fuel-system records for five makes. Candidate result: **no**.
There are no recall outcomes in this replay, so accuracy, recall, precision,
false-positive rates and their confidence intervals are not computed. No fitting,
calibration, threshold tuning or selection was performed. Exact command, config
hash, data hash and code commit are in [replay.json](replay/replay.json).

Validation is recorded in [VALIDATION.json](VALIDATION.json), including every
selected command, exit code and log hash:

- **{passed} tests passed** in the full `tests/frontline/` suite via
  `make test -o dashboard-build`, after a verified native-loader dashboard build.
- **23/23 functional gates passed** with `make eval-frontline`.
- Historical replay matched exactly, including all 100 random-reference draws;
  its complete output hash matches the prior frozen replay.
- Pipeline check, source/score integrity, desktop/mobile browser assertions,
  dashboard build and compilation passed.
- The initial suite exposed a dashboard-test import-path leak. The test-only
  repair restores `sys.path`; all frozen version gates remain intact. The
  interrupted failing run and successful rerun are retained.
- Chromium required an isolated retry outside the sandbox. The successful
  browser run retained all assertions and used native Vite config loading to
  preserve the shared dependency directory. See [reproduction details](REPRODUCE.md).
- The repaired full-suite run initially passed 2,038 tests with one sandbox
  socket-bind denial. The complete successful rerun outside the sandbox is the
  full-suite result reported above; the denied run is also retained.

Historical-opened context remains unchanged:

| Metric | Numerator / denominator | Value | Descriptive 95% Wilson CI |
|---|---:|---:|---:|
| Repair campaign recall | 22/41 | 53.7% | 38.7–67.9% |
| Repair mature-alert precision | 14/31 | 45.2% | 29.2–62.2% |
| Sensitivity campaign recall | 14/41 | 34.1% | 21.6–49.5% |
| Sensitivity mature-alert precision | 7/13 | 53.8% | 29.1–76.8% |
| 2025 fuel holdout recall | 5/8 | 62.5% | 30.6–86.3% |
| 2025 fuel holdout precision | 6/18 | 33.3% | 16.3–56.3% |

All six rows are historical-opened, model-labelled/official-recall proxy evidence,
not human semantic truth or candidate results. Scope, exact original command,
label source, config/data hashes and commits are preserved per row in
[unchanged_baseline.json](unchanged_baseline.json). Synthetic counts are not a
valid performance comparison against these historical results.

Both freeze tags and their artifact hashes verify. The original mode remains
baseline replication. The separate trained logistic prototype remains unvalidated;
its registered comparison uses the same reserved future cohort, not a second
independent replication. Human review remains **0/300**. No real 2027+ outcomes
were fetched or inspected. Custody remains procedural and tamper-evident;
no-peeking is honor-system because outcomes are public.

Phases 0–6 remain complete with their recorded deviations. Phases 7–8 remain
human-only: collect reserved 2027–2028 observations, wait for the 2029-12-31
outcome cutoff, apply the minimum 25-campaign rule, and make a separate merge
decision. The [existing runbook](../prospective/RUNBOOK.md) governs those steps;
synthetic data does not satisfy them. `PHASE_STATE.json` is preserved.

`main` remains `b8afe38`; the original checkout and its unrelated work are
unchanged. No merge, push, promotion or paid call occurred. The deliverable that
can be concluded today is the tested research prototype and its reproducible
handover. Scientific validation is explicitly left open in [STATUS.json](STATUS.json).
The verified source commit is {status['branch_commits_ahead_at_source_commit']} commits ahead of `main`, including the
original 17 readiness commits; this closeout adds one report commit. Merging the
branch would include all of them and remains a separate human decision.
'''
    with (OUT / 'PROJECT_CLOSEOUT.md').open('x') as stream:
        stream.write(text)
    (OUT / 'README.md').write_text('[Project closeout](PROJECT_CLOSEOUT.md) · [Machine-readable status](STATUS.json) · [Validation](VALIDATION.json) · [Reproduce](REPRODUCE.md)\n')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
