import importlib.util
import unittest
import numpy as np
from scipy.sparse import coo_matrix
from raster_dma_partition import constrain_ranges
from raster_boolean_solver import solve
from raster_cgram_packets import optimistic_dma_span


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class PhysicalRangeTests(unittest.TestCase):
    def witness(self,counts,window):
        upper=[];rows=[];lower=[];limits=[]
        def allocate():upper.append(1);return len(upper)-1
        def constraint(items,lo,hi):rows.append(items);lower.append(lo);limits.append(hi)
        writes={b:[allocate()for _ in range(n)]for b,n in enumerate(counts)}
        active={b:allocate()for b in range(8)}
        for b in range(8):
            for v in writes[b]:constraint([(v,1)],1,1)
            constraint([(active[b],1)],int(counts[b]>0),int(counts[b]>0))
        domains=constrain_ranges(writes,active,allocate,constraint,window)
        for v,limit in domains.items():upper[v]=limit
        rr=[];cc=[];vv=[]
        for i,row in enumerate(rows):
            for v,c in row:rr.append(i);cc.append(v);vv.append(c)
        matrix=coo_matrix((vv,(rr,cc)),shape=(len(rows),len(upper)))
        return solve(matrix,lower,limits,np.zeros(len(upper)),time_limit=5,workers=1,variable_upper=upper)

    def test_range_constraint_matches_independent_partition_dynamic_program(self):
        cases=[[1,1,1,0,0,0,0,0],[15]*8,[2,0,3,0,1,0,0,4],
               [0,0,0,1,1,0,0,0],[0]*8,[1,0,0,0,0,0,0,0]]
        for counts in cases:
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            required=max(0,optimistic_dma_span(updates)['best_partition_span_master_clocks']-8)
            with self.subTest(counts=counts):
                self.assertEqual(self.witness(counts,required+1).status,0)
                if required:self.assertEqual(self.witness(counts,required).status,2)

    def test_two_bridges_cannot_ignore_middle_bank_extent(self):
        counts=[1,1,1,0,0,0,0,0]
        self.assertEqual(self.witness(counts,72).status,2)
        self.assertEqual(self.witness(counts,81).status,0)


if __name__=='__main__':unittest.main()
