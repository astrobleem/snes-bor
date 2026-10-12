import unittest
from raster_obj_compact import compact,unpack


class ObjCompactionTests(unittest.TestCase):
    def test_merge_retains_intersection_of_child_bank_domains(self):
        source=self.schedule([(0,4,0,0),(0,4,8,0)])
        source['pieces'][0]['allowed_banks']=[3,4]
        source['pieces'][1]['allowed_banks']=[4,5]
        result=compact(source)
        self.assertEqual(result['pieces'][0]['allowed_banks'],[4])
        source['pieces'][1]['allowed_banks']=[5]
        with self.assertRaisesRegex(ValueError,'PIECE_BANK_ELIGIBILITY'):compact(source)

    def test_no_legal_merge_reports_hardware_failure_without_admission(self):
        source=self.schedule([(i,0,i,0)for i in range(33)])
        source['status']='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW'
        result=compact(source)
        self.assertEqual(result['status'],'BOUNDED_FIXED_BANK_COMPACTION_NO_LEGAL_GEOMETRY')
        self.assertEqual(result['geometry']['peak_sprites'],33)
        self.assertFalse(result['hardware_geometry_admitted'])
        self.assertFalse(result['native_presentation_proven'])
        self.assertFalse(result['geometry_compaction']['universal_raster_rejected'])

    def schedule(self,positions):
        pieces=[];masks=[]
        for actor,bank,x,y in positions:
            pieces.append(dict(actor=actor,bank=bank,local_x=x,local_y=y,x=x,y=y,width=8,height=8,rows={y:[31]}))
            masks.append(dict(width=8,height=8,pixels_hex='01'+'00'*31))
        return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,
                    pieces=pieces,piece_pixel_masks=masks,trace=[{}]*64,geometry={},no_color_reduction=True)

    def test_merge_preserves_bank_slot_and_local_geometry(self):
        r=compact(self.schedule([(0,4,9,20),(0,4,17,20)]))
        self.assertEqual(r['geometry'],dict(oam_entries=1,peak_sprites=1,peak_tile_slivers=4))
        p=r['pieces'][0];self.assertEqual((p['bank'],p['local_x'],p['local_y'],p['width']),(4,9,20,32))
        image=unpack(r['piece_pixel_masks'][0]);self.assertEqual(int(image.sum()),2)
        self.assertEqual((int(image[0,0]),int(image[0,8])),(1,1))
        self.assertEqual(r['obsel_mode'],1)
        self.assertTrue(r['geometry_compaction']['pixel_bank_slot_identity_verified'])

    def test_transparent_extended_rows_must_count_towards_hardware_limits(self):
        r=compact(self.schedule([(0,0,0,0),(0,0,8,0)]+[(i+1,1,i*8,16)for i in range(32)]))
        self.assertEqual(r['geometry']['oam_entries'],34)
        self.assertEqual(r['geometry_compaction']['selected_merges'],0)
        self.assertEqual(r['geometry']['peak_sprites'],32)
        self.assertEqual(r['geometry']['peak_tile_slivers'],32)

    def test_different_banks_do_not_merge(self):
        r=compact(self.schedule([(0,0,0,0),(0,4,8,0)]))
        self.assertEqual(r['geometry']['oam_entries'],2)

    def test_16_pixel_pair_avoids_transparent_32_pixel_row_contention(self):
        source=self.schedule([(0,0,0,0),(0,0,8,0)]+[(i+1,1,i*8,16)for i in range(32)])
        source['status']='BOUNDED_FIXED_BANK_COMPACTION_NO_LEGAL_GEOMETRY'
        r=compact(source,large_size=16)
        self.assertEqual(r['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(r['geometry']['oam_entries'],33)
        self.assertEqual(r['geometry']['peak_sprites'],32)
        self.assertEqual(r['geometry_compaction']['selected_merges'],1)
        self.assertEqual(r['obsel_mode'],0)
        self.assertTrue(r['geometry_compaction']['pixel_bank_slot_identity_verified'])


if __name__=='__main__':unittest.main()
