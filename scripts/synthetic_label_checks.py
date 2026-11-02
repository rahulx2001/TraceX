"""Create fictional label-workflow fixtures, never human-validation evidence."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from scripts.defect_accuracy import resolve_human_label
from src.eval.improvement_metrics import classification
from src.eval.improvement_protocol import canonical, digest, write_once

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = 'reports/defect/taxonomy.json'
TAXONOMY_SHA = '285dc13ea5c9ddd9c2ee07f41d8b96d552a241aa069efb4fe9504d5415748812'
NOTICE = 'SYNTHETIC SOFTWARE FIXTURES — not real complaints, human labels, model accuracy, or prospective evidence.'
MAKES = ['FORD', 'HONDA', 'HYUNDAI', 'KIA', 'TOYOTA']
CONTEXTS = ['idling in a parking area', 'starting after an overnight stop',
            'driving uphill', 'driving at a steady speed', 'stopping at a junction']
SCENARIOS = [
    ('confirmed_pump', 'fuel_pump_failure', 'The technician documented that the fuel pump failed its delivery test despite normal electrical supply.', 'Explicit fuel-pump failure is stated.'),
    ('confirmed_electrical', 'fuel_system_other_electrical', 'Inspection confirmed an electrical short in the fuel-system wiring. The pump itself passed its test.', 'The confirmed fault is electrical within the fuel system.'),
    ('confirmed_hose_leak', 'hoses_lines_piping_and_fittings_leak', 'A pressure test confirmed fuel leaking from a hose-to-line fitting. The tank assembly did not leak.', 'A fuel hose/line fitting is the documented leak source.'),
    ('confirmed_tank_leak', 'tank_assembly_leak', 'A pressure test located the fuel leak in the tank assembly. The connected hoses were intact.', 'The tank assembly is the documented leak source.'),
    ('confirmed_diesel_detachment', 'fuel_system_diesel_detachment', 'Inspection documented that the diesel fuel-system assembly detached from its mounting.', 'Diesel fuel-system detachment is explicitly stated.'),
    ('confirmed_canister', 'canister_failure', 'The evaporative-emissions charcoal canister failed its functional test. No pump defect was found.', 'The canister failure is explicitly stated.'),
    ('vague_stall', 'other_unclear', 'The engine stalled once. No inspection has established the faulty part or the cause.', 'A generic stall does not establish a specific fuel defect.'),
    ('odor_without_source', 'other_unclear', 'A fuel-like odor was noticed, but inspection has not found a leak or identified its source.', 'Odor alone does not establish a component and failure mode.'),
    ('recall_mention_only', 'other_unclear', 'The owner read about a fuel-pump recall on the internet. This vehicle has no diagnosed pump failure.', 'A recall mention is not a diagnosis for this vehicle.'),
    ('negated_pump_failure', 'other_unclear', 'The fuel pump passed testing and was not defective. Occasional hesitation remains unexplained.', 'The specific pump diagnosis is explicitly negated.'),
    ('unresolved_alternatives', 'other_unclear', 'Possible causes mentioned were a pump problem or a hose problem. Neither has been confirmed.', 'Unresolved alternative causes do not support one specific label.'),
    ('wrong_component', 'other_unclear', 'The report was entered under fuel system, but the diagnosed issue was an alternator connector. Fuel-system tests were normal.', 'The actual documented fault lies outside the selected fuel taxonomy.'),
]


def vocabulary(root=ROOT):
    if digest(root / TAXONOMY) != TAXONOMY_SHA:
        raise ValueError('Frozen taxonomy hash mismatch')
    taxonomy = json.loads((root / TAXONOMY).read_text())
    labels = taxonomy['body']['components']['FUEL SYSTEM']['labels']
    return {entry['id']:entry['label'] for entry in labels}


def generate_cases():
    rows = []
    for family, expected, story, rationale in SCENARIOS:
        for make in MAKES:
            for index, context in enumerate(CONTEXTS):
                rows.append(dict(case_id=f'SYNTHETIC-{len(rows)+1:04}',
                                 is_synthetic=True, annotation_source='agent_authored_fixture',
                                 human_reviewed=False, human_label='', split='synthetic_software_test',
                                 independent_real_observation=False, fixture_family=family,
                                 component='FUEL SYSTEM', fictional_make=make, fictional_model_year=2015+index,
                                 narrative=f'[FICTIONAL TEST CASE] A fictional {2015+index} {make} test vehicle was {context}. {story}',
                                 expected_label=expected, expected_label_rationale=rationale, notice=NOTICE))
    return rows


def check_cases(rows, labels):
    if len(rows) != 300 or len({r['case_id'] for r in rows}) != 300:
        raise ValueError('Expected 300 distinct fixture IDs')
    ids = ';'.join(labels)
    text = '; '.join(f'{key}={value}' for key,value in labels.items())
    for row in rows:
        if (row.get('is_synthetic') is not True or row.get('annotation_source') != 'agent_authored_fixture'
            or row.get('human_reviewed') is not False or row.get('human_label') != ''
            or row.get('split') != 'synthetic_software_test' or not row['case_id'].startswith('SYNTHETIC-')
            or not row['narrative'].startswith('[FICTIONAL TEST CASE]') or row.get('notice') != NOTICE
            or row.get('independent_real_observation') is not False):
            raise ValueError('Synthetic provenance must be explicit; human attribution is forbidden')
        resolved, status = resolve_human_label(row['expected_label'], ids, text)
        if status != 'ok' or resolved != row['expected_label']:
            raise ValueError('Expected fixture label is outside the frozen taxonomy')
    # Deliberately authored calculator control, not classifier predictions.
    control = classification(['pump', 'tank', 'hose'], ['pump', None, 'other_unclear'])
    if (control['accuracy']['numerator'], control['accuracy']['denominator']) != (1, 3):
        raise ValueError('Missing predictions changed the all-example denominator')
    return dict(status='software_checks_passed', fixture_records=len(rows),
                underlying_scenario_families=len({r['fixture_family'] for r in rows}),
                valid_fixture_label_ids=len(rows), explicit_synthetic_markers=len(rows),
                template_variant_counts=dict(sorted(Counter(r['fixture_family'] for r in rows).items())),
                parser_and_denominator_control='passed; parser accepts registered labels and missing predictions retain denominator mass',
                model_classifier_called=False, model_predictions_generated=False,
                semantic_correctness_verified=False, human_accuracy=None,
                human_validation={'labelled':0,'total':300}, is_candidate_result=False,
                confidence_interval=None,
                limitation='300 template variants from 12 authored stories are not 300 independent observations. Expected labels are agent-authored expectations, not verified truth.',
                notice=NOTICE)


def build(out, *, root=ROOT):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory; existing artifacts are never overwritten')
    labels = vocabulary(root)
    rows = generate_cases()
    checks = check_cases(rows, labels)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'synthetic_cases.jsonl').open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')
    manifest = dict(schema_version=1, created_at=datetime.now(timezone.utc).isoformat(),
                    annotation_source='agent_authored_fixture', split='synthetic_software_test', notice=NOTICE,
                    records=len(rows), scenario_families=len(SCENARIOS), real_independent_observations=0,
                    no_human_annotation=True, classifier_executed=False, allowed_label_ids=labels,
                    dataset_sha256=digest(out / 'synthetic_cases.jsonl'), taxonomy_file_sha256=TAXONOMY_SHA,
                    generator_sha256=digest(Path(__file__)), configuration_sha256=canonical(dict(scenarios=SCENARIOS,makes=MAKES,contexts=CONTEXTS)),
                    code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                    forbidden_uses=['human-review import','fitting/calibration/model selection','updating dashboard accuracy','replacing a frozen benchmark','prospective performance or project validation claims'])
    write_once(out / 'manifest.json', manifest)
    write_once(out / 'software_checks.json', checks)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.out), indent=2))


if __name__ == '__main__':
    main()
