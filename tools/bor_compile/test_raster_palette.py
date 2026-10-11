"""Admission and identity checks for offline raster scheduling."""
import unittest
import numpy as np
from raster_palette import prove_frame, schedule,bounded_schedule, assign_banks, split_scene_color_masks,split_color_masks


class RasterPaletteTests(unittest.TestCase):
    def test_prefetch_limits_allow_other_class_to_share_write_budget(self):
        piece=dict(rows={0:[0],2:[1],3:[2]})
        trace,states=schedule([piece],[0],4,lookahead=1,capacity=3,prefetch_write_limits={1:0,2:1})
        self.assertEqual(trace[1]['colors_written'],0)
        self.assertEqual(trace[2]['colors_written'],1)
        self.assertIn(1,states[2][0])
        self.assertIn(2,states[3][0])
        with self.assertRaisesRegex(ValueError,'PREFETCH_WRITE_LIMIT_DOMAIN'):schedule([piece],[0],4,prefetch_write_limits={1:-1})

    def test_temporal_union_restriction_preserves_colors_and_is_not_universal_rejection(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:list(range(8)),1:list(range(8,16))})]
        for backend in('highs','cp-sat'):
            ordinary=split_color_masks(pieces,(0,),time_limit=10,global_color_banks=True,solver_backend=backend)
            self.assertEqual(ordinary['status'],'COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN')
            blocked=split_color_masks(pieces,(0,),time_limit=10,global_color_banks=True,solver_backend=backend,residency_window_lines=2)
            self.assertEqual(blocked['status'],'MASK_GRID_INFEASIBLE')
            self.assertFalse(blocked['universal_raster_rejected'])
            valid=split_color_masks(pieces,(0,1),time_limit=10,global_color_banks=True,solver_backend=backend,residency_window_lines=2)
            self.assertEqual(valid['status'],'COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN')
            actual={}
            for p,b in zip(valid['pieces'],valid['assignment']):
                for y,cs in p['rows'].items():actual.setdefault(y,set()).update(cs)
            self.assertEqual(actual,{0:set(range(8)),1:set(range(8,16))})
        with self.assertRaisesRegex(ValueError,'MASK_RESIDENCY_WINDOW_DOMAIN'):split_color_masks(pieces,(0,),residency_window_lines=2)

    def test_global_mask_color_bank_identity_survives_rows_and_both_solvers(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:list(range(8)),1:list(range(8,16))}),
            dict(x=8,y=0,width=8,height=8,rows={0:list(range(8,16)),1:list(range(8))})]
        for backend in('highs','cp-sat'):
            result=split_color_masks(pieces,(0,1),time_limit=10,global_color_banks=True,solver_backend=backend,maximum_frame_colors_per_bank=8)
            self.assertEqual(result['status'],'COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN')
            identities={};required={}
            for piece,bank in zip(result['pieces'],result['assignment']):
                for y,colors in piece['rows'].items():
                    for color in colors:identities.setdefault(color,set()).add(bank);required.setdefault((y,bank),set()).add(color)
            self.assertEqual(set(identities),set(range(16)))
            self.assertTrue(all(len(banks)==1 for banks in identities.values()))
            self.assertTrue(all(len(colors)<=15 for colors in required.values()))
            for bank in(0,1):self.assertEqual(sum(bank in values for values in identities.values()),8)
            self.assertEqual(result['objective'],4)

    def test_piece_bank_eligibility_and_equal_colors_on_different_actors(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:[7]},allowed_banks=[0]),
                dict(x=8,y=0,width=8,height=8,rows={0:[7]},allowed_banks=[4])]
        self.assertEqual(assign_banks(pieces,[0,4])['assignment'],[0,4])
        r=split_scene_color_masks(pieces,[0,4])
        self.assertEqual(r['assignment'],[0,4])
        self.assertTrue(r['piece_row_color_identity_verified'])
        pieces[1]['allowed_banks']=[7]
        self.assertEqual(assign_banks(pieces,[0,4])['status'],'FIXED_GRID_INFEASIBLE')
        self.assertEqual(split_scene_color_masks(pieces,[0,4])['status'],'SCENE_MASK_GRID_INFEASIBLE')

    def test_transparent_frame_needs_no_objects_or_palette_writes(self):
        r=prove_frame(np.full((16,16),-1))
        self.assertEqual(r['geometry']['oam_entries'],0)
        self.assertTrue(r['pixel_identity_verified'])

    def test_bounded_schedule_preloads_and_enforces_real_slot_limit(self):
        piece=dict(rows={0:[1],1:[2],2:[3]})
        r=bounded_schedule([piece],[4],3,capacity=3,write_budget=0,lookahead=3)
        self.assertEqual(r['status'],'BOUNDED_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(sum(t['colors_written'] for t in r['trace'][1:]),0)
        rejected=bounded_schedule([piece],[4],3,capacity=2,write_budget=0,lookahead=3)
        self.assertEqual(rejected['status'],'WRITE_BUDGET_INFEASIBLE')
    def test_opaque_black_and_transparency_are_distinct(self):
        pixels=np.array([[0,-1,31],[32,0,-1]])
        r=prove_frame(pixels,banks=(4,))
        self.assertTrue(r['pixel_identity_verified'])
        self.assertEqual(r['pieces'][0]['rows'][0],[0,31])

    def test_optional_physical_slot_locks_are_checked(self):
        piece=dict(rows={0:[1,2],1:[1,2]})
        locks={(0,0,0):2,(0,0,1):2,(0,1,0):1,(0,1,1):1}
        r=bounded_schedule([piece],[0],2,capacity=2,write_budget=0,
                           slot_locks=locks,fixed_residency={(0,1,0):True})
        self.assertEqual(r['status'],'BOUNDED_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(r['states'][1][0],[2,1])
        conflict=bounded_schedule([piece],[0],2,capacity=2,write_budget=0,
                                  fixed_residency={(0,1,0):False})
        self.assertEqual(conflict['status'],'PINNED_REQUIRED_RESIDENCY_CONFLICT')

    def test_fixed_piece_over_capacity_cannot_use_another_bank_per_row(self):
        pixels=np.tile(np.arange(16),(16,1))
        r=prove_frame(pixels,size=(16,16),banks=(0,1))
        self.assertEqual(r['status'],'FIXED_GRID_INFEASIBLE')
        split=prove_frame(pixels,size=(16,16),banks=(0,1),color_masks=True)
        self.assertTrue(split['pixel_identity_verified'])
        self.assertEqual(split['geometry']['oam_entries'],2)

    def test_mask_solver_enforces_total_oam_admission(self):
        pixels=np.full((8*129,8),1)
        r=prove_frame(pixels,banks=(0,),color_masks=True)
        self.assertEqual(r['status'],'MASK_GRID_INFEASIBLE')

    def test_slot_liveness_retains_required_colors_and_preloads(self):
        pieces=[dict(rows={0:[1],1:[1],2:[2],3:[1,2]})]
        trace,states=schedule(pieces,[4],4,lookahead=3)
        self.assertTrue(trace[0]['prefetched'])
        self.assertEqual(sum(r['colors_written'] for r in trace[1:]),0)
        self.assertEqual(states[0][4],states[3][4])


if __name__=='__main__':unittest.main()
