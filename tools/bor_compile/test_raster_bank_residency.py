import unittest
import numpy as np
from raster_bank_residency import optimize,favorable_span,relaxed_bound,constrain_dp,constrain_adjacent,restrict_interval,flow_partition_hint
from raster_cgram_packets import optimistic_dma_span
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class ResidencyTests(unittest.TestCase):
    def test_invisible_bank_prefix_preloads_first_demand_without_source_loss(self):
        import test_raster_slot_layout as fixtures
        source=fixtures.SlotLayoutTests().schedule()
        for backend in('cp-sat','highs'):
            result=optimize(source,write_budget=2,lookahead=0,window=None,time_limit=5,solver_backend=backend,collapse_bank_idle_prefix=True)
            self.assertEqual(result['bank_residency']['bank_first_visible_rows'][1],2)
            self.assertGreater(result['bank_residency']['bank_idle_prefix_resident_variables_collapsed'],0)
            self.assertTrue(all(e['bank']!=1 for row in result['trace'][1:3]for e in row['updates']))
            for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        with self.assertRaisesRegex(ValueError,'IDLE_PREFIX_DOMAIN'):optimize(source,collapse_bank_idle_prefix=1)
        with self.assertRaisesRegex(ValueError,'IDLE_PREFIX_DOMAIN'):optimize(source,collapse_bank_idle_prefix=True,repair_interval=(1,2))

    def test_bank_budget_candidate_requires_integer_cache_and_cap_replay(self):
        caps={y:[int(y in(7,12)and b in(0,1))for b in range(8)]for y in range(1,16)}
        source=source_schedule()
        for backend in('cp-sat','highs'):
            result=optimize(source,2,0,None,5,solver_backend=backend,bank_write_caps=caps)
            self.assertTrue(result['bank_residency']['per_bank_write_caps_enforced'])
            self.assertTrue(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
            self.assertFalse(result['bank_residency']['native_timing_admitted'])
            for row in result['trace'][1:]:
                self.assertTrue(all(sum(e['bank']==b for e in row['updates'])<=caps[row['scanline']][b]for b in range(8)))
            blocked={y:list(v)for y,v in caps.items()};blocked[7][0]=0
            self.assertEqual(optimize(source,2,0,None,5,solver_backend=backend,bank_write_caps=blocked)['solver_status'],'INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'WRITE_CAPS_DOMAIN'):optimize(source,bank_write_caps={})

    def test_flow_partition_hints_match_independent_endpoint_dp(self):
        rng=np.random.default_rng(1729)
        for counts in [[0]*8,[1,9,7,1,0,0,0,0],*[list(map(int,rng.integers(0,16,8)))for _ in range(100)]]:
            cost,ranges=flow_partition_hint(counts)
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            self.assertEqual(max(0,cost-40),favorable_span(updates))
            self.assertLessEqual(len(ranges),4)
            self.assertTrue(all(sum(a<=b<=z for a,z in ranges)==1 for b,n in enumerate(counts)if n))
        with self.assertRaisesRegex(ValueError,'COUNTS'):flow_partition_hint([16]*8)
        with self.assertRaisesRegex(ValueError,'RANGES'):flow_partition_hint([1]*8,0)

    def test_active_bank_batching_counts_actual_writes_without_timing_admission(self):
        source=source_schedule()
        for backend in ('cp-sat','highs'):
            for limit in (1,2):
                result=optimize(source,2,0,None,5,solver_backend=backend,maximum_active_banks=limit)
                if limit==1:
                    self.assertEqual(result['solver_status'],'INFEASIBLE')
                    self.assertFalse(result['universal_raster_rejected'])
                else:
                    report=result['bank_residency']
                    self.assertEqual(report['peak_noninitial_active_banks'],2)
                    self.assertFalse(report['physical_slot_schedule_proven'])
                    for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        for bad in (0,9,True):
            with self.assertRaisesRegex(ValueError,'ACTIVE_BANK_DOMAIN'):
                optimize(source,maximum_active_banks=bad)

    def test_integer_transfer_fractional_cache_does_not_emit_schedule(self):
        source=source_schedule()
        result=optimize(source,write_budget=2,lookahead=0,time_limit=10,
                        window=345,range_backend='ranges',solver_backend='highs',relax_cache=True)
        self.assertEqual(result['status'],'FRACTIONAL_CACHE_INTEGER_TRANSFER_CANDIDATE')
        self.assertTrue(result['palette_residency_integrality_relaxed'])
        self.assertGreater(result['fractional_cache_variables'],0)
        self.assertFalse(result['integer_palette_schedule_proven'])
        self.assertFalse(result['complete_source_frame_pixel_identity_proven'])
        self.assertNotIn('trace',result)
        rejected=optimize(source,write_budget=1,lookahead=0,time_limit=10,
                          window=345,range_backend='ranges',solver_backend='highs',relax_cache=True)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        self.assertFalse(rejected['universal_raster_rejected'])
        with self.assertRaisesRegex(ValueError,'RELAXED_CACHE_BACKEND'):
            optimize(source,relax_cache=True)

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
        self.assertFalse(result['complete_source_frame_pixel_identity_proven'])

    def test_invalid_budget_rejected(self):
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_DOMAIN'):optimize(source_schedule(),write_budget=-1)

    def test_minimum_total_writes_preserves_pixels_with_both_backends(self):
        for backend in ('cp-sat','highs'):
            source=source_schedule()
            result=optimize(source,write_budget=2,lookahead=0,time_limit=10,window=None,
                            solver_backend=backend,minimize_writes=True)
            self.assertEqual(result['bank_residency']['solver_status'],'OPTIMAL')
            self.assertTrue(result['bank_residency']['total_noninitial_writes_objective'])
            self.assertEqual(result['bank_residency']['total_noninitial_scheduled_writes'],4)
            _,_,a=demand(source);_,_,b=demand(result)
            self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))

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

    def test_milp_and_cp_backends_agree_on_exact_pixels_and_failure(self):
        source=source_schedule();_,_,expected=demand(source)
        for budget in (1,2):
            results=[optimize(source,write_budget=budget,lookahead=0,time_limit=10,range_backend='ranges',solver_backend=b)for b in('cp-sat','highs')]
            self.assertEqual(results[0].get('bank_residency',results[0])['solver_status'],results[1].get('bank_residency',results[1])['solver_status'])
            if budget==2:
                for result in results:
                    _,_,actual=demand(result)
                    self.assertTrue(all(np.array_equal(x,y)for x,y in zip(expected,actual)))
                self.assertEqual(results[1]['bank_residency']['maximum_integer_constraint_violation'],0)

    def test_native_highs_consumes_soft_start_without_relaxing_pixels_or_budget(self):
        import importlib.util
        if importlib.util.find_spec('highspy')is None:self.skipTest('optional native HiGHS interface not installed')
        source=source_schedule()
        hint=optimize(source,2,0,356,5,'flow',minimize_span=True)
        result=optimize(source,2,0,356,5,'flow',solver_backend='highspy',residency_hint=hint,minimize_span=True)
        report=result['bank_residency']
        self.assertEqual(report['solver_status'],'OPTIMAL')
        self.assertTrue(report['supplied_residency_hint_used_by_solver'])
        self.assertGreater(report['native_mip_start_variable_count'],0)
        self.assertTrue(report['native_mip_start_is_soft'])
        self.assertEqual(report['maximum_integer_constraint_violation'],0)
        self.assertEqual(report['peak_optimistic_prepared_span'],hint['bank_residency']['peak_optimistic_prepared_span'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        blocked=optimize(source,1,0,356,5,'flow',solver_backend='highspy',residency_hint=hint)
        self.assertEqual(blocked['solver_status'],'INFEASIBLE')
        self.assertFalse(blocked['native_timing_admitted'])

    def test_nonfinite_milp_incumbent_cannot_become_a_palette_witness(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from ortools.sat.python import cp_model
        from raster_bank_residency import solve_linear
        model=cp_model.CpModel();v=model.new_bool_var('invalid');model.add(v==0)
        invalid=SimpleNamespace(x=np.array([np.nan]),status=0,message='invalid incumbent',mip_dual_bound=None)
        with patch('scipy.optimize.milp',return_value=invalid):
            with self.assertRaisesRegex(AssertionError,'NONFINITE_SOLUTION'):solve_linear(model,1)

    def test_milp_rejects_non_linear_backend(self):
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_SOLVER_BACKEND'):optimize(source_schedule(),solver_backend='highs')

    def test_peak_span_objective_preserves_source_and_agrees_across_exact_bounds(self):
        source=source_schedule()
        results=[optimize(source,2,0,356,5,backend,minimize_span=True)for backend in('dp','adjacent','ranges','flow')]
        results.append(optimize(source,2,0,356,5,'ranges',solver_backend='highs',minimize_span=True))
        results.append(optimize(source,2,0,356,5,'flow',solver_backend='highs',minimize_span=True))
        for result in results:
            report=result['bank_residency']
            self.assertTrue(report['peak_optimistic_prepared_span_objective'])
            self.assertFalse(report['physical_slot_schedule_proven'])
            self.assertFalse(report['native_timing_admitted'])
            for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(results[0]['bank_residency']['peak_optimistic_prepared_span'],results[1]['bank_residency']['peak_optimistic_prepared_span'])
        for result in results[2:]:
            self.assertEqual(result['bank_residency']['peak_optimistic_prepared_span'],results[0]['bank_residency']['peak_optimistic_prepared_span'])
            self.assertEqual(result['bank_residency']['peak_optimistic_span_lower_bound_for_this_fixed_bank_family'],results[0]['bank_residency']['peak_optimistic_prepared_span'])
        self.assertEqual(results[0]['bank_residency']['peak_optimistic_span_lower_bound_for_this_fixed_bank_family'],results[0]['bank_residency']['peak_optimistic_prepared_span'])
        with self.assertRaisesRegex(ValueError,'SPAN_OBJECTIVE_DOMAIN'):optimize(source,window=None,minimize_span=True)
        with self.assertRaisesRegex(ValueError,'SPAN_OBJECTIVE_DOMAIN'):optimize(source,minimize_span=True,minimize_writes=True)

    def test_lns_peak_span_search_replays_complete_pixels(self):
        source=source_schedule();result=optimize(source,2,0,356,2,'adjacent',minimize_span=True,search_strategy='lns')
        self.assertEqual(result['bank_residency']['solver_search_strategy'],'lns')
        self.assertTrue(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        with self.assertRaisesRegex(ValueError,'SEARCH_STRATEGY'):optimize(source,search_strategy='invalid')

    def test_interval_relaxation_preserves_only_retained_pixels_and_geometry(self):
        source=source_schedule();relaxed=restrict_interval(source,4,9)
        self.assertEqual(relaxed['pieces'],source['pieces'])
        self.assertFalse(relaxed['compiled_pixel_identity_verified'])
        with self.assertRaisesRegex(ValueError,'GREEDY_VALIDATED_SOURCE_SCHEDULE_REQUIRED'):demand(relaxed)
        _,_,a=demand(source);_,_,b=demand(relaxed,allow_restricted=True)
        for p,expected,actual in zip(source['pieces'],a,b):
            for ly in range(p['height']):
                if 4<=p['y']+ly<=9:self.assertTrue(np.array_equal(expected[ly],actual[ly]))
                else:self.assertTrue(np.all(actual[ly]==-1))
        result=optimize(relaxed,write_budget=2,lookahead=0,time_limit=10)
        self.assertTrue(result['bank_residency']['outside_interval_pixels_relaxed'])
        self.assertFalse(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_SCANLINE_INTERVAL'):restrict_interval(source,4,3)

    def test_partial_residency_hint_does_not_relax_complete_frame_demand(self):
        import copy
        source=source_schedule();hint=restrict_interval(source,4,9)
        result=optimize(source,write_budget=2,lookahead=0,time_limit=10,residency_hint=hint)
        self.assertEqual(result['bank_residency']['soft_residency_hint_interval'],[4,9])
        self.assertTrue(result['bank_residency']['supplied_residency_hint_used_by_solver'])
        milp=optimize(source,write_budget=2,lookahead=0,time_limit=10,range_backend='flow',solver_backend='highs',residency_hint=hint)
        self.assertEqual(milp['bank_residency']['soft_residency_hint_interval'],[4,9])
        self.assertFalse(milp['bank_residency']['solver_consumes_soft_hints'])
        self.assertFalse(milp['bank_residency']['supplied_residency_hint_used_by_solver'])
        self.assertTrue(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        bad=copy.deepcopy(hint);data=bytearray.fromhex(bad['piece_pixel_masks'][0]['pixels_hex']);data[32]=0x22
        bad['piece_pixel_masks'][0]['pixels_hex']=data.hex()
        with self.assertRaisesRegex(ValueError,'BANK_RESIDENCY_HINT_PIXEL_IDENTITY'):optimize(source,residency_hint=bad)


if __name__=='__main__':unittest.main()
