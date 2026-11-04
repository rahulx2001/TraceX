import copy
import json

import numpy as np
import pytest

from scripts import synthetic_project_smoke as smoke
from src.eval.prospective_research import structured_rows


def models():
    protocol = json.loads((smoke.ROOT / 'reports/improvement/comparison_v1/protocol.json').read_text())
    return [json.loads((smoke.ROOT / protocol[name]['path']).read_text()) for name in ('baseline', 'challenger')]


def test_saved_cases_execute_frozen_detector_without_claiming_accuracy(tmp_path):
    # Register this software fixture separately from the immutable real study.
    from .test_prospective_comparison import registered_repository
    from scripts.synthetic_label_checks import TAXONOMY
    root, _ = registered_repository(tmp_path/'synthetic-registration')
    for name in [*smoke.INPUT_HASHES, TAXONOMY]:
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((smoke.ROOT/name).read_bytes())
    out = tmp_path / 'replay'
    report = smoke.build(out, root=root, command='synthetic test')
    assert report['input_records'] == report['records_preserved'] == 300
    assert report['specific_label_records'] == report['unclear_label_records'] == 150
    assert report['count_feature_candidates'] == report['finite_logistic_scores'] > 0
    assert report['baseline_alert_episodes'] > 0
    assert all(report['assertions'].values())
    assert report['performance_metrics'] is None and report['human_accuracy'] is None
    assert not report['classifier_executed'] and not report['fitting_performed']
    assert report['human_validation'] == {'labelled': 0, 'total': 300}
    assert not report['is_candidate_result'] and report['real_independent_campaigns_added'] == 0
    before = (out / 'replay.json').read_bytes()
    with pytest.raises(FileExistsError):
        smoke.build(out, root=root)
    assert (out / 'replay.json').read_bytes() == before


@pytest.mark.parametrize('name', list(smoke.INPUT_HASHES))
def test_changed_saved_input_is_rejected_before_output(tmp_path, name):
    for path in smoke.INPUT_HASHES:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((smoke.ROOT / path).read_bytes())
    with (tmp_path / name).open('a') as stream:
        stream.write('\n')
    with pytest.raises(ValueError, match='input hash mismatch'):
        smoke.build(tmp_path / 'out', root=tmp_path)
    assert not (tmp_path / 'out').exists()


def test_injected_human_provenance_rejected():
    rows = smoke.read_inputs()
    rows[0]['human_reviewed'] = True
    with pytest.raises(ValueError, match='provenance'):
        smoke.complaints_from_cases(rows)


def test_replay_deterministic_without_mutating_supplied_records():
    rows = smoke.read_inputs()
    before = copy.deepcopy(rows)
    first = smoke.replay(rows, *models())
    assert first == smoke.replay(list(reversed(rows)), *models())
    assert rows == before
    frame = smoke.complaints_from_cases(rows)
    assert set(frame.odino) == {r['case_id'] for r in rows}
    assert frame.datea.between('2019-01-01', '2019-12-31').all()


def test_date_boundary_and_nonfinite_scores_refused(monkeypatch):
    rows = smoke.read_inputs()
    frame = smoke.complaints_from_cases(rows)
    frame.loc[0, 'datea'] = '2021-01-01'
    with pytest.raises(ValueError):
        structured_rows(frame, end='2020-12-31')
    monkeypatch.setattr(smoke, 'predict_json', lambda model, features: np.full(len(features), np.nan))
    with pytest.raises(ValueError, match='Invalid or misaligned'):
        smoke.replay(rows, *models())
