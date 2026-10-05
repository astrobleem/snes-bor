"""Admission and identity checks for offline raster scheduling."""
import unittest
import numpy as np
from raster_palette import prove_frame, schedule,bounded_schedule, assign_banks, split_scene_color_masks


class RasterPaletteTests(unittest.TestCase):
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
