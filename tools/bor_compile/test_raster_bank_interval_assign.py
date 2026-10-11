import unittest
import numpy as np
from raster_bank_interval_assign import assign
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


class IntervalAssignmentTests(unittest.TestCase):
    def test_interval_bank_search_replays_words_and_keeps_scope_explicit(self):
        source=source_schedule()
        result=assign(source,0,8,write_budget=1,lookahead=0,time_limit=5,window=32)
        r=result['interval_bank_assignment']
        self.assertEqual(r['status'],'NECESSARY_INTERVAL_BANK_ASSIGNMENT_FOUND')
        self.assertEqual(r['interval_peak_writes'],1)
        self.assertTrue(r['independent_interval_replay_verified'])
        self.assertFalse(r['full_frame_schedule_proven'])
        self.assertTrue(r['outside_interval_cache_continuity_relaxed'])
        self.assertFalse(r['physical_transfer_admitted'])
        self.assertAlmostEqual(r['full_frame_cache_lower_bound']['validated_dual_lower_bound'],1)
        _,_,before=demand(source);_,_,after=demand(result)
        for a,b in zip(before,after):np.testing.assert_array_equal(a,b)

    def test_infeasible_interval_does_not_reject_raster_generally(self):
        result=assign(source_schedule(),0,8,write_budget=0,lookahead=0,time_limit=5)
        r=result['interval_bank_assignment']
        self.assertEqual(r['solver']['message'],'INFEASIBLE')
        self.assertFalse(r['universal_raster_rejected'])
        self.assertFalse(r['full_frame_schedule_proven'])

    def test_outside_interval_bank_capacity_is_still_required(self):
        source=source_schedule()
        source['pieces'][0]['allowed_banks']=[0]
        source['pieces'][1]['allowed_banks']=[0]
        for row in source['trace']:
            row['resident_before'][1]=[None if c is None else c+20 for c in row['resident_before'][1]]
            for e in row['updates']:
                if e['bank']==1:
                    e['color']+=20
                    if e['old']is not None:e['old']+=20
        result=assign(source,7,8,write_budget=0,time_limit=5)
        self.assertEqual(result['interval_bank_assignment']['solver']['message'],'INFEASIBLE')

    def test_fractional_cache_retains_integer_banks_without_schedule_claim(self):
        result=assign(source_schedule(),0,8,write_budget=1,lookahead=0,time_limit=5,fractional_cache=True)
        r=result['interval_bank_assignment']
        self.assertEqual(r['status'],'NECESSARY_INTERVAL_BANK_ASSIGNMENT_FOUND')
        self.assertGreater(r['solver']['fractional_cache_variables'],0)
        self.assertLess(r['solver']['maximum_integer_constraint_violation'],1e-6)
        self.assertTrue(r['full_source_pixel_words_replayed'])
        self.assertFalse(r['integer_interval_schedule_proven'])
        self.assertFalse(r['independent_interval_replay_verified'])
        self.assertFalse(r['full_frame_schedule_proven'])
        self.assertEqual(r['interval_trace'],[])
        self.assertTrue(all(type(b)is int for b in r['piece_assignment']))


if __name__=='__main__':unittest.main()
