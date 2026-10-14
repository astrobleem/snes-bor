import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from m4_tile_fusion_evidence import audit_rom,certify
from m4_opaque_dma_replay import verify as replay


class FusedNativeTests(unittest.TestCase):
    root=Path('out/byor-motu-tile-fusion-v2')

    def test_assembled_code_and_all_existing_rom_leases(self):
        contract=json.loads((self.root/'contract.json').read_text())
        report=audit_rom((self.root/'native/bor.sfc').read_bytes(),contract)
        self.assertEqual(report['bytes'],289)
        self.assertEqual(report['remaining_to_nmi'],3295)
        self.assertTrue(report['old_kernel_byte_identical'])
        self.assertTrue(report['all_bytes_outside_code_bank_identical'])

    def test_changed_refcount_rom_lease_and_nmi_cannot_pass_audit(self):
        contract=json.loads((self.root/'contract.json').read_text());rom=(self.root/'native/bor.sfc').read_bytes()
        for at,reason in ((0x343000,'OUTSIDE_CODE_BANK'),(57*32768+0x7000,'NMI_CORRUPTION'),(57*32768+0x6000,'REFERENCE_KERNEL_CORRUPTION')):
            corrupted=bytearray(rom);corrupted[at]^=1
            with self.subTest(at=at),self.assertRaisesRegex(ValueError,reason):audit_rom(corrupted,contract)

    def test_complete_native_control_identity_and_paired_improvement(self):
        result=json.loads((self.root/'result.json').read_text());report=certify(self.root,result)
        self.assertEqual(report['classification'],'BYOR_MOTU_FUSED_TILE_NATIVE_PASS')
        self.assertEqual(len(report['paired_epochs']),18)
        self.assertGreater(report['composition_reduction_percent'],5)
        self.assertEqual(report['byte_identical_source_snapshots'],18)
        self.assertEqual(replay(self.root)['verified_vram_bytes'],18*65536)
        for p in report['paired_epochs']:
            if p['render_noop']:
                self.assertEqual((p['tiles'],p['rows'],p['after']['ms']['composition'],p['after']['ms']['dma'],p['after']['ms']['forced_blank']),(0,0,0,0,0))

    def test_new_row_tile_instrumentation_is_required(self):
        result=copy.deepcopy(json.loads((self.root/'result.json').read_text()))
        result['helper_measurements'][1]['tile_calls']-=1
        with self.assertRaisesRegex(ValueError,'NATIVE_CALL_COUNTS'):certify(self.root,result)
        result['helper_measurements'][1]['tile_calls']+=1
        result['helper_measurements'][1]['legacy_row_calls']=1
        with self.assertRaisesRegex(ValueError,'NATIVE_CALL_COUNTS'):certify(self.root,result)

    def test_resident_vram_drift_cannot_be_excused_as_unused_boot_data(self):
        import numpy as np
        path=self.root/'native/vram-00.bin';vram=bytearray(path.read_bytes())
        refs=np.frombuffer((self.root/'native/directory-00.bin').read_bytes(),dtype='<u2')
        slot=next(i for i,r in enumerate(refs) if r&0x3fff)
        vram[slot*64]^=1;read=Path.read_bytes
        result=json.loads((self.root/'result.json').read_text())
        with patch.object(Path,'read_bytes',lambda p:bytes(vram) if p==path else read(p)):
            with self.assertRaisesRegex(ValueError,'resident_vram'):certify(self.root,result)


if __name__=='__main__':unittest.main()
