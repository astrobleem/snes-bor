"""Source owner adapter identity, immutable latch and unchanged guard contracts."""
import unittest
from pathlib import Path
from source_safepoint import transform,LATCH,LATCH_EPOCH,movement_code
from m4_source_safepoint_native import audit_rom
from m4_opaque_component_publisher import transform as producer
from m4_input_controller_native import offset

class SafePointTests(unittest.TestCase):
    native=Path('out/byor-motu-source-safepoint-candidate-v5/native')
    def test_actual_rom_and_original_movement_instructions(self):
        r=audit_rom((self.native/'bor.sfc').read_bytes(),self.native)
        self.assertEqual(r['movement_instructions_identical'],119)
        self.assertLess(r['code'][1],0x39c000)
    def test_latch_is_header_padding_and_post_reads_are_immutable(self):
        self.assertEqual((LATCH,LATCH_EPOCH+2),(0x42d60c,0x42d620))
        s=(self.native/'publisher.pasm').read_text().splitlines();segment=s[s.index('NbPublishRefs:'):s.index('NbVisible:')]
        self.assertFalse(any('7FBA' in x or '8370' in x for x in segment))
        self.assertIn(' lda.l $42D61E',segment)
    def test_pre_ready_epoch_and_queue_checks_still_exist(self):
        s=(self.native/'publisher.pasm').read_text().splitlines()
        self.assertIn(' cmp.l $7FBA90',s);self.assertIn('NbAllPairsReady:',s)
        self.assertLess(s.index('NbGuard4:'),s.index(' jsr SpReadyBoundary'))
    def test_real_owner_no_constructor_no_recursive_publisher(self):
        s=movement_code();self.assertFalse(any('$398000' in x or 'LiveGroundBoot' in x for x in s))
        from actor_s5_entity_fixture import symbols
        from source_safepoint import SOURCE_SYM
        sy=symbols(SOURCE_SYM)
        self.assertIn(' jsl '+str(symbols(Path('src/main.sym'))['SourceInputController_Refresh']),s)
        self.assertIn(' jsl '+str(sy['LiveGroundSeal']),s)
    def test_not_enabled_without_accepted_backend(self):
        with self.assertRaisesRegex(ValueError,'REQUIRES_CONDITIONAL'):producer(Path('out/astra-opaque-assets-v1'),source_safepoint=True)
    def test_unrelated_code_and_assets_fail_mutation_audit(self):
        original=(self.native/'bor.sfc').read_bytes()
        for address in (0x398000,0x39c000,0x39d400,0x39e000,0xf43600):
            altered=bytearray(original);altered[address&0x3fffff if address>=0xc00000 else offset(address)]^=1
            with self.assertRaises(ValueError):audit_rom(altered,self.native)
