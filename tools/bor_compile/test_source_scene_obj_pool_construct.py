import hashlib,unittest
from unittest.mock import patch
import numpy as np
from source_bg_feasibility import rgb555
from source_scene_obj_pool_construct import construct,select_words
from raster_math_windows import compile_mask
from raster_palette import split_color_masks


class PoolConstructionTests(unittest.TestCase):
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
        for frame_cover in (False,True):
            with patch('source_scene_obj_pool_construct.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_pool_construct.compose_rgb8',return_value=(background,{})):
                result=construct(None,None,{},candidate,time_limit=10,frame_word_cover=frame_cover)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertTrue(result['hardware_geometry_admitted'])
            self.assertEqual(result['geometry']['oam_entries'],1)
            self.assertGreaterEqual(result['pieces'][0]['bank'],4)
            self.assertEqual(result['peak_selected_colors_by_class'],[0,1])
            self.assertFalse(result['native_presentation_proven'])
            self.assertEqual(result['operand_selection_policy'],'GREEDY_EXACT_FRAME_SET_COVER'if frame_cover else'GREEDY_EXACT_ROW_SET_COVER')

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
