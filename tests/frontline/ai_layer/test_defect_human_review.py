import json

import pandas as pd
import pytest

from scripts import defect_review
from scripts.defect_accuracy import immutable_sample_hash, load_sample


@pytest.fixture
def review_source(tmp_path, monkeypatch):
    sample = tmp_path / 'sample.csv'
    pd.DataFrame([{'sample_id':'S001','odino':'1','component':'FUEL SYSTEM',
                   'allowed_label_ids':'pump;other_unclear','allowed_label_text':'pump=Fuel pump failure;other_unclear=other/unclear',
                   'narrative':'Pump stopped.','label':'','notes':''}]).to_csv(sample,index=False)
    monkeypatch.setattr(defect_review,'SAMPLE',sample)
    payload = {'sample_hash':immutable_sample_hash(load_sample(sample)), 'annotation_source':'human',
               'attestation':True,'reviewer':'Test reviewer',
               'reviews':[{'sample_id':'S001','label':'pump','notes':'Documented failure.'}]}
    return sample,payload


def test_review_import_preserves_frozen_sample_and_tracks_reviewer(tmp_path, review_source):
    source,payload = review_source
    original = source.read_bytes()
    path = tmp_path/'review.json';path.write_text(json.dumps(payload))
    out = tmp_path/'out'
    defect_review.import_review(path,destination=out)
    assert source.read_bytes() == original
    assert load_sample(out/'human_labelled.csv').label.tolist() == ['pump']
    assert json.loads((out/'human_review_provenance.json').read_text())['annotation_source'] == 'human'
    with pytest.raises(FileExistsError):
        defect_review.import_review(path,destination=out)


@pytest.mark.parametrize('fault',['machine','unattested','wrong_sample','duplicate','invalid'])
def test_review_rejects_invalid_provenance_or_choices(tmp_path,review_source,fault):
    _,p = review_source
    if fault == 'machine':p['annotation_source']='model'
    if fault == 'unattested':p['attestation']=False
    if fault == 'wrong_sample':p['sample_hash']='different'
    if fault == 'duplicate':p['reviews']*=2
    if fault == 'invalid':p['reviews'][0]['label']='invented'
    path=tmp_path/'review.json';path.write_text(json.dumps(p))
    with pytest.raises(ValueError):defect_review.import_review(path,destination=tmp_path/'out')
    assert not (tmp_path/'out/human_labelled.csv').exists()


def test_immutable_hash_detects_edited_narrative_but_allows_annotations(review_source):
    source,_=review_source
    frame=load_sample(source);before=immutable_sample_hash(frame)
    frame.loc[0,'label']='pump';frame.loc[0,'notes']='checked'
    assert immutable_sample_hash(frame)==before
    frame.loc[0,'narrative']='Different complaint'
    assert immutable_sample_hash(frame)!=before
