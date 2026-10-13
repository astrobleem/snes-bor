import unittest
from raster_math_mode_liveness import lower_bound,verify_integer_pool


class ModeLivenessTests(unittest.TestCase):
    def test_total_load_objective_reports_peak_and_total_separately(self):
        rows=[{'add':{(c,())}}for c in (1,2,1)]
        result=lower_bound(rows,capacities=(1,0),integer_modes=True,
            integer_palette=True,integer_backend='cp-sat',time_limit=5,
            write_budget=4,integer_cache_objective='loads')
        self.assertEqual(result['cache_objective_value'],2)
        self.assertEqual(result['total_replayed_pool_writes'],2)
        self.assertTrue(result['modeled_loads_match_replayed_residency_changes'])
        self.assertEqual(result['peak_write_objective'],1)
        self.assertFalse(result['schedule_proven'])
        with self.assertRaisesRegex(ValueError,'INTEGER_CACHE_OBJECTIVE'):
            lower_bound(rows,integer_cache_objective='loads')

    def test_class_load_transfer_bound_rejects_twenty_two_writes_in_three_banks(self):
        first={(c,())for c in range(60)}|{(1000+c,(c,))for c in range(60)}
        second={(c,())for c in range(43)}|{(c,())for c in range(60,77)}|{(2000+c,(60+c,))for c in range(5)}
        rows=[{'add':first},{'add':second}]
        options=dict(integer_modes=True,integer_palette=True,integer_backend='cp-sat',write_budget=22,time_limit=5)
        blocked=lower_bound(rows,minimum_transfer_window=357,**options)
        self.assertEqual(blocked['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
        admitted=lower_bound(rows,minimum_transfer_window=369,**options)
        self.assertEqual(admitted['peak_replayed_pool_writes'],22)
        self.assertTrue(admitted['integer_pool_pixel_coverage_verified'])
        self.assertFalse(admitted['minimum_transfer_bound_is_complete_partition_proof'])
        admitted['necessary_minimum_transfer_window']=357
        with self.assertRaisesRegex(AssertionError,'MINIMUM_TRANSFER_REPLAY'):verify_integer_pool(admitted,rows)
        with self.assertRaisesRegex(ValueError,'DISJOINT_FOUR_BANK_CLASSES'):lower_bound(rows,capacities=(120,60),minimum_transfer_window=357)

    def test_controls_only_window_hint_cannot_pin_wrong_pixel_gates(self):
        rows=[{'a':{(0,(7,))}},{'a':{(1,(7,))}}]
        pixels=[[{'x':4,'output':out,'modes':{'a':(7,)}}]for out in(0,1)]
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,integer_windows=True,integer_palette=True,integer_backend='cp-sat',write_budget=0,time_limit=5,window_pixels=pixels,controls_hint={'selected_modes':{0:'a',1:'a'},'selected_window_eligibility':{0:{4:0},1:{4:0}}})
        self.assertEqual(result['selected_window_eligibility'],{0:{4:1},1:{4:1}})
        self.assertEqual(result['peak_replayed_pool_writes'],0)
        self.assertTrue(result['integer_pool_pixel_coverage_verified'])
        self.assertFalse(result['source_controls_hint']['palette_residency_hinted'])
        self.assertEqual(result['source_controls_hint']['hint_variables'],4)

    def test_controls_only_hint_can_change_mode_without_pinning_residency(self):
        rows=[{'a':{(0,(7,))},'b':{(0,(9,))}},{'a':{(1,(8,))},'b':{(1,(9,))}}]
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,integer_palette=True,integer_backend='cp-sat',write_budget=0,time_limit=5,controls_hint={'selected_modes':{0:'a',1:'a'}})
        self.assertEqual(result['selected_modes'],{0:'b',1:'b'})
        self.assertEqual(result['peak_replayed_pool_writes'],0)
        self.assertEqual(result['source_controls_hint']['pinned_variables'],0)
        self.assertFalse(result['source_controls_hint']['palette_residency_hinted'])
        self.assertFalse(result['schedule_proven'])
        with self.assertRaisesRegex(ValueError,'CONTROLS_HINT_DOMAIN'):
            lower_bound(rows,integer_modes=True,integer_palette=True,integer_backend='cp-sat',controls_hint={'selected_modes':{0:'missing'}})

    def test_fixed_initial_cache_cannot_gain_free_colors_at_segment_boundary(self):
        rows=[{'a':{(1,())}},{'a':{(2,())}}]
        opts=dict(capacities=(2,0),integer_modes=True,integer_palette=True,integer_backend='cp-sat',time_limit=5)
        resident=lower_bound(rows,initial_state={0:[1,2],1:[]},**opts)
        self.assertEqual(resident['peak_replayed_pool_writes'],0)
        loaded=lower_bound(rows,initial_state={0:[1],1:[]},**opts)
        self.assertEqual(loaded['peak_replayed_pool_writes'],1)
        self.assertFalse(loaded['optimal_initial_residency_allowed'])
        loaded['selected_palette_residency'][0][0]=[1,2]
        with self.assertRaisesRegex(AssertionError,'INITIAL_STATE'):verify_integer_pool(loaded,rows,(2,0))
        with self.assertRaisesRegex(ValueError,'INITIAL_STATE_DOMAIN'):lower_bound(rows,capacities=(1,0),initial_state={0:[1,2],1:[]})

    def test_required_normal_rows_are_fixed_without_reserving_whole_frame_union(self):
        rows=[{'a':set()},{'a':{(2,(2,))}}]
        report=lower_bound(rows,capacities=(1,1),required_normal_rows={0:{0},1:{1}},time_limit=5)
        self.assertAlmostEqual(report['validated_dual_lower_bound'],1)
        self.assertEqual(report['required_normal_rows'],{0:[0],1:[1]})
        blocked=lower_bound([{'a':{(0,(0,)),(1,())}}],capacities=(1,1),required_normal_rows={0:{0}},time_limit=5)
        self.assertIn(blocked['status'],('RELAXED_MODE_LIVENESS_INFEASIBLE','ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE'))

    def test_per_scanline_capacity_cannot_hide_required_reload(self):
        rows=[{'a':{(i,())}}for i in range(3)]
        blocked=lower_bound(rows,capacities=(1,1),scanline_write_limits={1:0},time_limit=5)
        self.assertEqual(blocked['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
        valid=lower_bound(rows,capacities=(1,1),scanline_write_limits={1:1,2:1},time_limit=5)
        self.assertAlmostEqual(valid['validated_dual_lower_bound'],1)
        self.assertEqual(valid['scanline_write_limits'],{1:1,2:1})

    def test_static_reservation_is_fixed_even_when_math_can_encode_same_word(self):
        rows=[{'a':{(0,(0,)),(1,())},'b':{(0,(0,)),(1,())}}]
        free=lower_bound(rows,capacities=(1,1),time_limit=5)
        self.assertEqual(free['status'],'FRACTIONAL_MODE_LIVENESS_LOWER_BOUND')
        fixed=lower_bound(rows,capacities=(1,1),time_limit=5,reserved_normal_colors=[0])
        self.assertEqual(fixed['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
        self.assertTrue(fixed['static_normal_residency_fixed_for_complete_interval'])

    def test_static_reservation_dual_and_integer_replay(self):
        rows=[{'a':{(1,(1,))}},{'a':{(2,(2,))}}]
        bound=lower_bound(rows,capacities=(1,1),time_limit=5,reserved_normal_colors=[0])
        self.assertAlmostEqual(bound['validated_dual_lower_bound'],1)
        for backend in ('highs','cp-sat'):
            result=lower_bound(rows,capacities=(1,1),time_limit=5,reserved_normal_colors=[0],integer_modes=True,integer_palette=True,integer_backend=backend)
            self.assertEqual(result['peak_write_objective'],1)
            self.assertTrue(all(0 in state[0] for state in result['selected_palette_residency'].values()))

    def test_verified_residency_hint_can_change_modes_and_words_to_meet_lower_budget(self):
        rows=[{'a':{(0,(7,))},'b':{(0,(9,))}},{'a':{(1,(8,))},'b':{(1,(9,))}}]
        seed=dict(selected_modes={0:'a',1:'a'},selected_palette_residency={0:{0:[],1:[7]},1:{0:[],1:[8]}},peak_write_objective=1)
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,integer_palette=True,integer_backend='cp-sat',write_budget=0,time_limit=10,residency_hint=seed)
        self.assertEqual(result['peak_write_objective'],0)
        self.assertEqual(result['selected_modes'],{0:'b',1:'b'})
        self.assertTrue(result['source_residency_hint']['hint_is_soft'])
        self.assertEqual(result['source_residency_hint']['pinned_variables'],0)
        self.assertEqual(result['source_residency_hint']['input_peak_replayed_writes'],1)
        self.assertFalse(result['schedule_proven'])

    def test_integer_palette_capacity_is_checked_without_native_admission(self):
        rows=[{'a':{(i,())}}for i in range(3)]
        for backend in('highs','cp-sat'):
            r=lower_bound(rows,capacities=(1,1),integer_modes=True,integer_palette=True,integer_backend=backend,write_budget=1,time_limit=10)
            self.assertEqual(r['peak_write_objective'],1)
            self.assertFalse(r['palette_residency_integrality_relaxed'])
            self.assertFalse(r['schedule_proven'])
            self.assertEqual(r['selected_palette_residency'],{y:{0:[y],1:[]}for y in range(3)})
            self.assertLessEqual(r['maximum_integer_control_residual'],1e-6)
            blocked=lower_bound(rows,capacities=(1,1),integer_modes=True,integer_palette=True,integer_backend=backend,write_budget=0,time_limit=10)
            self.assertEqual(blocked['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'INTEGER_PALETTE_CONTROLS'):lower_bound(rows,integer_palette=True)
        with self.assertRaisesRegex(ValueError,'INTEGER_BACKEND'):lower_bound(rows,integer_backend='cp-sat')

    def test_lp_residency_hint_is_soft_and_does_not_grant_admission(self):
        rows=[{'a':{(i,())}}for i in range(3)]
        r=lower_bound(rows,capacities=(1,1),integer_modes=True,integer_palette=True,integer_backend='cp-sat',lp_hint=True,write_budget=1,time_limit=10)
        self.assertEqual(r['peak_write_objective'],1)
        self.assertEqual(r['lp_residency_hint']['pinned_variables'],0)
        self.assertTrue(r['lp_residency_hint']['hint_is_soft'])
        self.assertGreater(r['boolean_stats']['hint_variables'],0)
        self.assertFalse(r['schedule_proven'])

    def test_saved_pool_replay_rejects_tampered_palette_and_write_budget(self):
        import json,copy
        rows=[{'a':{(i,())}}for i in range(3)]
        r=lower_bound(rows,capacities=(1,1),integer_modes=True,integer_palette=True,write_budget=1,time_limit=10)
        saved=json.loads(json.dumps(r));verify_integer_pool(saved,rows,(1,1))
        self.assertTrue(saved['integer_pool_pixel_coverage_verified'])
        bad=copy.deepcopy(saved);bad['selected_palette_residency']['1']['0']=[]
        with self.assertRaisesRegex(AssertionError,'PIXEL_REPLAY'):verify_integer_pool(bad,rows,(1,1))
        bad=copy.deepcopy(saved);bad['peak_write_objective']=0
        with self.assertRaisesRegex(AssertionError,'WRITE_REPLAY'):verify_integer_pool(bad,rows,(1,1))

    def test_shared_mode_cannot_choose_different_mode_for_each_pixel(self):
        rows=[{'a':{(0,(7,)),(1,())},'b':{(0,()),(1,(7,))}}]
        for integer in (False,True):
            result=lower_bound(rows,capacities=(0,1),integer_modes=integer)
            self.assertIn(result['status'],('RELAXED_MODE_LIVENESS_INFEASIBLE','ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE'))
            self.assertFalse(result['schedule_proven'])

    def test_native_mode_can_change_between_lines_without_rewriting_shared_operand(self):
        rows=[{'a':{(0,(7,))},'b':{(0,())}},{'a':{(1,())},'b':{(1,(7,))}}]
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,write_budget=0)
        self.assertEqual(result['selected_modes'],{0:'a',1:'b'})
        self.assertEqual(result['peak_write_objective'],0)
        self.assertFalse(result['schedule_proven'])

    def test_one_mode_recovers_exact_necessary_write_bound(self):
        rows=[{'a':{(i,())}}for i in range(3)]
        result=lower_bound(rows,capacities=(1,1))
        self.assertAlmostEqual(result['validated_dual_lower_bound'],1)
        self.assertEqual(result['maximum_dual_residual'],0)
        failed=lower_bound(rows,capacities=(1,1),integer_modes=True,write_budget=0)
        self.assertEqual(failed['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')

    def test_fractional_modes_still_require_whole_pixel_coverage(self):
        rows=[{'a':{(0,()),(1,())},'b':{(0,()),(1,())}}]
        result=lower_bound(rows,capacities=(1,1))
        self.assertEqual(result['status'],'ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE')

    def test_modes_exceeding_integer_opaque_capacity_are_removed_before_fractional_relaxation(self):
        rows=[{'a':{(0,()),(1,())},'b':{(0,(7,)),(1,(7,))}}]
        result=lower_bound(rows,capacities=(1,1))
        self.assertEqual(result['mode_variables'],1)
        self.assertEqual(result['forced_opaque_modes_pruned'],[dict(scanline=0,mode='a',forced_opaque_colors=2)])
        self.assertAlmostEqual(result['validated_dual_lower_bound'],0)

    def test_union_coverage_filters_pruned_operands_independently_on_each_line(self):
        rows=[{'a':{(0,(7,))},'b':{(0,())}},{'a':{(1,())},'b':{(1,(8,))}}]
        union=[{(0,(7,99))},{(1,(8,99))}]
        result=lower_bound(rows,capacities=(0,1),union_rows=union)
        self.assertAlmostEqual(result['validated_dual_lower_bound'],1)
        self.assertEqual(len(result['forced_opaque_modes_pruned']),2)

    def test_two_windows_can_represent_mask_that_one_window_cannot(self):
        rows=[{'add':{(1,()),(2,(1,))}}]
        pixels=[[dict(x=x,output=1 if x%2==0 else 2,modes={'add':()if x%2==0 else(1,)})for x in range(4)]]
        union=[{(1,(1,)),(2,(1,2))}]
        for changes,expected in ((2,'RELAXED_MODE_LIVENESS_INFEASIBLE'),(4,'RELAXED_MODE_LIVENESS_CANDIDATE')):
            result=lower_bound(rows,capacities=(0,1),union_rows=union,window_pixels=pixels,integer_windows=True,integer_modes=True,maximum_window_transitions=changes)
            self.assertEqual(result['status'],expected)
            if changes==4:self.assertEqual(result['selected_window_eligibility'],{0:{0:0,1:1,2:0,3:1}})
            self.assertFalse(result['schedule_proven'])

    def test_integral_control_hint_is_explicitly_a_restricted_family(self):
        rows=[{'add':{(0,(7,))}}]
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,pin_lp_controls=True)
        self.assertEqual(result['pinned_lp_control_family']['pinned_variables'],1)
        self.assertTrue(result['pinned_lp_control_family']['restricted_family_only'])
        self.assertEqual(result['selected_modes'],{0:'add'})
        self.assertFalse(result['schedule_proven'])

    def test_positive_window_family_disables_math_at_viewport_edges(self):
        rows=[{'add':{(1,()),(2,(1,))}}]
        pixels=[[dict(x=0,output=2,modes={'add':(1,)}),dict(x=100,output=1,modes={'add':()})]]
        unrestricted=lower_bound(rows,capacities=(0,1),window_pixels=pixels,integer_windows=True)
        self.assertEqual(unrestricted['status'],'RELAXED_MODE_LIVENESS_CANDIDATE')
        restricted=lower_bound(rows,capacities=(0,1),window_pixels=pixels,integer_windows=True,positive_windows_only=True)
        self.assertEqual(restricted['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
        self.assertTrue(restricted['positive_union_with_disabled_edges_only'])

    def test_subset_cuts_prevent_fractional_modes_from_covering_unselected_outputs_for_free(self):
        modes=('a','b','c','d');rows=[];pixels=[]
        for colors in ((1,2,3,4),(5,6,8,9)):
            row={m:set()for m in modes};line=[]
            for i,out in enumerate(colors):
                choices={m:(99,)if i==j else()for j,m in enumerate(modes)}
                line.append(dict(x=100+i,output=out,modes=choices))
                for m in modes:row[m].add((out,choices[m]))
            rows.append(row);pixels.append(line)
        weak=lower_bound(rows,capacities=(1,3),window_pixels=pixels)
        strong=lower_bound(rows,capacities=(1,3),window_pixels=pixels,subset_mode_cuts=True)
        self.assertAlmostEqual(weak['validated_dual_lower_bound'],0)
        self.assertGreater(strong['validated_dual_lower_bound'],0)
        self.assertFalse(strong['schedule_proven'])


if __name__=='__main__':unittest.main()
