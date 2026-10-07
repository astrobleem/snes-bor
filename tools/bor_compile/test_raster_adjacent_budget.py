import unittest
from raster_palette import split_scene_color_masks

class AdjacentBudgetTests(unittest.TestCase):
    def test_bank_union_lower_bound(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:list(range(8)),1:list(range(8,16))})]
        rejected=split_scene_color_masks(pieces,banks=[0],adjacent_write_budget=0,time_limit=5)
        self.assertEqual(rejected['status'],'SCENE_MASK_GRID_INFEASIBLE')
        admitted=split_scene_color_masks(pieces,banks=[0],adjacent_write_budget=1,time_limit=5)
        self.assertEqual(admitted['status'],'COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN')
        self.assertEqual(admitted['adjacent_write_lower_bounds'][1],1)
        self.assertFalse(admitted['complete_palette_write_schedule_proven'])
    def test_invalid_budget(self):
        with self.assertRaisesRegex(ValueError,'INVALID_ADJACENT_WRITE_BUDGET'):
            split_scene_color_masks([dict(x=0,y=0,width=8,height=8,rows={0:[1]})],adjacent_write_budget=-1)

if __name__=='__main__':unittest.main()
