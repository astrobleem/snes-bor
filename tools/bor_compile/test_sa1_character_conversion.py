import unittest
import numpy as np
from sa1_character_conversion import bitmap_bytes,type1_descriptor


class Conversion(unittest.TestCase):
    def test_bitmap_order_and_lsb_packing(self):
        pixels=np.arange(128,dtype=np.uint8).reshape(2,8,8)
        raw=bitmap_bytes(pixels,8,2)
        self.assertEqual(raw[:16],bytes([*range(8),*range(64,72)]))
        low=pixels%4
        self.assertEqual(bitmap_bytes(low,2,2)[:4],bytes([0xe4]*4))

    def test_alignment_and_lossless_domain(self):
        self.assertEqual(type1_descriptor(0x420000,8,16,128,0)['bytes'],8192)
        with self.assertRaisesRegex(ValueError,'ALIGNMENT'):type1_descriptor(0x420040,8,16,128,0)
        with self.assertRaisesRegex(ValueError,'PIXEL_RANGE'):bitmap_bytes(np.full((1,8,8),4),2,1)
        with self.assertRaisesRegex(ValueError,'COMPLETE_TILE_ROWS'):bitmap_bytes(np.zeros((3,8,8)),2,2)


if __name__=='__main__':unittest.main()
