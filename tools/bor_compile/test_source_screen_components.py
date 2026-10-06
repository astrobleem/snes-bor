import unittest
import numpy as np
from source_screen_components import projection_tables


class ScreenComponents(unittest.TestCase):
    def test_every_rgb8_pair_preserves_rgb555_components(self):
        raw=np.frombuffer(projection_tables(),dtype=np.uint8).reshape(4,65536).astype(np.uint16)
        packed=raw[0]|raw[1]|((raw[2]|raw[3])<<8)
        low=packed>>14;key=packed&8191
        actual=(key&31)|(((((key>>5)&15)*2)+(low&1))<<5)|(((((key>>9)&15)*2)+(low>>1))<<10)
        i=np.arange(65536,dtype=np.uint32)
        v=(255-((255-(i&255))*(255-(i>>8))//255))>>3
        expected=v|(v<<5)|(v<<10)
        self.assertTrue(np.array_equal(actual,expected))
        self.assertFalse(np.any(packed&0x2000))


if __name__=='__main__':unittest.main()
