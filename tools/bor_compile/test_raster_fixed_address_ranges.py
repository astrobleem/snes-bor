import importlib.util,random,unittest
from raster_physical_ranges import constrain_fixed_addresses
from raster_physical_relabel import point_partition


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class FixedAddressRangeTests(unittest.TestCase):
    def solve(self,points,window=3001):
        from ortools.sat.python import cp_model
        model=cp_model.CpModel();flags={}
        for address in points:
            b,s=divmod(address,16)
            flags.setdefault((1,b),[]).append((15*b+s-1,model.new_constant(1)))
        _,peak=constrain_fixed_addresses(model,flags,2,4,window)
        model.minimize(peak);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=5
        status=solver.solve(model)
        return status,solver.value(peak)if status in(cp_model.OPTIMAL,cp_model.FEASIBLE)else None

    def test_exact_cost_matches_independent_partition(self):
        from ortools.sat.python import cp_model
        rng=random.Random(3201);opaque=[a for a in range(128)if a%16]
        cases=[[1],[1,17,33,49,65],[14,15,17,18],[1,15,113,127],opaque]
        cases += [rng.sample(opaque,n)for n in(3,7,15,24)]
        for points in cases:
            with self.subTest(points=points):
                status,cost=self.solve(points)
                self.assertEqual(status,cp_model.OPTIMAL)
                self.assertEqual(max(0,cost-40),point_partition(points)[0])

    def test_strict_window_and_empty_row(self):
        from ortools.sat.python import cp_model
        points=[1,2,3,4];span=point_partition(points)[0]
        self.assertEqual(self.solve(points,span)[0],cp_model.INFEASIBLE)
        self.assertEqual(self.solve(points,span+1)[0],cp_model.OPTIMAL)
        self.assertEqual(self.solve([]),(cp_model.OPTIMAL,0))


if __name__=='__main__':unittest.main()
