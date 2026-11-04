"""Replay the saved embedding-to-alert experiment without raw narratives or APIs.

python3 -m scripts.public_model_replay verify --download
python3 -m scripts.public_model_replay verify --inputs /path/to/extracted/bundle

The public projection retains the original text-filter decisions, row order,
embeddings and fitted weights. It is a replay of an opened historical result,
not a new holdout, new provider run or a human validation study.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path('reports/defect/fuel_holdout')
MANIFEST = REPORT/'public_replay_manifest.json'
RELEASE = REPORT/'public_replay_release.json'
CACHE = ROOT/'data/public_replay/fuel-v1'
MAX_BUNDLE_BYTES = 40_000_000
RELEASE_PREFIX = 'https://github.com/rahulx2001/TraceX/releases/download/'
TAIL_ABSOLUTE_TOLERANCE = 1e-12
TABLES = {
    'development': ['datea', 'odino', 'make', 'component', 'include_record'],
    'holdout': ['datea', 'odino', 'make', 'component', 'include_record'],
    'teacher': ['datea', 'label_id'],
    'development_recalls': ['campno', 'component', 'rcdate', 'make', 'label_id'],
    'holdout_recalls': ['campno', 'component', 'rcdate', 'make', 'label_id'],
}
ARRAYS = ['development_vectors.npy', 'holdout_vectors.npy', 'teacher_vectors.npy', 'final_student.npz']
FILES = {f'{name}.csv' for name in TABLES} | set(ARRAYS)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1_048_576), b''):
            h.update(block)
    return h.hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def result_differences(actual, expected, path='$'):
    """Locate strict mismatches without discarding fields or numeric precision."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in sorted(actual.keys() | expected.keys()):
            child = f'{path}.{key}'
            if key not in actual or key not in expected:
                yield {'path': child, 'reason': 'missing or unexpected field'}
            else:
                yield from result_differences(actual[key], expected[key], child)
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            yield {'path': path, 'actual_length': len(actual), 'expected_length': len(expected)}
        for index, (left, right) in enumerate(zip(actual, expected)):
            yield from result_differences(left, right, f'{path}[{index}]')
    elif actual != expected:
        yield {'path': path, 'actual': actual, 'expected': expected}


def result_comparison(actual, expected):
    """Accept only platform roundoff in diagnostic tail probabilities.

    Counts, chosen alerts, campaign IDs, dates, metrics, configuration and all
    random-reference outcomes still require exact equality. The frozen
    detector runs unchanged before this comparison.
    """
    mismatches, roundoff = [], []
    for difference in result_differences(actual, expected):
        left, right = difference.get('actual'), difference.get('expected')
        tail_path = re.fullmatch(
            r'\$\.(method|count_baseline)\.alert_details\[\d+\]\.tail_(4|13|26)', difference['path'])
        if (tail_path and isinstance(left, float) and isinstance(right, float)
                and math.isfinite(left) and math.isfinite(right)
                and abs(left-right) <= TAIL_ABSOLUTE_TOLERANCE):
            roundoff.append(abs(left-right))
        else:
            mismatches.append(difference)
    return {'mismatches': mismatches, 'exact_non_tail_fields': not mismatches,
            'tail_probability_absolute_tolerance': TAIL_ABSOLUTE_TOLERANCE,
            'tail_roundoff_differences': len(roundoff),
            'maximum_tail_absolute_difference': max(roundoff, default=0.0)}


def descriptor(root=ROOT):
    body = json.loads((root/MANIFEST).read_text())
    if body['schema_version'] != 1 or set(body['files']) != FILES:
        raise ValueError('Unexpected replay manifest or file inventory')
    for name, columns in TABLES.items():
        if body['files'][name+'.csv']['columns'] != columns:
            raise ValueError('Unexpected public projection columns')
    return body


def validate_inputs(directory, manifest):
    directory = Path(directory)
    for name, spec in manifest['files'].items():
        if name not in FILES or Path(name).name != name:
            raise ValueError('Unexpected replay path')
        p = directory/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size != spec['bytes'] or sha(p) != spec['sha256']:
            raise ValueError(f'Missing or changed public replay input: {name}')


