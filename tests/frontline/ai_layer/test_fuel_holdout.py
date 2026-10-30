import numpy as np
import pandas as pd
import pytest

from src.eval.fuel_detection import (clean_reports,deduplicate_fuel,fit_student,predict_student,
                                     features,detect,evaluate_period,opportunity_bound,random_reference,wilson_interval)


def complaint(day,odino='1',label='pump',text='Fuel pump stopped.'):
    return dict(datea=day,odino=odino,make='HONDA',component='FUEL SYSTEM',label_id=label,text=text)


def test_cross_code_duplicates_count_once_and_preserve_provenance():
    rows=[complaint('2020-01-01'),complaint('2020-01-01'),complaint('2020-01-02','2')]
    rows[1]['component']='FUEL/PROPULSION SYSTEM';rows[1]['text']='A longer fuel pump failure report.'
    result=deduplicate_fuel(pd.DataFrame(rows))
    assert len(result)==2
    assert result.iloc[0].source_component=='FUEL/PROPULSION SYSTEM'
    assert result.component.eq('FUEL SYSTEM').all()


@pytest.mark.parametrize('method',['ridge','centroid'])
def test_student_learns_train_classes_and_abstains_on_ties(method):
    x=np.array([[1,0],[1,.05],[0,1],[.05,1]],dtype=float)
    model=fit_student(x,['pump','pump','other_unclear','other_unclear'],method=method)
    label,_=predict_student(model,np.array([[1,0],[0,1],[.5,.5]]))
    assert label==['pump','other_unclear','other_unclear']
    with pytest.raises(ValueError,match='abstention'):
        fit_student(x,['pump']*4,method=method)


def test_features_are_future_invariant_and_weeks_complete():
    frame=pd.DataFrame([complaint('2020-01-01'),complaint('2020-06-01','2'),complaint('2020-06-10','3')])
    before=features(frame,end='2020-06-15')
    after=features(pd.concat([frame,pd.DataFrame([complaint('2021-04-01','4')])]),end='2021-05-01')
    assert before==[x for x in after if x['available_at']<='2020-06-15']
    assert before[-1]['available_at']=='2020-06-15'
    assert before[-1]['count_4']==2
    assert not any(x['available_at']=='2020-06-15' for x in features(frame,end='2020-06-14'))


def test_causal_workload_and_per_slice_cooldown():
    rows=[]
    for i,day in enumerate(pd.date_range('2025-01-06','2025-12-29',freq='W-MON')):
        for label in ['pump','tank','canister','hose']:
            rows.append(dict(make='HONDA',component='FUEL SYSTEM',label_id=label,
                             available_at=day.date().isoformat(),count_13=3,tail_13=.01,cusum=4))
    alerts=detect(rows,dict(detector='count',window=13,minimum=2,threshold=0),start='2025-01-01',end='2025-12-31')
    assert len(alerts)<=24
    counts=pd.Series([a['available_at'][:7] for a in alerts]).value_counts()
    assert counts.max()<=2
    assert len(set(a['available_at'] for a in alerts))==len(alerts)
    for label in ['pump','tank','canister','hose']:
        dates=[pd.Timestamp(a['available_at']) for a in alerts if a['label_id']==label]
        assert all((b-a).days>=91 for a,b in zip(dates,dates[1:]))


def test_followup_can_confirm_precision_without_inflating_target_recall():
    alerts=[dict(make='HONDA',component='FUEL SYSTEM',label_id='pump',available_at='2025-06-02')]
    refs=pd.DataFrame([dict(make='HONDA',component='FUEL SYSTEM',label_id='pump',rcdate='2026-01-01',campno='NEXT_YEAR'),
                       dict(make='HONDA',component='FUEL SYSTEM',label_id='tank',rcdate='2025-07-01',campno='MISS')])
    score=evaluate_period(alerts,refs,start='2025-01-01',end='2025-12-31',outcome_end='2026-09-30')
    assert score['campaigns']==1 and score['hits']==0
    assert score['episode_precision']==1 and score['mature_alerts']==1
    with pytest.raises(ValueError,match='outside'):
        evaluate_period(alerts,refs,start='2024-01-01',end='2024-12-31',outcome_end='2026-09-30')


def test_opportunity_bound_does_not_drop_unreachable_campaigns():
    c=pd.DataFrame([complaint('2025-01-01')])
    refs=pd.DataFrame([dict(make='HONDA',component='FUEL SYSTEM',label_id=label,rcdate='2025-06-01',campno=str(i))
                       for i,label in enumerate(['pump','tank','other_unclear'])])
    bound=opportunity_bound(c,refs,start='2025-01-01',end='2025-12-31')
    assert bound['campaigns']==3 and bound['with_prior_evidence']==1
    assert bound['diagnostic_only']
    assert len(clean_reports(pd.DataFrame([complaint('2025-01-01',text='Recall parts unavailable.')])) )==0


def test_reference_matches_monthly_workload_and_is_reproducible():
    rows=[]
    for day in pd.date_range('2025-01-06','2025-12-29',freq='W-MON'):
        for i in range(10):rows.append(dict(make='HONDA',component='FUEL SYSTEM',label_id=str(i),available_at=day.date().isoformat()))
    actual=[rows[0],rows[20],rows[60],rows[90]]
    a=random_reference(rows,actual,seed=17);b=random_reference(rows,actual,seed=17)
    assert a==b
    from collections import Counter
    assert Counter(r['available_at'][:7] for r in a)==Counter(r['available_at'][:7] for r in actual)
    assert len({r['available_at'] for r in a})==len(a)


def test_small_perfect_sample_does_not_imply_certain_high_recall():
    lower,upper=wilson_interval(10,10)
    assert lower<.86 and upper==pytest.approx(1)
    assert wilson_interval(0,0)==[0,1]
