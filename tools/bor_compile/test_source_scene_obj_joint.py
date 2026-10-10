import unittest
from unittest.mock import patch
import numpy as np
from source_bg_feasibility import rgb555
from source_scene_obj_joint import probe


class JointSceneSolverTests(unittest.TestCase):
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
