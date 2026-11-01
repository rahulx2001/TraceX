"""Synthetic comparisons only; no prospective performance evidence."""
import argparse
import json

import pandas as pd
import pytest

from scripts import prospective_comparison as comparison
from src.eval.improvement_protocol import digest
from src.eval.prospective_io import MANIFEST
from src.eval.prospective_research import structured_rows
from .prospective_fixture import SOURCE, repository, frozen_data, write, commit, git


def registered_repository(tmp_path):
    root, volume = repository(tmp_path)
    protocol = json.loads((SOURCE / comparison.PROTOCOL).read_text())
    protocol['freeze']['original_tag_commit'] = git(root, 'rev-parse', 'ml-prospective-freeze-2026^{commit}')
    protocol['baseline']['sha256'] = digest(root / protocol['baseline']['path'])
    for name in [protocol['challenger']['path'], 'scripts/prospective_comparison.py']:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((SOURCE / name).read_bytes())
    write(root / comparison.PROTOCOL, protocol)
    files = [comparison.PROTOCOL, 'scripts/prospective_comparison.py', protocol['challenger']['path'], protocol['baseline']['path']]
    write(root / comparison.INDEX, dict(files={name:digest(root / name) for name in files}))
    commit(root)
    git(root, 'tag', '-a', comparison.TAG, '-m', 'Synthetic comparison registration')
    return root, volume


def authorize(root):
    manifest = json.loads((root / MANIFEST).read_text())
    manifest.update(prev_sha256=digest(root / MANIFEST), comparison_authorizations={
        'fixed-logistic-comparison-v1': digest(root / comparison.PROTOCOL)})
    write(root / MANIFEST, manifest)
    commit(root)


def args(volume, out, **changes):
    return argparse.Namespace(**(dict(final_comparison=True, custody_root=str(volume), manifest_ref='HEAD',
                                     out=str(out), today='2030-01-01') | changes))


@pytest.mark.parametrize('case, message', [('flag', '--final-comparison'), ('early', 'Before outcome'),
                                         ('dirty', 'Dirty'), ('hash', 'hash mismatch'), ('marker', 'marker'),
                                         ('clock_override', 'synthetic')])
def test_refuses_before_reading_outcomes(tmp_path, monkeypatch, case, message):
    root, volume = registered_repository(tmp_path)
    options = args(volume, tmp_path / 'out')
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION', '1')
    if case == 'flag': options.final_comparison = False
    elif case == 'early': options.today = '2029-12-30'
    elif case == 'dirty': (root / 'dirty.txt').write_text('synthetic')
    elif case == 'hash': (root / 'scripts/prospective_comparison.py').write_text('tampered')
    elif case == 'marker': (volume / '.rca-custody').unlink()
    else: monkeypatch.delenv('FRONTLINE_TEST_ISOLATION')
    monkeypatch.setattr(comparison, 'load_raw', lambda *a: pytest.fail('Outcomes read before gates'))
    with pytest.raises(ValueError, match=message):
        comparison.final_comparison(options, root=root)


@pytest.mark.parametrize('case, message', [('authorization','authorization'), ('attestation','attestation'),
                                         ('chain','chain'), ('coverage','follow-up')])
def test_committed_custody_and_study_gates(tmp_path, monkeypatch, case, message):
    root, volume = registered_repository(tmp_path)
    frozen_data(root, volume, monkeypatch)
    if case != 'authorization': authorize(root)
    if case != 'authorization':
        manifest = json.loads((root / MANIFEST).read_text())
        manifest['prev_sha256'] = digest(root / MANIFEST)
        if case == 'attestation': manifest['untouched_attestation'] = None
        elif case == 'chain': manifest['prev_sha256'] = '0' * 64
        else: manifest['outcomes_complete_through'] = None
        write(root / MANIFEST, manifest)
        commit(root)
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION', '1')
    monkeypatch.setattr(comparison, 'load_raw', lambda *a: pytest.fail('Outcomes read before gates'))
    with pytest.raises(ValueError, match=message):
        comparison.final_comparison(args(volume, tmp_path / 'out'), root=root)


