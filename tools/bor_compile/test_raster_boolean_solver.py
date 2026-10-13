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
    def test_joint_feasibility_flag_reaches_backend_and_replays_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[:8,:8,0]=16
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=np.full((8,8),2,dtype=np.int32),left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=joint.probe(None,None,{},size=8,write_budget=0,time_limit=5,
                solver_backend='cp-sat',feasibility_only=True)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        stats=result['solver']['boolean_stats']
        self.assertEqual(stats['search_objective'],'FEASIBILITY_ONLY')
        self.assertFalse(stats['optimal'])

    def test_feasibility_objective_preserves_constraints_without_optimality(self):
        result=solve(coo_matrix([[1,1],[1,-1]]),[1,-np.inf],[1,0],[1,2],time_limit=5,workers=1,feasibility_only=True)
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[0,1])
        self.assertFalse(result.boolean_stats['optimal'])
        self.assertEqual(result.boolean_stats['search_objective'],'FEASIBILITY_ONLY')
        with self.assertRaisesRegex(ValueError,'FEASIBILITY_DOMAIN'):
            solve(coo_matrix([[1]]),[1],[1],[0],feasibility_only=1)

    def test_sat_strategy_checks_integer_constraints_and_soft_hint(self):
        result=solve(coo_matrix([[1,0],[1,-3]]),[3,0],[3,0],[0,0],
                     time_limit=5,workers=1,variable_upper=[30,1],
                     hint={0:0,1:0},search_strategy='sat')
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[3,1])
        self.assertEqual(result.boolean_stats['search_strategy'],'sat')
        with self.assertRaisesRegex(ValueError,'SEARCH_STRATEGY'):
            solve(coo_matrix([[1]]),[1],[1],[0],search_strategy='unknown')

    def test_hint_repair_does_not_pin_invalid_palette_values(self):
        result=solve(coo_matrix([[1,0],[1,-3]]),[3,0],[3,0],[0,0],
                     time_limit=5,workers=1,variable_upper=[30,1],
                     hint={0:0,1:0},search_strategy='sat-repair')
        self.assertEqual(result.status,0)
        np.testing.assert_array_equal(result.x,[3,1])
        self.assertEqual(result.boolean_stats['search_strategy'],'sat-repair')

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
