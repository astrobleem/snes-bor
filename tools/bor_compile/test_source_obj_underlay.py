import unittest
import numpy as np
from source_obj_underlay import compile_underlay,encode8,decode8


class UnderlayTests(unittest.TestCase):
    def test_all_eight_planes_replay(self):
        for offset in range(4):
            tile=np.arange(offset*64,(offset+1)*64,dtype=np.uint8).reshape(8,8)
            self.assertTrue(np.array_equal(decode8(encode8(tile)),tile))

    def test_black_is_opaque_and_tiles_deduplicate(self):
        pixels=np.zeros((16,16),dtype=np.uint16);pixels[:,1::2]=32767
        report,data,mapping,palette=compile_underlay(pixels)
        self.assertEqual(report['unique_8x8_tiles'],1)
        self.assertEqual(report['colors'],2)
        self.assertTrue(report['source_pixel_identity_verified'])
        self.assertFalse(report['native_presentation_proven'])
        self.assertEqual(set(decode8(data).flat),{1,2})
        self.assertEqual(np.frombuffer(palette,dtype='<u2')[1],0)
        self.assertEqual(len(mapping),2048)

    def test_resource_failures_are_explicit(self):
        with self.assertRaisesRegex(ValueError,'LOWER_CGRAM_CAPACITY'):compile_underlay(np.arange(128,dtype=np.uint16).reshape(8,16))
        with self.assertRaisesRegex(ValueError,'RGB555_DOMAIN'):compile_underlay(np.full((8,8),32768,dtype=np.uint16))
        with self.assertRaisesRegex(ValueError,'VIEWPORT_DOMAIN'):compile_underlay(np.zeros((7,8),dtype=np.uint16))
        pixels=np.random.default_rng(21).integers(0,2,size=(224,256),dtype=np.uint16)
        with self.assertRaisesRegex(ValueError,'CHR_VRAM_CAPACITY'):compile_underlay(pixels)


if __name__=='__main__':unittest.main()
