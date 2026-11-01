import copy
import json

import pandas as pd
import pytest

from scripts import defect_review, synthetic_label_checks as synthetic
from scripts.defect_accuracy import immutable_sample_hash, load_sample


def test_300_deterministic_fixtures_have_explicit_nonhuman_provenance():
    rows = synthetic.generate_cases()
    assert rows == synthetic.generate_cases()
    result = synthetic.check_cases(rows, synthetic.vocabulary())
    assert result['fixture_records'] == 300 and result['underlying_scenario_families'] == 12
    assert all(n == 25 for n in result['template_variant_counts'].values())
    assert result['human_accuracy'] is None
    assert not result['model_classifier_called'] and not result['semantic_correctness_verified']


@pytest.mark.parametrize('field,value', [('human_reviewed',True),('human_label','fuel_pump_failure'),
                                        ('is_synthetic',False),('annotation_source','human'),
                                        ('independent_real_observation',True)])
def test_generated_fixtures_cannot_be_marked_as_human_evidence(field,value):
    rows = copy.deepcopy(synthetic.generate_cases())
    rows[0][field] = value
    with pytest.raises(ValueError,match='provenance'):
        synthetic.check_cases(rows, synthetic.vocabulary())


def test_unknown_taxonomy_label_and_duplicate_identity_are_rejected():
    rows = synthetic.generate_cases()
    rows[0]['expected_label'] = 'invented'
    with pytest.raises(ValueError,match='taxonomy'):
        synthetic.check_cases(rows, synthetic.vocabulary())
    rows = synthetic.generate_cases()
    rows[0]['case_id'] = rows[1]['case_id']
    with pytest.raises(ValueError,match='distinct'):
        synthetic.check_cases(rows, synthetic.vocabulary())


def test_build_preserves_existing_output(tmp_path):
    out = tmp_path / 'fixtures'
    synthetic.build(out)
    before = (out / 'synthetic_cases.jsonl').read_bytes()
    with pytest.raises(FileExistsError):
        synthetic.build(out)
    assert (out / 'synthetic_cases.jsonl').read_bytes() == before


def test_real_review_importer_rejects_synthetic_provenance(tmp_path,monkeypatch):
    sample = tmp_path / 'sample.csv'
    pd.DataFrame([dict(sample_id='SYNTHETIC-0001',odino='SYNTHETIC-ID',component='FUEL SYSTEM',
                       allowed_label_ids='fuel_pump_failure;other_unclear',allowed_label_text='fuel_pump_failure=Fuel pump failure;other_unclear=other/unclear',
                       label='',notes='',narrative='Fictional software control.')]).to_csv(sample,index=False)
    monkeypatch.setattr(defect_review,'SAMPLE',sample)
    payload = dict(sample_hash=immutable_sample_hash(load_sample(sample)),annotation_source='agent_authored_fixture',
                   attestation=False,reviewer='',reviews=[dict(sample_id='SYNTHETIC-0001',label='fuel_pump_failure')])
    path = tmp_path / 'synthetic_export.json'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='human-review attestation'):
        defect_review.import_review(path,destination=tmp_path/'imported')
    assert not (tmp_path/'imported').exists()
