#!/usr/bin/env python3
"""Read-only S8 evidence aggregation. Route acceptance is NOT release approval.

Requires explicit reports and candidate ROM; never runs an emulator or changes
availability. Missing evidence fails closed. Existing output files are preserved.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / 'tools' / 'verify'
# This verifier is also imported by its unit tests. Keep its sibling runtime
# helper ahead of the checkout root, which may contain stale decompiler stubs
# with the same module name.
for _path in (str(ROOT), str(VERIFY)):
    if _path in sys.path:
        sys.path.remove(_path)
sys.path[0:0] = [str(VERIFY), str(ROOT)]
PENDING = {
    'stage_pixels_and_hardware_commit': 'Need candidate-matched committed/unblanked pixel evidence for all 14 actual Normal stages; boundary screenshots are insufficient.',
    'frontpanel_sequence_motion': 'Need native receipts for actual source frontpanel uses, including Normal 1A four-panel sequence motion; static implementation/allocation is not native proof.',
    'generated_media_source_fidelity': 'Artifact identity alone does not validate source media or rendering.',
    'required_actor_item_environment_semantics': 'Accelerated queue/camera/HP progression bypasses behavioral coverage.',
    'audio_and_manual_visual_acceptance': 'Track-selection counters are not audible or manual visual acceptance.',
    'timer_time_pickup': 'Bind native Time pickup, timer reset/decrement/timeout and exactly-once effect to this candidate.',
    'opponent_hud': 'Bind P1/P2 native hit target, source name/HP and committed HUD output to this candidate.',
    'bounds_holes_water': 'Bind all required source environment cases, actor lifecycle and native outputs to this candidate.',
    'ramon_actor_behavior': 'Correct admission identity does not establish source moves, damage, or lifecycle.',
    'easy_scene_compatibility': 'Easy three-clear control does not exercise S7 extra completion after Rugal.',
}

_CAMPAIGN_BRIDGE = None


def campaign_bridge():
    """Load the verifier beside this file, never a same-named root stub."""
    global _CAMPAIGN_BRIDGE
    if _CAMPAIGN_BRIDGE is None:
        path = VERIFY / 'game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_acceptance_campaign_bridge', path)
        if spec is None or spec.loader is None:
            raise ImportError(f'cannot load campaign verifier bridge: {path}')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CAMPAIGN_BRIDGE = module
    return _CAMPAIGN_BRIDGE


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def contracts():
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    import build_rom as build
    return {mode: dict(entries=[list(e) for e in build.CAMPAIGN_ENTRY_MAPS[cid]],
                       flags=[int(e['next_after']) for e in build.CAMPAIGN_CONFIGS[cid]['entries']],
                       completion_flags=build.CAMPAIGN_CONFIGS[cid]['completion_flags'],
                       completion_policy=build.CAMPAIGN_CONFIGS[cid]['completion_policy'])
            for mode, cid in [('skip', 'BOR_NORMAL_1A_INTERNAL'),
                              ('natural', 'BOR_NORMAL_1A_INTERNAL'), ('easy', 'BOR_ORIGINAL')]}


def required_checks(mode, contract):
    names = ['compiler exposes 16 typed entries', 'generated release gate permits selected set',
             'generated selected campaign mapping matches ABI', 'generated next flags match source compiler',
             'source tail is 6B -> RUGAL -> 6C -> ENDING', 'cold TITLE helper passed',
             'player selector retains selected source set', 'native campaign starts at compiler first stage',
             'new run completion latch is clear', 'all gate checks passed']
    names.append('generated completion flags match explicit compatibility policy')
    if mode != 'easy':
        names += ['Normal selected while difficulty prompt remains active',
                  'all 16 compiler entries consumed in order', 'completion credited exactly once',
                  'two scene continuations exactly once', 'TITLE dwell has no late scene swaps']
    else:
        names += ['bounded Easy control leaves TimesCompleted unchanged']
    for i, (kind, _, name) in enumerate(contract['entries'][:3 if mode == 'easy' else 16]):
        names.append(f'entry {i} native order/identity')
        if kind == 'stage':
            names.append(f'entry {i} completion policy behavior')
            if contract['completion_flags'][i]:
                names.append(f'entry {i} showcomplete advances exactly once')
        else:
            names += [name + suffix for suffix in (' campaign scene continuation',
                      ' source scene audio selection', ' preserves score/lives/credits', ' clean scene transport')]
            names += ([name + ' complete natural playback'] if mode == 'natural' else
                      [name + ' real input skip exactly once', name + ' no swaps after skip cleanup'])
            if mode == 'natural' and name == 'ENDING':
                names.append('ENDING has four clip transitions')
    return names


def validate(report, mode, contract, artifacts, rom):
    errors = []
    def check(ok, reason):
        if not ok:
            errors.append(reason)
    try:
        check(report['mode'] == mode and report['verdict'] == 'PASS' and not report.get('error'), 'mode/verdict/error')
        checks = report['checks']
        check(all(len(c) == 2 and c[1] is True for c in checks), 'failed/malformed check')
        names = [c[0] for c in checks]
        check(len(names) == len(set(names)), 'duplicate check names')
        check(set(required_checks(mode, contract)) <= set(names), 'missing required gate')
        check(len(contract['entries']) == 16 and len(contract['flags']) == 16, 'source contract not 16 entries')
        check(report['expected_entries'] == contract['entries'], 'source order/physical IDs')
        check(report['next_flags'] == contract['flags'], 'source next flags')
        check(report['completion_flags'] == contract['completion_flags']
              and report['completion_policy'] == contract['completion_policy'], 'runtime compatibility policy')
        check(Path(report['rom_path']).resolve() == rom, 'ROM path')
        check(Path(report['msu_path']).resolve() == rom.with_suffix('.msu'), 'MSU sibling')
        recorded = {str(Path(p).resolve()): h for p, h in report['artifacts'].items()}
        check(recorded == artifacts, 'candidate artifact hashes')
        count = 3 if mode == 'easy' else 16
        check(len(report['route']) == count, 'route length')
        before = report['times_before']
        check(type(before) is int and 0 <= before <= 0xFFFFFFFF, 'Times baseline')
        campaign = 0 if mode == 'easy' else 3
        for i, row in enumerate(report['route']):
            kind, value, name = contract['entries'][i]
            check([row['kind'], row['physical_or_scene'], row['source']] == [kind, value, name]
                  and row['ordinal'] == i and row['next_after'] == bool(contract['flags'][i]), f'entry {i} identity')
            start, end = row['start'], row['end']
            check(start['ordinal'] == i and start['campaign'] == campaign and start['times'] == before
                  and start['state'] == (0 if kind == 'stage' else 7), f'entry {i} native start')
            if kind == 'stage':
                check(start['stage'] == value and row['completion_expected'] == bool(contract['completion_flags'][i])
                      and row['saw_showcomplete'] == row['completion_expected'], f'entry {i} completion policy')
            else:
                scene = row['scene']
                check(scene['late'] == scene['retries'] == 0, f'{name} transport')
                if mode == 'natural':
                    check(scene['presented'] == (126 if name == 'RUGAL' else 1997)
                          and scene['completion'] == 1 and scene['skip'] == 0
                          and scene['transitions'] == (0 if name == 'RUGAL' else 4), f'{name} natural frames/completion')
                else:
                    fences = row.get('immediate_skip_fences', {})
                    # Exact named fence set; arbitrary {"PASS": true} is insufficient.
                    required = {'skip_mode', 'preceding_real_skip', 'consumed_once', 'seen_once',
                                'scene_id', 'inactive', 'clean', 'skipped_once', 'input_edge',
                                'ends_once', 'campaign', 'destination', 'credit'}
                    immediate = set(fences) == required and all(v is True for v in fences.values())
                    check(scene['skip'] == 1 and scene['completion'] == 0
                          and (row['skip_sent'] is True or immediate), f'{name} strict skip')
            terminal = i == 15
            next_kind, next_value, _ = contract['entries'][min(i + 1, 15)]
            check(end['campaign'] == campaign and end['ordinal'] == min(i + 1, 15)
                  and end['state'] == (1 if terminal else 0 if next_kind == 'stage' else 7)
                  and end['times'] == ((before + 1) & 0xFFFFFFFF if terminal else before), f'entry {i} exit/credit')
            if not terminal and next_kind == 'stage':
                check(end['stage'] == next_value, f'entry {i} next physical ID')
        after = before if mode == 'easy' else (before + 1) & 0xFFFFFFFF
        terminal = report['route'][-1]['end']
        final = report['final']
        # TITLE dwell is required to prove no late scene swaps, so live NMI,
        # DMA-ring and service counters legitimately advance after the route's
        # terminal sample. Compare only campaign/completion state here; a full
        # snapshot equality falsely rejects every correctly dwelled natural
        # receipt even when TimesCompleted and the terminal route are stable.
        terminal_fields = ('state', 'ordinal', 'stage', 'campaign', 'times', 'complete')
        terminal_fields += tuple(field for field in ('credits', 'p1_lives', 'p1_out')
                                 if field in final and field in terminal)
        check(report['times_after'] == after and final['times'] == after
              and all(final[field] == terminal[field] for field in terminal_fields),
              'final/Times credit')
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        errors.append(f'malformed evidence: {type(error).__name__}: {error}')
    return dict(status='PASS' if not errors else 'REJECTED', errors=errors)


def validate_traversal(report, expected):
    """Compare native admissions to a freshly compiled plan, not receipt-owned expectations."""
    validate_admission = campaign_bridge().validate_admission
    errors = []
    try:
        receipt = report['spawn_traversal']
        if receipt['status'] != 'PASS' or receipt['expected'] != expected:
            raise ValueError('traversal status/source plan mismatch')
        completed = receipt['completed']
        if len(completed) != len(expected) or sum(r['spawn'] for r in expected) != 614:
            raise ValueError('missing/extra source packed records or 614-spawn contract drift')
        for actual, source in zip(completed, expected):
            validate_admission(actual, source)
            for key in ('source_queue_index', 'source_model', 'source_definition'):
                if actual[key] != source[key]:
                    raise ValueError('admission source identity metadata mismatch')
        admissions = {(r['stage'], r['index']): r for r, e in zip(completed, expected) if e['spawn']}
        # HP acceleration is optional: current traversal receipts advance
        # the source-authored encounter and may record unlink delays without
        # using the older HP-write shortcut at all.
        for write in receipt.get('hp_accelerations', []):
            actor = admissions[(write['stage'], write['index'])]
            if (write['delay_fields'] < 2 or any(write[k] != actor[k]
                    for k in ('offset', 'roster', 'object_num'))):
                raise ValueError('HP acceleration lacks matching delayed admission')
        names = {name for name, passed in report['checks'] if passed is True}
        if 'all 614 source spawn identities and every control record observed' not in names:
            raise ValueError('missing traversal final gate')
        for physical in {r['stage'] for r in expected}:
            ordinal = next(i for i, e in enumerate(report['expected_entries']) if e[0] == 'stage' and e[1] == physical)
            if f'entry {ordinal} every packed record consumed natively' not in names:
                raise ValueError('missing stage traversal gate')
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, AssertionError) as error:
        errors.append(str(error))
    return dict(status='PASS' if not errors else 'REJECTED', errors=errors)


def inspect_feature(path, artifacts):
    """Quarantine heterogeneous receipts until a feature-specific oracle is bound.

    A generic PASS, relocation report or wrapper manifest cannot close a native
    feature. Still expose actual failures, missing hashes and linked subreports.
    """
    try:
        raw = Path(path).read_bytes()
        report = json.loads(raw)
        checks = report.get('checks', [])
        passed = [c.get('passed') if isinstance(c, dict) else c[1] for c in checks]
        errors = []
        if report.get('error') or report.get('verdict') == 'FAIL' or any(v is not True for v in passed):
            errors.append('receipt records native failure')
        recorded = {str(Path(p).resolve()): h for p, h in report.get('artifacts', {}).items()}
        if not artifacts or any(recorded.get(p) != h for p, h in artifacts.items()):
            errors.append('missing or mismatched candidate artifact binding')
        return dict(status='REJECTED' if errors else 'UNBOUND_FEATURE_SCHEMA', errors=errors,
                    path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(),
                    required_binding='Feature-specific expected cases, native measurements and consumer assertions; generic status is insufficient.')
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        return dict(status='MISSING_OR_INVALID', errors=[str(error)])


def aggregate(paths, rom, feature_paths=None):
    rom = Path(rom).resolve()
    result = dict(schema_version=1, release_verdict='BLOCKED_PENDING_EVIDENCE', reports={},
                  per_feature={name: dict(status='PENDING_NATIVE_EVIDENCE', reason=reason)
                               for name, reason in PENDING.items()},
                  nonclaims=['Static normal_coverage cannot certify runtime acceptance.',
                             'Accelerated route evidence is not full source behavior or visual/media acceptance.'])
    expected = contracts()
    result['entry_inventory'] = [dict(ordinal=i, kind=e[0], physical_or_scene=e[1], source=e[2],
        authored_next=expected['natural']['flags'][i], completion=expected['natural']['completion_flags'][i],
        required_receipts=['skip', 'natural'] + (['traversal'] if e[0] == 'stage' else []))
        for i, e in enumerate(expected['natural']['entries'])]
    try:
        artifacts = {str(p.resolve()): digest(p) for p in
                     (rom, rom.with_suffix('.msu'), ROOT / 'src/main.sym', ROOT / 'tools/audio/campaign_config.pasm')}
        result['artifacts'] = artifacts
    except OSError as error:
        artifacts = {}
        result['artifact_error'] = str(error)
    for mode in ('skip', 'natural', 'easy'):
        path = paths.get(mode)
        try:
            if path is None:
                raise ValueError('report not supplied')
            raw = Path(path).read_bytes()
            verdict = validate(json.loads(raw), mode, expected[mode], artifacts, rom)
            verdict.update(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest())
        except (OSError, ValueError) as error:
            verdict = dict(status='MISSING_OR_INVALID', errors=[str(error)])
        result['reports'][mode] = verdict
    result['route_evidence'] = ('PASS' if artifacts and all(r['status'] == 'PASS' for r in result['reports'].values())
                                else 'INCOMPLETE_OR_REJECTED')
    result['per_feature']['accelerated_campaign_routes'] = dict(status=result['route_evidence'])
    traversal_path = paths.get('traversal')
    if traversal_path:
        try:
            raw = Path(traversal_path).read_bytes()
            report = json.loads(raw)
            verdict = validate(report, 'natural', expected['natural'], artifacts, rom)
            if verdict['status'] == 'PASS':
                import build_rom as build
                traversal_plan = campaign_bridge().traversal_plan
                verdict = validate_traversal(report, traversal_plan(build, build.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']))
            verdict.update(path=str(Path(traversal_path).resolve()), sha256=hashlib.sha256(raw).hexdigest())
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as error:
            verdict = dict(status='REJECTED', errors=[str(error)])
    else:
        verdict = dict(status='MISSING', errors=['natural --spawn-traversal receipt required'])
    result['per_feature']['all_source_spawn_integration'] = verdict
    result['native_route_and_admission_evidence'] = ('PASS' if result['route_evidence'] == 'PASS'
                                                    and verdict['status'] == 'PASS' else 'MISSING_OR_REJECTED')
    result['feature_receipts'] = {}
    for feature, path in (feature_paths or {}).items():
        if feature not in PENDING:
            raise ValueError('unknown feature receipt: ' + feature)
        result['feature_receipts'][feature] = inspect_feature(path, artifacts)
    result['missing_receipt_bindings'] = {
        'route_dwell_raw': 'Harness checks 180-field TITLE dwell, but receipt lacks raw beginning/end credit/continuation counters and dwell count.',
        'producer_source_binding': 'Existing route reports hash artifacts, not executing harness or source PAK/LEVELS contents.',
        'feature_oracles': 'Feature receipts are diagnostic only until each concrete expected-case/measurement schema is implemented.',
        'release': 'No release authorization or complete native/media/manual acceptance is established here.'}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    for mode in ('skip', 'natural', 'easy'):
        parser.add_argument('--' + mode, type=Path)
    parser.add_argument('--traversal', type=Path, help='Natural full-route receipt with all 614 native spawn admissions.')
    parser.add_argument('--feature-receipt', action='append', default=[], metavar='FEATURE=PATH',
                        help='Diagnostic receipt binding only; never a generic feature PASS override.')
    parser.add_argument('--output', type=Path, help='New file only; existing evidence is never overwritten.')
    args = parser.parse_args()
    features = {}
    for item in args.feature_receipt:
        feature, separator, path = item.partition('=')
        if not separator or feature not in PENDING or feature in features:
            parser.error('feature receipt requires a unique known FEATURE=PATH')
        features[feature] = Path(path)
    result = aggregate({mode: getattr(args, mode) for mode in ('skip', 'natural', 'easy', 'traversal')}, args.rom, features)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(encoded)
    else:
        print(encoded, end='')
    return 1  # Release remains blocked; no PASS/force override is provided.


if __name__ == '__main__':
    raise SystemExit(main())
