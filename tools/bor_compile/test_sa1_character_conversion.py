import unittest
import numpy as np
from sa1_character_conversion import bitmap_bytes,type1_descriptor,reused_workspace_descriptors


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

    def test_reused_workspace_complete_rows_and_output_coverage(self):
        jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),
              dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
        ds=reused_workspace_descriptors(0x420000,0xd800,jobs)
        self.assertEqual([d['tile_count']for d in ds],[864,32,512])
        self.assertTrue(all(d['source']+d['bytes']<=0x42d800 for d in ds))
        self.assertEqual([(d['vram_word_address']*2,d['bytes'])for d in ds],[(0,55296),(55296,2048),(57344,8192)])
        for bpp in (2,4,8):
            pixels=np.arange(896*64,dtype=np.uint32).reshape(896,8,8)% (1<<bpp)
            rows=reused_workspace_descriptors(0x420000,8192,[dict(bpp=bpp,columns=16,tile_count=896,vram_byte_address=0)])
            pieces=[bitmap_bytes(pixels[d['tile_offset']:d['tile_offset']+d['tile_count']],bpp,16)for d in rows]
            self.assertEqual(b''.join(pieces),bitmap_bytes(pixels,bpp,16))
        with self.assertRaisesRegex(ValueError,'ONE_ROW'):reused_workspace_descriptors(0x420000,63,[jobs[0]])
        with self.assertRaisesRegex(ValueError,'VRAM_RANGE'):reused_workspace_descriptors(0x420000,8192,[dict(jobs[0],vram_byte_address=8194)])


if __name__=='__main__':unittest.main()
