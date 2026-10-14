"""Focused bounded transaction, ROM lease and independent planar tests."""
import json,unittest
from pathlib import Path
import numpy as np
from nonblank_slice import transform
from m4_nonblank_component_native import audit_rom,decode_vram
from m4_input_controller_native import offset
from m4_opaque_component_publisher import transform as producer

class NonblankTests(unittest.TestCase):
    native=Path('out/byor-motu-nonblank-v5/native')
    def test_actual_assembled_lease_and_control_integrity(self):
        result=audit_rom((self.native/'bor.sfc').read_bytes(),self.native)
        self.assertLess(result['end'],0x39c000)
        self.assertTrue(result['all_assets_kernels_and_other_banks_unchanged'])
    def test_rom_mutations_fail_closed(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0x39d000,0x39d400,0x39e000,0x39e200,0x39f000,0xf43000,0xf43600):
            with self.subTest(address=address):
                changed=bytearray(original);changed[(address&0x3fffff) if address>=0xc00000 else offset(address)]^=1
                with self.assertRaises(ValueError):audit_rom(changed,self.native)
    def test_transform_requires_exact_control(self):
        lines=Path('out/byor-motu-rect-map-v1/native/publisher.pasm').read_text().splitlines()
        self.assertEqual(transform(lines),(self.native/'publisher.pasm').read_text().splitlines())
        with self.assertRaises(ValueError):transform([s for s in lines if s!=' jsr WarmCompare'])
    def test_backend_requires_certified_component_options(self):
        with self.assertRaises(ValueError):producer(Path('out/astra-opaque-assets-v1'),nonblank_slice=True)
    def test_independent_decoder_matches_retained_oracles(self):
        base=Path('out/byor-motu-rect-map-v1/native')
        for i in (0,1,2):
            actual=decode_vram((base/f'vram-{i:02d}.bin').read_bytes(),(base/f'cgram-{i:02d}.bin').read_bytes())
            self.assertEqual(actual.astype('<u2').tobytes(),(base/f'expected-{i:02d}.rgb555').read_bytes())
    def test_decoder_rejects_mixed_high_low_map(self):
        base=Path('out/byor-motu-rect-map-v1/native');v=bytearray((base/'vram-00.bin').read_bytes());v[63488]^=1
        with self.assertRaises(ValueError):decode_vram(v,(base/'cgram-00.bin').read_bytes())
