import importlib.util,random,unittest
import numpy as np
from raster_physical_relabel import point_partition,relabel
from raster_slot_greedy import partition,demand
from raster_row_slot_permutations import optimize
import test_raster_slot_layout as fixtures


class PhysicalPointPartitionTests(unittest.TestCase):
    def test_exact_gaps_match_independent_dynamic_program(self):
        rng=random.Random(432)
        for count in range(1,41):
            points=rng.sample(range(128),count)
            cost,groups=point_partition(points)
            self.assertEqual(cost,partition([(p,p)for p in points])[0])
            self.assertLessEqual(len(groups),4)
            self.assertTrue(all(any(lo<=p<=hi for lo,hi in groups)for p in points))


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class PhysicalRelabelTests(unittest.TestCase):
    def test_pixels_opaque_zero_and_eligible_classes_are_preserved(self):
        source=fixtures.SlotLayoutTests().schedule()
        hint=optimize(source,356,10)
        result=relabel(hint,5)
        _,_,before=demand(hint);_,_,after=demand(result)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))
        for p,q in zip(hint['pieces'],result['pieces']):
            self.assertEqual(p['bank']//4,q['bank']//4)
            self.assertEqual((p['x'],p['y'],p['width'],p['height']),(q['x'],q['y'],q['width'],q['height']))
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])
        self.assertFalse(result['physical_slot_layout']['universal_raster_rejected'])


if __name__=='__main__':unittest.main()
