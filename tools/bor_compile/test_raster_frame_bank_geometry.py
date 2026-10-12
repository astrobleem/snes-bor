import unittest
from raster_frame_bank_geometry import search,subdivided_candidates


class FrameBankGeometryTests(unittest.TestCase):
    def test_fixed_piece_bank_lifetime_rejects_per_row_bank_switch(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        result=search(rectangles,{(0,0):{0:[0]},(1,0):{4:[33]}},height=8,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual({p['bank']for p in result['pieces']},{0,4})
        self.assertTrue(result['fixed_bank_for_entire_oam_rectangle'])
        self.assertFalse(result['native_presentation_proven'])

    def test_fifteen_slot_banks_are_not_one_pool(self):
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        pixels={(0,x):{0:[x]}for x in range(16)}
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])
        pixels[0,15]={1:[15]}
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)

    def test_full_transparent_padding_cannot_exceed_sliver_limit(self):
        rectangles=[dict(x=8*i,y=0,width=32,height=32,allowed_banks=[i%8])for i in range(9)]
        pixels={(0,8*i):{i%8:[i]}for i in range(9)}
        # Rectangles overlap, so force each point into its own rectangle by bank.
        for i,p in enumerate(rectangles):p['allowed_banks']=[i%8]
        result=search(rectangles,pixels,height=32,time_limit=3)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['native_presentation_proven'])

    def test_generic_subdivision_preserves_source_positions_and_word_options(self):
        parents=[dict(actor=0,x=0,y=0,local_x=0,local_y=0,width=32,height=32)]
        points={(0,0):{0:[0]},(8,9):{4:[33]}}
        candidates=subdivided_candidates(parents,points)
        self.assertEqual(len(candidates),3)
        self.assertTrue(all(p['x']==p['local_x']and p['y']==p['local_y']for p in candidates))
        result=search(candidates,points,height=32,time_limit=3)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual(result['geometry']['peak_tile_slivers'],1)

    def test_class_symmetry_requires_equivalent_eligible_word_domains(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        points={(0,0):{b:[0]for b in range(4)}}
        result=search(rectangles,points,height=8,time_limit=3,bank_symmetry=True)
        self.assertEqual(result['pieces'][0]['bank'],0)
        self.assertTrue(result['safe_class_bank_label_symmetry'])
        points[0,0][1]=[33]
        with self.assertRaisesRegex(ValueError,'UNSAFE_SYMMETRY'):search(rectangles,points,bank_symmetry=True)

    def test_equivalent_points_coalesce_only_with_identical_geometry_owners(self):
        points={(0,0):{0:[0]},(0,1):{0:[0]}}
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        result=search(rectangles,points,height=8,time_limit=3)
        self.assertEqual(result['equivalent_pixel_decision_atoms'],1)
        self.assertEqual(len(result['pixels']),2)
        rectangles.append(dict(x=1,y=0,width=8,height=8))
        result=search(rectangles,points,height=8,time_limit=3)
        self.assertEqual(result['equivalent_pixel_decision_atoms'],2)

    def test_feasibility_only_retains_all_bank_and_geometry_constraints(self):
        rectangles=[dict(x=0,y=0,width=32,height=32)]
        points={(0,x):{0:[x]}for x in range(16)}
        rejected=search(rectangles,points,height=32,time_limit=3,feasibility_only=True)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        points[0,15]={1:[15]}
        result=search(rectangles,points,height=32,time_limit=3,feasibility_only=True)
        self.assertEqual(result['solver_objective'],'FEASIBILITY_ONLY')
        self.assertEqual(result['geometry']['oam_entries'],2)

    def test_subset_geometry_hint_is_soft_and_replayed(self):
        rectangles=[dict(x=0,y=0,width=8,height=8)]
        hint=search(rectangles,{(0,0):{0:[0]}},height=8,time_limit=3)
        result=search(rectangles,{(0,0):{0:[0]},(1,0):{4:[33]}},height=8,time_limit=3,geometry_hint=hint)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertGreater(result['soft_geometry_hint_variables'],0)
        hint['pixels'][0]['color']=1
        with self.assertRaisesRegex(ValueError,'HINT_PIXEL'):
            search(rectangles,{(0,0):{0:[0]}},height=8,time_limit=3,geometry_hint=hint)


if __name__=='__main__':unittest.main()
