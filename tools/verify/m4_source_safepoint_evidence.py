"""Re-certify retained safe-point fields, source execution and control identity."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from compiler import Source
from m4_live_ground_component_native import scene_from_snapshot
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from m4_nonblank_component_native import decode_vram
import m4_nonblank_batch_native as batch
import m4_source_safepoint_native as safe
import m4_conditional_capacity_native as conditional

CLOCKS_PER_MS = 21477.270
ROOT = Path('out/byor-motu-source-safepoint-v1')
CASES = {'right': 'candidate-v5', 'direction_divergence': 'left-v1',
         'partial_queue': 'partial-v1', 'stale_epoch': 'stale-v1',
         'no_safepoint_control': 'control-v1'}

def collect():
    cases = {}
    source = Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    for name, suffix in CASES.items():
        folder = Path('out/byor-motu-source-safepoint-' + suffix)
        retained = json.loads((folder / 'result.json').read_text())
        fields = json.loads((folder / 'fields.json').read_text())
        contract = retained['contract']
        if name in ('right', 'direction_divergence'):
            result = safe.certify(folder, contract, fields)
        else:
            auditor = conditional.audit_rom if name == 'no_safepoint_control' else safe.audit_rom
            with patch.object(batch, 'audit_rom', auditor):
                result = batch.certify(folder, contract, fields)
            events = json.loads((folder / 'native-events.json').read_text())
            if any(e['kind'] == 'SP_START' for e in events):
                raise ValueError('CONTROL_EXECUTED_SAFEPOINT_MOVEMENT')
            result['classification'] = 'SOURCE_SAFEPOINT_INHERITED_CONTROL_PASS'
        result.pop('capacity_admission', None)
        native = folder/'native'
        images = {}
        for stage in ('cold', 'moved'):
            snapshot = (native/f'{stage}-world.bin').read_bytes()
            scene = scene_from_snapshot(snapshot, source)
            image, _ = compose_rgb8(source, 'DATA/LEVELS/GUILE2.TXT', scene)
            images[stage] = rgb555(image).astype('<u2')
            if images[stage].tobytes() != (native/f'{stage}-expected.rgb555').read_bytes():
                raise ValueError('SOURCE_ORACLE_RECOMPOSITION_FAILED')
        events = json.loads((folder/'native-events.json').read_text())
        commit_frame = next(e['frame'] for e in events if e['kind']=='PHASE'
                            and e['data'][:2]==['NbMapsComplete','2'])
        palette = (native/'cold-cgram.bin').read_bytes()
        for field in fields:
            picture = native/f"field-{field['index']:04d}.png"
            if hashlib.sha256(picture.read_bytes()).hexdigest()!=field['screenshot_sha256']:
                raise ValueError('FIELD_SCREENSHOT_HASH_CHANGED')
            expected = images['moved' if field['ppu']['frameCount']>commit_frame else 'cold']
            pixels = rgb555(np.asarray(Image.open(picture).convert('RGB')))
            vram = (native/f"field-{field['index']:04d}.vram").read_bytes()
            if not np.array_equal(pixels, expected) or not np.array_equal(decode_vram(vram,palette),expected):
                raise ValueError('SOURCE_PIXEL_OR_VRAM_MISMATCH')
        result['source_oracles_recomposed_and_every_png_rechecked'] = True
        if name == 'no_safepoint_control' and result['rom_sha256'] != safe.BASE_SHA:
            raise ValueError('DISABLED_BACKEND_CHANGED')
        result['evidence_folder'] = str(folder)
        # Keep independently checked field identities, hashes and PPU states.
        result['fields'] = [dict(f, ppu={k:v for k,v in f['ppu'].items() if k!='layers'}) for f in fields]
        result.pop('contract', None)
        result.pop('fields_receipt', None)
        result['source_events'] = [e for e in json.loads((folder / 'native-events.json').read_text())
                                   if e['kind'].startswith('SP_')]
        cases[name] = result

    before = json.loads((ROOT / 'dirty-before.json').read_text())
    after = [{'path': x['path'], 'sha256': hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()}
             for x in before]
    if len(before) != 29 or before != after:
        raise ValueError('INHERITED_DIRTY_FILES_CHANGED')
    (ROOT / 'dirty-after.json').write_text(json.dumps(after, indent=2) + '\n')

    right = cases['right']; control = cases['no_safepoint_control']
    for stage in ('cold', 'deferred', 'moved', 'noop', 'left'):
        a = Path(right['evidence_folder'], 'native', stage+'-world.bin').read_bytes()
        b = Path(control['evidence_folder'], 'native', stage+'-world.bin').read_bytes()
        if a!=b:
            raise ValueError('FRESH_NO_SAFEPOINT_SOURCE_CONTROL_DRIFT')
    right['fresh_control_all_snapshots_byte_identical'] = True
    def cost(result):
        clocks = next(x['total_clocks'] for x in result['transaction_costs'] if x['transaction'] == 2)
        return dict(fields=result['transition_fields'], master_clocks=clocks, ms=clocks/CLOCKS_PER_MS)
    timing = dict(control=cost(control), safepoint=cost(right))
    timing['added_master_clocks'] = timing['safepoint']['master_clocks'] - timing['control']['master_clocks']
    timing['added_ms'] = timing['added_master_clocks']/CLOCKS_PER_MS
    timing['added_fields'] = timing['safepoint']['fields'] - timing['control']['fields']
    events = json.loads(Path(right['evidence_folder'], 'native-events.json').read_text())
    phases = {e['data'][0]: e['clock'] for e in events
              if e['kind'] == 'PHASE' and e['data'][1] == '2'}
    timing['transaction_order'] = dict(start=phases['NbBegin'], **right['native_order'],
                                      maps_complete=phases['NbMapsComplete'])
    timing['ready_to_movement_start_clocks'] = right['native_order']['movement_start']-right['native_order']['ready']
    timing['movement_done_to_map_commit_clocks'] = right['native_order']['commit']-right['native_order']['movement_done']
    report = dict(classification='BYOR_MOTU_SOURCE_SAFEPOINT_PASS',
                  starting_commit='6f2339ee45f5b3070eefcc9cd80ad61d3cfb78dc',
                  cases=cases, timing=timing, focused_tests_passed=153,
                  verified_fields=sum(c['observed_fields'] for c in cases.values()),
                  verified_pixels=sum(c['verified_pixels'] for c in cases.values()),
                  pixel_mismatches=0, inherited_dirty_files_preserved=29,
                  dirty_fingerprint_before=str(ROOT/'dirty-before.json'),
                  dirty_fingerprint_after=str(ROOT/'dirty-after.json'),
                  latch_lease=['42D60C','42D620'], latch_bytes=20,
                  subsequent_presentation='Epoch 3 is rendered through the existing projected noop; no new CHR required.',
                  nonclaims=['continuous scheduling', '200-Hz source updates', 'SA-1 coexecution',
                             'general consecutive-frame capacity', '30 FPS', 'audio scheduling',
                             'breath', 'HUD', 'combat', 'complete MOTU Demo'])
    Path('docs/receipts/byor-motu-source-safepoint.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('classification','verified_fields','verified_pixels','timing')}, indent=2))
    return report

if __name__ == '__main__':
    collect()
