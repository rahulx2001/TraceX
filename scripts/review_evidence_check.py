"""Check published review provenance and adjudication consistency, not expertise.

python3 -m scripts.review_evidence_check
Only the standard library is used. No labels, scores or participant records are
created, and no provider calls are made.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUND = Path('reports/improvement/human_reviews/round4')
SAMPLE = Path('reports/defect/defect_label_sample_300.csv')
REVIEWERS = {'rahul': ROUND,
             **{n:ROUND/'third_review'/n for n in ['aryan','kaushal','ram','abhishek']}}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    required = {'sample_id','odino','component','allowed_label_ids','allowed_label_text','label'}
    for row in rows:
        if not required <= set(row):
            raise ValueError('Sample CSV is missing required fields')
        for key in required:
            row[key] = row[key].strip()
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate sample identities')
    return rows


def immutable_hash(rows):
    frozen = [{k:v for k,v in r.items() if k not in {'label','notes'}} for r in sorted(rows,key=lambda r:r['sample_id'])]
    return hashlib.sha256(json.dumps(frozen,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def validate_review(export, sample, sample_hash):
    if (export.get('sample_hash') != sample_hash or export.get('annotation_source') != 'human'
            or export.get('attestation') is not True or not str(export.get('reviewer') or '').strip()):
        raise ValueError('Review hash or attestation fields differ')
    result = {}
    for row in export.get('reviews',[]):
        sid = row.get('sample_id')
        if sid not in sample or sid in result:
            raise ValueError('Unknown or duplicate review identity')
        if row.get('label') not in sample[sid]['allowed_label_ids'].split(';'):
            raise ValueError('Review label outside the frozen taxonomy')
        result[sid] = row
    if not result:
        raise ValueError('No review rows supplied')
    return result


def validate(root=ROOT):
    registry = read(root/'reports/improvement/human_reviews/export_index.json')
    entries = registry['files']
    if (registry['schema_version'] != 1 or len(entries) != registry['supplied_files'] or
            len({e['supplied_filename'] for e in entries}) != len(entries) or
            len({e['sha256'] for e in entries}) != registry['distinct_original_byte_sequences']):
        raise ValueError('Supplied export inventory differs')
    public_copies = 0
    for entry in entries:
        for rel in entry['exact_public_paths']:
            path = root/rel
            if not path.resolve().is_relative_to(root.resolve()) or sha(path) != entry['sha256']:
                raise ValueError('Indexed public export hash differs')
            public_copies += 1
    original = csv_rows(root/SAMPLE)
    spec = read(root/'reports/defect/sample_manifest.json')
    if sha(root/SAMPLE) != spec['csv_sha256']:
        raise ValueError('Frozen sample changed')
    sample = {r['sample_id']:r for r in original}
    sample_hash = immutable_hash(original)
    if sample_hash != read(root/'reports/defect/repair/review_manifest.json')['immutable_rows_sha256']:
        raise ValueError('Immutable sample rows changed')
    reviews, coverage = {}, {}
    for name, directory in REVIEWERS.items():
        export_path = root/directory/('primary_review_export.json' if name=='rahul' else 'original_review_export.json')
        # Rahul's importer provenance is preserved in the original round.
        imported = root/'reports/improvement/human_reviews/round1' if name=='rahul' else root/directory
        provenance = read(imported/'human_review_provenance.json')
        labelled = csv_rows(imported/'human_labelled.csv')
        if (sha(export_path) != provenance['input_sha256'] or
                sha(imported/'human_labelled.csv') != provenance['output_sha256'] or immutable_hash(labelled) != sample_hash):
            raise ValueError(f'Review export/import provenance changed: {name}')
        export = read(export_path)
        review = validate_review(export,sample,sample_hash)
        imported_rows = {r['sample_id']:r for r in labelled}
        if provenance['reviewed'] != len(review) or provenance['sample_size'] != len(sample):
            raise ValueError('Importer coverage differs')
        for sid,row in review.items():
            if imported_rows[sid]['label'] != row['label'] or imported_rows[sid]['notes'] != str(row.get('notes') or ''):
                raise ValueError(f'Imported label or note differs: {name}')
        reviews[name] = review
        coverage[name] = {'reviewer':export['reviewer'],'annotations':len(review),'sample_size':len(sample)}
    active = {n:reviews[n] for n in ['rahul','aryan','kaushal','ram']}
    disputes = {sid for sid in sample if len({r[sid]['label'] for r in active.values() if sid in r})>1}
    trail = read(root/ROUND/'adjudication/decision_trail.json')
    decisions = {d['sample_id']:d for d in trail['adjudication_decisions']}
    if len(decisions) != len(trail['adjudication_decisions']) or set(decisions) != disputes:
        raise ValueError('Adjudication identity/coverage differs from source disagreements')
    gold = csv_rows(root/ROUND/'adjudication/adjudicated_labels_v2.csv')
    if len(gold) != len(sample) or immutable_hash(gold) != sample_hash:
        raise ValueError('Adjudicated sample identity or coverage differs')
    for row in gold:
        sid = row['sample_id']
        if sid in decisions:
            d = decisions[sid]
            votes = {n:r[sid]['label'] for n,r in active.items() if sid in r}
            if d['votes'] != votes or d['narrative_excerpt'] not in sample[sid]['narrative']:
                raise ValueError('Adjudication source votes or excerpt differ')
            label = d['adjudicated_label']
        else:
            label = reviews['rahul'][sid]['label']
        if row['label'] != label or label not in sample[sid]['allowed_label_ids'].split(';'):
            raise ValueError('Gold label differs from the retained decision')
    extra = set().union(*(set(reviews[n]) for n in ['aryan','kaushal','ram']))
    status = read(root/ROUND/'review_status.json')
    if status['coverage_unique_ids'] != len(extra) or status['disputes_adjudicated'] != len(disputes):
        raise ValueError('Published coverage counters differ')
    return {'ok':True,'validation':'published review/import hashes, taxonomy, source votes and adjudication consistency',
            'indexed_supplied_exports':len(entries),'indexed_exact_public_copies_checked':public_copies,
            'frozen_sample_records':len(sample),'reviewers':coverage,
            'round4_additional_distinct_records':len(extra),'round4_primary_only_records':len(sample)-len(extra),
            'round4_disputes':len(disputes),'countersign_status':status['status'],
            'abhishek_in_round4_gold':False,'review_blinding':status['blinding'],
            'new_model_calls':0,'new_human_labels':0,'human_independence_or_correctness_verified':False,
            'limits':'Attestation and internal consistency do not independently authenticate a reviewer, establish blinding or prove mechanical truth. Withdrawn/assisted archival rounds are not counted as new independent review.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,help='new local report path; existing reports are not replaced')
    args=parser.parse_args();result=validate()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x') as file:
            json.dump(result,file,indent=2);file.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
