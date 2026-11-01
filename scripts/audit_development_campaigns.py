"""Census campaign identities in the pinned archive without parsing outcome text."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
import zipfile

import pandas as pd

from scripts.defect_prepare_inputs import _iso_date
from src.domains.nhtsa_components import normalize_component
from src.eval.improvement_protocol import check_development, digest, write_once
from src.eval.prospective_io import verify_freeze

ROOT = Path(__file__).resolve().parents[1]
RECALL_SHA = '6e886e1076d33dc457f44deafb848c28a791ec406022d6e67d1cc3662e3cbebc'
DATA = 'data/ml_improvement/recalls.parquet'
DATA_SHA = '63577ea14c59acc7d8bb9c32c86bf3efe65762dc0c148b107ef2ed6cff1db809'
MAKES = {'FORD', 'HONDA', 'HYUNDAI', 'KIA', 'TOYOTA'}


def census(lines):
    """Inspect date headers first; retain only in-window identity/scope fields."""
    campaigns = {}
    bad_dates = 0
    for line in lines:
        # RCDATE is field 15. Never decode or retain the defect/remedy text.
        prefix = line.rstrip(b'\r\n').split(b'\t', 16)[:16]
        if len(prefix) != 16:
            raise ValueError('Unexpected recall archive field layout')
        day = _iso_date(prefix[15].decode('ascii').strip())
        if day is None:
            bad_dates += 1
            continue
        if not '2015-01-01' <= day <= '2020-12-31':
            continue
        make = prefix[2].decode('utf-8').strip().upper()
        if make not in MAKES or prefix[10].strip() != b'V':
            continue
        try:
            year = int(prefix[4])
        except ValueError:
            continue
        component = normalize_component(prefix[6].decode('utf-8'))
        if not 2015 <= year <= 2024 or component != 'FUEL SYSTEM':
            continue
        campaign = prefix[1].decode('ascii').strip()
        if not campaign:
            raise ValueError('Missing campaign identity')
        entry = campaigns.setdefault(campaign, {'dates': set(), 'scopes': set()})
        entry['dates'].add(day)
        entry['scopes'].add((make, prefix[3].decode('utf-8').strip(), year, component))
    if bad_dates:
        raise ValueError(f'Archive contains {bad_dates} unparseable date headers; completeness not established')
    return {key: dict(dates=sorted(value['dates']), scope_rows=len(value['scopes']))
            for key, value in sorted(campaigns.items())}


def audit(archive, *, root=ROOT):
    if digest(archive) != RECALL_SHA or digest(root / DATA) != DATA_SHA:
        raise ValueError('Pinned source/input hash mismatch; no source parsing performed')
    verify_freeze(root)
    with zipfile.ZipFile(archive) as source:
        names = [name for name in source.namelist() if not name.endswith('/')]
        if len(names) != 1:
            raise ValueError('Expected exactly one flat file')
        with source.open(names[0]) as stream:
            inventory = census(stream)
    known = pd.read_parquet(root / DATA)
    check_development(known, 'rcdate')
    known_ids = set(known.campno)
    source_ids = set(inventory)
    return dict(created_at=datetime.now(timezone.utc).isoformat(), split='development',
                code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                script_sha256=digest(Path(__file__)),
                exact_command=shlex.join(['.venv-hackathon/bin/python', '-B', '-m', 'scripts.audit_development_campaigns', *sys.argv[1:]]),
                scope=dict(makes=sorted(MAKES), model_years=[2015, 2024], component='FUEL SYSTEM',
                           campaign_dates=['2015-01-01', '2020-12-31'], recall_type='V'),
                archive_sha256=RECALL_SHA, prepared_data_sha256=DATA_SHA,
                source_campaigns=len(source_ids), prepared_campaigns=len(known_ids),
                additional_campaign_ids=sorted(source_ids-known_ids),
                prepared_ids_absent_from_source=sorted(known_ids-source_ids),
                campaigns=inventory, new_campaigns_acquired=0,
                source_read='Pinned local archive only; date headers filter rows before retaining scope/identity fields; no outcome descriptions parsed and no post-2020 data frame created.',
                completeness='Census of the pinned snapshot in the unchanged scope, not proof that all real-world defects were reported or campaigns are statistically independent.',
                followup='Campaign dates do not create new independent alert outcomes. The development outcome cutoff remains 2020-12-31; mature alerts require the existing full 364-day follow-up.',
                evaluation_data='All prepared 2015-2020 data were opened; none is redesignated as untouched.',
                performance_metrics=None, is_candidate_result=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recalls-zip', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.recalls_zip)
    write_once(args.out, result)
    print(json.dumps({k: result[k] for k in ['source_campaigns', 'prepared_campaigns',
                                          'additional_campaign_ids', 'new_campaigns_acquired']}, indent=2))


if __name__ == '__main__':
    main()
