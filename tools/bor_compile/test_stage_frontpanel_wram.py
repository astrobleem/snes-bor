"""Actual queue/include-closure regression; no assembly, pack or native run."""
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from compiler import ROOT
import queue_abi
import stage_frontpanel_wram as wram


class FrontpanelWramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts=wram.include_closure(ROOT)
        cls.module=(ROOT/'src/core/stage_frontpanel_bg2.pasm').resolve()

    def changed(self,name,value):
        texts=dict(self.texts)
        for path,text in texts.items():
            texts[path]=re.sub(r'(^\s*'+name+r'\s*=\s*)(\$[0-9a-fA-F]+|\d+)',
                              lambda m:m[1]+f'${value:X}',text,flags=re.M)
        return texts

    def test_exact_allocation_extents_bank_and_unchanged_queue_arena(self):
        result=wram.allocation_proof(texts=self.texts)
        self.assertEqual((result['block_start'],result['block_end_exclusive']), (0x7EE020,0x7EEAB6))
        self.assertEqual((result['allocated_bytes'],result['span_bytes'],result['dma_bank']),(2640,2710,0x7E))
        self.assertEqual((queue_abi.SPEC['arena_base'],queue_abi.SPEC['arena_end_exclusive']), (0x7F9200,0x7FA000))
        self.assertEqual(queue_abi.TARGET_CAPACITY,255)

    def test_real_queue_guard_current_plan_and_max_dynamic_capacity(self):
        current=json.loads((ROOT/'src/generated/queue_abi.json').read_text())
        self.assertEqual(queue_abi.assert_layout(ROOT,current)['status'],'PASS')
        maximum=queue_abi.plan_build([dict(project='fixture',set='Normal',stage=22,source_path='fixture',packed_records=255)])
        self.assertEqual(queue_abi.assert_layout(ROOT,maximum)['status'],'PASS')

    def test_original_history_collision_is_rejected_by_real_queue_guard(self):
        real=Path.read_text
        def old(path,*a,**kw):
            text=real(path,*a,**kw)
            return text.replace('StageFp_BG2History = $7EE100','StageFp_BG2History = $7F9200') if path.resolve()==self.module else text
        plan=json.loads((ROOT/'src/generated/queue_abi.json').read_text())
        with patch.object(Path,'read_text',old),self.assertRaisesRegex(ValueError,'QUEUE_WRAM_OVERLAP'):
            queue_abi.assert_layout(ROOT,plan)

    def test_all_private_buffers_are_checked_not_only_history(self):
        for name in ('StageFp_BG2TileBuf','StageFp_BG2ColBuf','StageFp_BG2State',
                     'StageFp_BG2History','StageFp_BG2Refs','StageFp_BG2Columns'):
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'OUTSIDE_AUDITED_GAP'):
                wram.allocation_proof(texts=self.changed(name,0x7F9200))

    def test_vm_growth_guard_growth_and_trace_move_are_rejected(self):
        for name,value in [('VM_CODE_MAX',0x9000),('VM_GUARD_LEN',0x100),('G12_AnimTrace_Ring',0x7EEA00)]:
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'OUTSIDE_AUDITED_GAP'):
                wram.allocation_proof(texts=self.changed(name,value))

    def test_wrong_dma_bank_and_foreign_owner_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'DMA_BANK'):
            wram.allocation_proof(texts=self.changed('StageFp_BG2TileBank',0x7F))
        texts=dict(self.texts);texts[ROOT/'src/core/foreign_fixture.pasm']='Other = $7EE800\n'
        with self.assertRaisesRegex(ValueError,'FOREIGN_OWNER'):wram.allocation_proof(texts=texts)

    def test_queue_spec_overlap_and_internal_buffer_overlap_rejected(self):
        spec=dict(queue_abi.SPEC,arena_base=0x7EE000,arena_end_exclusive=0x7EF000)
        with self.assertRaisesRegex(ValueError,'WRAM_OVERLAP'):wram.allocation_proof(texts=self.texts,queue_spec=spec)
        with self.assertRaisesRegex(ValueError,'WRAM_OVERLAP'):
            wram.allocation_proof(texts=self.changed('StageFp_BG2ColBuf',0x7EE040))


if __name__=='__main__':unittest.main()
