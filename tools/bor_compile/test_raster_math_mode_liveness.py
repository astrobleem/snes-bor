import unittest
from raster_math_mode_liveness import lower_bound


class ModeLivenessTests(unittest.TestCase):
    def test_shared_mode_cannot_choose_different_mode_for_each_pixel(self):
        rows=[{'a':{(0,(7,)),(1,())},'b':{(0,()),(1,(7,))}}]
        for integer in (False,True):
            result=lower_bound(rows,capacities=(0,1),integer_modes=integer)
            self.assertEqual(result['status'],'RELAXED_MODE_LIVENESS_INFEASIBLE')
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


if __name__=='__main__':unittest.main()
