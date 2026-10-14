"""Focused compiled candidate mutation and integration checks."""
import unittest
from pathlib import Path
from m4_rect_map_audit import audit,BASE_SHA
from m4_input_controller_native import offset
from m4_opaque_component_publisher import transform

class CandidateTests(unittest.TestCase):
    native=Path('out/byor-motu-rect-map-v1/native')
    base=Path('out/byor-motu-direct-pair-v1/native')
    def test_actual_poppy_layout_and_unchanged_leases(self):
        result=audit((self.native/'bor.sfc').read_bytes(),self.native,self.base)
        self.assertEqual(result['gap_before_direct_bytes'],319)
        self.assertTrue(result['full_preflight_clone_unchanged'])
    def test_unrelated_asset_kernel_and_direct_mutations_rejected(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0xf43000,0xf43600,0x39d400,0x39e000,0x39e200,0x39f000):
            with self.subTest(address=address):
                changed=bytearray(original);changed[(address & 0x3fffff) if address>=0xc00000 else offset(address)]^=1
                with self.assertRaises(ValueError):audit(changed,self.native,self.base)
    def test_capability_dependencies_fail_closed(self):
        import inspect
        self.assertIn('rect_map_diff',inspect.signature(transform).parameters)
        with self.assertRaises(ValueError):transform(Path('out/astra-opaque-assets-v1'),rect_map_diff=True)
