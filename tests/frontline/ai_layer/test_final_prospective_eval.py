"""All prospective records in these tests are authored synthetic fixtures."""
import json
import pytest

from scripts import final_prospective_eval as final
from src.eval.prospective_io import MANIFEST,PHASE
from src.eval.improvement_protocol import digest
from .prospective_fixture import repository,frozen_data,final_args,commit,write


def test_final_requires_explicit_flag(tmp_path):
    root,volume=repository(tmp_path)
    with pytest.raises(ValueError,match='--final-analysis'):final.final_analysis(final_args(volume,tmp_path/'out',final_analysis=False),root=root)


@pytest.mark.parametrize('case,match', [('early','Before outcome'),('dirty','Dirty'),('hash','hash mismatch'),('marker','marker')])
def test_final_refuses_before_any_outcome_read(tmp_path,monkeypatch,case,match):
    root,volume=repository(tmp_path);args=final_args(volume,tmp_path/'out')
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION','1')
    if case=='early':args.today='2029-12-30'
    elif case=='dirty':(root/'uncommitted.txt').write_text('dirty')
    elif case=='hash':(root/'scripts/seal_prospective.py').write_text('tamper')
    else:(volume/'.rca-custody').unlink()
    monkeypatch.setattr(final,'load_raw',lambda *a:pytest.fail('no outcomes before gates'))
    with pytest.raises(ValueError,match=match):final.final_analysis(args,root=root)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('case,match',[('chain','chain'),('attestation','attestation'),('coverage','follow-up')])
def test_final_manifest_and_attestation_refusals(tmp_path,monkeypatch,case,match):
    root,volume=repository(tmp_path);frozen_data(root,volume,monkeypatch)
    m=json.loads((root/MANIFEST).read_text());m['prev_sha256']=digest(root/MANIFEST)
    if case=='chain':m['prev_sha256']='0'*64
    elif case=='attestation':m['untouched_attestation']=None
    else:m['outcomes_complete_through']=None
    write(root/MANIFEST,m);commit(root);monkeypatch.setenv('FRONTLINE_TEST_ISOLATION','1')
    monkeypatch.setattr(final,'load_raw',lambda *a:pytest.fail('no outcomes before gates'))
    with pytest.raises(ValueError,match=match):final.final_analysis(final_args(volume,tmp_path/'out'),root=root)


def test_below_25_counts_only_without_labels_or_metrics(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);frozen_data(root,volume,monkeypatch,campaigns=24)
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION','1')
    monkeypatch.setattr(final,'apply_labels',lambda *a:pytest.fail('no labels/metrics below sample floor'))
    out=tmp_path/'out';assert final.final_analysis(final_args(volume,out),root=root)==2
    r=json.loads((out/'final_analysis.json').read_text())
    assert r['status']=='INCONCLUSIVE_SAMPLE' and r['eligible_campaigns']==24 and r['metrics'] is None
    assert not (out/'campaigns.csv').exists() and not (out/'alerts.csv').exists()


def test_synthetic_25_campaign_analysis_and_no_silent_second_run(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);frozen_data(root,volume,monkeypatch,campaigns=25)
    monkeypatch.setenv('FRONTLINE_TEST_ISOLATION','1');out=tmp_path/'out'
    assert final.final_analysis(final_args(volume,out),root=root)==0
    for name in ['final_analysis.json','final_analysis.md','campaigns.csv','alerts.csv','run_manifest.json']:assert (out/name).is_file()
    r=json.loads((out/'final_analysis.json').read_text())
    assert r['eligible_campaigns']==25 and r['improvement_claim'] is None
    assert r['metrics']['all_reports']['recall']['denominator']==25
    before=digest(out/'final_analysis.json')
    with pytest.raises(ValueError,match='Second run'):final.final_analysis(final_args(volume,out),root=root)
    assert digest(out/'final_analysis.json')==before
    assert str(volume) not in (out/'run_manifest.json').read_text()


def test_clock_override_unavailable_in_real_custody_configuration(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);monkeypatch.delenv('FRONTLINE_TEST_ISOLATION',raising=False)
    with pytest.raises(ValueError,match='synthetic'):final.final_analysis(final_args(volume,tmp_path/'out'),root=root)


def test_collection_log_tampering_refuses_before_raw_read(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);frozen_data(root,volume,monkeypatch)
    (root/'reports/improvement/prospective/collection_log.jsonl').write_text('')
    commit(root);monkeypatch.setenv('FRONTLINE_TEST_ISOLATION','1')
    monkeypatch.setattr(final,'load_raw',lambda *a:pytest.fail('no raw access after tampering'))
    with pytest.raises(ValueError,match='Collection log'):final.final_analysis(final_args(volume,tmp_path/'out'),root=root)
