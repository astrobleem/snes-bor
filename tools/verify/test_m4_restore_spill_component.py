"""Actual emitted spill source, strict binary mutations and opt-in guards."""
import unittest
from pathlib import Path
from restore_spill import transform
from m4_restore_spill_native import audit_rom,audit_branches
from m4_restore_spill_capacity_native import audit as capacity_audit
from m4_opaque_component_publisher import transform as producer
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset

class SpillIntegration(unittest.TestCase):
    native=Path('out/byor-motu-restore-spill-regression-v1/native')
    def test_exact_actual_generated_splice(self):
        expected=transform(Path('out/byor-motu-batch-rescue-v1/native/publisher.pasm').read_text().splitlines())
        self.assertEqual(expected,(self.native/'publisher.pasm').read_text().splitlines())
        self.assertTrue(audit_rom((self.native/'bor.sfc').read_bytes(),self.native)['queue_unchanged'])
    def test_branch_bytes_and_ranges(self):
        self.assertGreater(audit_branches((self.native/'publisher.pasm').read_text().splitlines(),symbols(self.native/'publisher.sym'),(self.native/'publisher.bin').read_bytes()),100)
    def test_immutable_other_rom_bytes(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0x398000,0x39c000,0x39d400,0x39e000,0x39e200,0xf43000,0xf43600):
            altered=bytearray(original);altered[address&0x3fffff if address>=0xc00000 else offset(address)]^=1
            with self.assertRaises(ValueError):audit_rom(altered,self.native)
    def test_disabled_option_retains_certified_rom(self):
        from m4_nonblank_component_native import sha
        self.assertEqual(sha(Path('out/byor-motu-restore-spill-disabled-v1/native/bor.sfc').read_bytes()),'e710074d80cd6ad2354664956c7d0be867008c13a98006042f51d6fc9bd091ec')
    def test_opt_in_requires_batch_backend(self):
        with self.assertRaisesRegex(ValueError,'SPILL_REQUIRES_BATCH'):producer(Path('out/astra-opaque-assets-v1'),nonblank_restore_spill=True)
    def test_new_success_fixture_is_separately_audited(self):
        native=Path('out/byor-motu-restore-spill-capacity-v1/native')
        self.assertTrue(capacity_audit((native/'bor.sfc').read_bytes(),native)['kernels_assets_and_other_banks_unchanged'])
