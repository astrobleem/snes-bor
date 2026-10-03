import io
import unittest
from PIL import Image
from frame_packing import pack_image,reconstruct,transition_delta,viewport_resources


def png(image):
    data=io.BytesIO();image.save(data,format='PNG');return data.getvalue()


class PackingTests(unittest.TestCase):
    def test_large_merge_preserves_every_pixel(self):
        raw=png(Image.new('P',(32,64),1));packed=pack_image(raw,(7,13))
        self.assertTrue(reconstruct(raw,packed))
        self.assertEqual([p['size'] for p in packed['pieces']],[[32,64]])
        self.assertEqual(packed['tile_bytes'],1024)

    def test_transparent_canvas_trim_is_not_art_crop(self):
        image=Image.new('P',(160,160));image.putpixel((159,159),1)
        raw=png(image);packed=pack_image(raw)
        self.assertTrue(reconstruct(raw,packed))
        self.assertEqual(packed['bbox'],[159,159,160,160])
        self.assertEqual(packed['tile_bytes'],256)
        self.assertEqual(packed['nonempty_tiles'],1)

    def test_empty_frame_requires_nothing(self):
        packed=pack_image(png(Image.new('P',(64,64))))
        self.assertEqual(packed['pieces'],[])
        self.assertEqual(packed['tile_bytes'],0)

    def test_offsets_do_not_change_visible_source_pixels(self):
        image=Image.new('P',(43,78));image.paste(2,(3,5,39,70))
        raw=png(image);packed=pack_image(raw,(22,76))
        self.assertTrue(reconstruct(raw,packed))
        for p in packed['pieces']:
            x,y=p['source_xy'];w,_=p['size']
            self.assertEqual(p['right_xy'],[x-22,y-76])
            self.assertEqual(p['left_xy'],[22-x-w+1,y-76])

    def test_identical_transition_has_zero_missing_content(self):
        packed=pack_image(png(Image.new('P',(32,64),1)))
        self.assertEqual(transition_delta(packed,packed)['new_bytes'],0)
        self.assertFalse(transition_delta(packed,packed)['physical_placement_proven'])

    def test_large_canvas_is_not_total_visible_oam(self):
        packed=pack_image(png(Image.new('P',(660,550),1)))
        resource=viewport_resources(packed)
        self.assertGreater(len(packed['pieces']),128)
        self.assertEqual(resource['oam_entries'],32)
        self.assertTrue(resource['fits'])
        self.assertFalse(resource['hardware_verified'])


if __name__=='__main__':unittest.main()
