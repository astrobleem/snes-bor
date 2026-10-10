import itertools,unittest
from raster_bank_search import assign
from raster_palette_interval import interval_bound

class BankSearchTests(unittest.TestCase):
 def test_matches_exhaustive_tiny_graphs_and_eligibility(self):
  patterns=({0:list(range(10)),1:list(range(5,15))},{0:list(range(10,20)),1:list(range(15,25))},{0:list(range(5)),1:list(range(20,25))})
  for masks in itertools.product((1,2,3),repeat=3):
   pieces=[dict(rows=rows,allowed_banks=[b for b in (0,1)if mask&(1<<b)])for rows,mask in zip(patterns,masks)]
   for budget in (None,0,3,10):
    valid=[]
    for candidate in itertools.product((0,1),repeat=3):
     if any(b not in p['allowed_banks']for p,b in zip(pieces,candidate)):continue
     demands=[{b:{c for p,bb in zip(pieces,candidate)if bb==b for c in p['rows'][y]}for b in(0,1)}for y in(0,1)]
     if any(len(s)>15 for row in demands for s in row.values()):continue
     lower=sum(max(0,len(demands[0][b]|demands[1][b])-15)for b in(0,1))
     if budget is None or lower<=budget:valid.append(candidate)
    result=assign(pieces,(0,1),time_limit=2,adjacent_write_budget=budget)
    self.assertEqual('assignment'in result,bool(valid))
    if valid:self.assertIn(tuple(result['assignment']),valid)
 def test_unused_bank_symmetry_does_not_drop_an_assignment(self):
  pieces=[dict(rows={0:list(range(i*8,i*8+8))})for i in range(4)]
  r=assign(pieces,range(4));self.assertEqual(len(set(r['assignment'])),4)
 def test_interval_relaxes_banks_and_allows_pending_low_byte(self):
  r=interval_bound([set(range(6)),set(range(6,12))],slots=6,window_master_clocks=88)
  self.assertEqual(r['worst_interval']['minimum_window_cgram_data_bytes'],11)
  self.assertEqual(r['status'],'LOWER_BOUND_DOES_NOT_REJECT')
  r=interval_bound([set(range(6)),set(range(6,12))],slots=6,window_master_clocks=80)
  self.assertEqual(r['status'],'CGRAM_DATA_WINDOW_INFEASIBLE')
 def test_multi_line_bound_rejects_even_when_adjacent_pairs_fit(self):
  rows=[set(range(0,5)),set(range(5,10)),set(range(10,15))]
  r=interval_bound(rows,slots=10,window_master_clocks=32)
  self.assertEqual(r['status'],'CGRAM_DATA_WINDOW_INFEASIBLE');self.assertEqual(r['worst_interval']['minimum_new_color_commits'],5)
if __name__=='__main__':unittest.main()
