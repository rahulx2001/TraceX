"""Read-only verification of preserved evidence and both prospective freezes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.prospective_comparison import verify_registration


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def check_hashes(base, expected):
    names = list(expected)
    actual = {}
    for offset in range(0, len(names), 100):
        output = subprocess.check_output(['shasum', '-a', '256', *names[offset:offset+100]], cwd=base, text=True)
        for line in output.splitlines():
            sha, name = line.split('  ', 1)
            actual[name] = sha
    differences = [name for name, sha in expected.items() if actual.get(name) != sha]
    if differences:
        raise ValueError('Hash mismatch: ' + str(differences))
    return len(names)


def verify():
    start = json.loads((OUT / 'precheck.json').read_text())
    old = json.loads((ROOT / 'reports/improvement/research_v2/precheck.json').read_text())
    original = ROOT.with_name('v2_ai_rca_tool')
    protocol, index, tag = verify_registration(ROOT)
    frozen = json.loads((ROOT / 'reports/improvement/phase1/freeze_manifest.json').read_text())
    counts = {'original_freeze_files': len(frozen['code']['files']), 'comparison_freeze_files': len(index['files'])}
    for group in ['protected_artifacts', 'development_input_hashes', 'preserved_files']:
        counts[group] = check_hashes(ROOT, old[group])
    for path in ['research_v2/ARTIFACT_HASHES.json', 'synthetic_review_v1/HASHES.json']:
        counts[path] = check_hashes(ROOT, json.loads((ROOT / 'reports/improvement' / path).read_text())['files'])
    counts['original_reports'] = check_hashes(original, json.loads((ROOT / 'reports/improvement/original_artifact_hashes.json').read_text()))
    counts['original_changed_files'] = check_hashes(original, start['original_changed_file_hashes'])
    checks = dict(
        main_unchanged=git('rev-parse', 'main') == start['main'],
        original_checkout_head_unchanged=git('rev-parse', 'HEAD', cwd=original) == start['original_checkout_head'],
        original_checkout_status_unchanged=git('status', '--short', '--branch', cwd=original) == start['original_checkout_status'],
        worktree_branch=git('branch', '--show-current') == 'ml-score-improvement',
        comparison_tag_unchanged=tag == start['comparison_tag'],
    )
    manifest = json.loads((ROOT / 'data/prospective/manifest.json').read_text())
    checks['prospective_reserved_without_snapshots'] = manifest['status'] == 'reserved' and manifest['snapshots'] == []
    checks['collection_log_empty'] = (ROOT / 'reports/improvement/prospective/collection_log.jsonl').stat().st_size == 0
    checks['baseline_replication_unchanged'] = frozen['mode'] == 'baseline_replication'
    if not all(checks.values()):
        raise ValueError('Preservation check failed: ' + str(checks))
    return dict(created_at=datetime.now(timezone.utc).isoformat(), status='verified', checks=checks,
                hashes_verified=counts, code_commit=git('rev-parse', 'HEAD'), main=git('rev-parse', 'main'),
                original_freeze_commit=protocol['freeze']['original_tag_commit'], comparison_freeze_commit=tag,
                worktree_status=git('status', '--short', '--branch'),
                note='Only task-owned additions may be uncommitted during report creation; final commit is checked separately.',
                discrepancies=[])


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
