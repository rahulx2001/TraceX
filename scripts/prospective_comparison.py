"""Fixed prospective challenger comparison. Real execution is future human work."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from scripts.final_prospective_eval import apply_labels, estimate, load_raw
from src.eval.defect_prediction import KEY, alert_episodes, candidates, evaluate
from src.eval.improvement_detection import RECALL, scored_alerts
from src.eval.improvement_metrics import calibration
from src.eval.improvement_protocol import digest, require_disjoint, write_once
from src.eval.prospective_io import (CUSTODY, blob, check_attestation, check_collection_log,
                                     external_root, git, load, manifest_chain, now, today, verify_freeze)
from src.eval.prospective_research import FEATURES, predict_json

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'reports/improvement/comparison_v1'
PROTOCOL = DIRECTORY + '/protocol.json'
INDEX = DIRECTORY + '/REGISTERED_HASHES.json'
TAG = 'ml-logistic-comparison-freeze-2026-v1'


def verify_registration(root):
    _, _, original_tag = verify_freeze(root)
    registered = git(root, 'rev-parse', TAG + '^{commit}')
    if blob(root, registered, INDEX) != (root / INDEX).read_bytes():
        raise ValueError('Comparison registration index differs from tag')
    index = load(root / INDEX)
    for name, expected in index['files'].items():
        if digest(root / name) != expected or hashlib.sha256(blob(root, registered, name)).hexdigest() != expected:
            raise ValueError('Comparison frozen hash mismatch: ' + name)
    protocol = load(root / PROTOCOL)
    if original_tag != protocol['freeze']['original_tag_commit']:
        raise ValueError('Original baseline freeze changed')
    for name in ('challenger', 'baseline'):
        if digest(root / protocol[name]['path']) != protocol[name]['sha256']:
            raise ValueError('Model hash mismatch: ' + name)
    if platform.python_version() != protocol['environment']['python'] or any(
        version(package) != expected for package, expected in protocol['environment']['versions'].items()
    ):
        raise ValueError('Runtime differs from registered Python/dependency versions')
    return protocol, index, registered


def prospective_rows(complaints, window):
    """Same four prior-only counts as structured_rows, with prospective dates."""
    c = complaints.copy()
    if c.datea.isna().any() or not c.datea.astype(str).str.fullmatch(r'\d{4}-\d{2}-\d{2}').all():
        raise ValueError('Invalid prospective complaint date')
    for value in c.datea:
        date.fromisoformat(value)
    if not c.datea.between(window['flag_start'], window['flag_end']).all():
        raise ValueError('Complaint outside the registered flag window')
    if c.odino.astype(str).duplicated().any():
        raise ValueError('Duplicate complaint identity')
    dates = pd.to_datetime(c.datea)
    rows = candidates(c, window=13, end=window['flag_end'])
    for row in rows:
        available = pd.Timestamp(row['available_at'])
        specific = c.make.eq(row['make']) & c.component.eq(row['component']) & c.label_id.eq(row['label_id'])
        for days in (30, 90, 365):
            prior = dates.ge(available-pd.Timedelta(days=days)) & dates.lt(available)
            row[f'complaints_{days}d'] = int((prior & specific).sum())
        row['same_make_365d'] = int((prior & c.make.eq(row['make'])).sum())
    return rows


def paired_components(baseline, challenger, campaigns, uncertainty):
    """Preserve evaluator denominators, including precision-only 2029 matches."""
    campaign_ids = sorted(set(campaigns))
    parent = {('campaign', c): ('campaign', c) for c in campaign_ids}
    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]
    def union(left, right):
        parent[find(right)] = find(left)
    def identity(alert):
        return ('alert', alert['available_at'], *(str(alert[k]) for k in KEY))
    for result in (baseline, challenger):
        for alert in result['alert_details']:
            key = identity(alert)
            find(key)
            for campaign in alert['matched_campaigns']:
                union(key, ('campaign', campaign))
    roots = sorted({find(key) for key in list(parent)})
    indices = {key: i for i, key in enumerate(roots)}
    values = np.zeros((len(roots), 7))
    for campaign in campaign_ids:
        row = values[indices[find(('campaign', campaign))]]
        row[:3] += [1, campaign in baseline['campaign_hits'], campaign in challenger['campaign_hits']]
    for offset, result in ((3, baseline), (5, challenger)):
        for alert in result['alert_details']:
            if alert['full_followup']:
                values[indices[find(identity(alert))], offset:offset+2] += [bool(alert['matched_campaigns']), 1]
    total = values.sum(axis=0)
    expected = [len(campaign_ids), len(baseline['campaign_hits']), len(challenger['campaign_hits']),
                baseline['confirmed_mature_alerts'], baseline['mature_alerts'],
                challenger['confirmed_mature_alerts'], challenger['mature_alerts']]
    if total.tolist() != expected:
        raise ValueError('Bootstrap component totals differ from evaluator denominators')
    def delta(v, metric):
        with np.errstate(divide='ignore', invalid='ignore'):
            return ((v[..., 2]-v[..., 1])/v[..., 0] if metric == 'recall'
                    else v[..., 5]/v[..., 6]-v[..., 3]/v[..., 4])
    output = dict(eligible_campaigns=len(campaign_ids),
                  campaign_linked_components=len({find(('campaign', c)) for c in campaign_ids}),
                  total_components=len(roots), evaluator_counts=expected, metrics={})
    draws = uncertainty['draws']
    for metric in ('recall', 'precision'):
        point = delta(total, metric)
        runs = []
        for seed in uncertainty['seeds']:
            if len(roots):
                weights = np.random.default_rng(seed).multinomial(len(roots), np.full(len(roots), 1/len(roots)), size=draws)
                samples = delta(weights @ values, metric)
            else:
                samples = np.full(draws, np.nan)
            valid = samples[np.isfinite(samples)]
            interval = np.quantile(valid, [.025, .975]).tolist() if len(valid) >= .95*draws else None
            runs.append(dict(seed=seed, draws=draws, valid_draws=len(valid), ci95=interval))
        output['metrics'][metric] = dict(value=float(point) if np.isfinite(point) else None, bootstrap=runs)
    return output


def compare(c, r, protocol, baseline_model, challenger_model):
    window = protocol['prospective']
    eligible = sorted(set(r.loc[r.rcdate.between(window['flag_start'], window['flag_end']), 'campno']))
    if len(eligible) < protocol['sample']['minimum_campaigns']:
        raise ValueError('INCONCLUSIVE_SAMPLE: count before metrics')
    require_disjoint(protocol['development']['excluded_campaign_ids'], [], r.campno)
    variants, campaign_rows, alert_rows = {}, [], []
    for variant, frame in [('all_reports', c), ('excluding_explicit_recall_reports', c[~c.text.map(lambda t: bool(RECALL.search(str(t))))])]:
        rows = prospective_rows(frame, window)
        scores = predict_json(challenger_model, rows)
        alerts = {
            'baseline': alert_episodes(rows, min_count=baseline_model['min_count'], max_tail=baseline_model['max_tail'], start=window['flag_start'], end=window['flag_end']),
            'challenger': scored_alerts(rows, scores, threshold=challenger_model['threshold'], start=window['flag_start'], end=window['flag_end'])}
        estimates, evaluated = {}, {}
        for method, selected in alerts.items():
            metrics, recall, precision = estimate(selected, r, window)
            evaluated[method] = {**precision, 'campaign_hits': recall['campaign_hits']}
            metrics['per_make'] = {make: estimate([a for a in selected if a['make'] == make], r[r.make.eq(make)], window)[0]
                                   for make in protocol['scope']['makes']}
            estimates[method] = metrics
            campaign_rows.extend(dict(variant=variant, method=method, campaign=campaign, detected=campaign in recall['campaign_hits'], lead_days=recall['campaign_hits'].get(campaign)) for campaign in eligible)
            alert_rows.extend(dict(variant=variant, method=method, available_at=a['available_at'], make=a['make'], component=a['component'], label_id=a['label_id'], full_followup=a['full_followup'], matched_campaigns=';'.join(a['matched_campaigns'])) for a in precision['alert_details'])
        difference = paired_components(evaluated['baseline'], evaluated['challenger'], eligible, protocol['uncertainty'])
        outcomes = evaluate(rows, r, start=window['flag_start'], end=window['outcome_cutoff'])['alert_details']
        mature = [(a, score) for a, score in zip(outcomes, scores) if a['full_followup']]
        diagnostics = calibration([int(bool(a['matched_campaigns'])) for a, _ in mature], [score for _, score in mature], reference_probability=protocol['challenger']['training_prevalence'], bins=10, seed=17)
        diagnostics['notice'] = 'Uncalibrated score diagnostics against model/recall proxies; not semantic accuracy or evidence of calibrated physical-defect risk.'
        variants[variant] = dict(methods=estimates, difference=difference, score_diagnostics=diagnostics)
    def positive(variant):
        return all(v['value'] is not None and v['value'] > 0 and all(b['ci95'] is not None and b['ci95'][0] > 0 for b in v['bootstrap'])
                   for v in variants[variant]['difference']['metrics'].values())
    primary = variants['all_reports']
    enough_components = primary['difference']['campaign_linked_components'] >= protocol['sample']['minimum_campaign_linked_clusters_for_confirmation']
    loss = any(v['value'] is not None and v['value'] < 0 for v in primary['difference']['metrics'].values())
    confirmed = positive('all_reports') and enough_components
    status = 'IMPROVEMENT_CONFIRMED' if confirmed else ('FAILURE_BELOW_BASELINE' if loss else 'INCONCLUSIVE_COMPARISON')
    target = all(primary['methods']['challenger'][metric]['value'] is not None and primary['methods']['challenger'][metric]['value'] >= threshold for metric, threshold in protocol['decision']['target_met'].items())
    return dict(status=status, eligible_campaigns=len(eligible), variants=variants, target_met=target,
                improvement_confirmed=confirmed, sensitivity_supported=positive('excluding_explicit_recall_reports'),
                original_phase2_qualification=False, production_promotion=False), campaign_rows, alert_rows


def final_comparison(args, *, root=ROOT):
    if not args.final_comparison:
        raise ValueError('--final-comparison is required')
    protocol, index, registered = verify_registration(root)
    registry = root / protocol['analysis']['run_registry']
    if registry.exists():
        raise ValueError('Comparison already attempted; a committed deviation and human review are required')
    if git(root, 'status', '--porcelain'):
        raise ValueError('Dirty working tree')
    day = today()
    if args.today:
        if os.environ.get('FRONTLINE_TEST_ISOLATION') != '1' or load(root / CUSTODY).get('synthetic_fixture') is not True:
            raise ValueError('--today is only available in synthetic test repositories')
        day = date.fromisoformat(args.today).isoformat()
    window = protocol['prospective']
    if day < window['outcome_cutoff']:
        raise ValueError('Before outcome cutoff; no raw data access')
    custody = external_root(root, args.custody_root)
    manifest, chain = manifest_chain(root, args.manifest_ref)
    if manifest['status'] != 'data_frozen':
        raise ValueError('Manifest is not data_frozen')
    attestation = check_attestation(root, args.manifest_ref, manifest)
    check_collection_log(root, args.manifest_ref, manifest, chain)
    if manifest.get('outcomes_complete_through') != window['outcome_cutoff'] or not manifest['snapshots'] or max(s['snapshot_date'] for s in manifest['snapshots']) < window['outcome_cutoff']:
        raise ValueError('Complete outcome follow-up is not attested')
    if manifest.get('comparison_authorizations', {}).get(protocol['study_id']) != index['files'][PROTOCOL]:
        raise ValueError('Missing committed authorization for this comparison protocol')
    if manifest.get('comparison_runs', {}).get(protocol['study_id']) is not None:
        raise ValueError('Comparison already recorded in manifest')
    output = Path(args.out).absolute()
    if any(p.is_symlink() for p in [output, *output.parents]) or output == custody or custody in output.parents:
        raise ValueError('Output must be outside custody and not symlinked')
    if output.exists():
        raise ValueError('Output already exists; no overwrites')
    run = dict(status='started', started_at=now(), study_id=protocol['study_id'],
               source_commit=git(root, 'rev-parse', 'HEAD'), freeze_tag_commit=registered,
               config_hash=index['files'][PROTOCOL], data_hash=chain[-1]['sha256'], manifest_chain=chain,
               split='prospective-sealed', label_source='Pinned model hypotheses and official recall dates; no human semantic truth',
               scope=protocol['scope'], seeds=protocol['uncertainty']['seeds'], attestation=attestation,
               exact_command_template='.venv-hackathon/bin/python -B -m scripts.prospective_comparison --final-comparison --custody-root <human-mounted-volume> --manifest-ref '+args.manifest_ref+' --out <new-output-directory>',
               custody_limitation=protocol['custody']['threat_model'])
    write_once(registry, run)
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / 'run_manifest.json', run)
    try:
        c, r, quality = load_raw(custody, manifest, protocol)
        count = int(r.loc[r.rcdate.between(window['flag_start'], window['flag_end']), 'campno'].nunique())
        if count < protocol['sample']['minimum_campaigns']:
            result = dict(status='INCONCLUSIVE_SAMPLE', eligible_campaigns=count, minimum_campaigns=25, metrics=None)
            write_once(output / 'final_analysis.json', result)
            write_once(output / 'completion.json', dict(status=result['status'], exit_code=2, finished_at=now()))
            return 2
        require_disjoint(protocol['development']['excluded_campaign_ids'], [], r.campno)
        c, r = apply_labels(c, r, custody, manifest, protocol)
        result, campaigns, alerts = compare(c, r, protocol, load(root / protocol['baseline']['path']), load(root / protocol['challenger']['path']))
        result.update(provenance=run, parser_quality=quality, is_candidate_result=True,
                      label_limit='Model/recall proxy comparison only; human semantic validation remains unavailable')
        write_once(output / 'final_analysis.json', result)
        lines = ['# Fixed prospective model comparison', '', result['status'], '',
                 'Prospective-sealed; model/recall proxy labels, not human semantic accuracy.', '',
                 '| Variant | Method | Metric | Numerator / denominator | Value | Wilson 95% CI |',
                 '|---|---|---|---|---|---|']
        for variant, data in result['variants'].items():
            for method, metrics in data['methods'].items():
                for metric in ('recall', 'precision'):
                    m = metrics[metric]
                    lines.append(f"| {variant} | {method} | {metric} | {m['numerator']}/{m['denominator']} | {m['value']} | {m['ci95']} |")
        lines.extend(['', 'All paired intervals, seed results, dependence counts and diagnostics: final_analysis.json.',
                      'Shared cohort with the original Mode B study; not an independent replication. No promotion authorized.'])
        with (output / 'final_analysis.md').open('x') as stream:
            stream.write('\n'.join(lines)+'\n')
        for name, rows, fields in [('campaigns.csv', campaigns, ['variant','method','campaign','detected','lead_days']),
                                  ('alerts.csv', alerts, ['variant','method','available_at','make','component','label_id','full_followup','matched_campaigns'])]:
            with (output / name).open('x', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        write_once(output / 'completion.json', dict(status='completed', finished_at=now(), exit_code=0,
                                                   outputs={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
        return 0
    except BaseException:
        write_once(output / 'completion.json', dict(status='failed', finished_at=now(), exit_code=1))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-comparison', action='store_true')
    parser.add_argument('--custody-root', required=True)
    parser.add_argument('--manifest-ref', default='ml-score-improvement')
    parser.add_argument('--out', required=True)
    parser.add_argument('--today', help='Synthetic repositories only')
    args = parser.parse_args()
    try:
        raise SystemExit(final_comparison(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()
