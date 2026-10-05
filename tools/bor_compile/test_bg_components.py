import unittest
import numpy as np
from bg_components import split_pixels,compile_frame,schedule_group


class BgComponentTests(unittest.TestCase):
    def test_all_rgb555_colors_reconstruct_without_reduction(self):
        pixels=np.arange(32768,dtype=np.uint16).reshape(128,256)
        for bits in ((1,1,1),(2,1,1),(1,2,1),(1,1,2),(0,1,1),(1,0,1),(1,1,0)):
            high,low,palette=split_pixels(pixels,bits)
            self.assertTrue(np.array_equal(high+np.array(palette)[low],pixels))
            self.assertLessEqual(max(palette),32767)
            self.assertLessEqual(int(low.max()),15)

    def test_static_palette_and_black_keep_opaque_bg1_indices(self):
        pixels=np.zeros((224,256),dtype=np.uint16);pixels[:,128:]=32767
        r,high,low=compile_frame(pixels)
        self.assertEqual(r['solver']['status'],'STATIC_COMPONENT_PALETTE_PROVEN')
        self.assertTrue(r['pixel_identity_verified'])
        self.assertGreater(int(high.min()),0)
        self.assertEqual(r['peak_hblank_colors_written'],0)

    def test_invalid_component_capacity_rejected(self):
        with self.assertRaises(ValueError):split_pixels(np.array([0]),(2,2,1))
        with self.assertRaises(ValueError):compile_frame(np.zeros((224,256),dtype=np.uint16),capacity=240)

    def test_shared_schedule_keeps_unchanged_pixels_at_same_indices(self):
        a=np.zeros((224,256),dtype=np.uint16);a[:,128:]=32767
        b=a.copy();b[80:88,80:88]=1024
        solved=schedule_group([a,b],(0,1,1))
        ra,ha,la=compile_frame(a,(0,1,1),236,7,solved)
        rb,hb,lb=compile_frame(b,(0,1,1),236,7,solved)
        self.assertTrue(ra['pixel_identity_verified'] and rb['pixel_identity_verified'])
        self.assertTrue(np.array_equal(ha[a==b],hb[a==b]))
        self.assertTrue(np.array_equal(la[a==b],lb[a==b]))


if __name__=='__main__':unittest.main()
