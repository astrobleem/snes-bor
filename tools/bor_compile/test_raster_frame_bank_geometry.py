import unittest
from raster_frame_bank_geometry import search,subdivided_candidates


class FrameBankGeometryTests(unittest.TestCase):
    def test_fixed_piece_bank_lifetime_rejects_per_row_bank_switch(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        result=search(rectangles,{(0,0):{0:[0]},(1,0):{4:[33]}},height=8,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual({p['bank']for p in result['pieces']},{0,4})
        self.assertTrue(result['fixed_bank_for_entire_oam_rectangle'])
        self.assertFalse(result['native_presentation_proven'])

    def test_fifteen_slot_banks_are_not_one_pool(self):
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        pixels={(0,x):{0:[x]}for x in range(16)}
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])
        pixels[0,15]={1:[15]}
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)

    def test_full_transparent_padding_cannot_exceed_sliver_limit(self):
        rectangles=[dict(x=8*i,y=0,width=32,height=32,allowed_banks=[i%8])for i in range(9)]
        pixels={(0,8*i):{i%8:[i]}for i in range(9)}
        # Rectangles overlap, so force each point into its own rectangle by bank.
        for i,p in enumerate(rectangles):p['allowed_banks']=[i%8]
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['native_presentation_proven'])

    def test_generic_subdivision_preserves_source_positions_and_word_options(self):
        parents=[dict(actor=0,x=0,y=0,local_x=0,local_y=0,width=32,height=32)]
        points={(0,0):{0:[0]},(8,9):{4:[33]}}
        candidates=subdivided_candidates(parents,points)
        self.assertEqual(len(candidates),3)
        self.assertTrue(all(p['x']==p['local_x']and p['y']==p['local_y']for p in candidates))
        result=search(candidates,points,height=32,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual(result['geometry']['peak_tile_slivers'],1)

    def test_class_symmetry_requires_equivalent_eligible_word_domains(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        points={(0,0):{b:[0]for b in range(4)}}
        result=search(rectangles,points,height=8,time_limit=3,bank_symmetry=True)
        self.assertEqual(result['pieces'][0]['bank'],0)
        self.assertTrue(result['safe_class_bank_label_symmetry'])
        points[0,0][1]=[33]
        with self.assertRaisesRegex(ValueError,'UNSAFE_SYMMETRY'):search(rectangles,points,bank_symmetry=True)

    def test_equivalent_points_coalesce_only_with_identical_geometry_owners(self):
        points={(0,0):{0:[0]},(0,1):{0:[0]}}
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        result=search(rectangles,points,height=8,time_limit=3)
        self.assertEqual(result['equivalent_pixel_decision_atoms'],1)
        self.assertEqual(result['independent_required_word_coverage_clauses'],1)
        self.assertEqual(len(result['pixels']),2)
        rectangles.append(dict(x=1,y=0,width=8,height=8))
        result=search(rectangles,points,height=8,time_limit=3)
        self.assertEqual(result['equivalent_pixel_decision_atoms'],2)

    def test_feasibility_only_retains_all_bank_and_geometry_constraints(self):
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        points={(0,x):{0:[x]}for x in range(16)}
        rejected=search(rectangles,points,height=32,time_limit=3,feasibility_only=True)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        points[0,15]={1:[15]}
        result=search(rectangles,points,height=32,time_limit=3,feasibility_only=True)
        self.assertEqual(result['solver_objective'],'FEASIBILITY_ONLY')
        self.assertEqual(result['geometry']['oam_entries'],2)

    def test_subset_geometry_hint_is_soft_and_replayed(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        hint=search(rectangles,{(0,0):{0:[0]}},height=8,time_limit=3)
        result=search(rectangles,{(0,0):{0:[0]},(1,0):{4:[33]}},height=8,time_limit=3,geometry_hint=hint)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertGreater(result['soft_geometry_hint_variables'],0)
        hint['pixels'][0]['color']=1
        with self.assertRaisesRegex(ValueError,'HINT_PIXEL'):
            search(rectangles,{(0,0):{0:[0]}},height=8,time_limit=3,geometry_hint=hint)
        hint['pixels'][0]['color']=0
        hint['cache_resident_colors']={0:{0:[0]}}
        result=search(rectangles,{(0,0):{0:[0]},(1,0):{4:[33]}},height=8,time_limit=3,geometry_hint=hint,cache_window=353)
        self.assertTrue(result['independent_integer_cache_and_ideal_partition_replayed'])
        hint['cache_resident_colors'][0][8]=[0]
        with self.assertRaisesRegex(ValueError,'HINT_CACHE_DOMAIN'):
            search(rectangles,{(0,0):{0:[0]}},height=8,time_limit=3,geometry_hint=hint,cache_window=353)

    def test_joint_integer_cache_rejects_unavoidable_loads_above_window(self):
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        points={(y,x):{x//15:[y*30+x]}for y in range(2)for x in range(30)}
        rejected=search(rectangles,points,height=32,time_limit=3,cache_window=353)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        result=search(rectangles,points,height=32,time_limit=3,cache_window=505)
        self.assertTrue(result['independent_integer_cache_and_ideal_partition_replayed'])
        self.assertEqual(result['peak_joint_cache_writes'],30)
        self.assertEqual(result['peak_joint_cache_ideal_span'],480)
        self.assertFalse(result['native_presentation_proven'])
        optimized=search(rectangles,points,height=32,time_limit=3,cache_window=505,minimize_cache_span=True)
        self.assertEqual(optimized['solver_status'],'OPTIMAL')
        self.assertEqual(optimized['peak_joint_cache_ideal_span'],480)
        self.assertEqual(optimized['solver_objective_lower_bound'],520)
        optimized['cache_resident_colors']={r['scanline']:r['resident_colors']for r in optimized['joint_cache_trace']}
        hinted=search(rectangles,points,height=32,time_limit=3,cache_window=505,minimize_cache_span=True,geometry_hint=optimized)
        self.assertTrue(hinted['complete_source_witness_hint_model_verified'])
        self.assertEqual(hinted['soft_geometry_hint_variables'],hinted['model_variables'])
        self.assertEqual(hinted['peak_joint_cache_ideal_span'],480)
        repaired=search(rectangles,points,height=32,time_limit=3,cache_window=505,minimize_cache_span=True,geometry_hint=optimized,repair_interval=[1,1])
        self.assertTrue(repaired['outside_repair_cache_and_pixel_owners_fixed'])
        self.assertGreater(repaired['repair_fixed_variables'],0)
        self.assertEqual(repaired['repair_interval_peak_joint_cache_ideal_span'],480)
        self.assertEqual(repaired['joint_cache_trace'][0]['resident_colors'],optimized['joint_cache_trace'][0]['resident_colors'])
        too_tight=search(rectangles,points,height=32,time_limit=3,cache_window=353,geometry_hint=optimized)
        self.assertFalse(too_tight['complete_source_witness_hint_model_verified'])
        self.assertGreater(too_tight['complete_source_witness_hint_violation_count'],0)
        self.assertEqual(too_tight['solver_status'],'INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'CACHE_WINDOW_DOMAIN'):
            search(rectangles,points,bank_symmetry=True,cache_window=505)

    def test_concurrent_geometry_reserves_full_padding_but_not_palette_admission(self):
        rects=[dict(x=0,y=0,width=8,height=8)];points={(0,0):{0:[0]}}
        reservation=dict(oam_entries=127,sprites_per_line=[31]*8,tile_slivers_per_line=[33]*8)
        result=search(rects,points,height=8,time_limit=3,geometry_reservation=reservation)
        self.assertEqual(result['combined_reserved_geometry'],dict(oam_entries=128,peak_sprites=32,peak_tile_slivers=34))
        self.assertFalse(result['reservation_palette_and_layer_demand_included'])
        reservation['tile_slivers_per_line'][7]=34
        self.assertEqual(search(rects,points,height=8,time_limit=3,geometry_reservation=reservation)['solver_status'],'INFEASIBLE')
        reservation['oam_entries']=True
        with self.assertRaisesRegex(ValueError,'RESERVATION_DOMAIN'):search(rects,points,height=8,geometry_reservation=reservation)

    def test_native_highs_joint_cache_matches_bank_capacity_and_transfer_gates(self):
        import importlib.util
        if not importlib.util.find_spec('highspy'):self.skipTest('optional native HiGHS backend')
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        points={(y,x):{x//15:[y*30+x]}for y in range(2)for x in range(30)}
        self.assertEqual(search(rectangles,points,height=32,time_limit=3,cache_window=353,solver_backend='highspy')['solver_status'],'INFEASIBLE')
        result=search(rectangles,points,height=40,time_limit=3,cache_window=481,solver_backend='highspy')
        self.assertEqual(result['peak_joint_cache_ideal_span'],480)
        self.assertTrue(result['independent_linear_integer_model_verified'])


if __name__=='__main__':unittest.main()
