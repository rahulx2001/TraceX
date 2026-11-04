"""Archive safety regressions; all data here is explicit temporary test data."""
import hashlib
import zipfile

import pytest

from scripts.public_model_replay import FILES, TABLES, json_bytes, sha, unpack, validate_inputs
from scripts.review_evidence_check import validate_review


@pytest.fixture
def bundle(tmp_path):
    payload={name:('explicit synthetic test data '+name).encode() for name in FILES}
    manifest={'schema_version':1,'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in payload.items()}}
    for name,columns in TABLES.items():
        manifest['files'][name+'.csv']['columns']=columns
    def write(extra=None,changed=None,omit=None):
        path=tmp_path/f'bundle-{len(list(tmp_path.glob("*.zip")))}.zip'
        with zipfile.ZipFile(path,'x') as archive:
            archive.writestr('manifest.json',json_bytes(manifest))
            for name,data in payload.items():
                if name != omit:
                    archive.writestr(name,changed if name=='final_student.npz' and changed is not None else data)
            if extra:
                archive.writestr(extra,b'not permitted')
        return path
    return manifest,write


def test_verified_bundle_extracts_and_modified_weights_fail(tmp_path,bundle):
    manifest,write=bundle;path=write();dest=tmp_path/'inputs'
    unpack(path,dest,manifest,sha(path))
    validate_inputs(dest,manifest)
    (dest/'final_student.npz').write_bytes(b'changed fitted weights')
    with pytest.raises(ValueError,match='changed public replay input'):
        validate_inputs(dest,manifest)


def test_existing_cache_is_not_replaced(tmp_path,bundle):
    manifest,write=bundle;path=write();dest=tmp_path/'existing';dest.mkdir()
    sentinel=dest/'keep.txt';sentinel.write_text('owner data')
    with pytest.raises(ValueError,match='already exists'):
        unpack(path,dest,manifest,sha(path))
    assert sentinel.read_text()=='owner data'


@pytest.mark.parametrize('member',['../outside.txt','/outside.txt','unexpected.json'])
def test_unexpected_archive_member_never_writes_destination(tmp_path,bundle,member):
    manifest,write=bundle;path=write(extra=member);dest=tmp_path/'inputs'
    with pytest.raises(ValueError,match='unexpected members'):
        unpack(path,dest,manifest,sha(path))
    assert not dest.exists()
    assert not (tmp_path/'outside.txt').exists()


def test_missing_member_never_writes_destination(tmp_path,bundle):
    manifest,write=bundle;path=write(omit='teacher_vectors.npy');dest=tmp_path/'inputs'
    with pytest.raises(ValueError,match='missing'):
        unpack(path,dest,manifest,sha(path))
    assert not dest.exists()


def test_changed_member_is_detected_even_with_valid_whole_archive_hash(tmp_path,bundle):
    manifest,write=bundle;path=write(changed=b'changed fitted weights');dest=tmp_path/'inputs'
    with pytest.raises(ValueError,match='member size|member changed'):
        unpack(path,dest,manifest,sha(path))
    assert not dest.exists()


def test_whole_archive_hash_is_required(tmp_path,bundle):
    manifest,write=bundle;path=write();dest=tmp_path/'inputs'
    with pytest.raises(ValueError,match='archive hash'):
        unpack(path,dest,manifest,'0'*64)
    assert not dest.exists()


def test_duplicate_review_rows_are_rejected():
    sample={'S001':{'allowed_label_ids':'other_unclear;fuel_pump_failure'}}
    export={'synthetic_test_fixture':True,'sample_hash':'frozen','annotation_source':'human','attestation':True,
            'reviewer':'Explicit test fixture','reviews':[{'sample_id':'S001','label':'other_unclear'}]*2}
    with pytest.raises(ValueError,match='duplicate review'):
        validate_review(export,sample,'frozen')


def test_out_of_taxonomy_review_is_rejected():
    sample={'S001':{'allowed_label_ids':'other_unclear;fuel_pump_failure'}}
    export={'synthetic_test_fixture':True,'sample_hash':'frozen','annotation_source':'human','attestation':True,
            'reviewer':'Explicit test fixture','reviews':[{'sample_id':'S001','label':'invented_failure'}]}
    with pytest.raises(ValueError,match='outside the frozen taxonomy'):
        validate_review(export,sample,'frozen')
