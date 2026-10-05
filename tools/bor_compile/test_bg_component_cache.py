import unittest
import numpy as np
from bg_component_cache import cache_plane,row_transfer


class ComponentCacheTests(unittest.TestCase):
    def test_two_frames_share_unchanged_tiles_and_reconstruct_encoded_pixels(self):
        a=np.zeros((224,256),dtype=np.uint8);b=a.copy();b[80:88,80:88]=3
        raw,maps=cache_plane([a,b],2)
        self.assertEqual(len(raw),32)
        for expected,tilemap in zip((a,b),maps):
            decoded=np.zeros_like(expected)
            for y in range(28):
                for x in range(32):
                    tile=raw[int(tilemap[y,x])*16:int(tilemap[y,x])*16+16]
                    for row in range(8):
                        for col in range(8):
                            decoded[y*8+row,x*8+col]=sum(
                                ((tile[row*2+p]>>(7-col))&1)<<p for p in range(2))
            self.assertTrue(np.array_equal(decoded,expected))
        delta=row_transfer(maps[0],maps[1],0xf000)
        self.assertEqual(delta['vram_byte_address'],0xf000+10*64)
        self.assertEqual(delta['bytes'],64)
        self.assertIsNone(row_transfer(maps[0],maps[0],0xf000))


if __name__=='__main__':unittest.main()
