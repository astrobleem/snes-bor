import copy,unittest
import numpy as np
from raster_mask_rectangle_cover import cover
from raster_obj_compact import unpack


def fixture():
    state={b:[None]*15 for b in range(8)};trace=[]
    for y in range(16):
        before=copy.deepcopy(state);events=[]
        if y==0:
            for b,c in [(0,0),(4,33)]:
                events.append(dict(bank=b,slot=1,old=None,color=c));state[b][0]=c
        trace.append(dict(scanline=y,resident_before=before,updates=events))
    image=np.zeros((8,8),dtype=np.uint8);image[1,2]=1;image[6,7]=1
    flat=image.flatten();mask=dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
    return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,
        metadata=dict(source_dimensions=[48,16]),native_presentation_proven=True,
        pieces=[dict(actor=0,bank=b,x=x,y=4,local_x=x,local_y=4,width=8,height=8,allowed_banks=[b])for b,x in [(0,10),(4,30)]],
        piece_pixel_masks=[mask,copy.deepcopy(mask)],trace=trace)


def indexed_pixels(frame):
    return {(p['actor'],int(p['y']+y),int(p['x']+x)):(p['bank'],int(image[y,x]))
        for p,m in zip(frame['pieces'],frame['piece_pixel_masks'])for image in [unpack(m)]for y,x in zip(*np.where(image))}


class MaskCoverTests(unittest.TestCase):
    def test_non_grid_cover_preserves_opaque_black_and_all_bank_slot_identities(self):
        source=fixture();result=cover(source,time_limit=3,repair_hint=True)
        self.assertEqual(result['geometry_pixel_rectangle_cover']['status'],'FIXED_BANK_PIXEL_RECTANGLE_COVER_PROVEN')
        self.assertEqual(indexed_pixels(source),indexed_pixels(result))
        self.assertEqual(source['trace'],result['trace'])
        self.assertEqual(source['metadata'],result['metadata'])
        self.assertTrue(all(p['bank']in p['allowed_banks']for p in result['pieces']))
        self.assertFalse(result['native_presentation_proven'])
        self.assertFalse(result['geometry_pixel_rectangle_cover']['concurrent_palette_or_layer_admitted'])
        self.assertTrue(result['geometry_pixel_rectangle_cover']['repair_hint'])
        self.assertEqual(result['geometry_pixel_rectangle_cover']['combined_horizontal_tile_lower_bound'],2)
        self.assertGreater(result['geometry_pixel_rectangle_cover']['equivalent_candidate_rectangles_removed'],0)
        self.assertEqual(result['geometry_pixel_rectangle_cover']['raw_candidate_rectangles'],
            result['geometry_pixel_rectangle_cover']['candidate_rectangles']+
            result['geometry_pixel_rectangle_cover']['equivalent_candidate_rectangles_removed'])

    def test_full_reserved_tile_rows_reject_without_rejecting_general_raster(self):
        reserve=dict(oam_entries=0,sprites_per_line=[0]*16,tile_slivers_per_line=[34]*16)
        result=cover(fixture(),time_limit=3,geometry_reservation=reserve)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertEqual(result['combined_horizontal_tile_lower_bound'],36)
        self.assertFalse(result['universal_raster_rejected'])
        reserve['oam_entries']=True
        with self.assertRaisesRegex(ValueError,'RESERVATION'):cover(fixture(),geometry_reservation=reserve)

    def test_mismatched_actor_origin_fails_explicitly(self):
        source=fixture();source['pieces'][1]['local_x']+=1
        with self.assertRaisesRegex(ValueError,'ACTOR_ORIGIN'):cover(source)

    def test_native_highs_matches_exact_geometry_and_rejects_overflow(self):
        source=fixture();result=cover(source,time_limit=3,solver_backend='highspy')
        self.assertEqual(indexed_pixels(source),indexed_pixels(result))
        self.assertEqual(result['geometry'],dict(oam_entries=2,peak_sprites=2,peak_tile_slivers=2))
        self.assertEqual(result['geometry_pixel_rectangle_cover']['solver_backend'],'highspy')
        reserve=dict(oam_entries=0,sprites_per_line=[0]*16,tile_slivers_per_line=[34]*16)
        rejected=cover(source,time_limit=3,geometry_reservation=reserve,solver_backend='highspy')
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        self.assertFalse(rejected['universal_raster_rejected'])

    def test_multiple_visible_actor_owners_at_one_pixel_fail_explicitly(self):
        source=fixture();source['pieces'][1].update(actor=1,x=10,local_x=10)
        with self.assertRaisesRegex(ValueError,'GLOBAL_VISIBLE_OVERLAP'):cover(source)


if __name__=='__main__':unittest.main()
