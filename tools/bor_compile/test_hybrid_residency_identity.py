"""Physical tile offset, eight planes and map flip decoding witnesses."""
import unittest
import numpy as np
from hybrid_residency_identity import decode_plane


class HybridIdentityTests(unittest.TestCase):
    def test_high_tile_offset_and_all_planes(self):
        vram=bytearray(65536)
        # Tile 64 is the first high BG tile after the 4096-byte OBJ atlas.
        for bit in range(8):
            if 0xa5&(1<<bit):vram[4096+(bit//2)*16+4+(bit%2)]=0x10
        vram[61440:61442]=(64).to_bytes(2,'little')
        actual=decode_plane(vram,61440,0,8)
        self.assertEqual(int(actual[2,3]),0xa5)
        self.assertEqual(np.count_nonzero(actual),1)

    def test_low_component_tile_flip(self):
        vram=bytearray(65536);vram[49152+16+4]=0x10;vram[49152+16+5]=0x10
        vram[63488:63490]=(1|0xc000).to_bytes(2,'little')
        actual=decode_plane(vram,63488,49152,2)
        self.assertEqual(int(actual[5,4]),3)
        self.assertEqual(np.count_nonzero(actual),1)


if __name__=='__main__':unittest.main()
