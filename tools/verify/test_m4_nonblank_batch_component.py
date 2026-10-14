"""Compiled queue ABI, forbidden ROM mutations and retained capacity witness."""
import json,unittest
from pathlib import Path
from m4_nonblank_batch_native import audit_rom
from m4_input_controller_native import offset
from nonblank_batch_rescue import transform
from m4_opaque_component_publisher import transform as producer

class IntegrationTests(unittest.TestCase):
    native=Path('out/byor-motu-batch-rescue-v1/native')
    def test_actual_poppy_placement_and_immutable_control(self):
        result=audit_rom((self.native/'bor.sfc').read_bytes(),self.native)
        self.assertLess(result['end'],0x39c000)
        self.assertEqual(result['iram_queue'],[0x3500,0x36e0])
    def test_no_unexpanded_python_expression_in_assembly(self):
        lines=transform(Path('out/byor-motu-nonblank-v5/native/publisher.pasm').read_text().splitlines())
        self.assertFalse(any('{' in s or '}' in s for s in lines))
        self.assertIn(' adc #$3500',lines)
    def test_old_routines_assets_and_kernels_fail_closed(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0x398000,0x39c000,0x39d400,0x39e000,0x39e200,0x39f000,0xf43000,0xf43600):
            with self.subTest(address=address):
                altered=bytearray(original);altered[(address&0x3fffff) if address>=0xc00000 else offset(address)]^=1
                with self.assertRaises(ValueError):audit_rom(altered,self.native)
    def test_requires_established_nonblank_backend(self):
        with self.assertRaises(ValueError):producer(Path('out/astra-opaque-assets-v1'),nonblank_batch_rescue=True)
    def test_real_exact_filter_adds_restoration_homes(self):
        evidence=json.loads(Path('out/byor-motu-batch-rescue-v1/capacity-validation.json').read_text())
        self.assertEqual((evidence['conservative_actor'],evidence['exact_actor'],evidence['occluded']),(96,88,8))
        self.assertEqual((len(evidence['conservative_restoration_homes']),len(evidence['exact_restoration_homes'])),(30,34))
        self.assertEqual((evidence['conservative_slots'],evidence['exact_slots'],evidence['free_tail']),(126,122,124))
