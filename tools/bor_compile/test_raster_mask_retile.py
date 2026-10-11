import copy,hashlib,json,unittest
import numpy as np
from raster_mask_retile import retile
from raster_slot_greedy import demand


def fixture(points):
    state={b:[None]*15 for b in range(8)};trace=[]
    for y in range(32):
        before=copy.deepcopy(state);updates=[]
        if y==0:
            for b in range(8):
                updates.append(dict(bank=b,slot=1,old=None,color=31));state[b][0]=31
        trace.append(dict(scanline=y,resident_before=before,updates=updates))
    pieces=[dict(actor=a,bank=b,x=x,y=y,local_x=x,local_y=y,width=8,height=8,rows={y:[31]})for a,b,x,y in points]
    return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,
        pieces=pieces,trace=trace,piece_pixel_masks=[dict(width=8,height=8,pixels_hex='01'+'00'*31)for p in pieces],
        geometry=dict(oam_entries=len(pieces),peak_sprites=len(pieces),peak_tile_slivers=len(pieces)),
        source_rgb555_sha256='fixture',no_color_reduction=True)


class RetileTests(unittest.TestCase):
    def test_per_line_other_actor_reservations_are_replayed(self):
        source=fixture([(0,4,7,4),(0,4,8,4)])
        reservation=dict(oam_entries=127,sprites_per_line=[31]*32,tile_slivers_per_line=[33]*32)
        result=retile(source,5,geometry_reservation=reservation)
        self.assertEqual(result['mask_retile']['combined_reserved_geometry'],dict(oam_entries=128,peak_sprites=32,peak_tile_slivers=34))
        reservation['sprites_per_line'][4]=32
        self.assertEqual(retile(source,5,geometry_reservation=reservation)['solver_status'],'INFEASIBLE')
        for bad in ({},dict(reservation,oam_entries=True),dict(reservation,sprites_per_line=[0])):
            with self.assertRaisesRegex(ValueError,'RESERVATION_DOMAIN'):retile(source,geometry_reservation=bad)

    def test_mixed_size_pair_charges_full_tile_width(self):
        source=fixture([(0,4,7,4),(0,4,15,4)])
        result=retile(source,5,oam_limit=1,large_size=16)
        self.assertEqual(result['geometry'],dict(oam_entries=1,peak_sprites=1,peak_tile_slivers=2))
        self.assertEqual(result['pieces'][0]['width'],16)
        again=retile(result,5,large_size=16)
        self.assertEqual(again['geometry'],result['geometry'])
        small=retile(result,5)
        self.assertEqual(small['geometry']['oam_entries'],2)
        self.assertEqual(retile(source,5,oam_limit=1,tile_limit=1,large_size=16)['solver_status'],'INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'SIZE_PAIR_DOMAIN'):retile(source,large_size=32)
        with self.assertRaisesRegex(ValueError,'OBJECTIVE_DOMAIN'):retile(source,objective_kind='unknown')
        result=retile(source,5,large_size=16,objective_kind='tiles')
        self.assertEqual(result['geometry']['peak_tile_slivers'],2)
        self.assertEqual(result['mask_retile']['objective_kind'],'tiles')

    def test_shifted_sparse_masks_merge_without_changing_source_or_palette(self):
        source=fixture([(0,4,7,4),(0,4,8,4)])
        result=retile(source,time_limit=5)
        self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertEqual(result['trace'],source['trace'])
        self.assertEqual(sum(np.sum(im>=0)for im in demand(result)[2]),2)
        self.assertEqual(result['pieces'][0]['bank'],4)
        self.assertFalse(result['native_presentation_proven'])

    def test_banks_and_actors_do_not_merge_and_resources_are_explicit(self):
        for points in ([(0,0,7,4),(0,4,8,4)],[(0,4,7,4),(1,4,8,4)]):
            source=fixture(points)
            self.assertEqual(retile(source,5)['geometry']['oam_entries'],2)
            for kwargs in (dict(oam_limit=1),dict(sprite_limit=1),dict(tile_limit=1)):
                result=retile(source,5,**kwargs)
                self.assertEqual(result['solver_status'],'INFEASIBLE')
                self.assertFalse(result['universal_raster_rejected'])

    def test_extended_transparent_rows_count_and_invalid_inputs_reject(self):
        source=fixture([(0,0,7,4),(1,4,8,5)])
        self.assertEqual(retile(source,5,sprite_limit=1)['solver_status'],'INFEASIBLE')
        for kwargs in (dict(oam_limit=True),dict(sprite_limit=33),dict(tile_limit=35),dict(time_limit=0)):
            with self.assertRaisesRegex(ValueError,'RESOURCE_DOMAIN'):retile(source,**kwargs)
        source['pieces'][1]['local_x']+=1;source['pieces'][1]['actor']=0
        with self.assertRaisesRegex(ValueError,'ACTOR_ORIGIN'):retile(source)

    def test_hash_binds_source_math_controls(self):
        source=fixture([(0,4,7,4)])
        source.update(scanline_math_controls_source_bound=True,selected_modes={'4':'add'},compiled_color_window_descriptors={'4':{'bounds':[[3,8]]}})
        result=retile(source,5)
        before=result['compiled_schedule_sha256']
        payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'],
                     selected_modes=source['selected_modes'],compiled_color_window_descriptors=source['compiled_color_window_descriptors'])
        self.assertEqual(before,hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
        source['selected_modes']['4']='half-add'
        self.assertNotEqual(before,retile(source,5)['compiled_schedule_sha256'])


if __name__=='__main__':unittest.main()
