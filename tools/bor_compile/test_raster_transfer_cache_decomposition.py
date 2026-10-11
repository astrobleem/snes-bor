import copy,unittest
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from raster_transfer_cache_decomposition import search,cache_cut
from raster_bank_residency import favorable_span
from test_raster_slot_greedy import source_schedule


class TransferCacheTests(unittest.TestCase):
    def test_linear_master_preserves_fractional_and_failure_scopes(self):
        r=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=2,master_backend='highs')
        self.assertEqual(r['status'],'INTEGER_BANK_BUDGET_FRACTIONAL_CACHE_CANDIDATE')
        self.assertAlmostEqual(r['iterations'][-1]['cache_fractional_deficit'],0)
        self.assertFalse(r['compiled_pixel_identity_verified'])
        self.assertFalse(r['native_timing_admitted'])
        r=search(source_schedule(),write_budget=1,time_limit=5,master_seconds=2,master_backend='highs')
        self.assertTrue(r['fixed_bank_transfer_family_rejected'])
        self.assertFalse(r['universal_raster_rejected'])
        with self.assertRaisesRegex(ValueError,'MASTER_BACKEND'):
            search(source_schedule(),master_backend='highs',range_backend='adjacent')

    def test_budget_hint_is_checked_and_never_grants_pixel_admission(self):
        first=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=1)
        result=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=1,budget_hint=first['bank_write_caps'])
        self.assertTrue(result['budget_hint_supplied'])
        self.assertEqual(result['status'],'INTEGER_BANK_BUDGET_FRACTIONAL_CACHE_CANDIDATE')
        self.assertFalse(result['compiled_pixel_identity_verified'])
        self.assertFalse(result['native_timing_admitted'])
        for bad in ({},dict(first['bank_write_caps'],junk=[0]*8)):
            with self.assertRaises(ValueError):search(source_schedule(),budget_hint=bad)
        bad=copy.deepcopy(first['bank_write_caps']);next(iter(bad.values()))[0]=True
        with self.assertRaisesRegex(ValueError,'BUDGET_HINT_DOMAIN'):search(source_schedule(),budget_hint=bad)

    def test_local_budget_rejection_does_not_reject_whole_fixed_bank_family(self):
        first=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=1)
        hint=first['bank_write_caps']
        local=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=1,budget_hint=hint,budget_repair_interval=[7,12])
        self.assertEqual(local['status'],'INTEGER_BANK_BUDGET_FRACTIONAL_CACHE_CANDIDATE')
        for y,v in local['bank_write_caps'].items():
            if not 7<=y<=12:self.assertEqual(v,hint[y])
        blocked=search(source_schedule(),window=17,write_budget=2,time_limit=5,master_seconds=1,budget_hint=hint,budget_repair_interval=[7,12])
        self.assertTrue(blocked['fixed_budget_repair_family_rejected'])
        self.assertFalse(blocked['fixed_bank_transfer_family_rejected'])
        self.assertFalse(blocked['universal_raster_rejected'])
        with self.assertRaisesRegex(ValueError,'BUDGET_REPAIR_DOMAIN'):
            search(source_schedule(),budget_repair_interval=[7,12])

    def test_positive_deficit_cut_excludes_bad_budget_and_keeps_every_feasible_budget(self):
        # Required resident R=1, R<=W, and W<=budget+deficit.
        matrix=csc_matrix([[1,-1,0],[-1,0,0],[0,1,-1]])
        objective=np.array([0.,0.,1.]);rhs=np.array([0.,-1.,0.])
        bounds=[(0,1),(0,1),(0,None)]
        bad=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=bounds)
        self.assertAlmostEqual(bad.fun,1)
        coefficients,target,certificate=cache_cut(matrix,objective,rhs,np.ones(2),{(1,0):2},bad,{(1,0):0})
        self.assertLess(0,target)
        self.assertAlmostEqual(certificate['constant'],1)
        corrupt=copy.deepcopy(bad);corrupt.ineqlin.marginals[0]=1
        with self.assertRaisesRegex(ValueError,'CUT_DUAL_DOMAIN'):
            cache_cut(matrix,objective,rhs,np.ones(2),{(1,0):2},corrupt,{(1,0):0})
        for budget in range(1,16):
            right=rhs.copy();right[2]=budget
            good=linprog(objective,A_ub=matrix,b_ub=right,bounds=bounds)
            self.assertAlmostEqual(good.fun,0)
            self.assertGreaterEqual(coefficients[1,0]*budget,target)

    def test_candidate_never_grants_integer_cache_pixel_or_native_admission(self):
        for backend in ('flow','adjacent'):
            r=search(source_schedule(),write_budget=2,lookahead=0,time_limit=5,master_seconds=1,range_backend=backend)
            self.assertEqual(r['status'],'INTEGER_BANK_BUDGET_FRACTIONAL_CACHE_CANDIDATE')
            for row in r['bank_write_caps'].values():
                self.assertLess(favorable_span([dict(bank=b)for b,n in enumerate(row)for _ in range(n)]),345)
            self.assertFalse(r['compiled_pixel_identity_verified'])
            self.assertFalse(r['physical_slot_schedule_proven'])
            self.assertFalse(r['native_timing_admitted'])
            self.assertNotIn('piece_pixel_masks',r)
            self.assertAlmostEqual(r['iterations'][-1]['cache_fractional_deficit'],0)

    def test_necessary_master_failure_is_fixed_family_only(self):
        for budget,window in ((1,345),(2,17)):
            r=search(source_schedule(),write_budget=budget,window=window,time_limit=5,master_seconds=1)
            self.assertTrue(r['fixed_bank_transfer_family_rejected'])
            self.assertFalse(r['universal_raster_rejected'])
            self.assertEqual(r['iterations'][0]['master_status'],'INFEASIBLE')

    def test_invalid_resource_domains_reject(self):
        for kwargs in (dict(window=0),dict(write_budget=True),dict(lookahead=-1),dict(iterations=0),dict(range_backend='bad')):
            with self.assertRaises(ValueError):search(source_schedule(),**kwargs)


if __name__=='__main__':unittest.main()
