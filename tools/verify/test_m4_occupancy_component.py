import copy
import json
from pathlib import Path
import struct
import unittest
from actor_s5_entity_fixture import symbols
from astra_opaque_kernel import emit
from m4_input_controller_native import offset
from m4_occupancy_publisher import apply,DATA,TABLE,END
from m4_occupancy_assets import verify as verify_assets
from m4_occupancy_evidence import certify
from m4_opaque_dma_replay import verify as replay


class OccupancyIntegrationTests(unittest.TestCase):
    root=Path('out/byor-motu-occupancy-v1')
    baseline=Path('out/byor-motu-opaque-warm-v4')
    phases=Path('out/astra-opaque-assets-v1')
    occupancy=Path('out/astra-occupancy-assets-v1')

    def test_actual_source_all_phases_signed_clipping_and_foreground_superset(self):
        result=verify_assets(self.phases,self.occupancy,Path('out/byor-motu-online-v3/assets'),self.baseline/'native/observations.json')
        self.assertEqual(result['all_phase_screen_tile_comparisons'],860160)
        self.assertEqual(result['maximum_required_pairs'],707)
        self.assertEqual(result['legacy_false_negatives'],0)

    def test_compiled_rom_lease_and_every_phase_pointer(self):
        old=(self.baseline/'native/bor.sfc').read_bytes();rom=(self.root/'native/bor.sfc').read_bytes()
        self.assertFalse(any(old[DATA:END]))
        self.assertEqual(rom[0x343000:DATA],old[0x343000:DATA])
        authority=json.loads(Path('out/byor-motu-online-v3/assets/source-assets.json').read_text())
        manifest=json.loads((self.occupancy/'occupancy-manifest.json').read_text())
        cursor=DATA
        for i,frame in enumerate(authority['frames']):
            for px,entry in enumerate(manifest['frames'][frame['role']]['x_phases']):
                raw=(self.occupancy/entry['filename']).read_bytes()
                self.assertEqual(rom[cursor:cursor+len(raw)],raw)
                stride=entry['cols']*entry['tile_rows']
                for q in range(8):
                    p,c,r=struct.unpack_from('<IHH',rom,TABLE+i*512+px*64+q*8)
                    self.assertEqual((p,c,r),(0xc00000+cursor+q*stride,entry['cols'],entry['tile_rows']))
                    self.assertEqual(rom[p-0xc00000:p-0xc00000+stride],raw[q*stride:(q+1)*stride])
                cursor+=len(raw)
        self.assertEqual(cursor-DATA,39616)
        self.assertLessEqual(cursor,TABLE)

    def test_occupied_rom_lease_is_rejected_before_modification(self):
        rom=bytearray((self.baseline/'native/bor.sfc').read_bytes());rom[DATA+47]=1;before=bytes(rom)
        with self.assertRaisesRegex(ValueError,'OCCUPANCY_ROM_LEASE'):
            apply([],rom,{},self.phases,self.occupancy)
        self.assertEqual(bytes(rom),before)

    def test_original_foreground_blitter_and_175_byte_kernel_are_unchanged(self):
        sy=symbols(self.root/'native/publisher.sym');oldsy=symbols(self.baseline/'native/publisher.sym')
        rom=(self.root/'native/bor.sfc').read_bytes();old=(self.baseline/'native/bor.sfc').read_bytes()
        a=offset(sy['OnlineRowPointers']);b=offset(sy['OnlineCoverage']);end=b+rom[b:b+256].index(bytes.fromhex('a55a60'))+3
        oa=offset(oldsy['OnlineRowPointers'])
        self.assertEqual(rom[a:end],old[oa:oa+end-a])
        k=offset(sy['AstraOpaqueRow']);self.assertEqual(rom[k:k+175],emit().code)
        self.assertLess(sy['WarmPresenceDone'],sy['AstraOpaqueRow'])
        entry=offset(sy['WarmTestCoverage'])
        self.assertEqual(rom[entry:entry+3],b'\x20'+(sy['WarmSourcePresence']&65535).to_bytes(2,'little'))

    def test_native_pixels_world_noops_rejection_and_actual_dma(self):
        r=json.loads((self.root/'result.json').read_text());proof=certify(self.root,r)
        self.assertEqual(proof['source_snapshots_byte_identical'],18)
        self.assertLess(proof['after']['coverage_lookup_clocks'],proof['before']['coverage_lookup_clocks']/10)
        self.assertEqual(replay(self.root)['verified_vram_bytes'],18*65536)

    def test_native_admission_instrumentation_cannot_silently_drift(self):
        r=copy.deepcopy(json.loads((self.root/'result.json').read_text()))
        r['helper_measurements'][1]['kernel_calls']-=8
        with self.assertRaisesRegex(ValueError,'OCCUPANCY_NATIVE_ADMISSION_COUNT'):certify(self.root,r)


if __name__=='__main__':unittest.main()
