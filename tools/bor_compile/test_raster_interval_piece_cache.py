import unittest
import numpy as np
from raster_interval_piece_cache import optimize
from raster_slot_greedy import demand
import test_raster_piece_bank_cache as fixtures


class IntervalCacheTests(unittest.TestCase):
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
