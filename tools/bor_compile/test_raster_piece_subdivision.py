import copy,unittest
import numpy as np
from raster_piece_subdivision import subdivide,identities,select_for_bank_flexibility
from test_raster_retile import fixture


class SubdivisionTests(unittest.TestCase):
    def test_bounded_selection_preserves_pixels_and_entry_budget(self):
        source=self.source()
        for budget,wanted in ((2,1),(3,4)):
            result=select_for_bank_flexibility(source,budget)
            self.assertEqual(len(result['pieces']),wanted)
            self.assertEqual(identities(result),identities(source))
            self.assertLessEqual(result['bounded_subdivision_selection']['added_entries'],budget)
            self.assertFalse(result['bounded_subdivision_selection']['palette_and_transfer_feasibility_proven'])
        with self.assertRaisesRegex(ValueError,'ADDED_ENTRY_BUDGET'):select_for_bank_flexibility(source,True)

    def test_subdivision_counts_inherited_concurrent_geometry(self):
        source=self.source();height=len(source['trace'])
        source['geometry_reservation']=dict(oam_entries=124,sprites_per_line=[30]*height,tile_slivers_per_line=[32]*height)
        result=subdivide(source,[0])
        self.assertEqual(result['combined_reserved_geometry'],dict(oam_entries=128,peak_sprites=32,peak_tile_slivers=34))
        self.assertFalse(result['reservation_palette_and_layer_demand_included'])
        source['geometry_reservation']['oam_entries']=125
        rejected=subdivide(source,[0])
        self.assertEqual(rejected['status'],'SELECTIVE_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT')
        self.assertEqual(rejected['combined_reserved_geometry']['oam_entries'],129)
        self.assertFalse(rejected['universal_raster_rejected'])

    def source(self):
        source=fixture();source['pieces']=source['pieces'][:1];source['piece_pixel_masks']=source['piece_pixel_masks'][:1]
        p=source['pieces'][0];p.update(width=16,height=16)
        image=np.zeros((16,16),dtype=np.uint8);image[0,0]=image[0,8]=image[8,0]=image[8,8]=1
        flat=image.flatten();source['piece_pixel_masks'][0]=dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
        return source

    def test_four_legal_children_preserve_every_source_word_and_bank(self):
        source=self.source();result=subdivide(source,[0])
        self.assertEqual(identities(source),identities(result))
        self.assertEqual(result['geometry'],dict(oam_entries=4,peak_sprites_per_line=2,peak_tile_slivers_per_line=2))
        self.assertTrue(all(p['width']==p['height']==8 for p in result['pieces']))
        self.assertFalse(result['selective_piece_subdivision']['native_timing_admitted'])
        self.assertEqual(result['trace'],source['trace'])

    def test_empty_quadrants_do_not_cost_oam(self):
        source=self.source();image=np.zeros((16,16),dtype=np.uint8);image[0,0]=1;flat=image.flatten()
        source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        result=subdivide(source,[0]);self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertEqual(identities(source),identities(result))

    def test_limits_are_explicit_and_never_admit_an_overflow(self):
        source=self.source();source['pieces']*=17;source['piece_pixel_masks']*=17
        result=subdivide(source,range(17))
        self.assertEqual(result['status'],'SELECTIVE_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT')
        self.assertEqual(result['geometry']['peak_sprites_per_line'],34)
        self.assertFalse(result['universal_raster_rejected'])
        self.assertNotIn('pieces',result)

    def test_illegal_selection_or_parent_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'PIECE_DOMAIN'):subdivide(self.source(),[1])
        with self.assertRaisesRegex(ValueError,'16X16_PARENT'):subdivide(subdivide(self.source(),[0]),[0])


if __name__=='__main__':unittest.main()
