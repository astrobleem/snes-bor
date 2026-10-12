import io,tempfile,unittest
from pathlib import Path
from PIL import Image
from source_isolated_context import isolated_source,fixed_bank_context,literal_actor_context
from unittest.mock import patch
import numpy as np


class IsolatedContextTests(unittest.TestCase):
    def test_actor_domains_survive_fixed_bank_search_and_compaction(self):
        pixels=np.full((8,16),-1,dtype=np.int32);pixels[0,[0,8]]=31
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy()
        expected[0,[0,8],0]=248
        with patch('source_isolated_context.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_isolated_context.compose_rgb8',return_value=(background,{})):
            for backend in('csp','highs','cp-sat'):
                result=fixed_bank_context(None,None,{},actor_bank_domains=[[3]],bank_assignment_backend=backend,compact_geometry=True)
                self.assertTrue(result['compiled_pixel_identity_verified'])
                self.assertTrue(all(p['bank']==3 and p['allowed_banks']==[3]for p in result['pieces']))
            for domains in([], [[]], [[8]], [[True]], [[3,3]]):
                with self.assertRaisesRegex(ValueError,'ACTOR_BANK_DOMAINS'):fixed_bank_context(None,None,{},actor_bank_domains=domains)
            with self.assertRaisesRegex(ValueError,'DOMAINS_INCOMPATIBLE'):fixed_bank_context(None,None,{},actor_bank_domains=[[3]],global_color_banks=True)

    def test_literal_actor_bank_replays_black_and_rejects_alpha(self):
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[0,:2]=[0,31]
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[0,1,0]=248
        actor=dict(pixels=pixels,left=0,top=0,metadata=dict(alpha=0))
        with patch('source_isolated_context.prepare',return_value=([actor],{},expected)),patch('source_isolated_context.compose_rgb8',return_value=(background,{})):
            result=literal_actor_context(None,None,{},[2])
            self.assertEqual(result['pieces'][0]['bank'],2)
            self.assertEqual(result['pieces'][0]['width'],16)
            self.assertTrue(result['source_opaque_mask_identity_verified'])
            actor['metadata']['alpha']=1
            with self.assertRaisesRegex(ValueError,'LITERAL_OBJ_ALPHA'):literal_actor_context(None,None,{},[2])

    def test_literal_shared_bank_checks_combined_row_capacity(self):
        actors=[];background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy()
        for i in range(2):
            pixels=np.full((16,16),-1,dtype=np.int32);pixels[0,:8]=np.arange(i*8+1,i*8+9)
            actors.append(dict(pixels=pixels,left=i*16,top=0,metadata=dict(alpha=0)))
            expected[0,i*16:i*16+8,0]=pixels[0,:8]*8
        with patch('source_isolated_context.prepare',return_value=(actors,{},expected)),patch('source_isolated_context.compose_rgb8',return_value=(background,{})):
            with self.assertRaisesRegex(ValueError,'BANK_ROW_OVERFLOW'):literal_actor_context(None,None,{},[0,0])
            self.assertTrue(literal_actor_context(None,None,{},[0,1])['compiled_pixel_identity_verified'])

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
