import hashlib,unittest
from unittest.mock import patch
import numpy as np
from source_obj_rectangle_cover import cover
from source_scene_obj_joint import probe
from source_bg_feasibility import rgb555


class RectangleCoverTests(unittest.TestCase):
    def test_empty_pixels_do_not_get_opaque_ownership(self):
        pixels=np.full((24,24),-1,dtype=np.int32);pixels[1,1]=0;pixels[17,17]=31
        actors=[dict(pixels=pixels,left=0,top=10)]
        result=cover(actors,time_limit=3)
        self.assertTrue(result['source_visible_pixel_ownership_verified'])
        self.assertFalse(result['bank_assignment_proven'])
        self.assertEqual(result['geometry']['oam_entries'],2)
        shifted=cover(actors,time_limit=3,origin=(4,4))
        self.assertTrue(shifted['source_visible_pixel_ownership_verified'])
        self.assertTrue(any(p['local_x']<0 for p in shifted['rectangles']))

    def test_tile_limit_failure_is_restricted_and_explicit(self):
        result=cover([dict(pixels=np.ones((8,16),dtype=np.int32),left=0,top=0)],time_limit=3,maximum_tiles=1)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_geometry_rejected'])

    def test_joint_compiler_rechecks_geometry_pixels_and_source_identity(self):
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[1,1]=31;pixels[2,2]=0
        actors=[dict(pixels=pixels,left=0,top=0)]
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[1,1,0]=248
        rectangles=cover(actors,time_limit=3)
        rectangles.update(metadata={},source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size='mixed',mixed_large_size=16,rectangle_cover=rectangles,write_budget=0,time_limit=3,solver_backend='cp-sat')
            self.assertTrue(result['compiled_pixel_identity_verified'])
            rectangles['rectangles']*=2
            with self.assertRaisesRegex(ValueError,'PIXEL_OWNERSHIP'):probe(None,None,{},size='mixed',mixed_large_size=16,rectangle_cover=rectangles)
            rectangles['source_rgb555_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'SOURCE_IDENTITY'):probe(None,None,{},rectangle_cover=rectangles)

    def test_subdivision_can_reduce_palette_mask_tile_overflow(self):
        actors=[];background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();rectangles=[]
        # Every 16-wide row has sixteen words: a single bank cannot encode it.
        # Two overlapping 16-wide masks cost 4 slivers; two 8-wide masks cost 2.
        for i in range(16):
            pixels=np.full((16,16),-1,dtype=np.int32);pixels[0]=1
            actors.append(dict(pixels=pixels,left=i*16,top=0))
            expected[0,i*16:i*16+16,0]=pixels[0]*8
            rectangles.append(dict(actor=i,local_x=0,local_y=0,x=i*16,y=0,width=16,height=16))
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[0]=np.arange(1,17)
        actors.append(dict(pixels=pixels,left=0,top=1));expected[1,:16,0]=pixels[0]*8
        rectangles.append(dict(actor=16,local_x=0,local_y=0,x=0,y=1,width=16,height=16))
        plan=dict(status='SOURCE_EXACT_OBJ_RECTANGLE_COVER_PROVEN',metadata={},rectangles=rectangles,
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            kwargs=dict(size='mixed',mixed_large_size=16,rectangle_cover=plan,color_math='precomposited',write_budget=0,time_limit=10,solver_backend='cp-sat',bank_symmetry=True)
            rejected=probe(None,None,{},**kwargs)
            result=probe(None,None,{},subdivide_rectangle_cover=True,**kwargs)
        self.assertEqual(rejected['solver']['status'],2)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['peak_tile_slivers'],34)
        self.assertLessEqual(result['geometry']['peak_sprites'],32)


if __name__=='__main__':unittest.main()
