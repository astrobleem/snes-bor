import unittest
import numpy as np
from raster_bank_lp_refine import refine
from raster_bank_rebalance import rebalance
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class LpRefineTests(unittest.TestCase):
    def test_verified_lp_improves_duplicate_color_traffic(self):
        source=source_schedule()
        for guidance in (False,True):
            result=refine(source,lookahead=0,maximum_trials=7,time_limit=10,dual_guidance=guidance,include_swaps=guidance)
            report=result['bank_lp_refinement']
            self.assertAlmostEqual(report['initial_validated_lower_bound'],2)
            self.assertAlmostEqual(report['final_validated_lower_bound'],1)
            self.assertTrue(any(t.get('accepted')for t in report['trials']))
            self.assertFalse(report['physical_transfer_admitted'])
            if guidance:
                pressure=report['initial_dual_pressure']
                self.assertTrue(pressure['dual_active_bank_capacity'])
                self.assertTrue(all(e['marginal']<0 for e in pressure['dual_active_bank_capacity']))
                self.assertLess(pressure['maximum_dual_residual'],1e-6)
            _,_,a=demand(source);_,_,b=demand(result)
            for old,new in zip(a,b):np.testing.assert_array_equal(old,new)

    def test_explicit_bank_assignment_is_validated_and_replayed(self):
        source=source_schedule()
        result=rebalance(source,maximum_moves=0,initial_assignment=[2,3])
        self.assertEqual([p['bank']for p in result['pieces']],[2,3])
        self.assertEqual(result['bank_rebalance']['explicit_initial_assignment'],[2,3])
        with self.assertRaisesRegex(ValueError,'EXPLICIT_ASSIGNMENT_DOMAIN'):rebalance(source,initial_assignment=[4,1])
        with self.assertRaisesRegex(ValueError,'EXPLICIT_ASSIGNMENT_DOMAIN'):rebalance(source,initial_assignment=[0])


if __name__=='__main__':unittest.main()
