import copy
import json
from pathlib import Path
import unittest
from m4_direct_pair_evidence import audit_rom,certify,BASE_SHA
from m4_opaque_dma_replay import verify
import hashlib


class DirectNativeTests(unittest.TestCase):
    root=Path('out/byor-motu-direct-pair-v1')

    def test_default_control_still_builds_byte_identically(self):
        self.assertEqual(hashlib.sha256(Path('out/byor-motu-direct-control-rebuild-v1/native/bor.sfc').read_bytes()).hexdigest(),BASE_SHA)

    def test_only_two_call_operands_and_the_new_code_lease_change(self):
        contract=json.loads((self.root/'contract.json').read_text());rom=(self.root/'native/bor.sfc').read_bytes()
        layout=audit_rom(rom,contract)
        self.assertEqual(len(layout['changed_calls']),2)
        self.assertTrue(layout['fused_tile_kernel_unchanged'])
        for at in (0x343000,57*32768+0x6200,57*32768+0x6000):
            modified=bytearray(rom);modified[at]^=1
            with self.assertRaisesRegex(ValueError,'UNRELATED_ROM_CHANGE'):audit_rom(modified,contract)

    def test_native_direct_descriptors_replay_complete_vram(self):
        report=verify(self.root)
        self.assertEqual(report['verified_vram_bytes'],18*65536)
        result=json.loads((self.root/'result.json').read_text());proof=certify(self.root,result)
        self.assertEqual(proof['classification'],'BYOR_MOTU_DIRECT_PAIR_DMA_PASS')
        self.assertEqual(proof['paired_epochs'][17]['direct']['calls'],126)
        self.assertEqual(proof['paired_epochs'][17]['after']['dma_descriptors'],316)

    def test_noops_are_graphics_free_and_staging_cannot_silently_resume(self):
        result=json.loads((self.root/'result.json').read_text());proof=certify(self.root,result)
        self.assertEqual([p['epoch'] for p in proof['paired_epochs'] if p['render_noop']],[3,5,7,11,12,13])
        changed=copy.deepcopy(result);changed['direct_measurements'][1]['stage_calls']=1
        with self.assertRaisesRegex(ValueError,'STAGE_OR_FENCE'):certify(self.root,changed)

    def test_negligible_cpu_change_is_not_a_performance_pass(self):
        result=json.loads((self.root/'result.json').read_text())
        baseline=json.loads(Path('out/byor-motu-tile-fusion-v2/result.json').read_text())
        for before,after in zip(baseline['measured_costs']['epochs'],result['measured_costs']['epochs']):
            if not after.get('render_noop'):after['production_clocks']=before['production_clocks']-1
        self.assertEqual(certify(self.root,result)['classification'],'DIRECT_PAIR_DMA_NO_SPEEDUP')


if __name__=='__main__':unittest.main()
