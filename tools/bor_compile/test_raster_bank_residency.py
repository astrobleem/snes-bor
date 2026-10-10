import unittest
import numpy as np
from raster_bank_residency import optimize,favorable_span,relaxed_bound,constrain_dp,constrain_adjacent
from raster_cgram_packets import optimistic_dma_span
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class ResidencyTests(unittest.TestCase):
    def test_cache_solution_preserves_fixed_bank_pixels_and_black(self):
        source=source_schedule();result=optimize(source,write_budget=2,lookahead=0,time_limit=10)
        self.assertEqual(result['pieces'],source['pieces'])
        self.assertLessEqual(result['peak_scheduled_writes'],2)
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        self.assertFalse(result['bank_residency']['physical_slot_schedule_proven'])
        self.assertFalse(result['bank_residency']['native_timing_admitted'])

    def test_one_write_cannot_replace_two_full_banks_at_once(self):
        result=optimize(source_schedule(),write_budget=1,lookahead=0,time_limit=10)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_invalid_budget_rejected(self):
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_DOMAIN'):optimize(source_schedule(),write_budget=-1)

    def test_independent_partition_bound_matches_existing_unlimited_dp(self):
        for counts in ([1,1,1,0,0,0,0,0],[15]*8,[2,0,3,0,1,0,0,4],[0]*8):
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            expected=max(0,optimistic_dma_span(updates)['best_partition_span_master_clocks']-8)
            self.assertEqual(favorable_span(updates,8),expected)
            self.assertGreaterEqual(favorable_span(updates,4),expected)

    def test_fractional_bound_has_matching_primal_dual_and_known_peak(self):
        result=relaxed_bound(source_schedule(),lookahead=0)
        self.assertAlmostEqual(result['peak_write_lower_bound'],2)
        self.assertAlmostEqual(result['validated_dual_lower_bound'],2)
        self.assertLessEqual(result['maximum_dual_residual'],1e-6)

    def test_computed_cp_partition_matches_independent_dp_at_boundary(self):
        from ortools.sat.python import cp_model
        for counts in ([1,1,1,0,0,0,0,0],[15]*8,[2,0,3,0,1,0,0,4],[0]*8,[3,3,3,3,3,3,3,3]):
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)];span=favorable_span(updates,4)
            for window in ([span,span+1]if span else[1]):
                model=cp_model.CpModel();values=[model.new_constant(n)for n in counts]
                active=[model.new_bool_var('a'+str(b))for b in range(8)]
                for v,n in zip(active,counts):model.add(v==int(n>0))
                constrain_dp(model,values,active,window,'test')
                solver=cp_model.CpSolver();status=solver.solve(model)
                self.assertEqual(status==cp_model.OPTIMAL,window>span)

    def test_adjacent_partition_admissions_are_independently_safe(self):
        from ortools.sat.python import cp_model
        cases=([0,1,4,6,3,0,2,2],[0,0,5,4,4,0,4,1],[0,2,3,4,3,0,2,3],[1]*8,[0]*8)
        for counts in cases:
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            for window in (320,344,356):
                model=cp_model.CpModel();values=[model.new_constant(n)for n in counts]
                active=[model.new_bool_var('a'+str(b))for b in range(8)]
                for v,n in zip(active,counts):model.add(v==int(n>0))
                constrain_adjacent(model,values,active,window,'test',18)
                solver=cp_model.CpSolver();status=solver.solve(model)
                if status==cp_model.OPTIMAL:self.assertLess(favorable_span(updates),window)

    def test_repair_interval_is_reported_and_preserves_pixels(self):
        source=source_schedule();result=optimize(source,write_budget=2,lookahead=0,time_limit=10,repair_interval=(0,255))
        self.assertEqual(result['bank_residency']['fixed_outside_repair_interval'],(0,255))
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_REPAIR_INTERVAL'):optimize(source,repair_interval=(4,3))


if __name__=='__main__':unittest.main()
