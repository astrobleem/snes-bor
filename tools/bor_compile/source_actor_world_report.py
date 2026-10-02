"""Report bounded world-program admission separately from whole-model certification.

Consumes freshly parsed project reports. No source identity selects behavior;
no native fixture PASS removes a whole-model blocker automatically.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from source_actor_link import link_scheduler
from source_actor_world_link import link_world_program


def summarize(path):
    raw = Path(path).read_bytes()
    project = json.loads(raw)
    models = {}
    for name, row in sorted(project['models'].items()):
        actor = row['actor_lowering']
        try:
            _, scheduler = link_scheduler(actor, bank_base=0x298000)
            _, program = link_world_program(actor, scheduler, 0,
                controlled_player_action=actor['stats'].get('type') == 'player')
            admission = dict(status='BOUNDED_PROGRAM_LINKABLE', program=program,
                             note='Not a per-model live proof or full certification')
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            admission = dict(status='BLOCKED', reason=str(error))
        requirements = []
        if actor['dialect'] != 'historical-bor':
            requirements.append('DIALECT_SOURCE_DRIVER_CONTRACT')
        elif actor['behavior'].get('driver') in (
                'enemy_drop_then_ai', 'player', 'noncombat_horizontal_drift'):
            requirements.append('NUMERIC_GENERAL_MOVEMENT_AND_OR_GRAVITY')
        if actor['stats'].get('type') == 'player':
            requirements.append('MODEL_FULL_PLAYER_CONTROLLER')
        if actor['behavior'].get('default_effect') == 'reset_timer':
            requirements.append('SPECIAL_EFFECT_GAMEPLAY_TIMER_LIFECYCLE')
        models[name] = dict(source_identity=actor['source_identity'],
            source_path=actor['source_path'], world_program=admission,
            whole_model_status=row['lowering_profiles']['SOURCE_EXACT']['status'],
            additional_domain_requirements=requirements,
            shipped_target_categories=row['actor_certification']['matrix'])
    entries = []
    for entry in project['entries']:
        blockers = [n for n in entry.get('required_models', [])
                    if n not in models or models[n]['whole_model_status'] != 'SOURCE_CERTIFIED']
        entries.append(dict(set=entry['set_name'], ordinal=entry['ordinal'],
            source_path=entry.get('source_path'), kind=entry['kind'],
            status='BLOCKED', model_dependencies=blockers,
            source_analysis_status=entry['status'],
            environment_diagnostics=[d for d in entry.get('diagnostics', [])
                if d.get('category') not in ('DIRECTLY_LOWERABLE', 'LOWERABLE_WITH_ADAPTER')],
            media_link_requirement=entry.get('link_blocker'),
            authored_queue_count=entry.get('authored_queue_count'),
            packed_queue_candidate_count=entry.get('packed_queue_candidate_count')))
    return dict(input_sha256=hashlib.sha256(raw).hexdigest(),
        project_id=project['project_id'], models=models, entries=entries,
        whole_model_counts=dict(Counter(m['whole_model_status'] for m in models.values())),
        bounded_program_counts=dict(Counter(m['world_program']['status'] for m in models.values())),
        requirement_counts=dict(Counter(r for m in models.values()
                                       for r in m['additional_domain_requirements'])),
        note='Shipped-target categories are retained, not rewritten as opt-in core failures. '
             'Bounded program admission never certifies a complete model. Entry publication remains blocked.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', nargs=2, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = dict(schema='source-world-admission-v1', publication=False,
        projects={label: summarize(path) for label, path in args.project})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'world-admission.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    lines = ['# Bounded source-world admission', '',
             'Program linking is not whole-model certification. No production content published.', '',
             '| Project | Models | Source certified | Bounded programs linkable |',
             '|---|---:|---:|---:|']
    for label, report in result['projects'].items():
        lines.append(f"| {label} | {len(report['models'])} | "
                     f"{report['whole_model_counts'].get('SOURCE_CERTIFIED', 0)} | "
                     f"{report['bounded_program_counts'].get('BOUNDED_PROGRAM_LINKABLE', 0)} |")
    (args.output/'world-admission.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
