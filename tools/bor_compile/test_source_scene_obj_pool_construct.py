import hashlib,unittest
from unittest.mock import patch
import numpy as np
from source_bg_feasibility import rgb555
from source_scene_obj_pool_construct import construct,select_words
from raster_math_windows import compile_mask
from raster_palette import split_color_masks


class PoolConstructionTests(unittest.TestCase):
    def test_legal_large_pieces_subdivide_only_over_capacity_rows(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        for piece_size,words,expected_entries in ((16,np.full((16,16),6,dtype=np.int32),1),
                                                 (16,np.tile(np.arange(1,17,dtype=np.int32),(16,1)),4),
                                                 (32,np.full((16,16),6,dtype=np.int32),1),
                                                 (32,np.tile(np.arange(1,17,dtype=np.int32),(16,1)),4)):
            expected=background.copy();expected[:16,:16,0]=words*8
            candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
                source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
                selected_modes={str(y):'add'for y in range(16)},
                compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(16)},
                selected_palette_residency={str(y):{'0':sorted(set(map(int,words[y]))),'1':[]}for y in range(16)})
            with patch('source_scene_obj_pool_construct.prepare',return_value=([dict(pixels=words,left=0,top=0)],{},expected)),patch('source_scene_obj_pool_construct.compose_rgb8',return_value=(background,{})):
                result=construct(None,None,{},candidate,time_limit=5,local_piece_banks=True,piece_size=piece_size)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertEqual(result['geometry']['oam_entries'],expected_entries)
            self.assertEqual(result['geometry']['peak_tile_slivers'],4 if piece_size==32 and expected_entries==1 else 2)
            self.assertTrue(all(p['width']in(8,piece_size)for p in result['pieces']))
            self.assertEqual(result['obsel_mode'],1 if piece_size==32 else 0)
        with self.assertRaisesRegex(ValueError,'PIECE_SIZE'):
            construct(None,None,{},None,piece_size=24)

    def test_local_piece_bank_policy_rejects_conflicting_geometry_modes(self):
        for kwargs in (dict(joint_bank_geometry=True),dict(persistent_word_indices=True),dict(bank_residency_window_lines=8)):
            with self.assertRaisesRegex(ValueError,'LOCAL_PIECE_BANK_POLICY'):
                construct(None,None,{},None,local_piece_banks=True,**kwargs)

    def test_outside_math_preference_preserves_exact_pixels_and_bank_domains(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:16,:8,0]=32
        expected=background.copy();expected[:16,:8,0]=48
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,selected_modes={str(y):'add'for y in range(8)},compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(8)},selected_palette_residency={str(y):{'0':[6],'1':[2]}for y in range(8)})
        for prefer in (False,True):
            with patch('source_scene_obj_pool_construct.prepare',return_value=([dict(pixels=np.full((16,8),6,dtype=np.int32),left=0,top=0)],{},expected)),patch('source_scene_obj_pool_construct.compose_rgb8',return_value=(background,{})):
                result=construct(None,None,{},candidate,time_limit=5,banks_by_kind={0:(3,),1:(7,)},prefer_math_outside_controls=prefer,local_piece_banks=True)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertFalse(result['global_color_bank_identity_restricted'])
            self.assertTrue(all(p['allowed_banks']==[p['bank']]for p in result['pieces']))
            self.assertEqual([p['bank']for p in result['pieces']],[3,7]if prefer else[3,3])
            self.assertEqual(result['prefer_exact_math_outside_control_rows'],prefer)
            self.assertFalse(result['native_presentation_proven'])
        with self.assertRaisesRegex(ValueError,'OUTSIDE_MATH_POLICY'):
            construct(None,None,{},candidate,frame_word_cover=True,prefer_math_outside_controls=True)

    def test_exact_operand_cover_and_fixed_bank_pixel_replay(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:8,:8,0]=32
        expected=background.copy();expected[:8,:8,0]=16
        pixels=np.full((8,8),2,dtype=np.int32)
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={str(y):'subtract'for y in range(8)},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(8)},
            selected_palette_residency={str(y):{'0':[],'1':[6]}for y in range(8)})
        for frame_cover,joint,fixed_indices,banks in ((False,False,False,None),(True,False,False,None),(False,True,False,None),(False,True,True,None),(False,False,False,{0:(3,),1:(7,)}),(False,True,False,{0:(3,),1:(7,)}),(False,True,True,{0:(3,),1:(7,)})):
            with patch('source_scene_obj_pool_construct.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_pool_construct.compose_rgb8',return_value=(background,{})):
                result=construct(None,None,{},candidate,time_limit=10,frame_word_cover=frame_cover,joint_bank_geometry=joint,persistent_word_indices=fixed_indices,banks_by_kind=banks)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertTrue(result['hardware_geometry_admitted'])
            self.assertEqual(result['geometry']['oam_entries'],1)
            self.assertGreaterEqual(result['pieces'][0]['bank'],4)
            if banks is not None:
                self.assertEqual(result['pieces'][0]['bank'],7)
                self.assertEqual(result['eligible_banks_by_math_class'],{0:[3],1:[7]})
            self.assertEqual(result['peak_selected_colors_by_class'],[0,1])
            self.assertFalse(result['native_presentation_proven'])
            self.assertEqual(result['operand_selection_policy'],'GREEDY_EXACT_FRAME_SET_COVER'if frame_cover else'GREEDY_EXACT_ROW_SET_COVER')

    def test_bank_domains_reject_wrong_math_class_or_duplicate_banks(self):
        for banks in ({0:(4,),1:(7,)},{0:(3,),1:(3,)},{0:(3,),1:(7,7)},{0:(),1:(7,)}):
            with self.assertRaisesRegex(ValueError,'BANK_CLASS_DOMAIN'):
                construct(None,None,{},None,banks_by_kind=banks)

    def test_deferred_geometry_does_not_silently_admit_sprite_overflow(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:[1]})for _ in range(33)]
        normal=split_color_masks(pieces,(0,),solver_backend='cp-sat',time_limit=10)
        self.assertEqual(normal['status'],'MASK_GRID_INFEASIBLE')
        deferred=split_color_masks(pieces,(0,),solver_backend='cp-sat',time_limit=10,defer_geometry_admission=True)
        self.assertEqual(len(deferred['pieces']),33)
        self.assertTrue(deferred['geometry_admission_deferred'])

    def test_greedy_cover_shares_exact_word_and_rejects_empty_options(self):
        owners,words=select_words([{(0,1),(1,6)},{(0,2),(1,6)}])
        self.assertEqual(words,[(1,6)])
        self.assertEqual(set(owners.values()),{(1,6)})
        owners,words=select_words([{(0,1),(1,6)},{(0,2),(1,6)}],{(0,1):1,(0,2):1})
        self.assertEqual(set(words),{(0,1),(0,2)})
        with self.assertRaisesRegex(ValueError,'PIXEL_WITHOUT_EXACT_WORD'):select_words([set()])


if __name__=='__main__':unittest.main()
