import copy,unittest
import numpy as np
from raster_physical_slot_permute import permute
from raster_row_slot_permutations import optimize
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
import test_raster_slot_layout as fixtures


class PhysicalSlotPermutationTests(unittest.TestCase):
    def test_fixed_slot_search_retains_source_and_write_times_without_mutation(self):
        source=optimize(fixtures.SlotLayoutTests().schedule(),356,5)
        source['trace'][2]['prefetched']=source['trace'][2]['updates']
        before=copy.deepcopy(source)
        result=permute(source,2000,7,5,1)
        self.assertEqual(source,before)
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(source['pieces'],result['pieces'])
        self.assertEqual([len(r['updates'])for r in source['trace']],[len(r['updates'])for r in result['trace']])
        report=result['physical_slot_layout']
        self.assertLessEqual(report['final_score'],report['initial_score'])
        self.assertFalse(report['native_timing_admitted'])
        self.assertTrue(all(sorted(p)==list(range(1,16))for p in report['opaque_slot_permutations']))

    def test_invalid_budget_rejected(self):
        with self.assertRaisesRegex(ValueError,'PERMUTATION_DOMAIN'):permute({},steps=-1)


if __name__=='__main__':unittest.main()
