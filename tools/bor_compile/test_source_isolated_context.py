import io,tempfile,unittest
from pathlib import Path
from PIL import Image
from source_isolated_context import isolated_source,fixed_bank_context
from unittest.mock import patch
import numpy as np


class IsolatedContextTests(unittest.TestCase):
    def test_compaction_checks_final_oam_limit_after_exact_mask_merging(self):
        pixels=np.ones((72,128),dtype=np.int32)
        background=np.zeros((224,256,3),dtype=np.uint8)
        expected=background.copy();expected[:72,:128,0]=8
        def run(compact):
            with patch('source_isolated_context.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_isolated_context.compose_rgb8',return_value=(background,{})):
                return fixed_bank_context(None,None,{},time_limit=10,global_color_banks=True,compact_geometry=compact)
        rejected=run(False)
        self.assertEqual(rejected['status'],'FIXED_SMALL_GEOMETRY_LIMIT')
        result=run(True)
        self.assertTrue(result['hardware_geometry_admitted'])
        self.assertEqual(result['geometry_compaction']['original_geometry']['oam_entries'],144)
        self.assertLessEqual(result['geometry']['oam_entries'],128)
        self.assertLessEqual(result['geometry']['peak_tile_slivers'],34)
        self.assertTrue(result['geometry_compaction']['pixel_bank_slot_identity_verified'])

    def test_fixed_context_preserves_opaque_black_and_transparent_pixels(self):
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:2]=[0,31]
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[0,1,0]=248
        for global_banks in(False,True):
            with patch('source_isolated_context.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_isolated_context.compose_rgb8',return_value=(background,{})):
                result=fixed_bank_context(None,None,{},time_limit=10,global_color_banks=global_banks)
            self.assertTrue(result['source_opaque_mask_identity_verified'])
            self.assertEqual(result['source_visible_opaque_pixels'],2)
            self.assertEqual(result['source_opaque_output_rgb555_colors'],2)
            from raster_slot_greedy import demand
            _,_,decoded=demand(result)
            self.assertEqual(sum(np.count_nonzero(a>=0)for a in decoded),2)
            self.assertEqual({int(c)for a in decoded for c in a[a>=0]},{0,31})

    def test_virtual_underlay_preserves_original_assets_without_writing_files(self):
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder);(p/'actor.bin').write_bytes(b'original source bytes')
            source,stage,metadata=isolated_source(p,(12,34,56))
            self.assertEqual(source.read('actor.bin'),b'original source bytes')
            self.assertIn(b'order a',source.read(stage))
            with Image.open(io.BytesIO(source.read(metadata['virtual_underlay'])))as image:
                self.assertEqual(image.size,(256,224));self.assertEqual(image.getpalette()[:3],[12,34,56])
                self.assertEqual(set(image.getdata()),{0})
            self.assertEqual(list(p.iterdir()),[p/'actor.bin'])
            self.assertFalse(metadata['authored_stage_pixels_present'])

    def test_invalid_color_and_existing_asset_collision_are_explicit(self):
        with self.assertRaisesRegex(ValueError,'ISOLATED_UNDERLAY_RGB8'):isolated_source('unused',(0,0,256))
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder);(p/'BYOR_PROOF').mkdir();(p/'BYOR_PROOF'/'CONSTANT_UNDERLAY.PNG').write_bytes(b'owned')
            with self.assertRaisesRegex(ValueError,'ISOLATED_VIRTUAL_ASSET_COLLISION'):isolated_source(p)
            self.assertEqual((p/'BYOR_PROOF'/'CONSTANT_UNDERLAY.PNG').read_bytes(),b'owned')


if __name__=='__main__':unittest.main()
