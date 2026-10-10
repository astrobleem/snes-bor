import unittest
import numpy as np
from test_raster_slot_greedy import source_schedule
from raster_slot_greedy import demand
from raster_reverse_search import mirror,search,forward_candidate


class ReverseTests(unittest.TestCase):
    def test_double_mirror_preserves_geometry_pixels_and_color_demand(self):
        source=source_schedule();result=mirror(mirror(source))
        self.assertEqual(result['pieces'],source['pieces'])
        self.assertEqual(result['piece_pixel_masks'],source['piece_pixel_masks'])
        a,_,pixels=demand(source);b,_,other=demand(result)
        self.assertEqual(a,b)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(pixels,other)))

    def test_forward_replay_retains_black_reload_and_zero_prefetch_bound(self):
        source=source_schedule();result=search(source,lookahead=0,seed=4)
        r=result['physical_slot_layout']
        self.assertTrue(r['pixel_color_identity_verified'])
        self.assertTrue(r['all_packet_cgram_identities_verified'])
        self.assertEqual(r['maximum_noninitial_prefetch_latency_lines'],0)
        self.assertLess(r['peak_prepared_commit_span'],356)
        self.assertFalse(r['native_timing_admitted'])
        a,_,pixels=demand(source);b,_,other=demand(result)
        self.assertEqual(a,b)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(pixels,other)))

    def test_small_backward_window_is_heuristic_failure(self):
        result=search(source_schedule(),window=17,lookahead=0)
        self.assertEqual(result['status'],'BOUNDED_GREEDY_NO_CANDIDATE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_forward_range_failure_keeps_pixel_proof_without_admission(self):
        source=source_schedule();result=forward_candidate(source,mirror(source),window=17,lookahead=0)
        r=result['physical_slot_layout']
        self.assertEqual(r['status'],'FORWARD_PHYSICAL_PACKET_WINDOW_EXCEEDED')
        self.assertTrue(r['pixel_color_identity_verified'])
        self.assertGreaterEqual(r['peak_prepared_commit_span'],17)
        self.assertFalse(r['universal_raster_rejected'])
        self.assertFalse(r['native_timing_admitted'])


if __name__=='__main__':unittest.main()
