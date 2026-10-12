import unittest

from raster_palette_interval import interval_bound, transfer_interval


class IntervalBoundTests(unittest.TestCase):
 def test_transparent_bank_holes_reject_23_commits(self):
  rows=[set(range(120))]+[set(range(120+22*i,120+22*(i+1)))for i in range(6)]+[set(range(252,275))]
  relaxed=interval_bound(rows)
  banked=interval_bound(rows,obj_bank_gaps=True)
  self.assertEqual(relaxed['status'],'LOWER_BOUND_DOES_NOT_REJECT')
  self.assertEqual(transfer_interval(155,7)['minimum_peak_commit_span_master_clocks'],352)
  self.assertEqual(banked['status'],'CGRAM_DATA_WINDOW_INFEASIBLE')
  self.assertEqual(banked['worst_interval']['minimum_peak_color_commits'],23)
  self.assertEqual(banked['worst_interval']['minimum_peak_commit_span_master_clocks'],368)
  self.assertFalse(banked['feasibility_proven'])

 def test_bank_holes_do_not_reject_22_commits(self):
  report=interval_bound([set(range(120)),set(range(120,142))],obj_bank_gaps=True)
  self.assertEqual(report['status'],'LOWER_BOUND_DOES_NOT_REJECT')
  self.assertEqual(report['worst_interval']['minimum_peak_commit_span_master_clocks'],352)


if __name__=='__main__':unittest.main()
