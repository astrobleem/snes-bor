import unittest
from unittest.mock import patch
import numpy as np
from source_bg_feasibility import rgb555
from source_scene_obj_joint import probe,saturated_corners


class JointSceneSolverTests(unittest.TestCase):
    def test_additive_only_reserves_normal_banks_and_preserves_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),31,dtype=np.int32);expected=background.copy();expected[:8,:8,0]=248
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,additive_only=True)
        self.assertTrue(r['compiled_pixel_identity_verified']);self.assertEqual(r['opaque_obj_banks_reserved'],4)
        self.assertTrue(all(p['bank']>=4 for p in r['pieces']))
        self.assertTrue(all(e['bank']>=4 for row in r['trace']for e in row['updates']))

    def test_pool_reports_required_final_output_color_identity_counts(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),31,dtype=np.int32);pixels[1,1]=0
        expected=background.copy();expected[:8,:8,0]=248;expected[1,1,0]=0
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,pool_only=True,time_limit=10,underlay_bypass=True)
        self.assertEqual(r['visible_final_obj_output_full_frame_colors'],1)
        self.assertEqual(r['peak_visible_final_obj_output_colors_per_scanline'],1)
        self.assertTrue(r['final_output_counts_apply_source_alpha_and_occlusion'])
        self.assertTrue(r['final_output_counts_exclude_exact_underlay_bypass_pixels'])
        self.assertEqual(r['underlay_bypassed_pixels'],1)

    def test_other_math_modes_are_explicit_pool_relaxation_only(self):
        with self.assertRaisesRegex(ValueError,'JOINT_MATH_MODES_REQUIRE_RELAXED_POOL_ONLY'):
            probe(None,None,{},pool_math_modes=('half-add',))
        background=np.zeros((224,256,3),dtype=np.uint8);background[:8,:8,0]=8
        pixels=np.full((8,8),16,dtype=np.int32);expected=background.copy();expected[:8,:8,0]=128
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,pool_only=True,pool_math_modes=('half-add',),time_limit=10)
        self.assertEqual(r['color_math'],'RELAXED_POOL_MATH_MODES')
        self.assertAlmostEqual(r['validated_dual_lower_bound'],0)
        self.assertFalse(r['global_math_mode_constraints_relaxed'])
        self.assertFalse(r['schedule_proven'])

    def test_additive_only_cannot_silently_approximate_darker_output(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:,:,0]=248
        expected=background.copy();expected[:8,:8,0]=240;pixels=np.full((8,8),30,dtype=np.int32)
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,additive_only=True)
        self.assertEqual(r['solver']['status'],2);self.assertFalse(r['native_presentation_proven'])

    def test_pool_prefetch_obeys_actual_pixel_use_lookahead(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,64),-1,dtype=np.int32);pixels[0,:60]=np.arange(1,61);pixels[2,0]=0
        expected=background.copy()
        for y,x in zip(*np.where(pixels>=0)):
            c=int(pixels[y,x]);expected[y+44,x]=[(c>>s&31)*8 for s in (0,5,10)]
        actors=[dict(pixels=pixels,left=0,top=44)]
        entries=[dict(kind=0,color=c,line=44,value=1)for c in range(1,61)]+[dict(kind=0,color=0,line=y,value=1)for y in (45,46)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=entries)
        for lead,expected_status in ((0,2),(1,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=0,early_write_budget=1,late_start=46,lookahead=lead,time_limit=10,pool_residency=pool,bank_symmetry=True,feasibility_only=True)
            self.assertEqual(r['solver']['status'],expected_status)
            if lead:
                self.assertTrue(r['compiled_pixel_identity_verified']);self.assertTrue(r['noninitial_prefetch_lookahead_enforced'])
                self.assertEqual(r['maximum_noninitial_prefetch_latency_lines'],1)
                self.assertTrue(r['noninitial_prefetch_latency_replayed'])

    def test_mixed_sixteen_small_geometry_is_a_legal_global_pair(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((16,16),31,dtype=np.int32);expected=background.copy();expected[:16,:16,0]=248
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size='mixed',mixed_small_size=16,write_budget=0,time_limit=10,color_math='precomposited',coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['mixed_small_size'],16)
        self.assertTrue(all(p['width']in(16,32)for p in r['pieces']))
        with self.assertRaisesRegex(ValueError,'MIXED_SMALL_SIZE_DOMAIN'):probe(None,None,{},mixed_small_size=12)
        with self.assertRaisesRegex(ValueError,'MIXED_SIZE_PAIR_DOMAIN'):probe(None,None,{},mixed_small_size=16,mixed_large_size=16)
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size='mixed',mixed_large_size=16,write_budget=0,time_limit=10,color_math='precomposited',coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertTrue(all(p['width']in(8,16)for p in r['pieces']))

    def test_precomposited_context_can_use_all_eight_opaque_banks(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,120),-1,dtype=np.int32);pixels[0]=np.arange(120)
        expected=background.copy()
        expected[0,:120]=np.stack([(pixels[0]>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='precomposited',bank_symmetry=True,coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual({p['bank']for p in r['pieces']},set(range(8)))
        self.assertEqual(r['peak_scheduled_writes'],0)
        self.assertEqual(sum(len(set(v)-{None})for v in r['trace'][0]['resident_before'].values()),0)
        self.assertEqual(r['trace'][0]['colors_written'],120)
        self.assertEqual(r['color_math'],'precomposited')

    def test_precomposited_refuses_additive_pool_identity(self):
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,0]=31
        background=np.zeros((224,256,3),dtype=np.uint8)
        actors=[dict(pixels=pixels,left=0,top=0)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[])
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},background)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            with self.assertRaisesRegex(ValueError,'JOINT_POOL_COLOR_MATH'):
                probe(None,None,{},color_math='precomposited',pool_residency=pool)

    def test_equal_opaque_outputs_coalesce_across_distinct_underlays(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=[32,0,0];background[0,1]=[32,8,0]
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:2]=31
        expected=background.copy();expected[0,:2]=[248,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        results=[]
        for coalesce in (False,True):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=0,time_limit=5,coalesce_opaque_choices=coalesce)
            self.assertTrue(r['compiled_pixel_identity_verified'])
            self.assertEqual(r['geometry']['oam_entries'],1)
            results.append(r)
        self.assertEqual(results[0]['distinct_opaque_choice_variables'],8)
        self.assertEqual(results[1]['distinct_opaque_choice_variables'],4)
        self.assertEqual(results[0]['source_rgb555_sha256'],results[1]['source_rgb555_sha256'])

    def test_grid_padding_changes_piece_origin_without_changing_source_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((32,32),-1,dtype=np.int32);pixels[9:11,9:11]=31
        expected=background.copy();expected[9:11,9:11,0]=248
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=5,
                    align_visible_bounds=True,grid_padding_x=7,grid_padding_y=7)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['source_actor_canvases'],[[32,32]])
        self.assertEqual({(p['local_x'],p['local_y'])for p in r['pieces']},{(2,2),(10,2),(2,10),(10,10)})
        self.assertEqual(r['geometry']['oam_entries'],4)
        self.assertEqual(np.count_nonzero(pixels>=0),4)

    def test_grid_padding_requires_visible_bounds_and_legal_phase(self):
        for args in (dict(grid_padding_x=1),dict(align_visible_bounds=True,grid_padding_x=8)):
            with self.assertRaisesRegex(ValueError,'JOINT_GRID_PADDING_DOMAIN'):
                probe(None,None,{},size=8,**args)

    def test_complete_additive_family_uses_shared_noncorner_operand(self):
        word=lambda r,g,b:r|(g<<5)|(b<<10)
        common=word(5,12,7)
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=np.array([25,21,13])*8
        background[0,1]=np.array([29,18,13])*8
        pixels=np.full((8,8),-1,dtype=np.int32)
        pixels[0,0]=word(30,31,20);pixels[0,1]=word(31,30,20)
        expected=background.copy()
        expected[0,0]=np.array([30,31,20])*8
        expected[0,1]=np.array([31,30,20])*8
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},
                  fractional_residency=[dict(kind=1,color=common,line=0,value=1)])
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=5,
                    complete_additive_cover=True,pool_residency=pool)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['geometry']['oam_entries'],1)
        self.assertGreaterEqual(r['pieces'][0]['bank'],4)
        self.assertTrue(r['complete_additive_cover']['all_valid_operand_coverages_retained'])
        self.assertEqual(r['complete_additive_cover']['maximal_cover_operands'],1)

    def test_saturated_corners_include_white_missing_from_minimal_corpus(self):
        background=17|(9<<5)|(12<<10)
        values=saturated_corners(32767,background)
        self.assertEqual(len(values),8)
        self.assertIn(32767,values)
        from source_scene_obj_math import add_rgb555
        self.assertTrue(all(add_rgb555(c,background)==32767 for c in values))
        self.assertEqual(saturated_corners(0,background),[])

    def test_underlay_bypass_preserves_canvas_and_opaque_black(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:,:,0]=255
        pixels=np.full((32,32),31,dtype=np.int32);pixels[0,0]=0;original=pixels.copy()
        expected=background.copy();expected[0,0]=0
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=32,write_budget=0,time_limit=5,underlay_bypass=True,align_visible_bounds=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['source_actor_canvases'],[[32,32]])
        self.assertEqual(r['underlay_bypassed_pixels'],1023)
        self.assertEqual(r['geometry']['oam_entries'],1)
        self.assertEqual(r['pieces'][0]['rows'][0],[0])
        self.assertLess(r['pieces'][0]['bank'],4)
        np.testing.assert_array_equal(pixels,original)

    def test_partition_bound_requires_a_transfer_window(self):
        with self.assertRaisesRegex(ValueError,'JOINT_DMA_PARTITION_REQUIRES_WINDOW'):
            probe(None,None,{},prepared_dma_partition=True)

    def test_dma_window_rejects_bank_label_symmetry(self):
        with self.assertRaisesRegex(ValueError,'JOINT_DMA_BANK_SYMMETRY_UNSAFE'):
            probe(None,None,{},prepared_dma_window=356,bank_symmetry=True)

    def test_dma_window_counts_both_color_bytes(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:2,:2]=np.arange(4).reshape(2,2)
        expected=background.copy()
        for y in range(2):
            for x in range(2):expected[y,x]=[int(pixels[y,x])*8,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[dict(kind=0,color=c,line=y,value=1)for y,c in ((0,0),(0,1),(1,2),(1,3))])
        for window,status in ((16,2),(17,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=2,prepared_dma_window=window,prepared_dma_partition=True,pool_residency=pool,time_limit=5)
            self.assertEqual(r['solver']['status'],status)
            if status==0:self.assertTrue(r['compiled_pixel_identity_verified'])

    def test_forced_opaque_row_requires_three_fixed_masks(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((32,32),-1,dtype=np.int32);pixels[0,:31]=np.arange(31)
        expected=background.copy()
        for x in range(31):expected[0,x]=[x*8,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=32,write_budget=0,time_limit=5,bank_symmetry=True)
        self.assertEqual(result['mandatory_geometry_lower_bound'],dict(oam_entries=3,peak_sprites=3,peak_tile_slivers=12))
        self.assertEqual(result['geometry']['oam_entries'],3)
        self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_joint_encoding_preserves_opaque_black_and_negative_residual(self):
        background=np.full((224,256,3),112,dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32)
        pixels[0,0]=0;pixels[0,1]=32767;pixels[1,0]=31
        actors=[dict(pixels=pixels,left=0,top=0)]
        expected=background.copy()
        expected[0,0]=0;expected[0,1]=255;expected[1,0]=[255,0,0]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)), patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=5,feasibility_only=True,bank_symmetry=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['peak_scheduled_writes'],0)
        black_pieces=[p for p in result['pieces'] if 0 in p['rows'].get(0,[])]
        self.assertEqual(len(black_pieces),1)
        self.assertLess(black_pieces[0]['bank'],4)
        self.assertTrue(result['no_color_reduction'])
        self.assertFalse(result['native_presentation_proven'])

    def test_four_opaque_banks_need_liveness_for_sixty_four_identities(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.arange(64,dtype=np.int32).reshape(8,8)
        expected=background.copy()
        expected[:8,:8]=np.stack([(pixels>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        for budget in (0,1):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)), patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=budget,time_limit=5)
            if budget==0:
                self.assertEqual(result['status'],'BOUNDED_JOINT_SOLVER_NO_CANDIDATE')
                self.assertEqual(result['solver']['status'],2)
                self.assertFalse(result['universal_raster_rejected'])
            else:
                self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
                self.assertEqual(result['peak_scheduled_writes'],1)
                self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_saturated_additive_alternatives_are_replayed_exactly(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=[248,248,248]
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:2]=32767
        expected=background.copy();expected[0,:2]=255
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=5,saturated_reuse=True,feasibility_only=True,bank_symmetry=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(result['additive_alternative_count'],3)
        self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_visible_bounds_shift_pieces_without_changing_source_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((90,110),-1,dtype=np.int32);pixels[20:76,9:86]=31
        expected=background.copy();expected[40:96,39:116]=[255,0,0]
        actors=[dict(pixels=pixels,left=30,top=20)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=32,write_budget=0,time_limit=5,align_visible_bounds=True,bank_symmetry=True)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['oam_entries'],6)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertGreater(result['trace'][0]['colors_written'],0)
        self.assertEqual(min(p['local_x'] for p in result['pieces']),9)
        self.assertEqual(min(p['local_y'] for p in result['pieces']),20)

    def test_early_row_limit_is_enforced_before_late_window(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.arange(64,dtype=np.int32).reshape(8,8)
        expected=background.copy()
        expected[:8,:8]=np.stack([(pixels>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        for early,late_start,expected_status in ((0,75,2),(1,75,0),(0,1,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=1,time_limit=5,early_write_budget=early,late_start=late_start,bank_symmetry=True,feasibility_only=True)
            self.assertEqual(result['solver']['status'],expected_status)
            if expected_status==0:
                self.assertTrue(result['compiled_pixel_identity_verified'])
                self.assertLessEqual(max((row['colors_written'] for row in result['trace'][1:late_start]),default=0),early)

    def test_pool_gap_cannot_reload_evicted_initial_color_for_free(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,64),-1,dtype=np.int32)
        pixels[0,0]=pixels[2,0]=0;pixels[1,:60]=np.arange(1,61)
        expected=background.copy()
        for y,x in zip(*np.where(pixels>=0)):
            c=int(pixels[y,x]);expected[y+44,x]=[(c>>shift&31)*8 for shift in (0,5,10)]
        actors=[dict(pixels=pixels,left=0,top=44)]
        entries=[dict(kind=0,color=c,line=y,value=1) for c in range(1,61) for y in (44,45)]
        entries += [dict(kind=0,color=0,line=y,value=1) for y in (44,46)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=entries)
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,early_write_budget=1,late_start=46,time_limit=5,pool_residency=pool,bank_symmetry=True,feasibility_only=True)
        self.assertEqual(result['solver']['status'],2)
        self.assertFalse(result['universal_raster_rejected'])

    def test_mixed_geometry_replays_actual_nonoverlapping_piece_masks(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[2,2]=31;pixels[2,3]=0
        expected=background.copy();expected[46,2]=[255,0,0]
        actors=[dict(pixels=pixels,left=0,top=44)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[dict(kind=0,color=color,line=y,value=1)for color in (0,31)for y in range(44,47)])
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size='mixed',write_budget=0,time_limit=5,pool_residency=pool,clip_horizontal=True,pin_pool_intervals=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertTrue(result['full_pool_intervals_retained'])
        self.assertEqual(result['pool_residency_intervals'],2)
        self.assertEqual(len(result['piece_pixel_masks']),1)
        data=np.frombuffer(bytes.fromhex(result['piece_pixel_masks'][0]['pixels_hex']),dtype=np.uint8)
        self.assertEqual(int(np.count_nonzero(data&15)+np.count_nonzero(data>>4)),2)


if __name__=='__main__':unittest.main()
