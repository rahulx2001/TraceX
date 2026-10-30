"""Expanded fuel-source experiment with a sealed 2025 temporal holdout.

Phases: prepare, encode, develop, test. No external model calls. The local
student learns from existing dated Meta labels; none are human truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.ai_oos_backtest import canonical_hash
from scripts.defect_repair import ROOT, MAKES, MODEL, write_json
from scripts.defect_prepare_inputs import _iter_recall_rows, _iter_complaints_from_zip, _iso_date, file_sha256
from scripts.ingest_nhtsa import flat_line_to_mapping_row
from src.eval.fuel_detection import (clean_reports,deduplicate_fuel,fit_student,predict_student,
                                     features,detect,evaluate_period,opportunity_bound,random_reference,wilson_interval)

DATA=ROOT/'data/defect/fuel_holdout'
OUT=ROOT/'reports/defect/fuel_holdout'
OUTCOME_END='2026-09-30'


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare():
    if (OUT/'protocol.json').exists():
        raise ValueError('Protocol already exists; refusing replacement')
    DATA.mkdir(parents=True,exist_ok=True)
    raw=pd.read_parquet(ROOT/'data/defect/complaints.parquet')
    base=raw[raw.make.isin(MAKES)&raw.year.between(2015,2024)]
    source=ROOT/'data/defect/source_cache'
    # No evaluation occurs here; the held-out file is stored separately.
    held=[]
    for line in _iter_complaints_from_zip(source/'FLAT_CMPL.zip'):
        parts=line.rstrip('\r\n').split('\t')
        if len(parts)<20 or not parts[15].startswith('2025') or parts[3] not in MAKES:
            continue
        row=flat_line_to_mapping_row(line)
        if not row or row['COMPONENT'] not in {'FUEL SYSTEM','FUEL/PROPULSION SYSTEM'}:
            continue
        try:year=int(row['MODEL_YR'])
        except ValueError:continue
        day=_iso_date(row['DATEA'])
        if not 2015<=year<=2024 or not day or not '2025-01-01'<=day<='2025-12-31':
            continue
        held.append(dict(datea=day,odino=row['ODINO'],cmplid=row['CMPLID'],make=row['MAKETXT'],
                         model=row['MODELTXT'],year=year,component=row['COMPONENT'],text=row['CDESC']))
    development=deduplicate_fuel(base)
    holdout=deduplicate_fuel(pd.DataFrame(held))
    # Same identity cannot enter both development and held-out complaints.
    if set(development.odino)&set(holdout.odino):
        raise ValueError('Complaint identity crosses temporal partitions')
    cached=pd.concat([pd.read_parquet(ROOT/'reports/defect/classifications.parquet'),
                      pd.read_parquet(ROOT/'reports/defect/repair/classifications.parquet')])
    cached=cached[cached.status.eq('ok')&cached.component.eq('FUEL SYSTEM')&cached.model.eq(MODEL)]
    cached=cached.drop_duplicates('record_id',keep='last')
    raw=raw.copy();raw['record_id']=raw.odino.astype(str)+'|'+raw.component
    teacher=raw.merge(cached[['record_id','label_id','model','prompt_version','taxonomy_sha256']],
                      on='record_id',how='inner',validate='one_to_one',suffixes=('','_teacher'))
    teacher=clean_reports(teacher[teacher.datea.le('2024-12-31')]).reset_index(drop=True)
    tax=json.loads((ROOT/'reports/defect/taxonomy.json').read_text())
    if not teacher.taxonomy_sha256.eq(tax['sha256']).all() or not teacher.prompt_version.eq('defect-cls-v2').all():
        raise ValueError('Mixed teacher provenance')
    scopes,_=_iter_recall_rows(source/'FLAT_RCL_POST_2010.zip',limit=0,preserve_scopes=True)
    scopes=pd.DataFrame(scopes)
    scopes=scopes[scopes.make.isin(MAKES)&scopes.year.between(2015,2024)&scopes.component.eq('FUEL SYSTEM')
                  &scopes.rcl_type.eq('V')&scopes.rcdate.between('2015-01-01',OUTCOME_END)]
    labels=pd.read_parquet(ROOT/'reports/defect/recall_labels.parquet')
    labels=labels[labels.status.eq('ok')&labels.model.eq(MODEL)&labels.taxonomy_sha256.eq(tax['sha256'])]
    refs=scopes.merge(labels[['campno','component','desc_defect','label_id']],on=['campno','component','desc_defect'],
                      how='left',validate='many_to_one')
    if refs.label_id.isna().any():
        raise ValueError('Some recall descriptions need labels; do not silently drop them')
    frames={'development':development,'holdout':holdout,'teacher':teacher,
            'development_recalls':refs[refs.rcdate.le('2024-12-31')],
            'holdout_recalls':refs[refs.rcdate.ge('2025-01-01')]}
    for name,frame in frames.items():frame.to_parquet(DATA/f'{name}.parquet',index=False)
    protocol={'created_at':now(),'target_campaign_recall':.86,'target_comparison':'strictly greater than',
              'scope':{'makes':MAKES,'model_years':[2015,2024],
                       'complaint_sources':['FUEL SYSTEM','FUEL/PROPULSION SYSTEM'],
                       'target_recalls':'FUEL SYSTEM, type V, complete make/model/year scope'},
              'primary_input':'exclude explicit recall/campaign mentions, deduplicate ODINO across fuel codes',
              'development_folds':[['2021-01-01','2022-12-31'],['2023-01-01','2024-12-31']],
              'development_student_training_end':'2020-12-31','final_student_training_end':'2024-12-31',
              'holdout':['2025-01-01','2025-12-31'],'outcome_end':OUTCOME_END,
              'selection':'Require >=50% mature episode precision in BOTH development folds and >=3 mature alerts/fold. Maximise worst-fold campaign recall; tie: mean F1, then fewer alerts. If none qualify, retain best mean-F1 diagnostic and mark unqualified.',
              'workload':'max 1 alert/week, 2/month, 13-week cooldown per make/defect',
              'evaluation':'7-364 days between complete-week availability and recall; unknown labels never match; one hit per campaign; precision only on full 364-day follow-up',
              'students':['ridge','centroid'],'detectors':['bayes','count','cusum'],
              'guardrails':['no dropping missed campaigns','no reclassifying human labels','no tuning after opening 2025 outcomes',
                            'student labels and recall labels are model hypotheses, not human validation',
                            '2025 is unseen locally, but historical Meta labels can carry model pretraining leakage',
                            'a contemporary flat-file snapshot can contain revised historical narratives'],
              'inputs':{name:{'path':str((DATA/f'{name}.parquet').relative_to(ROOT)),
                             'sha256':file_sha256(DATA/f'{name}.parquet')} for name in frames},
              'sources':{name:file_sha256(source/name) for name in ['FLAT_CMPL.zip','FLAT_RCL_POST_2010.zip']},
              'taxonomy_sha256':tax['sha256']}
    write_json(OUT/'protocol.json',protocol)
    print(json.dumps({'development_complaints':len(development),'heldout_complaints':len(holdout),
                      'teacher_examples':len(teacher),'status':'2025 outcomes not evaluated'}))


def read(name):
    p=json.loads((OUT/'protocol.json').read_text());spec=p['inputs'][name]
    if file_sha256(ROOT/spec['path'])!=spec['sha256']:raise ValueError(f'{name} changed')
    return pd.read_parquet(ROOT/spec['path'])


def encode():
    from src.ml_runtime.onnx_embedder import OnnxSemanticEmbedder
    from src.security.pii import redact_pii
    embedder=OnnxSemanticEmbedder(ROOT/'models/minilm',intra_op_threads=2,max_batch_size=32)
    for name in ['teacher','development','holdout']:
        dest=DATA/f'{name}_vectors.npy';stamp=DATA/f'{name}_vectors.json'
        frame=read(name)
        metadata={'input_sha256':file_sha256(DATA/f'{name}.parquet'),'embedding_version':embedder.version}
        if dest.exists() and stamp.exists() and json.loads(stamp.read_text())==metadata:
            print(f'{name}: reusing verified embeddings',flush=True);continue
        array=np.zeros((len(frame),384),dtype=np.float32)
        texts=frame.text.fillna('').tolist()
        for start in range(0,len(texts),64):
            vectors=embedder.embed_many([redact_pii(x) for x in texts[start:start+64]])
            array[start:start+len(vectors)]=np.array([x.values[:384] for x in vectors],dtype=np.float32)
            if start%1024==0:print(f'{name}: {start}/{len(texts)}',flush=True)
        np.save(dest,array);write_json(stamp,metadata)


def labelled(method, cutoff, *, include_holdout=False):
    teacher=read('teacher');selected=teacher.datea.le(cutoff).to_numpy()
    vectors=np.load(DATA/'teacher_vectors.npy')
    model=fit_student(vectors[selected],teacher.loc[selected,'label_id'].tolist(),method=method)
    frames=[]
    for name in ['development']+(['holdout'] if include_holdout else []):
        frame=read(name)
        predictions,margin=predict_student(model,np.load(DATA/f'{name}_vectors.npy'))
        frame['label_id']=predictions;frame['student_margin']=margin
        frames.append(frame)
    return clean_reports(pd.concat(frames,ignore_index=True)),model


def configurations():
    out=[]
    for w in (4,13,26):
        for m in (2,3):
            for p in (.05,.2):out.append(dict(detector='bayes',window=w,minimum=m,threshold=p))
            out.append(dict(detector='count',window=w,minimum=m,threshold=0))
    for threshold in (3,5):out.append(dict(detector='cusum',window=13,minimum=2,threshold=threshold))
    return out


def brief(m):
    return {k:v for k,v in m.items() if k not in {'campaign_hits','alert_details'}}


def fingerprints():
    files=[OUT/'protocol.json',ROOT/'src/eval/fuel_detection.py',Path(__file__)]
    files += [DATA/f'{name}_vectors.npy' for name in ['teacher','development','holdout']]
    return {str(p.relative_to(ROOT)):file_sha256(p) for p in files}


def develop():
    dest=OUT/'selection.json'
    if dest.exists():raise ValueError('Selection already frozen')
    protocol=json.loads((OUT/'protocol.json').read_text());refs=read('development_recalls')
    trials=[]
    for student in protocol['students']:
        frame,_=labelled(student,'2020-12-31');rows=features(frame,end='2024-12-31')
        for config in configurations():
            folds=[]
            for start,end in protocol['development_folds']:
                alerts=detect(rows,config,start=start,end=end)
                folds.append(brief(evaluate_period(alerts,refs,start=start,end=end,outcome_end=end)))
            qualified=all(m['mature_alerts']>=3 and (m['episode_precision'] or 0)>=.5 for m in folds)
            trials.append({'student':student,'config':config,'folds':folds,'qualified':qualified})
    eligible=[x for x in trials if x['qualified']]
    def rank(x):
        return (min(m['campaign_recall'] for m in x['folds']) if eligible else np.mean([m['objective'] for m in x['folds']]),
                np.mean([m['objective'] for m in x['folds']]),-sum(m['alerts'] for m in x['folds']))
    best=max(eligible or trials,key=rank)
    # Refit the selected student using only labels dated through 2024. Holdout
    # text is encoded by a fixed model; outcomes remain unopened here.
    _,model=labelled(best['student'],'2024-12-31')
    np.savez(DATA/'final_student.npz',weights=model['weights'],classes=np.array(model['classes']),method=model['method'])
    body={'selected':best,'trials':trials,'hashes':fingerprints(),
          'final_student_sha256':file_sha256(DATA/'final_student.npz'),'frozen_at':now(),
          'holdout_status':'not evaluated','protocol_qualified':bool(eligible)}
    write_json(dest,{'sha256':canonical_hash(body),'body':body})
    print(json.dumps({'selected':best,'candidates':len(trials),'qualified_candidates':len(eligible)},indent=2))


def compute_frozen():
    frozen=json.loads((OUT/'selection.json').read_text());body=frozen['body']
    if canonical_hash(body)!=frozen['sha256'] or fingerprints()!=body['hashes']:
        raise ValueError('Frozen selection/code/input hashes differ')
    if file_sha256(DATA/'final_student.npz')!=body['final_student_sha256']:
        raise ValueError('Frozen student weights changed')
    protocol=json.loads((OUT/'protocol.json').read_text());chosen=body['selected']
    archive=np.load(DATA/'final_student.npz',allow_pickle=False)
    model={'weights':archive['weights'],'classes':archive['classes'].tolist(),'method':str(archive['method'])}
    frames=[]
    for name in ['development','holdout']:
        frame=read(name);frame['label_id'],frame['student_margin']=predict_student(model,np.load(DATA/f'{name}_vectors.npy'));frames.append(frame)
    frame=clean_reports(pd.concat(frames,ignore_index=True));start,end=protocol['holdout']
    refs=read('holdout_recalls');rows=features(frame,end=end)
    alerts=detect(rows,chosen['config'],start=start,end=end)
    measured=evaluate_period(alerts,refs,start=start,end=end,outcome_end=protocol['outcome_end'])
    measured['recall_wilson95']=wilson_interval(measured['hits'],measured['campaigns'])
    # Count policy is fixed before holdout opening, not selected afterwards.
    baseline=detect(rows,dict(detector='count',window=13,minimum=2,threshold=0),start=start,end=end)
    base=evaluate_period(baseline,refs,start=start,end=end,outcome_end=protocol['outcome_end'])
    ceiling=opportunity_bound(frame,refs,start=start,end=end)
    draws=[]
    for i in range(100):
        random_alerts=random_reference(rows,alerts,seed=20261030+i)
        draws.append({'seed':20261030+i,**brief(evaluate_period(random_alerts,refs,start=start,end=end,outcome_end=protocol['outcome_end']))})
    target_met=(measured['campaign_recall']>.86 and (measured['episode_precision'] or 0)>=.5
                and body['protocol_qualified'])
    result={'evaluated_at':now(),'selection_sha256':frozen['sha256'],'target_met':target_met,
            'scope':protocol['scope'],'holdout':protocol['holdout'],'outcome_end':protocol['outcome_end'],
            'selected':chosen,'method':measured,'count_baseline':base,'evidence_ceiling':ceiling,
            'random_reference':{'draws':draws,'mean_recall':float(np.mean([x['campaign_recall'] for x in draws])),
                                'fraction_at_least_method':sum(x['campaign_recall']>=measured['campaign_recall'] for x in draws)/len(draws)},
            'interpretation':'Locally untouched 2025 temporal holdout, using model-labelled recalls. No human accuracy or prospective accident-prevention claim.',
            'human_validation':'not completed','promoted_to_production':False}
    return result


def test():
    with (OUT/'.holdout_opened').open('x') as f:f.write(now())
    result=compute_frozen()
    write_json(OUT/'holdout_results.json',result)
    print(json.dumps({'target_met':result['target_met'],'method':brief(result['method']),
                      'count_baseline':brief(result['count_baseline']),
                      'random_mean_recall':result['random_reference']['mean_recall'],
                      'evidence_ceiling':{k:v for k,v in result['evidence_ceiling'].items() if k!='rows'}},indent=2))


def verify():
    expected=json.loads((OUT/'holdout_results.json').read_text())
    actual=compute_frozen()
    for value in [expected,actual]:value.pop('evaluated_at',None)
    if actual!=expected:raise ValueError('Frozen replay does not match saved results')
    print('Exact replay match: selected method, count policy, opportunity bound, all 100 random references. No retuning.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','encode','develop','test','verify'])
    phase=parser.parse_args().phase;globals()[phase]()


if __name__=='__main__':main()
