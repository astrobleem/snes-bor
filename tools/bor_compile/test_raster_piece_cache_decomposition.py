import copy,unittest
import numpy as np
import test_raster_word_bank_balance as fixtures
from raster_slot_greedy import demand
from raster_piece_cache_decomposition import search
from raster_bank_residency import relaxed_bound


class DecompositionTests(unittest.TestCase):
    def test_resume_checks_duals_and_keeps_prior_assignments(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        first=search(source,iterations=2,time_limit=10,master_seconds=1)
        saved=first['piece_cache_decomposition']
        resumed=search(source,iterations=2,time_limit=10,master_seconds=1,resume_report=saved)
        report=resumed['piece_cache_decomposition']
        self.assertEqual(report['restored_certified_cuts'],len(saved['certified_master_cuts']))
        self.assertTrue(set(map(tuple,saved['evaluated_assignments']))<=set(map(tuple,report['evaluated_assignments'])))
        for a,b in zip(demand(source)[2],demand(resumed)[2]):np.testing.assert_array_equal(a,b)
        bad=copy.deepcopy(saved);bad['cache_basis_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'SOURCE_BASIS'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['inequality_dual']=[[0,1.]]
        with self.assertRaisesRegex(ValueError,'DUAL_DOMAIN'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['inequality_dual']=[[0,-100.]]
        with self.assertRaisesRegex(ValueError,'DUAL_STATIONARITY'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['upper_dual']=[[saved['cache_lp_variables']-1,-1.]]
        with self.assertRaisesRegex(ValueError,'UNBOUNDED_PEAK_DUAL'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['upper_dual']=[[0,-100.]]
        # A nonpositive bound multiplier alone is valid but weak, so accepts.
        search(source,iterations=1,time_limit=5,resume_report=bad)
        bad=copy.deepcopy(saved);bad['evaluated_assignments'][0][0]=8
        with self.assertRaisesRegex(ValueError,'ASSIGNMENT_DOMAIN'):
            search(source,resume_report=bad)

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

    def test_row_word_masks_keep_source_pixels_and_full_geometry_limits(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=3,time_limit=10,master_seconds=1,
                      row_word_masks=True)
        def pixels(frame):
            return {(p['actor'],p['x']+x,p['y']+y):int(c)
                    for p,image in zip(frame['pieces'],demand(frame)[2])
                    for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertTrue(result['piece_cache_decomposition']['row_word_masks'])
        self.assertLessEqual(result['geometry']['oam_entries'],128)
        self.assertLessEqual(result['geometry']['peak_sprites'],32)
        self.assertLessEqual(result['geometry']['peak_tile_slivers'],34)
        self.assertFalse(result['piece_cache_decomposition']['native_timing_admitted'])


if __name__=='__main__':unittest.main()
