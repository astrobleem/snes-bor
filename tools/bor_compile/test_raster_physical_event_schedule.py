import copy,unittest
import numpy as np
import test_raster_slot_layout as fixtures
from raster_physical_event_schedule import optimize
from raster_physical_write_shift import shift
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets


class PhysicalEventScheduleTests(unittest.TestCase):
    def schedule(self):
        source=fixtures.SlotLayoutTests().schedule()
        source['physical_slot_layout']=dict(all_packet_cgram_identities_verified=True)
        source['prepared_dma_packets']=[dict(scanline=y,packets=[],prepared_commit_span=0)for y in range(16)]
        source['prepared_dma_packets'][1]['packets']=[dict(cgram_word_address=129,word_count=1,data_hex='e003')]
        source['prepared_dma_packets'][2]=dict(scanline=2,packets=[dict(cgram_word_address=129,word_count=1,data_hex='1f00'),dict(cgram_word_address=147,word_count=1,data_hex='0000')],prepared_commit_span=40)
        return source

    def test_exact_restricted_failure_and_valid_witness(self):
        source=self.schedule();before=copy.deepcopy(source)
        rejected=optimize(source,window=33,time_limit=5,lookahead=15)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        self.assertFalse(rejected['universal_raster_rejected'])
        result=optimize(source,window=41,time_limit=5,lookahead=15)
        self.assertIn(result['physical_event_schedule']['solver_status'],['OPTIMAL','FEASIBLE'])
        self.assertEqual(source,before);self.assertEqual(source['piece_pixel_masks'],result['piece_pixel_masks'])
        self.assertEqual(source['pieces'],result['pieces']);verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(result['physical_event_schedule']['native_timing_admitted'])

    def test_external_event_timing_cannot_overwrite_a_required_pixel(self):
        source=self.schedule()
        with self.assertRaisesRegex(AssertionError,'WRITE_SHIFT_REQUIRED_SLOT_IDENTITY'):
            shift(source,iterations=0,event_lines=[2,3,2])


if __name__=='__main__':unittest.main()
