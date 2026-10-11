import copy,importlib.util,unittest
from raster_slot_refine import refine,verify_packets,score
from raster_row_slot_permutations import optimize
from test_raster_slot_layout import SlotLayoutTests


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class SlotRefinementTests(unittest.TestCase):
    def test_necessary_bank_window_is_inherited_and_verified_globally(self):
        from test_raster_slot_greedy import source_schedule
        from raster_bank_residency import favorable_span
        source=source_schedule();hint=optimize(source,1001,5,True,necessary_bank_window=33,range_encoding='coverage')
        result=refine(source,hint,1,1,1,2,range_encoding='coverage')
        report=result['physical_slot_refinement']
        self.assertEqual(report['necessary_bank_window_master_clocks'],33)
        self.assertTrue(report['full_frame_necessary_bank_window_verified'])
        self.assertTrue(all(favorable_span(row['updates'])<33 for row in result['trace'][1:]))
        bad=copy.deepcopy(hint);bad['physical_slot_layout']['necessary_bank_window_master_clocks']=32
        with self.assertRaisesRegex(ValueError,'HINT_NECESSARY_BANK_WINDOW'):refine(source,bad)

    def test_met_offline_target_does_not_claim_native_admission(self):
        source=SlotLayoutTests().schedule();hint=optimize(source,356,10,True)
        result=refine(source,hint,356,1,1,1)
        self.assertEqual(score(result),score(hint))
        self.assertEqual(result['physical_slot_refinement']['trials'],[])
        self.assertTrue(result['physical_slot_refinement']['target_window_met_by_all_packets'])
        self.assertFalse(result['native_presentation_proven'])
        self.assertFalse(result['physical_slot_refinement']['native_timing_admitted'])

    def test_packet_corruption_and_partial_proof_are_rejected(self):
        source=SlotLayoutTests().schedule();hint=optimize(source,356,10)
        broken=copy.deepcopy(hint)
        row=next(r for r in broken['prepared_dma_packets']if r['packets'])
        p=row['packets'][0];raw=bytearray.fromhex(p['data_hex']);raw[0]^=1;p['data_hex']=raw.hex()
        with self.assertRaisesRegex(ValueError,'PACKET_IDENTITY'):verify_packets(broken)
        from raster_bank_residency import restrict_interval
        with self.assertRaises(ValueError):refine(source,restrict_interval(hint,1,2))

    def test_full_frame_write_budget_is_preserved_and_invalid_hint_rejected(self):
        source=SlotLayoutTests().schedule();hint=optimize(source,356,10,True)
        peak=max(len(row['updates'])for row in hint['trace'][1:])
        result=refine(source,hint,356,1,1,1,peak)
        self.assertTrue(result['physical_slot_refinement']['full_frame_write_budget_verified'])
        self.assertEqual(result['physical_slot_refinement']['maximum_physical_writes_per_transfer_row'],peak)
        if peak:
            with self.assertRaisesRegex(ValueError,'HINT_WRITE_BUDGET'):
                refine(source,hint,356,1,1,1,peak-1)
        with self.assertRaisesRegex(ValueError,'WRITE_BUDGET_DOMAIN'):
            refine(source,hint,356,1,1,1,121)


if __name__=='__main__':unittest.main()