def test_insufficient_sample_never_loads_labels_or_computes_metrics(tmp_path, monkeypatch):
    root, volume = registered_repository(tmp_path)
    frozen_data(root, volume, monkeypatch, campaigns=24)
    authorize(root)
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION', '1')
    monkeypatch.setattr(comparison, 'apply_labels', lambda *a: pytest.fail('Labels read below sample floor'))
    monkeypatch.setattr(comparison, 'compare', lambda *a: pytest.fail('Metrics computed below sample floor'))
    out = tmp_path / 'out'
    assert comparison.final_comparison(args(volume, out), root=root) == 2
    result = json.loads((out / 'final_analysis.json').read_text())
    assert result == dict(status='INCONCLUSIVE_SAMPLE', eligible_campaigns=24, minimum_campaigns=25, metrics=None)
    assert not (out / 'campaigns.csv').exists()


def test_synthetic_final_comparison_writes_all_outputs_and_reserves_one_run(tmp_path, monkeypatch):
    root, volume = registered_repository(tmp_path)
    frozen_data(root, volume, monkeypatch, campaigns=25)
    authorize(root)
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION', '1')
    out = tmp_path / 'out'
    assert comparison.final_comparison(args(volume, out), root=root) == 0
    for name in ['final_analysis.json', 'final_analysis.md', 'campaigns.csv', 'alerts.csv', 'run_manifest.json']:
        assert (out / name).is_file()
    result = json.loads((out / 'final_analysis.json').read_text())
    assert result['eligible_campaigns'] == 25
    assert result['original_phase2_qualification'] is False
    assert result['improvement_confirmed'] is False
    assert result['variants']['all_reports']['methods']['baseline']['recall']['denominator'] == 25
    with pytest.raises(ValueError, match='already attempted'):
        comparison.final_comparison(args(volume, tmp_path / 'different-out'), root=root)
    assert str(volume) not in (out / 'run_manifest.json').read_text()


def test_registered_runtime_versions_are_required(tmp_path, monkeypatch):
    root, _ = registered_repository(tmp_path)
    monkeypatch.setattr(comparison.platform, 'python_version', lambda: '3.12.0')
    with pytest.raises(ValueError, match='Runtime differs'):
        comparison.verify_registration(root)


def test_prospective_feature_recipe_reproduces_frozen_development_recipe():
    dates = pd.date_range('2019-01-07', periods=30, freq='7D').strftime('%Y-%m-%d')
    frame = pd.DataFrame([dict(odino=str(i), datea=day, make='FORD', component='FUEL SYSTEM', label_id='fuel_pump_failure')
                          for i, day in enumerate(dates)])
    window = dict(flag_start='2019-01-01', flag_end='2019-12-31')
    expected = structured_rows(frame, end=window['flag_end'])
    actual = comparison.prospective_rows(frame, window)
    assert actual
    assert [{k:r[k] for k in comparison.FEATURES} for r in actual] == [{k:r[k] for k in comparison.FEATURES} for r in expected]
    future = frame.iloc[-1:].copy()
    future['datea'] = '2020-01-01'
    with pytest.raises(ValueError, match='outside'):
        comparison.prospective_rows(pd.concat([frame, future]), window)


def test_precision_only_campaigns_link_alerts_without_inflating_recall_denominator():
    def alert(day):
        return dict(available_at=day, make='FORD', component='FUEL SYSTEM', label_id='fuel_pump_failure',
                    full_followup=True, matched_campaigns=['SYN2029'])
    baseline = dict(campaign_hits={}, alert_details=[alert('2028-01-01'), alert('2028-05-01')],
                    mature_alerts=2, confirmed_mature_alerts=2)
    challenger = dict(campaign_hits={}, alert_details=[alert('2028-01-01')],
                      mature_alerts=1, confirmed_mature_alerts=1)
    result = comparison.paired_components(baseline, challenger, [f'SYN{i}' for i in range(25)], dict(draws=2000,seeds=[17,29,43,71,101]))
    assert result['evaluator_counts'] == [25,0,0,2,2,1,1]
    assert result['campaign_linked_components'] == 25
    assert result['total_components'] == 26
    assert result['metrics']['recall']['value'] == result['metrics']['precision']['value'] == 0
    assert all(r['valid_draws'] < 2000 for r in result['metrics']['precision']['bootstrap'])
