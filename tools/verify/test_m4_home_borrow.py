"""Actual assets, native binary boundaries and fail-closed admission contracts."""
import unittest
import tempfile,json
from pathlib import Path
from home_borrow import transform,JOURNAL,END
from m4_home_borrow_capacity import inventory
from m4_home_borrow_native import audit_rom,BASE
from m4_opaque_component_publisher import transform as publisher
from m4_input_controller_native import offset

class HomeBorrowTests(unittest.TestCase):
    native=Path('out/byor-motu-home-borrow-build-v5/native')
    def test_real_physical_inventory(self):
        r=inventory(Path('out/byor-motu-consecutive-up-v2'))
        self.assertEqual((r['invalid_count'],r['valid_count']),(42,20))
        self.assertEqual(len(r['homes']),596)
        self.assertTrue(all(not h['display_high_references'] and not h['display_low_references'] and not h['pending_physical_references'] and not h['reserved'] for h in r['homes'] if h['borrowable']))
    def test_real_assembled_code_and_source_owner(self):
        r=audit_rom((self.native/'bor.sfc').read_bytes(),self.native)
        self.assertEqual(r['movement_instructions_identical'],119)
        self.assertGreater(r['branches_verified'],250)
        self.assertTrue(r['all_other_rom_bytes_identical'])
    def test_journal_lease_avoids_active_records_latch_queue_and_physics(self):
        self.assertEqual((JOURNAL,END),(0x42d710,0x42d790))
        self.assertGreater(JOURNAL,0x42d6f2);self.assertLess(END,0x42d800)
    def test_bad_backend_selection_fails_before_asset_access(self):
        with self.assertRaisesRegex(ValueError,'REQUIRES_SAFEPOINT'):
            publisher(Path('does-not-exist'),nonblank_home_borrow=True)
    def test_transform_rejects_missing_guard_and_duplicate_application(self):
        original=(BASE/'publisher.pasm').read_text().splitlines()
        with self.assertRaises(ValueError):transform([s for s in original if s!='NbAllPairsReady:'])
        with self.assertRaises(ValueError):transform(transform(original))
    def test_kernel_asset_and_other_rom_mutations_rejected(self):
        original=(self.native/'bor.sfc').read_bytes()
        for pc in (0x39c000,0x39d400,0x39e000,0x39e200,0xf43000,0xf43600,0xe00000):
            altered=bytearray(original);altered[pc-0xc00000 if pc>=0xc00000 else offset(pc)]^=1
            with self.assertRaises(ValueError):audit_rom(altered,self.native)
    def test_restore_fence_precedes_native_validity_clear(self):
        text=(self.native/'publisher.pasm').read_text()
        section=text[text.index('BhRollback:'):text.index('BhCommit:')]
        self.assertLess(section.index(' jsr NbFlushQueue'),section.index('BhRestorationFenced:'))
        self.assertLess(section.index('BhRestorationFenced:'),section.index(' and #$7FFF'))
    def test_actual_native_validity_clear_and_pixel_evidence(self):
        from m4_home_borrow_evidence import certify
        r=certify(Path('out/byor-motu-home-borrow-early-v7'))
        self.assertEqual([e['data'][1] for e in r['validity_clear_events']],['204'])
        self.assertTrue(any(e['home']==204 and e['rollback'] for e in r['backdrop_restorations']))
        self.assertEqual(r['pixel_mismatches'],0)
    def test_observer_errors_fail_closed_before_rom_admission(self):
        from m4_home_borrow_evidence import certify
        with tempfile.TemporaryDirectory(prefix='motu-observer-',dir='out') as path:
            folder=Path(path);self.assertTrue(folder.resolve().is_relative_to(Path('out').resolve()));(folder/'native').mkdir()
            (folder/'contract.json').write_text('{}');(folder/'fields.json').write_text('[]')
            (folder/'native/mesen.log').write_text('callback_owner.lua:99: callback failed\n')
            with self.assertRaisesRegex(ValueError,'LUA_OBSERVER_ERROR'):certify(folder)

if __name__=='__main__':unittest.main()
