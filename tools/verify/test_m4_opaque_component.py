import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from astra_opaque_kernel import emit
from m4_opaque_component_publisher import capacity_bound
from m4_opaque_dma_replay import verify
from m4_online_component_evidence import costs
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset


class OpaqueIntegrationTests(unittest.TestCase):
    root=Path('out/byor-motu-opaque-warm-v4')

    def test_all_alignment_capacity_bound_fits_the_actual_arena(self):
        bound=capacity_bound(Path('out/astra-opaque-assets-v1'))
        self.assertEqual(bound['source_coverage_tile_bounds'],dict(select=85,idle=103,walk=111))
        self.assertEqual(bound['maximum_required_pairs'],707)
        self.assertLess(bound['maximum_required_pairs'],bound['capacity'])

    def test_assembler_emits_the_supplied_relocatable_kernel_exactly(self):
        native=self.root/'native';sy=symbols(native/'publisher.sym');rom=(native/'bor.sfc').read_bytes()
        at=offset(sy['AstraOpaqueRow'])
        self.assertEqual(rom[at:at+175],emit().code)

    def test_actual_sparse_dma_replays_full_physical_vram_and_directory(self):
        report=verify(self.root)
        self.assertEqual(report['verified_vram_bytes'],18*65536)
        self.assertEqual(sum(r['descriptors']==0 for r in report['epochs']),6)
        self.assertLess(max(r['bytes'] for r in report['epochs'][1:]),10000)

    def test_wrong_physical_home_identity_cannot_pass_directory_flags(self):
        path=self.root/'native/directory-00.bin';words=np.frombuffer(path.read_bytes(),dtype='<u2').copy()
        vram=(self.root/'native/vram-00.bin').read_bytes();hi=Path('out/byor-motu-online-v3/assets/high.chr').read_bytes()
        slot=next(i for i in range(596) if words[i]&0x8000 and vram[i*64:i*64+64]!=hi[i*64:i*64+64])
        words[slot]&=0x7fff
        read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:words.tobytes() if p==path else read(p)):
            with self.assertRaisesRegex(ValueError,'HOME_IDENTITY'):verify(self.root)

    def test_source_snapshots_are_byte_identical_to_the_scalar_reference(self):
        for epoch in range(18):
            self.assertEqual((self.root/f'native/world-{epoch:02d}.bin').read_bytes(),Path(f'out/byor-motu-online-v3/native/world-{epoch:02d}.bin').read_bytes())

    def test_noop_acknowledges_without_graphics_and_still_requires_fences(self):
        events=[dict(phase='OnlinePublish',clock=0),dict(phase='OnlineNoopComplete',clock=100)]
        row=costs(events)['epochs'][0]
        self.assertEqual((row['composition_clocks'],row['dma_clocks'],row['dma_bytes']),(0,0,0))
        events.insert(1,dict(phase='DMA:80:24:0',clock=20))
        with self.assertRaisesRegex(ValueError,'NOOP_DID_GRAPHICS'):costs(events)


if __name__=='__main__':unittest.main()
