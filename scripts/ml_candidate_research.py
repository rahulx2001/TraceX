"""One fixed, unvalidated pre-2021 logistic prototype; never a baseline promotion."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shlex
import subprocess

import numpy as np
import pandas as pd

from src.eval.improvement_detection import labelled_candidates
from src.eval.improvement_protocol import Run, check_development, digest, require_disjoint, write_once
from src.eval.prospective_io import verify_freeze
from src.eval.prospective_research import FEATURES, fit_logistic, predict_json, structured_rows

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'reports/improvement/research_v2/PROTOCOL.json'
INPUTS = ('data/ml_improvement/complaints.parquet', 'data/ml_improvement/recalls.parquet')
NOTICE = 'Development-only evidence; not a candidate result and not a prospective estimate.'


def require_fixed_recipe(root, protocol):
    """The existing solver has fixed settings; never claim different settings."""
    expected = dict(steps=1000, learning_rate=0.1, C=1, threshold=0.5,
                    minimum_mature_rows=10, minimum_classes=2,
                    hyperparameter_search=False, calibration=False)
    if any(protocol['fitting'].get(k) != v for k, v in expected.items()):
        raise ValueError('Protocol differs from the fixed fitting recipe')
    if protocol['features'] != FEATURES or [protocol['data'][k] for k in ('start', 'end')] != ['2015-01-01', '2020-12-31']:
        raise ValueError('Protocol feature order or development window changed')
    for name in (PROTOCOL, 'scripts/ml_candidate_research.py'):
        committed = subprocess.run(['git', 'show', f'HEAD:{name}'], cwd=root,
                                   capture_output=True, check=False)
        if committed.returncode or committed.stdout != (root / name).read_bytes():
            raise ValueError('Commit the exact research recipe and script before fitting: ' + name)


def load_development(root, protocol):
    """Exactly two bounded, hash-pinned input files; never invoke preparation."""
    expected = protocol['data']['inputs']
    if set(expected) != set(INPUTS):
        raise ValueError('Only the two pinned development inputs are permitted')
    for name in INPUTS:
        if digest(root / name) != expected[name]:
            raise ValueError('Development input hash mismatch: ' + name)
    c = pd.read_parquet(root / INPUTS[0])
    check_development(c, 'datea')
    r = pd.read_parquet(root / INPUTS[1])
    check_development(r, 'rcdate')
    return c, r


def predict_proba(model, rows):
    """JSON-only numerical inference. Values are uncalibrated model outputs."""
    if model.get('type') != 'logistic' or model.get('feature_order') != FEATURES:
        raise ValueError('Unsupported model or feature order')
    for name in ('means', 'scales', 'coefficients'):
        values = np.asarray(model[name], dtype=float)
        if values.shape != (len(FEATURES),) or not np.isfinite(values).all():
            raise ValueError('Invalid model vector: ' + name)
    if np.any(np.asarray(model['scales']) <= 0):
        raise ValueError('Model scales must be positive')
    if not np.isfinite(model['intercept']) or not 0 <= model['threshold'] <= 1:
        raise ValueError('Invalid intercept or threshold')
    x = np.asarray([[row[f] for f in FEATURES] for row in rows], dtype=float).reshape(-1, len(FEATURES))
    if not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError('Count features must be finite and nonnegative')
    return predict_json(model, rows)


def support(c, r, protocol):
    folds = []
    for name, cut, start, end in [('A','2016-12-31','2017-01-01','2018-12-31'),
                                   ('B','2018-12-31','2019-01-01','2020-12-31')]:
        fit_r = r[r.rcdate.le(cut)]
        val_r = r[r.rcdate.between(start, end)]
        require_disjoint(fit_r.campno, [], val_r.campno)
        rows = structured_rows(c[c.datea.le(cut)], end=cut)
        training = labelled_candidates(rows, fit_r, start='2015-01-01', end=cut)
        folds.append(dict(fold=name, fit_end=cut, validation=[start,end],
            fit_campaigns=int(fit_r.campno.nunique()), validation_campaigns=int(val_r.campno.nunique()),
            candidate_rows=len(rows), mature_training_rows=len(training),
            positive_training_rows=sum(row['outcome'] for row in training),
            training_status='supported' if len(training)>=10 and len({x['outcome'] for x in training})==2 else 'insufficient_training_support'))
    rows = structured_rows(c, end=protocol['data']['end'])
    training = labelled_candidates(rows, r, start=protocol['data']['start'], end=protocol['data']['end'])
    audit = dict(notice=NOTICE, split='development', complaints=len(c), campaigns=int(r.campno.nunique()),
        complaints_by_year={str(k):int(v) for k,v in c.groupby(c.datea.str[:4]).size().items()},
        unclear_complaints=int(c.label_id.eq('other_unclear').sum()),
        specific_complaints=int(c.label_id.ne('other_unclear').sum()),
        registered_folds=folds, full_development_candidate_rows=len(rows),
        full_development_mature_rows=len(training), full_development_positive_rows=sum(x['outcome'] for x in training),
        distinct_positive_campaigns=sorted({camp for x in training for camp in x['matched_campaigns']}),
        causal_feature_recipe=FEATURES, performance_metrics=None,
        limitation='Full-development fitting is possible; both registered training folds remain unsupported. Rows sharing campaigns are not independent evidence.')
    return training, audit


def train(run_id, *, root=ROOT):
    protocol = json.loads((root / PROTOCOL).read_text())
    require_fixed_recipe(root, protocol)
    freeze, _, tag = verify_freeze(root)
    if tag != protocol['freeze']['existing_tag_commit'] or freeze['mode'] != 'baseline_replication':
        raise ValueError('Unexpected baseline freeze')
    # Reserve the append-only run before reading a data frame or fitting.
    command = 'FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -B -m scripts.ml_candidate_research --run-id ' + shlex.quote(run_id)
    run = Run(root, run_id, protocol, [root / name for name in (*INPUTS, PROTOCOL)], command, split='development')
    try:
        c, r = load_development(root, protocol)
        training, audit = support(c, r, protocol)
        write_once(run.path / 'support_audit.json', audit | {'provenance':run.meta})
        model = fit_logistic(training, threshold=protocol['fitting']['threshold'])
        model.update(schema_version=1, status='trained_unvalidated', notice=NOTICE,
            calibrated=False, production_eligible=False, freeze_eligible=False,
            training_window=[protocol['data']['start'],protocol['data']['end']],
            label_source=protocol['labels'], training_rows=len(training),
            positive_training_rows=sum(x['outcome'] for x in training), provenance=run.meta)
        predictions = predict_proba(model, training)
        write_once(run.path / 'model.json', model)
        restored = json.loads((run.path / 'model.json').read_text())
        error = float(np.max(np.abs(predictions - predict_proba(restored, training))))
        if error > protocol['evaluation']['reproduction_tolerance']:
            raise ValueError('JSON inference reproduction failed')
        write_once(run.path / 'serialization_check.json', dict(status='passed', rows=len(training),
            maximum_absolute_error=error, tolerance=protocol['evaluation']['reproduction_tolerance'],
            model_sha256=digest(run.path / 'model.json'), performance_validation=False, notice=NOTICE))
        queue = c[c.label_id.eq('other_unclear')].sort_values(['datea','odino'])
        with (run.path / 'review_queue.csv').open('x', newline='') as stream:
            fields=['complaint_id','received_date','make','component','existing_model_label','human_label','reviewer','reviewed_at']
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for row in queue.itertuples():
                writer.writerow(dict(complaint_id=row.odino,received_date=row.datea,make=row.make,
                                     component=row.component,existing_model_label=row.label_id,
                                     human_label='',reviewer='',reviewed_at=''))
        with (run.path / 'model_card.md').open('x') as stream:
            stream.write(f'''# Trained logistic prototype — unvalidated

{NOTICE}

One fixed numpy L2 logistic recipe fitted on {len(training)} mature rows,
including {sum(x['outcome'] for x in training)} positive rows, from 2015–2020.
These rows cover only {len(audit['distinct_positive_campaigns'])} distinct positive campaigns;
they are not independent observations. Features: {', '.join(FEATURES)}.
JSON contains feature order, means, scales, coefficients, intercept and the
fixed 0.5 threshold. No pickle, sklearn, new dependency, calibration, tuning,
paid call, new generated label or human semantic label was used.

Both registered training folds still have zero mature rows. No out-of-sample
performance metric is available for this full-development fit. No training-set
recall/precision is presented as an improvement. JSON reproduction error is
{error}; this proves serialization fidelity, not predictive quality.

The existing frozen baseline and 2027–2028 Mode B prospective test are unchanged.
This prototype is excluded from that test and is neither freeze- nor production-
eligible. A new pre-registered comparison and adequate independent training and
evaluation evidence would be needed before any better-model claim.

The blank review queue contains {len(queue)} existing unclear complaint IDs.
No human review has been performed; human semantic labels remain 0/300. Review
requires the original pre-2021 source records and the existing labeling guide.
Labels alone cannot create missing early observations or complete follow-up.

Split: development, full 2015–2020 fit only. Label source: {protocol['labels']}
Scope: unchanged five makes, MY2015–2024, repaired FUEL SYSTEM.
Baseline comparison: none; historical recall/precision remain unchanged.
Exact command: `{command}`.
Config hash: `{run.meta['config_hash']}`.
Data hash: `{run.meta['data_hash']}`.
Code commit: `{run.meta['code_commit']}`.
Is this a validated candidate result? No. Performance values and CIs: unavailable.
''')
        summary=dict(status='trained_unvalidated',notice=NOTICE,model=str((run.path/'model.json').relative_to(root)),
            model_sha256=digest(run.path/'model.json'),training_rows=len(training),
            positive_training_rows=sum(x['outcome'] for x in training),performance_metrics=None,
            improved_score_demonstrated=False,existing_freeze_unchanged=True,provenance=run.meta)
        write_once(run.path/'results.json',summary)
        verify_freeze(root)
        run.finish('trained_unvalidated')
        return summary
    except BaseException:
        run.finish('failed',exit_code=1)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    print(json.dumps(train(args.run_id),indent=2))


if __name__=='__main__':
    main()
