import unittest
import numpy as np
from raster_interval_piece_cache import optimize
from raster_slot_greedy import demand
import test_raster_piece_bank_cache as fixtures


class IntervalCacheTests(unittest.TestCase):
    def test_row_masks_replay_source_and_enforce_full_object_count(self):
        source=fixtures.PieceBankCacheTests().fixture()
        result=optimize(source,time_limit=5,write_budget=0,lookahead=0,maximum_loads=1,row_word_masks=True,maximum_masks_per_piece=2)
        def pixels(frame):return{(p['actor'],p['y']+int(y),p['x']+int(x)):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertEqual(result['geometry']['oam_entries'],4)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertTrue(result['interval_piece_cache']['fixed_bank_per_compiled_oam_entry'])
        self.assertFalse(result['prepared_dma_partition_bound_enforced'])
        rejected=optimize(source,time_limit=5,write_budget=0,lookahead=0,maximum_loads=1,row_word_masks=True,maximum_masks_per_piece=1)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')

    def test_reload_limit_is_a_restricted_family_not_raster_failure(self):
        source=fixtures.PieceBankCacheTests().fixture()
        single=optimize(source,time_limit=5,write_budget=1,lookahead=0,maximum_loads=1)
        self.assertEqual(single['solver_status'],'INFEASIBLE')
        self.assertFalse(single['universal_raster_rejected'])
        result=optimize(source,time_limit=5,write_budget=1,lookahead=0,maximum_loads=2)
        self.assertEqual(result['peak_scheduled_writes'],1)
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(result['prepared_dma_partition_bound_enforced'])
        self.assertFalse(result['interval_piece_cache']['native_timing_admitted'])


if __name__=='__main__':unittest.main()