def unpack(archive_path, destination, manifest, archive_sha256):
    """Validate the whole archive before creating a new cache directory."""
    archive_path, destination = Path(archive_path), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; refusing to replace it')
    if archive_path.stat().st_size > MAX_BUNDLE_BYTES or sha(archive_path) != archive_sha256:
        raise ValueError('Replay archive hash or size differs')
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if len(names) != len(set(names)) or set(names) != FILES | {'manifest.json'}:
            raise ValueError('Replay archive has missing, duplicate or unexpected members')
        if sum(m.file_size for m in members) > MAX_BUNDLE_BYTES:
            raise ValueError('Expanded replay archive is too large')
        for member in members:
            expected = len(json_bytes(manifest)) if member.filename == 'manifest.json' else manifest['files'][member.filename]['bytes']
            if member.file_size != expected or member.flag_bits & 1:
                raise ValueError('Replay member size/encryption differs')
        if archive.read('manifest.json') != json_bytes(manifest):
            raise ValueError('Archive manifest differs from the committed manifest')
        # Check every member before any final destination is written.
        for name in sorted(FILES):
            if hashlib.sha256(archive.read(name)).hexdigest() != manifest['files'][name]['sha256']:
                raise ValueError(f'Archive member changed: {name}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.tracex-replay-', dir=destination.parent))
        try:
            for name in sorted(FILES | {'manifest.json'}):
                with (staging/name).open('xb') as output, archive.open(name) as source:
                    shutil.copyfileobj(source, output)
            validate_inputs(staging, manifest)
            # os.rename alone can replace an existing empty directory. Keep
            # the final cache reserved so a concurrent/existing cache is safe.
            destination.mkdir(exist_ok=False)
            for p in staging.iterdir():
                os.rename(p, destination/p.name)
        finally:
            shutil.rmtree(staging)
    return destination


def download(destination=CACHE, root=ROOT):
    manifest = descriptor(root)
    if Path(destination).exists():
        validate_inputs(destination, manifest)
        return Path(destination)
    release = json.loads((root/RELEASE).read_text())
    url = release['url']
    if not url.startswith(RELEASE_PREFIX) or release['bytes'] > MAX_BUNDLE_BYTES:
        raise ValueError('Unexpected public replay release URL or size')
    with tempfile.TemporaryDirectory(prefix='tracex-download-') as temp:
        p = Path(temp)/'bundle.zip'
        request = urllib.request.Request(url, headers={'User-Agent': 'TraceX-public-model-replay/1'})
        total = 0
        with urllib.request.urlopen(request, timeout=30) as response, p.open('xb') as output:
            while block := response.read(1_048_576):
                total += len(block)
                if total > release['bytes']:
                    raise ValueError('Downloaded replay exceeds its published size')
                output.write(block)
        if total != release['bytes']:
            raise ValueError('Downloaded replay is incomplete')
        return unpack(p, destination, manifest, release['sha256'])


