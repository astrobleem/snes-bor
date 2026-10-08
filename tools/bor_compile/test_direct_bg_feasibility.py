import unittest
import numpy as np
from direct_bg_feasibility import split


class DirectBG(unittest.TestCase):
 def test_every_rgb555_matches_actual_direct_color_formula_plus_residual(self):
  pixels=np.arange(32768,dtype=np.uint16);high,low=split(pixels)
  restored=(((high.astype(np.uint16)&7)<<1)<<1)|((high.astype(np.uint16)&0x38)<<4)|((high.astype(np.uint16)&0xc0)<<7)
  self.assertTrue(np.array_equal(restored+low,pixels))
  self.assertEqual(int(high[1]),0);self.assertEqual(int(low[1]),1)
  self.assertEqual(int(high[32767]),255)


if __name__=='__main__':unittest.main()
