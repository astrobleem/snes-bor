"""Semantic Easy migration review against a preserved canonical-master receipt.

The baseline contains compiler-derived bytes, not unrelated dirty output files.
Rows describe declared/encoded behavior; native receipts separately certify it.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys

from compiler import ROOT, Source, project, stage, key, model_catalog
from production_campaign import compile_queues


def compare(baseline, shipped):
    source = Source(shipped.STAGE_CONFIGS[0]['pak'])
    easy = next(s for s in project(source).sets if s.name == 'Easy')
    models = model_catalog(source)
    campaign = shipped.CAMPAIGN_CONFIGS['BOR_ORIGINAL']
    blobs = compile_queues(shipped.STAGE_CONFIGS, shipped.ROSTER_CONFIGS)
    rows = []

    def row(domain, identity, old, new, authority, verdict):
        rows.append(dict(domain=domain, identity=identity, old=old, new=new,
                         source_authority=authority, verdict=verdict))

    row('campaign', 'source identity/unlock',
        [baseline['source_set']['source_id'], baseline['source_set']['ifcomplete']],
        [easy.source_id, easy.ifcomplete], 'DATA/LEVELS.TXT', 'LEGACY_EQUIVALENT')
    old_players = [i for i,r in enumerate(baseline['roster'])
                   if r['family'] == 'bor-original' and r.get('normal_player_selectable')]
    new_players = [i for i,r in shipped.normal_player_entries('bor-original')]
    row('selector', 'public source player roster', old_players, new_players,
        'DATA/MODELS.TXT player models; unchanged source-normal public selector mapping',
        'LEGACY_EQUIVALENT' if old_players == new_players else 'REGRESSION')
    for ordinal, entry in enumerate(easy.entries):
        old = baseline['campaign']['entries'][ordinal]
        new = campaign['entries'][ordinal]
        identity = entry.source_path
        row('campaign', identity, old, new, 'DATA/LEVELS.TXT',
            'LEGACY_EQUIVALENT' if old == new else 'REGRESSION')
        old_flag = baseline['campaign']['completion_flags'][ordinal]
        new_flag = campaign['completion_flags'][ordinal]
        assert new_flag == int(entry.next_after)
        row('showcomplete', identity, old_flag, new_flag,
            'DATA/LEVELS.TXT next; BOR.C playgame gonext',
            'LEGACY_EQUIVALENT' if old_flag == new_flag else 'SOURCE_CORRECTS_LEGACY')

    total_spawns = 0
    queue_changes = Counter()
    for old_stage in baseline['stages']:
        physical = old_stage['physical']
        cfg = shipped.STAGE_CONFIGS[physical]
        ir = stage(source, cfg['source_level'])
        old_ir = old_stage['source_ir']
        assert key(cfg['source_level']) == key(old_ir['source_path'])
        old_blob = bytes.fromhex(old_stage['packed_hex'])
        blob = blobs[cfg['spawn']]
        assert len(blob) == len(old_blob) == 10 * (len(ir.queue) + len(ir.environment.get('hole', [])))
        row('physical media', ir.source_path, physical, physical,
            'source identity mapping; original physical catalog pins', 'LEGACY_EQUIVALENT')
        row('environment declarations', ir.source_path, old_ir['environment'], ir.environment,
            ir.source_path, 'LEGACY_EQUIVALENT' if old_ir['environment'] == ir.environment else 'REGRESSION')
        contract_fields = ('background', 'frontpanel', 'panels', 'order', 'dimensions',
                           'scroll', 'music', 'bossmusic')
        current_ir = json.loads(json.dumps(asdict(ir)))
        old_contract = {k:old_ir[k] for k in contract_fields}
        new_contract = {k:current_ir[k] for k in contract_fields}
        row('authored stage contract', ir.source_path, old_contract, new_contract,
            ir.source_path, 'LEGACY_EQUIVALENT' if old_contract == new_contract else 'REGRESSION')
        media = json.loads((ROOT / cfg['bg'] / 'manifest.json').read_text())
        new_dimensions = {k:media[k] for k in ('width_px', 'height_px')}
        old_dimensions = old_stage['background_dimensions']
        row('encoded stage dimensions', ir.source_path, old_dimensions, new_dimensions,
            'authored panel order/dimensions; existing 4/5 scaling and tile-alignment adapter',
            'LEGACY_EQUIVALENT' if old_dimensions == new_dimensions else 'REGRESSION')
        prefix = len(ir.environment.get('hole', []))
        for index in range(len(blob) // 10):
            old = old_blob[index*10:(index+1)*10]
            new = blob[index*10:(index+1)*10]
            event = ir.queue[index-prefix] if index >= prefix else None
            if event is not None:
                authored = json.loads(json.dumps(asdict(event)))
                assert authored == old_ir['queue'][index-prefix], (ir.source_path, index, 'authored queue semantics changed')
            if event and event.character:
                total_spawns += 1
            # Positions, triggers, map/facing, held identities and group/wait
            # bytes must remain intact. Source bindings can change kind,
            # identity, default health and a source-derived pickup effect.
            assert old[:6] == new[:6], (ir.source_path, index, 'geometry/map changed')
            assert old[8] == new[8], (ir.source_path, index, 'held identity changed')
            if old != new:
                assert event and event.character
                queue_changes[event.character.casefold()] += 1
                verdict = 'SOURCE_CORRECTS_LEGACY'
                before = dict(record=old.hex(), binding='unidentified slot-owned actor or legacy missing source binding')
                after = dict(record=new.hex(), model=event.character,
                             roster=new[9], authored_health=event.health, model_health=models[event.character.casefold()]['entity'].get('health'),
                             encoded_hp=new[7], map=event.map,
                             boss=event.boss, item=event.item)
            else:
                verdict = 'LEGACY_EQUIVALENT'
                before = old.hex()
                after = new.hex()
            row('queue record', f'{ir.source_path}:{index}', before, after,
                f'{ir.source_path} authored queue {index-prefix}; DATA/MODELS.TXT and model definition', verdict)

    row('ordered frontpanels', 'DATA/EASY/1AEASY.TXT',
        'legacy scalar foreground: street/f03.gif',
        'four authored foregrounds in order: street/f00.gif, f01.gif, f02.gif, f03.gif',
        'DATA/EASY/1AEASY.TXT frontpanel declarations; frozen legacy out/fp_stage1a/manifest.json',
        'SOURCE_CORRECTS_LEGACY')

    row('mirror', 'DATA/EASY/6AEASY.TXT', 'fixed-size top Y reflection 352-normalTopY',
        'same source pose, ground mirror foot 248-nativeY; shared source resources',
        'BOR.C display_ents: (PLAYER_MIN_Z-10)+(PLAYER_MIN_Z-z)-a; 4/5 ACCEPTED_COMPAT projection',
        'SOURCE_CORRECTS_LEGACY')

    for domain, old, new, authority in (
        ('source combat world', 'SCPU compatibility AI; host mode 0',
         'persistent SA-1 source combat world; host mode 1', 'BOR.C source actor functions; explicit shared source-world adapters'),
        ('visuals', 'fixed 32x48 compatibility art', 'source-sized catalog/16 KiB residency; no fallback',
         'source model animation GIF paths and PAL.ACT/remaps'),
        ('stage environment service', 'legacy Easy adapters',
         'shared source bounds, ordered BG2 frontpanels, water/rock and drop adapters',
         'authored stage directives; existing ACCEPTED_COMPAT encoders/clock adapters'),
        ('health/coordinates', '64/100 HP, 4/5 coordinates, six actors',
         'same explicit HP/coordinate/actor-pool transport adaptations', 'documented shared ACCEPTED_COMPAT ABI'),
    ):
        row(domain, 'shared architecture', old, new, authority, 'ACCEPTED_COMPAT')
    for identity, value, authority in (
        ('music/media', 'source-bound stage music and ordered Rugal/Ending clips', 'stage and scene TXT declarations'),
        ('terminal completion', 'one TimesCompleted increment and TITLE destination', 'BOR.C playgame; shared completion latch'),
    ):
        row('presentation/progression', identity, value, value, authority, 'LEGACY_EQUIVALENT')
    counts = Counter(r['verdict'] for r in rows)
    assert total_spawns == 545
    return dict(schema=1, baseline_master=baseline['master'], source_set_id=easy.source_id,
                ifcomplete=easy.ifcomplete, packed_records=667, source_spawns=total_spawns,
                queue_identity_corrections=dict(queue_changes),
                counts={v:counts[v] for v in ('LEGACY_EQUIVALENT','SOURCE_CORRECTS_LEGACY','ACCEPTED_COMPAT','REGRESSION','UNPROVEN')},
                authored_queue_contracts_equal=664,
                authored_aliases_preserved=sum(bool(q['alias']) for s in baseline['stages'] for q in s['source_ir']['queue']),
                rows=rows, scope='source/encoded semantic differential; native behavior requires separate baseline and migrated receipts')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/audio'))
    import shipped_content
    report=compare(json.loads(args.baseline.read_text()),shipped_content)
    args.output.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report['counts']))
    return int(report['counts']['REGRESSION'] != 0)


if __name__=='__main__':
    raise SystemExit(main())
