import unittest
import numpy as np
from raster_bank_rebalance import rebalance,subdivide
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class RebalanceTests(unittest.TestCase):
    def test_duplicate_piece_colors_merge_banks_without_pixel_changes(self):
        source=source_schedule();source['bank_search']={'maximum_frame_colors_per_bank':15,'residency_window_lines':2}
        result=rebalance(source,lookahead=0)
        self.assertNotIn('bank_search',result)
        self.assertEqual(result['input_bank_search'],source['bank_search'])
        self.assertEqual(result['bank_assignment_authority'],'bank_rebalance')
        r=result['bank_rebalance']
        self.assertLess(r['final_objective'],r['initial_objective'])
        self.assertEqual(result['pieces'][0]['bank'],result['pieces'][1]['bank'])
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        for old,new in zip(source['pieces'],result['pieces']):
            self.assertEqual({k:v for k,v in old.items()if k not in('rows','bank')},{k:v for k,v in new.items()if k not in('rows','bank')})
        self.assertFalse(r['native_timing_admitted'])

    def test_math_class_prevents_literal_and_math_bank_merge(self):
        source=source_schedule();source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for e in row['updates']:
                if e['bank']==1:e['bank']=5
        result=rebalance(source,lookahead=0)
        self.assertTrue(result['bank_rebalance']['color_math_classes_preserved'])
        self.assertLess(result['pieces'][0]['bank'],4);self.assertGreaterEqual(result['pieces'][1]['bank'],4)

    def test_no_move_preserves_assignment_and_replays_pixels(self):
        source=source_schedule();result=rebalance(source,lookahead=0,maximum_moves=0)
        self.assertEqual(result['bank_rebalance']['moves'],[])
        self.assertEqual([p['bank']for p in result['pieces']],[p['bank']for p in source['pieces']])
        self.assertTrue(result['bank_rebalance']['pixel_color_identity_verified'])

    def test_legal_subdivision_preserves_full_visible_color_canvas(self):
        source=source_schedule();p=source['pieces'][0];m=source['piece_pixel_masks'][0]
        image=np.zeros((32,32),dtype=np.uint8);image[:16,:16]=unpack(m);flat=image.flatten()
        p.update(width=32,height=32);m.update(width=32,height=32,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
        result=subdivide(source,[0]);self.assertEqual(result['geometry']['oam_entries'],5)
        def canvas(s):
            _,_,images=demand(s);a=np.full((16,256),-1,dtype=np.int32)
            for p,image in zip(s['pieces'],images):
                for y,x in zip(*np.where(image>=0)):a[p['y']+y,p['x']+x]=image[y,x]
            return a
        np.testing.assert_array_equal(canvas(source),canvas(result))
        self.assertLessEqual(result['geometry']['peak_sprites_per_line'],32)
        self.assertLessEqual(result['geometry']['peak_tile_slivers_per_line'],34)

    def test_legal_sixteen_pixel_subdivision_and_invalid_square(self):
        source=source_schedule();source['compiled_schedule_sha256']='old';source['physical_slot_layout']={'status':'old'};result=subdivide(source,[0])
        self.assertEqual(result['geometry']['oam_entries'],5)
        self.assertEqual(result['mixed_large_size'],16)
        self.assertNotEqual(result['compiled_schedule_sha256'],'old')
        self.assertEqual(result['bank_subdivision']['input_compiled_schedule_sha256'],'old')
        self.assertNotIn('physical_slot_layout',result)
        self.assertTrue(result['bank_subdivision']['pixels_exact'])
        source['pieces'][0]['width']=12
        with self.assertRaisesRegex(ValueError,'GREEDY_PIECE_DOMAIN'):subdivide(source,[0])


if __name__=='__main__':unittest.main()
