"""Build the explicitly selected persistent-SA-1 production runtime candidate.

The shipped distribution ROM remains the S-CPU reference/fallback. This tool
creates a separate runnable image using its real stage services, source-sized
visual catalog, full-visual 30-Hz gate, and persistent BW-RAM world owner.
"""
import argparse
import hashlib
import json
import struct
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT, sha
from actor_s6_production_world import build, run
from actor_s7_persistent_worker import install


def source_visual_identity(base_dir):
    include = ROOT / 'src/generated/production_source_visual.pasm'
    generated = ROOT / 'src/generated/production_source_visual.bin'
    text = include.read_text()
    values = dict(re.findall(r'^(SOURCE_VISUAL_[A-Z_]+) = (.+)$', text, re.M))
    enabled = int(values['SOURCE_VISUAL_BUILD_ENABLED'])
    count = int(values['SOURCE_VISUAL_CATALOG_COUNT'])
    offset = int(values['SOURCE_VISUAL_MSU_OFFSET'].replace('$', '0x'), 16)
    size = int(values['SOURCE_VISUAL_MSU_SIZE'])
    blob = generated.read_bytes()
    msu = (base_dir / 'bor.msu').read_bytes()
    metadata = json.loads((ROOT / 'src/generated/production_source_visual.json').read_text(encoding='utf-8'))
    expected = metadata['summary']['entry_count']
    packed_count = struct.unpack_from('<H', blob, 6)[0] if blob[:5] == b'SVIS1' else -1
    if (enabled != 1 or count != expected or packed_count != count or count <= 0
            or metadata['summary']['blocker_count'] or size != len(blob)):
        raise RuntimeError('PRODUCTION_SOURCE_VISUAL_CATALOG_NOT_ENABLED_OR_EXPECTED')
    if offset + size > len(msu) or msu[offset:offset + size] != blob:
        raise RuntimeError('PRODUCTION_SOURCE_VISUAL_MSU_BYTES_MISMATCH')
    return dict(enabled=enabled, entries=count, msu_offset=offset, msu_size=size,
                catalog_sha256=hashlib.sha256(blob).hexdigest(),
                embedded_sha256=hashlib.sha256(msu[offset:offset + size]).hexdigest(),
                renderer_symbols={name: symbols(ROOT / 'src/main.sym')[name]
                                  for name in ('StageTimerHost_RenderFrame',
                                               'SourceVisual_RenderCurrent',
                                               'SourceVisual_CallCount')},
                obj_vram_byte_range=[0x8000, 0xC000], obj_vram_bytes=16384)


