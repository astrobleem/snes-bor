import unittest
import numpy as np
from raster_bank_order import optimize
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from test_raster_slot_greedy import source_schedule


class BankOrderTests(unittest.TestCase):
    def test_exhaustive_eligible_trace_order_preserves_pixels_and_packets(self):
        source=source_schedule();source['bank_residency']={'peak_optimistic_prepared_span':999}
        result=optimize(source);verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(result['optimistic_bank_order']['permutations_evaluated'],576)
        self.assertFalse(result['optimistic_bank_order']['native_timing_admitted'])
        self.assertNotIn('bank_residency',result)
        self.assertEqual(result['input_bank_residency']['peak_optimistic_prepared_span'],999)
        self.assertIsNone(result['prepared_dma_window_master_clocks'])

    def test_locked_banks_cannot_be_relabelled(self):
        source=source_schedule()
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        result=optimize(source)
        self.assertEqual([p['bank']for p in result['pieces']],[p['bank']for p in source['pieces']])
        self.assertLess(result['optimistic_bank_order']['permutations_evaluated'],576)


if __name__=='__main__':unittest.main()