def build(source_root, archive_path, *, release_url, root=ROOT):
    """Maintainer export: validate original inputs, then remove all free text."""
    import pandas as pd
    source_root, archive_path = Path(source_root), Path(archive_path)
    if archive_path.exists() or not release_url.startswith(RELEASE_PREFIX):
        raise ValueError('Archive already exists or release URL is not supported')
    protocol = json.loads((root/REPORT/'protocol.json').read_text())
    selection = json.loads((root/REPORT/'selection.json').read_text())
    if canonical_hash(selection['body']) != selection['sha256']:
        raise ValueError('Original selection hash differs')
    originals = {v['path']: v['sha256'] for v in protocol['inputs'].values()}
    originals.update({p:h for p,h in selection['body']['hashes'].items() if p.startswith('data/')})
    originals['data/defect/fuel_holdout/final_student.npz'] = selection['body']['final_student_sha256']
    for path, expected in originals.items():
        if sha(source_root/path) != expected:
            raise ValueError(f'Original frozen input changed: {path}')
    with tempfile.TemporaryDirectory(prefix='tracex-public-export-') as temp:
        directory = Path(temp)
        files = {}
        for name, columns in TABLES.items():
            frame = pd.read_parquet(source_root/protocol['inputs'][name]['path'])
            if name in {'development', 'holdout'}:
                frame['include_record'] = (~frame.text.str.contains(r'\brecall\w*\b|\bcampaign\b', case=False, regex=True, na=False)).astype(int)
            projection = frame[columns]
            projection.to_csv(directory/f'{name}.csv', index=False, lineterminator='\n')
            files[name+'.csv'] = {'columns': columns, 'rows': len(frame),
                                 'included_rows': int(frame.include_record.sum()) if 'include_record' in frame else len(frame)}
        for name in ARRAYS:
            shutil.copyfile(source_root/'data/defect/fuel_holdout'/name, directory/name)
            files[name] = {}
        for name, spec in files.items():
            spec.update(bytes=(directory/name).stat().st_size, sha256=sha(directory/name))
        source_files = ['reports/defect/fuel_holdout/protocol.json', 'reports/defect/fuel_holdout/selection.json',
                        'reports/defect/fuel_holdout/holdout_results.json', 'scripts/fuel_holdout.py',
                        'src/eval/fuel_detection.py', 'src/eval/defect_prediction.py']
        manifest = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'scope': 'Saved embedding-to-alert replay; original free text is excluded. Historical opened evaluation, not a new experiment.',
                    'selection_sha256': selection['sha256'], 'files': files,
                    'original_private_input_hashes': originals,
                    'source_hashes': {p:sha(root/p) for p in source_files},
                    'projection': 'Original row order and text exclusion flags; dates/public complaint IDs/labels only; no narrative, contact or VIN columns.',
                    'model_calls': 0, 'human_results_created': 0}
        (directory/'manifest.json').write_bytes(json_bytes(manifest))
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(FILES | {'manifest.json'}):
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 4, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (directory/name).read_bytes())
        release = {'schema_version': 1, 'url': release_url, 'bytes': archive_path.stat().st_size,
                   'sha256': sha(archive_path), 'scope': manifest['scope']}
        (root/MANIFEST).write_bytes(json_bytes(manifest))
        (root/RELEASE).write_bytes(json_bytes(release))
    return release


