import unittest
from raster_math_mode_liveness import lower_bound


class ModeLivenessTests(unittest.TestCase):
    def test_shared_mode_cannot_choose_different_mode_for_each_pixel(self):
        rows=[{'a':{(0,(7,)),(1,())},'b':{(0,()),(1,(7,))}}]
        for integer in (False,True):
            result=lower_bound(rows,capacities=(0,1),integer_modes=integer)
            self.assertIn(result['status'],('RELAXED_MODE_LIVENESS_INFEASIBLE','ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE'))
            self.assertFalse(result['schedule_proven'])

    def test_native_mode_can_change_between_lines_without_rewriting_shared_operand(self):
        rows=[{'a':{(0,(7,))},'b':{(0,())}},{'a':{(1,())},'b':{(1,(7,))}}]
        result=lower_bound(rows,capacities=(0,1),integer_modes=True,write_budget=0)
        self.assertEqual(result['selected_modes'],{0:'a',1:'b'})
        self.assertEqual(result['peak_write_objective'],0)
        self.assertFalse(result['schedule_proven'])

    def test_one_mode_recovers_exact_necessary_write_bound(self):
        rows=[{'a':{(i,())}}for i in range(3)]
        result=lower_bound(rows,capacities=(1,1))
        self.assertAlmostEqual(result['validated_dual_lower_bound'],1)
        self.assertEqual(result['maximum_dual_residual'],0)
        failed=lower_bound(rows,capacities=(1,1),integer_modes=True,write_budget=0)
        self.assertEqual(failed['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')

    def test_fractional_modes_still_require_whole_pixel_coverage(self):
        rows=[{'a':{(0,()),(1,())},'b':{(0,()),(1,())}}]
        result=lower_bound(rows,capacities=(1,1))
        self.assertEqual(result['status'],'ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE')

    def test_modes_exceeding_integer_opaque_capacity_are_removed_before_fractional_relaxation(self):
        rows=[{'a':{(0,()),(1,())},'b':{(0,(7,)),(1,(7,))}}]
        result=lower_bound(rows,capacities=(1,1))
        self.assertEqual(result['mode_variables'],1)
        self.assertEqual(result['forced_opaque_modes_pruned'],[dict(scanline=0,mode='a',forced_opaque_colors=2)])
        self.assertAlmostEqual(result['validated_dual_lower_bound'],0)

    def test_union_coverage_filters_pruned_operands_independently_on_each_line(self):
        rows=[{'a':{(0,(7,))},'b':{(0,())}},{'a':{(1,())},'b':{(1,(8,))}}]
        union=[{(0,(7,99))},{(1,(8,99))}]
        result=lower_bound(rows,capacities=(0,1),union_rows=union)
        self.assertAlmostEqual(result['validated_dual_lower_bound'],1)
        self.assertEqual(len(result['forced_opaque_modes_pruned']),2)

    def test_two_windows_can_represent_mask_that_one_window_cannot(self):
        rows=[{'add':{(1,()),(2,(1,))}}]
        pixels=[[dict(x=x,output=1 if x%2==0 else 2,modes={'add':()if x%2==0 else(1,)})for x in range(4)]]
        union=[{(1,(1,)),(2,(1,2))}]
        for changes,expected in ((2,'RELAXED_MODE_LIVENESS_INFEASIBLE'),(4,'RELAXED_MODE_LIVENESS_CANDIDATE')):
            result=lower_bound(rows,capacities=(0,1),union_rows=union,window_pixels=pixels,integer_windows=True,integer_modes=True,maximum_window_transitions=changes)
            self.assertEqual(result['status'],expected)
            if changes==4:self.assertEqual(result['selected_window_eligibility'],{0:{0:0,1:1,2:0,3:1}})
            self.assertFalse(result['schedule_proven'])


if __name__=='__main__':unittest.main()
