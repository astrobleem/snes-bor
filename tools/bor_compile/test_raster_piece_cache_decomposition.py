import unittest
import numpy as np
import test_raster_word_bank_balance as fixtures
from raster_slot_greedy import demand
from raster_piece_cache_decomposition import search
from raster_bank_residency import relaxed_bound


class DecompositionTests(unittest.TestCase):
    def test_dual_cuts_and_rebuilt_operands(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=4,time_limit=10,master_seconds=1)
        report=result['piece_cache_decomposition']
        self.assertTrue(report['iterations'])
        self.assertLessEqual(report['best_fractional_cache_bound'],1)
        self.assertAlmostEqual(relaxed_bound(result,lookahead=16,time_limit=5)['peak_write_lower_bound'],
                               report['best_fractional_cache_bound'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(report['physical_transfer_admitted'])

    def test_fixed_domains_do_not_change(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        result=search(source,iterations=3,time_limit=10,master_seconds=1)
        self.assertEqual([p['bank']for p in result['pieces']],[p['bank']for p in source['pieces']])

    def test_dma_objective_replays_operands_without_timing_admission(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=2,time_limit=10,master_seconds=1,
                      objective_kind='dma-window',write_budget=21)
        report=result['piece_cache_decomposition']
        self.assertEqual(report['objective_kind'],'dma-window')
        self.assertEqual(report['write_budget'],21)
        self.assertIsNotNone(report['best_fractional_dma_span_bound'])
        for iteration in report['iterations']:
            self.assertAlmostEqual(iteration['validated_dual_lower_bound'],
                                   iteration['peak_dma_span_lower_bound'])
            self.assertLessEqual(iteration['maximum_primal_violation'],1e-6)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(report['physical_transfer_admitted'])
        self.assertFalse(report['native_timing_admitted'])

    def test_invalid_dma_objective_rejected(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        for kwargs in ({'objective_kind':'unknown'},{'write_budget':121},
                       {'write_budget':True}):
            with self.assertRaisesRegex(ValueError,'OBJECTIVE_DOMAIN'):
                search(source,**kwargs)


if __name__=='__main__':unittest.main()