def build_candidate(output, base_dir, source_rom=None):
    output = Path(output).resolve()
    base_dir = Path(base_dir).resolve()
    if output.exists():
        raise FileExistsError(f'output already exists: {output}')
    if not (base_dir / 'bor.sfc').is_file() or not (base_dir / 'bor.msu').is_file():
        raise FileNotFoundError(f'production ROM/MSU pair missing under {base_dir}')
    source_rom = Path(source_rom).resolve() if source_rom else base_dir / 'bor.sfc'
    if not source_rom.is_file():
        raise FileNotFoundError(f'production source ROM missing: {source_rom}')
    visual = source_visual_identity(base_dir)
    output.mkdir(parents=True)
    linked = build(output, 'enemy', enemy_copies=4, resident=True,
                   layout_dispatch=True, stream_publisher=True,
                   presentation_divisor=2, base_dir=base_dir,
                   base_rom=source_rom)
    worker_symbols = install(output, production_runtime=True)
    pcm_names=[]
    for pcm in sorted(base_dir.glob('bor-*.pcm')):
        candidate = output / pcm.name
        if not candidate.is_file() or not os.path.samefile(pcm, candidate):
            raise RuntimeError(f'PCM_NOT_HARDLINKED: {candidate}')
        pcm_names.append(pcm.name)
    main_symbols = symbols(ROOT / 'src/main.sym')
    artifact = dict(status='OPT_IN_PERSISTENT_SA1_PRODUCTION_RUNTIME_CANDIDATE',
        selectable=True, fallback='unchanged distribution/bor.sfc S-CPU path',
        production_distribution_modified=False,
        source_image=dict(rom_sha256=sha(source_rom),
                          msu_sha256=sha(base_dir / 'bor.msu')),
        candidate=dict(rom_sha256=sha(output / 'bor.sfc'),
                       msu_sha256=sha(output / 'bor.msu')),
        workload=dict(stage='EASY5', players=2, active_opponents=4,
                      pending_opponents=0, source_clock_hz=200,
                      presentation_divisor=2, presentation='full visual',
                      source_profile='SOURCE_EXACT', correct_scale=True),
        runtime=dict(world_owner='persistent SA-1 BW-RAM epoch',
                     per_tick_acquire_release=False, whole_context_round_trip=False,
                     fallback_s_cpu_world_retained=True,
                     six_actor_source_contexts=6,
                     source_visual_catalog=visual,
                     obj_vram_byte_range=[0x8000, 0xC000],
                     obj_vram_bytes=16384,
                     bg2_frontpanel_character_base=0x3000,
                     input_protocol='8-byte sequenced command per source tick',
                     snapshot_protocol='double-buffered 272-byte sequence-acknowledged render snapshot',
                     event_protocol='16-byte sequence-numbered records; capacity 128; fail closed'),
        patches=linked['patches'], worker_symbols={k:v for k,v in worker_symbols.items()
                                                     if k in ('Worker_Gate','Worker_Execute',
                                                              'Worker_Complete','Relay_Run',
                                                              'Relay_Flush','Relay_DrainEvents')},
        pcm_hardlinks=pcm_names)
    (output / 'production-runtime.json').write_text(json.dumps(artifact, indent=2) + '\n')
    manifest=json.loads((output / 'worker-manifest.json').read_text())
    manifest['runtime_candidate']='OPT_IN_PRODUCTION_PATH'
    manifest['production_distribution_modified']=False
    manifest['source_visual_catalog']=visual
    (output / 'worker-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return output, artifact


def production_smoke_report(folder):
    folder = Path(folder)
    read_json = lambda name: json.loads((folder / name).read_text())
    proof = read_json('proof.json')
    input_report = read_json('input.json')['proof']
    observations = read_json('observations.json')
    delivered = read_json('events.json')
    presentation = read_json('presentation.json')
    ppu = read_json('production-smoke-ppu.json')

    if proof.get('status') != 'PASS_BOUNDED_WORLD_CORE':
        raise RuntimeError('PRODUCTION_SMOKE_WORLD_PROOF_FAILED')
    if input_report.get('status') != 'PASS_SA1_CONSUMED_REAL_INPUT_EDGE':
        raise RuntimeError('PRODUCTION_SMOKE_INPUT_NOT_CONSUMED')
    if (input_report.get('mask') != 0x4000 or
            input_report.get('consumed_records', 0) < 1):
        raise RuntimeError('PRODUCTION_SMOKE_INPUT_EDGE_MISMATCH')
    if not observations:
        raise RuntimeError('PRODUCTION_SMOKE_HAS_NO_OBSERVATIONS')

    final = observations[-1]
    stop = final.get('bounded_smoke_stop') or {}
    if not stop or stop.get('worker_completed') != stop.get('command_target'):
        raise RuntimeError('PRODUCTION_SMOKE_DID_NOT_STOP_AT_ACKNOWLEDGED_BOUNDARY')
    if stop.get('event_head') != stop.get('event_tail') or stop.get('event_overflow') != 0:
        raise RuntimeError('PRODUCTION_SMOKE_EVENT_QUEUE_NOT_DRAINED')
    if len(delivered) != stop.get('event_tail'):
        raise RuntimeError('PRODUCTION_SMOKE_EVENT_DELIVERY_COUNT_MISMATCH')

    event_rows = [line.split('|') for line in delivered]
    if any(len(row) < 12 or row[0] != 'S7EVENTDELIVER' for row in event_rows):
        raise RuntimeError('PRODUCTION_SMOKE_MALFORMED_EVENT_RECORD')
    event_sequences = [int(row[2]) for row in event_rows]
    if event_sequences != list(range(stop['event_tail'])):
        raise RuntimeError('PRODUCTION_SMOKE_EVENT_SEQUENCE_GAP_OR_REORDER')
    hit_rows = [row for row in event_rows if int(row[5]) == 2]
    if len(hit_rows) < 2:
        raise RuntimeError('PRODUCTION_SMOKE_REAL_DAMAGE_NOT_OBSERVED')

    first = observations[0]
    initial_hp = [row['hp'] for row in first['rows'][:2]]
    final_hp = [row['hp'] for row in final['rows'][:2]]
    if initial_hp != [64, 64] or final_hp != [46, 46]:
        raise RuntimeError('PRODUCTION_SMOKE_HEALTH_MIRROR_MISMATCH')
    before_damage = next((row for row in observations if row.get('tick') == 9), None)
    if before_damage is None or not any(
            (before_damage['rows'][i]['role'], before_damage['rows'][i]['frame']) !=
            (final['rows'][i]['role'], final['rows'][i]['frame'])
            for i in range(2, 6)):
        raise RuntimeError('PRODUCTION_SMOKE_AI_OR_ANIMATION_DID_NOT_ADVANCE')

    interval = presentation.get('ordered_multiple_events_between_visual_snapshots')
    if not interval or not interval.get('ordered_before_next_snapshot'):
        raise RuntimeError('PRODUCTION_SMOKE_MULTIPLE_EVENT_SNAPSHOT_INTERVAL_MISSING')
    gate_fields = [row['ppu_field'] for row in presentation['gate_observations']
                   if row['tag'] == 'yes']
    if (interval['previous_sampled_field'] not in gate_fields or
            interval['next_sampled_field'] not in gate_fields or
            not interval['previous_sampled_field'] <
                min(event['ppu_field'] for event in interval['events']) <
                interval['next_sampled_field'] or
            max(event['ppu_field'] for event in interval['events']) >=
                interval['next_sampled_field']):
        raise RuntimeError('PRODUCTION_SMOKE_EVENT_SNAPSHOT_ORDER_INVALID')

    live_actors = sum(row['hp'] > 0 for row in final['rows'])
    visual = final['visual']
    if (live_actors != 6 or stop.get('source_mode') != 1 or
            stop.get('actual_visible_oam_entries', 0) <= 0 or
            stop.get('forced_blank') or stop.get('brightness') != 15 or
            visual.get('calls', 0) <= 0 or visual.get('render_passes', 0) <= 0):
        raise RuntimeError('PRODUCTION_SMOKE_SOURCE_VISUAL_NOT_VISIBLE')
    if visual.get('last_error') not in (0, 39):
        raise RuntimeError('PRODUCTION_SMOKE_SOURCE_VISUAL_UNEXPECTED_ERROR')
    layers = {row['index']: row for row in ppu['layers']}
    if (ppu.get('forcedBlank') or ppu.get('brightness') != 15 or
            layers[1]['chrAddr'] != 0x3000 or layers[2]['chrAddr'] != 0x2000):
        raise RuntimeError('PRODUCTION_SMOKE_PPU_LAYOUT_OR_DISPLAY_INVALID')

    return {
        'status': 'PASS_OPT_IN_PRODUCTION_SMOKE',
        'bounded_stop': {
            'source_ticks': stop['worker_completed'],
            'field': final['field'],
            'event_records_delivered': len(delivered),
            'event_head_tail': [stop['event_head'], stop['event_tail']],
            'event_overflow': stop['event_overflow'],
            'damage_events': len(hit_rows),
            'ordered_damage_tick': [int(row[6]) for row in hit_rows],
        },
        'real_input': {
            'button': 'Y', 'mask': input_report['mask'],
            'first_worker_tick': input_report['first_worker_tick'],
            'consumed_records': input_report['consumed_records'],
        },
        'actors': {
            'live': live_actors,
            'player_hp': final_hp,
            'opponent_role_frame_changed': True,
        },
        'presentation': {
            'sample_fields': gate_fields,
            'multi_event_interval': interval,
            'source_visual_calls': visual['calls'],
            'render_passes': visual['render_passes'],
            'visible_oam_entries': stop['actual_visible_oam_entries'],
            'obj_residency_busy_diagnostic': visual.get('last_error'),
            'busy_is_fail_closed': visual.get('last_error') == 39,
        },
        'ppu': {
            'mode': ppu['bgMode'], 'forced_blank': ppu['forcedBlank'],
            'brightness': ppu['brightness'],
            'bg2_character_base': layers[1]['chrAddr'],
            'bg3_character_base': layers[2]['chrAddr'],
        },
        'artifacts': {
            'screenshot': 'production-smoke.png',
            'ppu': 'production-smoke-ppu.json',
            'oam': 'production-smoke-oam.bin',
        },
        'scope_note': ('bounded production-path smoke; S-CPU fallback remains; '
                       'not a campaign or full-roster certification'),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base',type=Path,default=ROOT/'distribution')
    parser.add_argument('--source-rom',type=Path,
                        help='rebuilt production ROM carrying current source modules')
    parser.add_argument('--run-smoke',action='store_true')
    parser.add_argument('--validate-existing-smoke',action='store_true',
                        help='Validate retained production smoke artifacts without starting Mesen')
    parser.add_argument('--fields',type=int,default=180)
    parser.add_argument('--input-start',type=int,default=50)
    parser.add_argument('--input-end',type=int,default=65)
    args=parser.parse_args()
    if args.run_smoke and args.validate_existing_smoke:
        parser.error('--run-smoke and --validate-existing-smoke are mutually exclusive')
    if args.validate_existing_smoke:
        folder=args.output.resolve()
        artifact=json.loads((folder/'production-runtime.json').read_text())
        artifact['smoke']=production_smoke_report(folder)
        (folder/'production-runtime.json').write_text(json.dumps(artifact,indent=2)+'\n')
        print(json.dumps({'output':str(folder),'smoke':artifact['smoke']},indent=2))
        return
    folder,artifact=build_candidate(args.output,args.base,args.source_rom)
    if args.run_smoke:
        run(folder,field_limit_override=args.fields,
            real_input=dict(start_field=args.input_start,end_field=args.input_end,
                            button='Y',port=0),
            stop_after_input_hit=True)
        artifact['smoke']=production_smoke_report(folder)
        (folder/'production-runtime.json').write_text(json.dumps(artifact,indent=2)+'\n')
    print(json.dumps(dict(output=str(folder),status=artifact['status'],
                          rom_sha256=artifact['candidate']['rom_sha256'],
                          msu_sha256=artifact['candidate']['msu_sha256']),indent=2))


if __name__=='__main__':
    main()
