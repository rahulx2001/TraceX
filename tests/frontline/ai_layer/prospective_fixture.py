"""Synthetic-only disposable repositories and external volumes for refusal tests."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

import pandas as pd

from src.eval.improvement_protocol import digest
from src.eval.prospective_io import PHASE,CUSTODY,MANIFEST

SOURCE=Path(__file__).resolve().parents[3]


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
def commit(root):git(root,'add','.');git(root,'commit','-qm','synthetic fixture');return git(root,'rev-parse','HEAD')


def repository(tmp_path):
    root=tmp_path/'repo';root.mkdir(parents=True);git(root,'init','-q');git(root,'config','user.email','fixture@example.invalid');git(root,'config','user.name','Synthetic test')
    protocol=json.loads((SOURCE/PHASE/'protocol.json').read_text());write(root/PHASE/'protocol.json',protocol)
    custody=json.loads((SOURCE/CUSTODY).read_text());custody['synthetic_fixture']=True;write(root/CUSTODY,custody)
    manifest=json.loads((SOURCE/MANIFEST).read_text());write(root/MANIFEST,manifest)
    volume=tmp_path/'volume';volume.mkdir();(volume/'.rca-custody').write_text(custody['volume_marker_uuid'])
    for path in ['scripts/seal_prospective.py','scripts/final_prospective_eval.py',PHASE+'/PREREGISTRATION.md']:
        p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic freeze integrity fixture\n')
    model=dict(type='baseline',window=13,min_count=2,max_tail=.2,feature_order=[],threshold=.2)
    write(root/PHASE/'baseline_model.json',model)
    commit(root)
    files={p:digest(root/p) for p in ['scripts/seal_prospective.py','scripts/final_prospective_eval.py',PHASE+'/protocol.json',PHASE+'/PREREGISTRATION.md',PHASE+'/baseline_model.json',CUSTODY]}
    frozen=dict(mode='baseline_replication',freeze_tag='ml-prospective-freeze-2026',candidate={'path':PHASE+'/baseline_model.json'},code={'files':files})
    write(root/PHASE/'freeze_manifest.json',frozen);c1=commit(root)
    hashes=dict(freeze_commit=c1,freeze_tree=git(root,'rev-parse',c1+'^{tree}'),freeze_manifest_sha256=digest(root/PHASE/'freeze_manifest.json'),preregistration_sha256=files[PHASE+'/PREREGISTRATION.md'],protocol_sha256=files[PHASE+'/protocol.json'],collector_sha256=files['scripts/seal_prospective.py'],analysis_script_sha256=files['scripts/final_prospective_eval.py'],candidate_sha256=files[PHASE+'/baseline_model.json'])
    write(root/PHASE/'FREEZE_HASHES.json',hashes);commit(root);git(root,'tag','-a','ml-prospective-freeze-2026','-m','synthetic fixture')
    return root,volume


def seal_args(volume,**changes):
    return argparse.Namespace(**dict(dict(seal=True,confirm_public_data=True,custody_root=str(volume),start='2027-01-01',end='2028-12-31',snapshot_id='synthetic'),**changes))


def zip_fetcher(campaigns=25):
    from scripts.ingest_nhtsa import _FLAT_FIELDS
    from scripts.ingest_recalls import FLAT_RCL_FIELDS
    def fetch(url,path):
        if 'cmpl/' in url:
            fields=_FLAT_FIELDS
            records=[dict(ODINO=str(i),CMPLID=str(i),MAKETXT='FORD',MODELTXT='TEST',YEARTXT='2018',MODEL_YR='2018',DATEA=d.strftime('%Y%m%d'),CDESCR='Synthetic fuel complaint, no diagnosis.',COMPDESC='FUEL SYSTEM, GASOLINE') for i,d in enumerate(pd.date_range('2027-01-01',periods=40,freq='7D'))]
        else:
            fields=FLAT_RCL_FIELDS
            records=[dict(CAMPNO=f'SYN{i:03}',RCDATE='20281201',DESC_DEFECT='Synthetic fuel pump issue',COMPNAME='FUEL SYSTEM, GASOLINE',MAKETXT='FORD',MODELTXT='TEST',YEARTXT='2018',RCLTYPECD='V') for i in range(campaigns)]
        body='\n'.join('\t'.join(r.get(k,'') for k in fields) for r in records)+'\n'
        with zipfile.ZipFile(path,'x') as z:z.writestr('synthetic.txt',body)
    return fetch


def frozen_data(root,volume,monkeypatch,campaigns=25):
    from scripts import seal_prospective as collector
    from scripts.final_prospective_eval import load_raw
    monkeypatch.setattr(collector,'today',lambda:'2030-01-01')
    collector.seal(seal_args(volume),root=root,fetcher=zip_fetcher(campaigns));commit(root)
    m=json.loads((root/MANIFEST).read_text());p=json.loads((root/PHASE/'protocol.json').read_text())
    c,r,_=load_raw(volume,m,p)
    version=p['classifier']
    common=dict(status='ok',model=version['model'],prompt_version=version['prompt_version'],taxonomy_sha256=version['taxonomy_sha256'],label_id='fuel_pump_failure')
    labels=pd.DataFrame([dict(record_id=str(row.odino)+'|'+row.component,**common) for row in c.itertuples()])
    recall_labels=pd.DataFrame([dict(record_id=row.campno,campno=row.campno,component=row.component,desc_defect=row.desc_defect,**common) for row in r.itertuples()])
    labels.to_parquet(volume/'complaint_labels.parquet',index=False);recall_labels.to_parquet(volume/'recall_labels.parquet',index=False)
    previous=digest(root/MANIFEST)
    document=root/'attestation.md';document.write_text('Synthetic test self-attestation; no actual prospective outcomes.\n')
    m.update(prev_sha256=previous,status='data_frozen',outcomes_complete_through='2029-12-31',untouched_attestation=dict(custodian='Rahul Kumar Singh',type='self-attestation',attested_at='2030-01-01',no_outcomes_inspected_during_development=True,document_path='attestation.md',sha256=digest(document)),analysis_inputs={name:dict(file=name+'.parquet',sha256=digest(volume/(name+'.parquet'))) for name in ['complaint_labels','recall_labels']})
    write(root/MANIFEST,m);commit(root)
    return m


def final_args(volume,out,**changes):
    return argparse.Namespace(**dict(dict(final_analysis=True,custody_root=str(volume),manifest_ref='HEAD',out=str(out),today='2030-01-01',rerun=False,deviation_id=None),**changes))
