import unittest
import json
from raster_palette_cover_liveness import lower_bound


class CoverLivenessTests(unittest.TestCase):
    def test_zero_normal_capacity_still_allows_exact_additive_reuse(self):
        result=lower_bound([{(0,(10,12))},{(1,(11,12))}],capacities=(0,1),include_solution=True)
        self.assertAlmostEqual(result['validated_dual_lower_bound'],0)
        self.assertTrue(all(e['value']==0 for e in result['fractional_residency'] if e['kind']==0))

    def test_zero_normal_capacity_rejects_forced_opaque_demand(self):
        result=lower_bound([{(0,None)}],capacities=(0,1))
        self.assertEqual(result['status'],'RELAXED_COVER_INFEASIBLE')

    def test_invalid_capacity_rejected(self):
        for capacities in ((0,0),(-1,1),(0,1.5)):
            with self.subTest(capacities=capacities),self.assertRaisesRegex(ValueError,'COVER_POOL_CAPACITY'):
                lower_bound([{(0,10)}],capacities=capacities)

    def test_forced_opaque_sequence_requires_one_write_each_line(self):
        result=lower_bound([{(0,None)},{(1,None)},{(2,None)}],capacities=(1,1))
        self.assertEqual(result['status'],'FRACTIONAL_COVER_LIVENESS_LOWER_BOUND')
        self.assertAlmostEqual(result['validated_dual_lower_bound'],1)
        self.assertFalse(result['schedule_proven'])

    def test_alternate_pool_can_preload_without_writes(self):
        result=lower_bound([{(0,10)},{(1,11)}],capacities=(1,1),include_solution=True)
        self.assertAlmostEqual(result['peak_write_lower_bound'],0)
        self.assertTrue(result['fractional_residency'])
        self.assertTrue(result['geometry_and_bank_assignment_relaxed'])

    def test_multiple_exact_operands_can_reuse_one_additive_identity(self):
        result=lower_bound([{(0,(10,12)),(1,(11,12)),(2,(12,))}],capacities=(1,1),include_solution=True,integer_budget=0)
        self.assertEqual(result['status'],'POOLED_INTEGER_RESIDENCY_CANDIDATE')
        self.assertEqual(result['candidate_peak_writes'],0)
        self.assertTrue(any(e['kind']==1 and e['color']==12 for e in result['fractional_residency']))
        self.assertFalse(result['schedule_proven'])

    def test_same_line_pool_capacity_failure_is_explicit(self):
        result=lower_bound([{(0,None),(1,None)}],capacities=(1,1))
        self.assertEqual(result['status'],'RELAXED_COVER_INFEASIBLE')
        self.assertFalse(result['schedule_proven'])

    def test_pinned_integer_candidate_retains_pool_nonclaim(self):
        result=lower_bound([{(0,None)},{(1,None)},{(2,None)}],capacities=(1,1),integer_budget=1,include_solution=True)
        self.assertEqual(result['status'],'POOLED_INTEGER_RESIDENCY_CANDIDATE')
        self.assertEqual(result['candidate_peak_writes'],1)
        self.assertIsInstance(result['candidate_peak_writes'],int)
        self.assertEqual(result['exact_new_colors_by_scanline'],{1:1,2:1})
        json.dumps(result)
        self.assertFalse(result['schedule_proven'])
        self.assertTrue(all(abs(e['value']-1)<1e-6 for e in result['fractional_residency']))


if __name__=='__main__':unittest.main()
