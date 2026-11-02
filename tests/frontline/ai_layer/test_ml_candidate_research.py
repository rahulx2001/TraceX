"""Numerical and data-boundary tests; synthetic fixtures are not model evidence."""
import copy
import json
import math
import subprocess

import numpy as np
import pandas as pd
import pytest

from scripts import ml_candidate_research as candidate


def model():
    return dict(type='logistic',feature_order=candidate.FEATURES,
                means=[1.,2.,3.,4.],scales=[2.,2.,2.,2.],
                coefficients=[1.,-1.,0.5,0.],intercept=0.25,threshold=0.5)


def test_json_inference_matches_independent_log_odds_and_empty_batch():
    row=dict(zip(candidate.FEATURES,[3.,2.,5.,4.]))
    expected=1/(1+math.exp(-1.75))
    restored=json.loads(json.dumps(model(),allow_nan=False))
    assert candidate.predict_proba(restored,[row]).tolist()==pytest.approx([expected])
    assert candidate.predict_proba(restored,[]).shape==(0,)


@pytest.mark.parametrize('field,value',[
    ('scales',[1.,0.,1.,1.]),('coefficients',[float('nan')]*4),
    ('means',[1.,2.]),('feature_order',list(reversed(candidate.FEATURES))),
    ('threshold',1.1),('intercept',float('inf'))])
def test_inference_rejects_invalid_model_parameters(field,value):
    bad=copy.deepcopy(model());bad[field]=value
    with pytest.raises(ValueError):candidate.predict_proba(bad,[])


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1.])
def test_inference_rejects_invalid_count_features(value):
    row=dict.fromkeys(candidate.FEATURES,1.);row[candidate.FEATURES[0]]=value
    with pytest.raises(ValueError,match='features'):candidate.predict_proba(model(),[row])


def test_fixed_logistic_recipe_learns_from_synthetic_two_class_support():
    rows=[dict(zip(candidate.FEATURES,[float(i),float(i*2),float(i*3),float(i*4)]),outcome=int(i>=10)) for i in range(20)]
    learned=candidate.fit_logistic(rows)
    restored=json.loads(json.dumps(learned,allow_nan=False))
    probabilities=candidate.predict_proba(restored,rows)
    assert probabilities[-1]>probabilities[0]
    assert np.max(np.abs(probabilities-candidate.predict_proba(learned,rows)))<1e-12


@pytest.mark.parametrize('count,positive', [(9, True), (20, False)])
def test_unsupported_fits_are_rejected(count,positive):
    rows=[dict.fromkeys(candidate.FEATURES,float(i))|{'outcome':int(positive and i>4)} for i in range(count)]
    with pytest.raises(ValueError,match='insufficient_training_support'):candidate.fit_logistic(rows)


def test_hash_mismatch_and_foreign_input_refuse_before_dataframe_read(tmp_path,monkeypatch):
    for name in candidate.INPUTS:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'synthetic')
    inputs={name:candidate.digest(tmp_path/name) for name in candidate.INPUTS}
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('must not read'))
    with pytest.raises(ValueError,match='Only the two'):
        candidate.load_development(tmp_path,{'data':{'inputs':inputs|{'reports/oos/file.parquet':'bad'}}})
    inputs[candidate.INPUTS[0]]='0'*64
    with pytest.raises(ValueError,match='hash mismatch'):
        candidate.load_development(tmp_path,{'data':{'inputs':inputs}})


def test_invalid_complaint_date_stops_before_reading_recalls(tmp_path,monkeypatch):
    for name in candidate.INPUTS:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'synthetic')
    inputs={name:candidate.digest(tmp_path/name) for name in candidate.INPUTS}
    calls=[]
    def read(path):
        calls.append(path.relative_to(tmp_path).as_posix())
        return pd.DataFrame({'datea':['2021-01-01']})
    monkeypatch.setattr(pd,'read_parquet',read)
    with pytest.raises(ValueError,match='Opened'):
        candidate.load_development(tmp_path,{'data':{'inputs':inputs}})
    assert calls==[candidate.INPUTS[0]]


def test_fixed_recipe_must_be_committed_and_unchanged(tmp_path):
    protocol = json.loads((candidate.ROOT / candidate.PROTOCOL).read_text())
    for name in (candidate.PROTOCOL, 'scripts/ml_candidate_research.py'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(protocol) if name == candidate.PROTOCOL else '# synthetic script\n')
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    git('init')
    with pytest.raises(ValueError, match='Commit the exact'):
        candidate.require_fixed_recipe(tmp_path, protocol)
    git('add', '.')
    git('-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'Synthetic fixed recipe')
    candidate.require_fixed_recipe(tmp_path, protocol)
    changed = copy.deepcopy(protocol)
    changed['fitting']['steps'] = 10
    with pytest.raises(ValueError, match='fixed fitting recipe'):
        candidate.require_fixed_recipe(tmp_path, changed)
    changed = copy.deepcopy(protocol)
    changed['data']['end'] = '2021-12-31'
    with pytest.raises(ValueError, match='development window'):
        candidate.require_fixed_recipe(tmp_path, changed)
    (tmp_path / 'scripts/ml_candidate_research.py').write_text('# changed after commit\n')
    with pytest.raises(ValueError, match='Commit the exact'):
        candidate.require_fixed_recipe(tmp_path, protocol)


def test_future_complaints_do_not_change_features_at_an_earlier_alert():
    dates = pd.date_range('2019-01-07', periods=24, freq='W-MON').strftime('%Y-%m-%d')
    complaints = pd.DataFrame([
        dict(odino=str(i), datea=day, make='FORD', component='FUEL SYSTEM', label_id='fuel_pump_failure')
        for i, day in enumerate(dates)
    ])
    before = candidate.structured_rows(complaints.iloc[:20], end='2019-05-27')
    later = candidate.structured_rows(complaints, end='2019-12-31')
    assert before
    assert [row for row in later if row['available_at'] <= '2019-05-27'] == before
    row = before[-1]
    day = pd.Timestamp(row['available_at'])
    assert row['complaints_30d'] == sum(day - pd.Timedelta(days=30) <= pd.Timestamp(d) < day for d in dates)
