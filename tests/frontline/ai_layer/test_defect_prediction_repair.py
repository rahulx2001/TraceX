from datetime import timedelta

import pandas as pd
import pytest

from scripts.defect_accuracy import resolve_human_label
from scripts.defect_prepare_inputs import _iter_recall_rows
from scripts.ingest_recalls import FLAT_RCL_FIELDS
from src.eval.defect_prediction import candidates, alert_episodes, reference_alerts, evaluate, join_labels, predictive_tail


def test_predictive_tail_matches_geometric_closed_form():
    for count in (1, 2, 8):
        assert predictive_tail(count, 1, .5) == pytest.approx(.5 ** count)


def test_recall_scope_preserves_multiple_makes_and_years(tmp_path):
    import zipfile
    lines = []
    for make, year in [("HONDA", "2018"), ("HONDA", "2019"), ("ACURA", "2019")]:
        values = dict(CAMPNO="20V001000", MAKETXT=make, MODELTXT="CAR", YEARTXT=year,
                      COMPNAME="FUEL SYSTEM", DESC_DEFECT="Pump may stop", RCDATE="20200115", RCLTYPECD="V")
        lines.append("\t".join(values.get(x, "") for x in FLAT_RCL_FIELDS))
    p = tmp_path / "recalls.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("FLAT_RCL.txt", "\n".join(lines + lines[:1]))
    descriptions, _ = _iter_recall_rows(p, limit=0)
    scopes, _ = _iter_recall_rows(p, limit=0, preserve_scopes=True)
    assert len(descriptions) == 1
    assert len(scopes) == 3
    assert {(r['make'], r['year']) for r in scopes} == {('HONDA', 2018), ('HONDA', 2019), ('ACURA', 2019)}


def complaint(day, odino="1", label="pump"):
    return dict(datea=day, odino=odino, make="HONDA", component="FUEL SYSTEM", label_id=label)


def test_completed_weeks_prior_only_and_sparse_signal():
    rows = [complaint("2020-01-06")]
    # Repeated complaints spread across weeks: no single-week count reaches 3.
    rows += [complaint(day, str(i)) for i, day in enumerate(["2020-04-07", "2020-04-14", "2020-04-21"], 2)]
    frame = pd.DataFrame(rows)
    base = candidates(frame, window=4, end="2020-04-27")
    assert base[-1]['available_at'] == '2020-04-27'
    assert base[-1]['record_count'] == 3
    assert base[-1]['prior_count'] == 1
    assert base[-1]['tail_score'] < .1
    later = candidates(pd.concat([frame, pd.DataFrame([complaint('2021-01-01')])]), window=4, end='2021-01-04')
    assert [r for r in later if r['available_at'] <= '2020-04-27'] == base
    assert not any(r['available_at'] == '2020-04-27' for r in candidates(frame, window=4, end='2020-04-26'))


def alert(day, label="pump"):
    return dict(make="HONDA", component="FUEL SYSTEM", label_id=label, available_at=day, record_count=3, tail_score=.01)


def recall(day, campaign="C1", label="pump"):
    return dict(make="HONDA", component="FUEL SYSTEM", label_id=label, rcdate=day, campno=campaign)


def test_campaign_dedup_actionable_lead_horizon_and_censoring():
    refs = pd.DataFrame([recall('2021-06-01'), recall('2021-06-01'),
                         recall('2021-01-05', 'TOO_SOON'), recall('2022-01-10', 'TOO_LATE'),
                         recall('2021-06-01', 'UNKNOWN', 'other_unclear')])
    ev = evaluate([alert('2021-01-04'), alert('2022-11-01'), alert('2021-01-04', 'other_unclear')],
                  refs, start='2021-01-01', end='2022-12-31')
    assert ev['campaigns'] == 4 and ev['hits'] == 1
    assert ev['mature_alerts'] == 2 and ev['censored_alerts'] == 1
    assert ev['episode_precision'] == .5
    # A known positive with insufficient follow-up stays out of BOTH precision
    # numerator and denominator, preventing outcome-dependent censoring.
    ev = evaluate([alert('2022-11-01')], pd.DataFrame([recall('2022-12-01')]), start='2021-01-01', end='2022-12-31')
    assert ev['hits'] == 1 and ev['episode_precision'] is None


def test_equal_episode_budgets_and_cooldown():
    rows = [alert((pd.Timestamp('2021-01-04') + timedelta(weeks=i)).date().isoformat()) for i in range(52)]
    chosen = alert_episodes(rows, min_count=2, max_tail=.1, start='2021-01-01', end='2021-12-31')
    assert len(chosen) == 4
    for seed in (None, 42):
        ref = reference_alerts(rows, budget=3, start='2021-01-01', end='2021-12-31', seed=seed)
        assert len(ref) == 3
        assert all((pd.Timestamp(b['available_at']) - pd.Timestamp(a['available_at'])).days >= 91 for a,b in zip(ref,ref[1:]))


def test_labels_cannot_disappear_from_denominator_or_change_provenance():
    c = pd.DataFrame([dict(odino='1', component='FUEL SYSTEM')])
    r = pd.DataFrame([dict(campno='C', component='FUEL SYSTEM', desc_defect='pump')])
    version = dict(model='M', prompt_version='P', taxonomy_sha256='T', status='ok', label_id='pump')
    cl = pd.DataFrame([dict(record_id='1|FUEL SYSTEM', **version)])
    rl = pd.DataFrame([dict(record_id='C', campno='C', component='FUEL SYSTEM', desc_defect='pump', **version)])
    a,b = join_labels(c,r,cl,rl,model='M',prompt='P',taxonomy='T')
    assert len(a) == len(b) == 1
    cl.loc[0,'status'] = 'missing'
    with pytest.raises(ValueError, match='incomplete'):
        join_labels(c,r,cl,rl,model='M',prompt='P',taxonomy='T')
    cl.loc[0,'model'] = 'other'
    with pytest.raises(ValueError, match='provenance'):
        join_labels(c,r,cl,rl,model='M',prompt='P',taxonomy='T')


def test_human_display_labels_resolve_only_to_allowed_ids():
    assert resolve_human_label('Fuel pump failure', 'pump;other_unclear', 'pump=Fuel pump failure; other_unclear=other/unclear') == ('pump','ok')
    assert resolve_human_label('other', 'pump', 'pump=Fuel pump failure')[1] == 'invalid'
    assert resolve_human_label('Surprise', 'pump', 'invented=Surprise')[1] == 'invalid'
