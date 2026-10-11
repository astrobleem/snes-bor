import unittest
from raster_dma_window_bound import aligned_window,minimum_commit_span
from raster_bank_residency import favorable_span


class DmaWindowTests(unittest.TestCase):
    def test_transparent_bank_entry_is_not_an_opaque_slot(self):
        for n in range(1,121):
            updates=[dict(bank=i//15)for i in range(n)]
            self.assertEqual(minimum_commit_span(n),favorable_span(updates,8))
        self.assertEqual(minimum_commit_span(22),352)
        self.assertEqual(minimum_commit_span(23),368)

    def test_alignment_has_alternating_twenty_one_and_twenty_two_upper_bounds(self):
        result=aligned_window()
        self.assertEqual(result['phase_advance_per_scanline'],4)
        self.assertEqual(result['phases'][0]['maximum_opaque_writes'],22)
        self.assertEqual(result['phases'][4]['maximum_opaque_writes'],21)
        self.assertEqual(result['phases'][4]['maximum_aligned_commit_span'],344)
        self.assertFalse(result['native_transport_admitted'])


if __name__=='__main__':unittest.main()
