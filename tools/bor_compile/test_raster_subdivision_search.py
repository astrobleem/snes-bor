import unittest
import numpy as np
from raster_subdivision_search import search
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class SubdivisionSearchTests(unittest.TestCase):
    def test_preserves_source_canvas_and_does_not_claim_admission(self):
        source=source_schedule();result=search(source,1,5,2,4,0)
        def canvas(schedule):
            image=np.full((len(schedule['trace']),256),-1,dtype=np.int32)
            for piece,colors in zip(schedule['pieces'],demand(schedule)[2]):
                for y,x in zip(*np.where(colors>=0)):image[piece['y']+y,piece['x']+x]=colors[y,x]
            return image
        np.testing.assert_array_equal(canvas(source),canvas(result))
        report=result['bounded_subdivision_search']
        self.assertLessEqual(report['final_interval_objective'],report['initial_interval_objective'])
        self.assertFalse(report['physical_transfer_admitted'])
        self.assertFalse(report['native_timing_admitted'])
        self.assertFalse(report['universal_raster_rejected'])
        self.assertTrue(report['no_color_reduction'])

    def test_invalid_budget_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'SUBDIVISION_SEARCH_DOMAIN'):search({},time_limit=0)


if __name__=='__main__':unittest.main()
