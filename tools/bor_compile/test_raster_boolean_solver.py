import importlib.util
import unittest
from unittest.mock import patch
from functools import partial
import numpy as np
from scipy.sparse import coo_matrix
import test_source_scene_obj_joint as joint
from raster_boolean_solver import solve


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class BooleanMatrixTests(unittest.TestCase):
    def test_bounded_integer_transfer_count_is_not_a_boolean(self):
        result=solve(coo_matrix([[1,0],[1,-3]]),[3,0],[3,0],[0,0],time_limit=5,workers=1,variable_upper=[30,1])
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[3,1])
        self.assertEqual(result.boolean_stats['nonboolean_integer_variables'],1)

    def test_infeasible_hint_is_soft_and_cannot_replace_constraints(self):
        result=solve(coo_matrix([[1]]),[1],[1],[0],time_limit=5,workers=1,hint={0:0})
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[1])
        self.assertEqual(result.boolean_stats['hint_variables'],1)

    def test_incumbent_is_exact_boolean_constraint_witness(self):
        matrix=coo_matrix([[1,1],[1,-1]])
        result=solve(matrix,[1,-np.inf],[1,0],[0,0],time_limit=5,workers=1)
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[0,1])

    def test_infeasibility_is_reported_without_values(self):
        result=solve(coo_matrix([[1],[1]]),[1,0],[1,0],[0],time_limit=5,workers=1)
        self.assertEqual(result.status,2)
        self.assertIsNone(result.x)

    def test_fractional_constraint_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'NONINTEGER_COEFFICIENT'):
            solve(coo_matrix([[.5]]),[0],[1],[0])


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class BooleanJointReplayTests(joint.JointSceneSolverTests):
    def setUp(self):
        replacement=patch.object(joint,'probe',partial(joint.probe,solver_backend='cp-sat'))
        replacement.start();self.addCleanup(replacement.stop)


if __name__=='__main__':unittest.main()