def verify(directory=CACHE, *, root=ROOT):
    import numpy as np
    import pandas as pd
    from src.eval.fuel_detection import (predict_student, features, detect, evaluate_period,
                                         opportunity_bound, random_reference, wilson_interval)
    manifest = descriptor(root)
    validate_inputs(directory, manifest)
    for rel, expected in manifest['source_hashes'].items():
        if sha(root/rel) != expected:
            raise ValueError(f'Frozen evaluation source changed: {rel}')
    tables = {}
    for name, columns in TABLES.items():
        frame = pd.read_csv(Path(directory)/(name+'.csv'), dtype=str, keep_default_na=False)
        if list(frame.columns) != columns or len(frame) != manifest['files'][name+'.csv']['rows']:
            raise ValueError('Projection columns or row counts differ')
        if 'include_record' in frame and not frame.include_record.isin(['0','1']).all():
            raise ValueError('Invalid preserved text-filter flag')
        tables[name] = frame
    with np.load(Path(directory)/'final_student.npz', allow_pickle=False) as archive:
        model = {'weights': archive['weights'], 'classes': archive['classes'].tolist(), 'method': str(archive['method'])}
    if model['method'] not in {'ridge','centroid'} or 'other_unclear' not in model['classes'] or not np.isfinite(model['weights']).all():
        raise ValueError('Invalid frozen model')
    frames = []
    for name in ['development','holdout']:
        frame = tables[name]
        vectors = np.load(Path(directory)/(name+'_vectors.npy'), allow_pickle=False)
        if vectors.shape != (len(frame),384) or not np.isfinite(vectors).all():
            raise ValueError('Invalid embedding shape or values')
        frame['label_id'], frame['student_margin'] = predict_student(model, vectors)
        frames.append(frame[frame.include_record.eq('1')])
    complaints = pd.concat(frames, ignore_index=True)
    protocol = json.loads((root/REPORT/'protocol.json').read_text())
    selection = json.loads((root/REPORT/'selection.json').read_text())
    chosen = selection['body']['selected']
    start, end = protocol['holdout']
    refs = tables['holdout_recalls']
    rows = features(complaints, end=end)
    alerts = detect(rows, chosen['config'], start=start, end=end)
    measured = evaluate_period(alerts, refs, start=start, end=end, outcome_end=protocol['outcome_end'])
    measured['recall_wilson95'] = wilson_interval(measured['hits'], measured['campaigns'])
    count = detect(rows, dict(detector='count',window=13,minimum=2,threshold=0), start=start, end=end)
    baseline = evaluate_period(count, refs, start=start, end=end, outcome_end=protocol['outcome_end'])
    ceiling = opportunity_bound(complaints, refs, start=start, end=end)
    draws = []
    for i in range(100):
        random_alerts = random_reference(rows, alerts, seed=20261030+i)
        metrics = evaluate_period(random_alerts, refs, start=start, end=end, outcome_end=protocol['outcome_end'])
        draws.append({'seed':20261030+i, **{k:v for k,v in metrics.items() if k not in {'campaign_hits','alert_details'}}})
    expected = json.loads((root/REPORT/'holdout_results.json').read_text())
    actual = {'selection_sha256': selection['sha256'],
              'target_met': measured['campaign_recall']>.86 and (measured['episode_precision'] or 0)>=.5 and selection['body']['protocol_qualified'],
              'scope':protocol['scope'], 'holdout':protocol['holdout'], 'outcome_end':protocol['outcome_end'],
              'selected':chosen, 'method':measured, 'count_baseline':baseline, 'evidence_ceiling':ceiling,
              'random_reference':{'draws':draws, 'mean_recall':float(np.mean([x['campaign_recall'] for x in draws])),
                 'fraction_at_least_method':sum(x['campaign_recall']>=measured['campaign_recall'] for x in draws)/len(draws)},
              'interpretation':expected['interpretation'], 'human_validation':expected['human_validation'],
              'promoted_to_production':False}
    expected.pop('evaluated_at',None)
    comparison = result_comparison(actual, expected)
    differences = comparison.pop('mismatches')
    if differences:
        raise ValueError('Public model/alert replay differs from the saved result: '+json.dumps({
            'numpy': np.__version__, 'pandas': pd.__version__,
            'mismatch_count': len(differences), 'first_mismatches': differences[:12]}, sort_keys=True))
    return {'ok':True, 'validation':'saved local-student predictions and alert evaluation match the original saved result',
            'comparison': comparison,
            'matched_sections':['method','count_baseline','evidence_ceiling','all 100 random references'],
            'campaign_hits':measured['hits'], 'campaigns':measured['campaigns'],
            'matching_mature_alerts':measured['confirmed_mature_alerts'], 'mature_alerts':measured['mature_alerts'],
            'new_model_api_calls':0, 'new_human_results':0, 'raw_narratives_included':False,
            'limits':'Replays cached embeddings/fitted weights and saved text-filter decisions. It does not regenerate embeddings, raw ingestion, provider outputs, training selection or human grades.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='phase', required=True)
    replay = sub.add_parser('verify')
    replay.add_argument('--download', action='store_true', help='fetch the checksummed public bundle if absent')
    replay.add_argument('--inputs', type=Path, default=CACHE)
    replay.add_argument('--out', type=Path, help='new validation report path; never replaces an existing report')
    export = sub.add_parser('build', help='maintainer: export an allow-listed projection from frozen local inputs')
    export.add_argument('--source-root', type=Path, required=True)
    export.add_argument('--archive', type=Path, required=True)
    export.add_argument('--release-url', required=True)
    args = parser.parse_args()
    if args.phase == 'build':
        result = build(args.source_root,args.archive,release_url=args.release_url)
    else:
        if args.download:
            download(args.inputs)
        result = verify(args.inputs)
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x') as file:
                file.write(json_bytes(result).decode())
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
