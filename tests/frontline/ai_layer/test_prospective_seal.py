"""Procedural refusal/tamper-evidence checks, not cross-identity access control."""
import json
import pytest

from scripts import seal_prospective as collector
from src.eval.improvement_protocol import digest
from src.eval.prospective_io import MANIFEST
from .prospective_fixture import repository,seal_args,zip_fetcher,commit,git


@pytest.mark.parametrize('change,match',[
    ({'seal':False},'--seal'),({'confirm_public_data':False},'--confirm-public-data'),
    ({'start':'2026-12-31'},'outside'),({'end':'2029-01-01'},'outside'),({'snapshot_id':'../bad'},'identifier')])
def test_seal_refusal_flags_and_dates(tmp_path,monkeypatch,change,match):
    root,volume=repository(tmp_path);monkeypatch.setattr(collector,'today',lambda:'2030-01-01')
    with pytest.raises(ValueError,match=match):collector.seal(seal_args(volume,**change),root=root,fetcher=lambda *a:pytest.fail('must not fetch'))
    assert list(volume.iterdir())==[volume/'.rca-custody']


@pytest.mark.parametrize('case', ['inside','symlink','missing','mismatch','readonly'])
def test_seal_root_and_marker_refusals(tmp_path,monkeypatch,case):
    root,volume=repository(tmp_path);monkeypatch.setattr(collector,'today',lambda:'2030-01-01')
    if case=='inside':volume=root
    elif case=='symlink':link=tmp_path/'link';link.symlink_to(volume,target_is_directory=True);volume=link
    elif case=='missing':(volume/'.rca-custody').unlink()
    elif case=='mismatch':(volume/'.rca-custody').write_text('wrong')
    else:volume.chmod(0o555)
    try:
        with pytest.raises(ValueError):collector.seal(seal_args(volume),root=root,fetcher=lambda *a:pytest.fail('must not fetch'))
    finally:
        if case=='readonly':volume.chmod(0o755)


def test_seal_metadata_only_atomic_chain_and_unique_snapshot(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);monkeypatch.setattr(collector,'today',lambda:'2030-01-01')
    previous=digest(root/MANIFEST);replacements=[];replace=collector.atomic_json
    def capture(path,value):
        replacements.append(path);replace(path,value)
    monkeypatch.setattr(collector,'atomic_json',capture)
    record=collector.seal(seal_args(volume),root=root,fetcher=zip_fetcher())
    assert replacements==[root/MANIFEST]
    m=json.loads((root/MANIFEST).read_text());assert m['prev_sha256']==previous
    log=root/'reports/improvement/prospective/collection_log.jsonl'
    assert len(log.read_text().splitlines())==1 and json.loads(log.read_text())==record
    assert not list(root.rglob('*.zip')) and not list(root.rglob('*.parquet'))
    assert str(volume) not in (root/MANIFEST).read_text()+log.read_text()
    assert 'Synthetic fuel complaint' not in (root/MANIFEST).read_text()
    assert not list((root/'data/prospective').glob('.manifest-*.tmp'))
    commit(root)
    with pytest.raises(ValueError,match='Duplicate'):collector.seal(seal_args(volume),root=root,fetcher=zip_fetcher())
    assert len(log.read_text().splitlines())==1


def test_no_real_future_collection_now(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);monkeypatch.setattr(collector,'today',lambda:'2026-10-31')
    with pytest.raises(ValueError,match='future'):collector.seal(seal_args(volume),root=root,fetcher=lambda *a:pytest.fail('must not fetch'))


def test_original_checkout_is_not_an_allowed_custody_root(tmp_path,monkeypatch):
    root,volume=repository(tmp_path);other=tmp_path/'second-worktree'
    git(root,'worktree','add','--detach',str(other),'HEAD')
    monkeypatch.setattr(collector,'today',lambda:'2030-01-01')
    with pytest.raises(ValueError,match='outside repository'):
        collector.seal(seal_args(other),root=root,fetcher=lambda *a:pytest.fail('must not fetch'))
