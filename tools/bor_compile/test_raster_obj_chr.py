import unittest
import numpy as np
from raster_obj_chr import compile,encode,decode


class ObjChrTests(unittest.TestCase):
    def schedule(self,images):
        pieces=[];masks=[]
        for i,image in enumerate(images):
            n=image.shape[0];flat=image.flatten()
            pieces.append(dict(bank=i%8,x=i%8*8,y=i//8*8,width=n,height=n))
            masks.append(dict(width=n,height=n,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,pieces=pieces,piece_pixel_masks=masks)

    def test_tile_codec_preserves_every_four_bit_value_and_transparency(self):
        tile=np.arange(64,dtype=np.uint8).reshape(8,8)%16
        np.testing.assert_array_equal(decode(encode(tile)),tile)

    def test_second_page_oam_name_bit_and_size_bits_decode_exactly(self):
        images=[]
        for i in range(17):
            image=np.ones((32,32),dtype=np.uint8);image[0,0]=i%16;image[0,1]=i//16;images.append(image)
        report,data,oam=compile(self.schedule(images))
        self.assertEqual(report['occupied_tile_cells'],272)
        self.assertTrue(oam[16*4+3]&1)
        self.assertEqual((oam[512+16//4]>>(2*(16%4)))&2,2)
        self.assertTrue(report['emitted_oam_chr_pixel_indices_verified'])

    def test_identical_tile_indices_share_chr_across_palette_banks(self):
        image=np.ones((8,8),dtype=np.uint8)
        report,data,oam=compile(self.schedule([image]*8))
        self.assertEqual(report['occupied_tile_cells'],1)
        self.assertEqual(len(data),32)
        self.assertEqual({oam[4*i+3]>>1&7 for i in range(8)},set(range(8)))

    def test_reserved_cells_are_excluded_from_actual_placement(self):
        image=np.ones((32,32),dtype=np.uint8)
        report,data,oam=compile(self.schedule([image]),reserved=range(256))
        self.assertEqual(report['occupied_tile_cells'],16)
        self.assertTrue(oam[3]&1)
        self.assertEqual(data[:8192],bytes(8192))

    def test_legal_sixteen_and_thirty_two_pair_keeps_exact_tile_pitch(self):
        images=[np.arange(256,dtype=np.uint8).reshape(16,16)%16,np.arange(1024,dtype=np.uint16).reshape(32,32).astype(np.uint8)%16]
        r,data,oam=compile(self.schedule(images))
        self.assertEqual(r['obj_size_mode'],3)
        self.assertEqual(r['obj_size_pair'],[16,32])
        self.assertEqual(oam[512]&2,0)
        self.assertEqual((oam[512]>>2)&2,2)
        self.assertTrue(r['emitted_oam_chr_pixel_indices_verified'])
        r,data,oam=compile(self.schedule(images[:1]))
        self.assertEqual(r['obj_size_mode'],0)
        self.assertEqual(oam[512]&2,2)
        with self.assertRaisesRegex(ValueError,'INCOMPATIBLE_GLOBAL_SIZE_PAIR'):compile(self.schedule([np.zeros((n,n),dtype=np.uint8)for n in (8,16,32)]))


if __name__=='__main__':unittest.main()
