"""Actual retained source contract, predictor binary and immutable leases."""
import unittest
from pathlib import Path
from early_capacity import transform,EarlyCapacityContractError
from m4_early_capacity_native import audit_rom,audit_capacity
from m4_input_controller_native import offset
from m4_opaque_component_publisher import transform as producer

class NativeIntegration(unittest.TestCase):
    native=Path('out/byor-motu-early-capacity-regression-v1/native')
    def test_actual_spill_source_and_cold_reset_are_supported(self):
        original=Path('out/byor-motu-restore-spill-regression-v1/native/publisher.pasm').read_text().splitlines()
        self.assertLess(original.index(' sta.l $42D606'),original.index('NbBeginRetry:'))
        self.assertEqual(transform(original),(self.native/'publisher.pasm').read_text().splitlines())
    def test_cold_reset_does_not_authorize_missing_retry_reset(self):
        original=Path('out/byor-motu-restore-spill-regression-v1/native/publisher.pasm').read_text().splitlines()
        at=original.index(' sta.l $42D606',original.index('NbBeginRetry:'));del original[at]
        with self.assertRaises(EarlyCapacityContractError):transform(original)
    def test_retry_reset_must_be_zero(self):
        original=Path('out/byor-motu-restore-spill-regression-v1/native/publisher.pasm').read_text().splitlines()
        at=original.index(' sta.l $42D606',original.index('NbBeginRetry:'));original[at-1]=' lda #1'
        with self.assertRaises(EarlyCapacityContractError):transform(original)
    def test_actual_poppy_code_and_branches(self):
        r=audit_rom((self.native/'bor.sfc').read_bytes(),self.native)
        self.assertLess(r['end'],0x39c000);self.assertTrue(r['queue_unchanged'])
        self.assertGreater(r['branch_instructions_verified'],100)
    def test_nontransaction_code_assets_cannot_mutate(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0x398000,0x39c000,0x39d400,0x39e000,0x39e200,0xf43000,0xf43600):
            altered=bytearray(original);altered[address&0x3fffff if address>=0xc00000 else offset(address)]^=1
            with self.assertRaises(ValueError):audit_rom(altered,self.native)
    def test_disabled_flag_retains_certified_spill_rom(self):
        from m4_nonblank_component_native import sha
        self.assertEqual(sha(Path('out/byor-motu-early-capacity-disabled-v1/native/bor.sfc').read_bytes()),'05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d')
    def test_requires_restoration_spill_backend(self):
        with self.assertRaisesRegex(ValueError,'REQUIRES_RESTORE_SPILL'):producer(Path('out/astra-opaque-assets-v1'),early_capacity_admission=True)
    def test_source_owned_success_fixture_separately_audited(self):
        n=Path('out/byor-motu-early-capacity-success-v1/native')
        self.assertTrue(audit_capacity((n/'bor.sfc').read_bytes(),n)['all_other_rom_bytes_identical'])
