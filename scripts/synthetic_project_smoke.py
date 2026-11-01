"""Replay saved fictional labels through frozen detector code; never estimate accuracy."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
import shlex
import subprocess
import sys

import numpy as np
import pandas as pd

from scripts.prospective_comparison import verify_registration
from scripts.synthetic_label_checks import check_cases, vocabulary
from src.eval.defect_prediction import COOLDOWN_DAYS, KEY, alert_episodes
from src.eval.improvement_detection import scored_alerts
from src.eval.improvement_protocol import canonical, digest, write_once
from src.eval.prospective_io import git, now
from src.eval.prospective_research import matrix, predict_json, structured_rows

ROOT = Path(__file__).resolve().parents[1]
PACK = 'reports/improvement/synthetic_review_v1'
CASES = PACK + '/fixtures/synthetic_cases.jsonl'
CLOSEOUT = PACK + '/PROJECT_CLOSEOUT.md'
INPUT_HASHES = {
    CASES: 'b61f887acc850867456526cdb3c8a912b2e4551feada772c4c3686af99fb144f',
    CLOSEOUT: '450ae2e75e25ccc216906afc32eae415c4e8f2bdea030b812539d7616a84f21e',
}
NOTICE = ('Synthetic software test only. Authored labels are injected; text classification '
          'is bypassed. No human accuracy, campaign performance, or model improvement is estimated.')
CONFIG = {
    'split': 'synthetic_software_test',
    'start': '2019-01-01', 'end': '2019-12-31', 'first_day': '2019-01-07',
    'weeks_by_fictional_model_year': {'2015': 0, '2016': 26, '2017': 27, '2018': 28, '2019': 29},
    'schedule_reason': 'An authored isolated observation followed by a weekly burst exercises count features and episode filtering; dates are fictional, not outcomes.',
    'label_source': 'agent_authored_fixture.expected_label injected directly as label_id',
    'fitting': False, 'calibration': False, 'selection': False,
    'campaign_outcomes': False, 'performance_metrics': False,
}


def read_inputs(root=ROOT):
    for name, expected in INPUT_HASHES.items():
        if digest(root / name) != expected:
            raise ValueError('Saved synthetic input hash mismatch: ' + name)
    rows = [json.loads(line) for line in (root / CASES).read_text().splitlines()]
    check_cases(rows, vocabulary(root))
    return rows


def complaints_from_cases(rows, *, root=ROOT):
    """Retain every fixture, including unclear labels, with explicit fictional dates."""
    check_cases(rows, vocabulary(root))
    first = date.fromisoformat(CONFIG['first_day'])
    return pd.DataFrame([
        dict(odino=row['case_id'], make=row['fictional_make'], component=row['component'],
             label_id=row['expected_label'], text=row['narrative'],
             datea=(first + timedelta(weeks=CONFIG['weeks_by_fictional_model_year'][str(row['fictional_model_year'])])).isoformat(),
             split='synthetic_software_test', is_synthetic=True,
             annotation_source=row['annotation_source'])
        for row in rows
    ])


def check_cooldown(alerts):
    previous = {}
    for row in alerts:
        key = tuple(row[k] for k in KEY)
        day = date.fromisoformat(row['available_at'])
        if key in previous and (day - previous[key]).days < COOLDOWN_DAYS:
            raise ValueError('Episode cooldown violated')
        previous[key] = day


def replay(rows, baseline_model, logistic_model, *, root=ROOT):
    frame = complaints_from_cases(rows, root=root)
    features = structured_rows(frame, end=CONFIG['end'])
    if not features or not np.isfinite(matrix(features)).all():
        raise ValueError('Missing or nonfinite structured features')
    scores = predict_json(logistic_model, features)
    if len(scores) != len(features) or not np.isfinite(scores).all() or not ((scores >= 0) & (scores <= 1)).all():
        raise ValueError('Invalid or misaligned logistic inference')
    baseline = alert_episodes(features, min_count=baseline_model['min_count'],
                              max_tail=baseline_model['max_tail'], start=CONFIG['start'], end=CONFIG['end'])
    logistic = scored_alerts(features, scores, threshold=logistic_model['threshold'],
                             start=CONFIG['start'], end=CONFIG['end'])
    by_id = {r['odino']: r for r in frame.to_dict('records')}
    for row in features:
        if row['label_id'] == 'other_unclear':
            raise ValueError('Unclear fixture produced a specific-label candidate')
        for identity in row['evidence_ids']:
            if by_id[identity]['datea'] >= row['available_at']:
                raise ValueError('Future evidence entered a candidate')
    for alerts in (baseline, logistic):
        check_cooldown(alerts)
    detail = [dict(row, logistic_score=float(score), split=CONFIG['split'], notice=NOTICE)
              for row, score in zip(features, scores)]
    report = dict(
        status='synthetic_detector_replay_passed', notice=NOTICE, split=CONFIG['split'],
        input_records=len(rows), records_preserved=len(frame),
        underlying_scenario_families=len({r['fixture_family'] for r in rows}),
        expected_label_counts=dict(sorted(Counter(frame.label_id).items())),
        specific_label_records=int(frame.label_id.ne('other_unclear').sum()),
        unclear_label_records=int(frame.label_id.eq('other_unclear').sum()),
        count_feature_candidates=len(features), finite_logistic_scores=len(scores),
        baseline_alert_episodes=len(baseline), logistic_alert_episodes=len(logistic),
        alert_count_note='Software execution counts on an authored timeline; alert volume is not evidence that either detector is better.',
        assertions={'prior_only_evidence': True, 'cooldown': True, 'unclear_not_specific_candidate': True,
                    'finite_features_and_scores': True, 'all_fixture_rows_retained': len(rows) == len(frame)},
        classifier_executed=False, label_injection=True, fitting_performed=False,
        model_selection_performed=False, campaign_outcomes_generated=False,
        human_validation={'labelled': 0, 'total': 300}, human_accuracy=None,
        performance_metrics=None, confidence_interval=None, is_candidate_result=False,
        real_independent_campaigns_added=0, prospective_records_collected=0,
        baseline_comparison='No performance comparison; frozen baseline and fixed logistic inference exercised only.',
        label_source=CONFIG['label_source'],
        scope='300 fictional FUEL SYSTEM fixtures for five makes; artificial 2019 timeline; no real complaints or recalls.',
    )
    return report, detail, baseline, logistic


def build(out, *, root=ROOT, command=None):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory; existing artifacts are never overwritten')
    rows = read_inputs(root)
    protocol, index, registration_commit = verify_registration(root)
    baseline = json.loads((root / protocol['baseline']['path']).read_text())
    logistic = json.loads((root / protocol['challenger']['path']).read_text())
    report, features, baseline_alerts, logistic_alerts = replay(rows, baseline, logistic, root=root)
    # Inputs must still match after processing, before any result is written.
    read_inputs(root)
    report['provenance'] = dict(
        created_at=now(), exact_command=command, code_commit=git(root, 'rev-parse', 'HEAD'),
        script_sha256=digest(Path(__file__)), config_hash=canonical(CONFIG),
        data_hash=INPUT_HASHES[CASES], input_hashes=INPUT_HASHES,
        registered_models={name: protocol[name] for name in ('baseline', 'challenger')},
        comparison_tag_commit=registration_commit, comparison_files_verified=len(index['files']),
        original_freeze_verified=True, original_freeze_tag=protocol['freeze']['original_tag_commit'],
    )
    out.mkdir(parents=True, exist_ok=False)
    write_once(out / 'config.json', CONFIG)
    write_once(out / 'replay.json', report)
    for name, records in [('feature_scores.jsonl', features), ('baseline_alerts.jsonl', baseline_alerts),
                          ('logistic_alerts.jsonl', logistic_alerts)]:
        with (out / name).open('x') as stream:
            for row in records:
                stream.write(json.dumps(dict(row, split=CONFIG['split'], notice=NOTICE), sort_keys=True) + '\n')
    names = sorted(p.name for p in out.iterdir())
    output = subprocess.check_output(['shasum', '-a', '256', *names], cwd=out, text=True)
    write_once(out / 'HASHES.json', dict(command='shasum -a 256',
               files={line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in output.splitlines()}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    command = 'FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -B -m scripts.synthetic_project_smoke ' + shlex.join(sys.argv[1:])
    print(json.dumps(build(args.out, command=command), indent=2))


if __name__ == '__main__':
    main()
