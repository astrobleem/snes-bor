import importlib.util,unittest
from raster_fixed_slot_permutation import optimize
from raster_row_slot_permutations import optimize as layout
from raster_slot_refine import verify_packets
from raster_slot_greedy import demand
from test_raster_slot_layout import SlotLayoutTests
import numpy as np


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class FixedSlotPermutationTests(unittest.TestCase):
    def test_permutation_preserves_pixels_banks_and_write_lifetimes(self):
        source=layout(SlotLayoutTests().schedule(),356,10,True)
        result=optimize(source,5)
        self.assertEqual(source['pieces'],result['pieces'])
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):self.assertTrue(np.array_equal(a,b))
        for a,b in zip(source['trace'],result['trace']):
            self.assertEqual(sorted((e['bank'],e['color'],e['old'])for e in a['updates']),sorted((e['bank'],e['color'],e['old'])for e in b['updates']))
        self.assertFalse(result['native_presentation_proven'])
        self.assertFalse(result['physical_slot_layout']['universal_raster_rejected'])

    def test_bad_time_budget_rejected(self):
        with self.assertRaisesRegex(ValueError,'TIME_DOMAIN'):optimize({},0)

    def test_bank_permutation_keeps_math_classes_and_source_pixels(self):
        source=layout(SlotLayoutTests().schedule(),356,10,True)
        source['color_math']='additive'
        result=optimize(source,5,True)
        mapping=result['physical_slot_layout']['fixed_piece_bank_permutation']
        self.assertEqual(sorted(mapping.values()),list(range(8)))
        for a,b in mapping.items():self.assertEqual(a//4,b//4)
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):self.assertTrue(np.array_equal(a,b))


if __name__=='__main__':unittest.main()
