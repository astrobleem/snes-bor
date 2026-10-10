import itertools
import unittest
from raster_math_windows import compile_mask,compile_sparse_mask,evaluate


class WindowTests(unittest.TestCase):
    def test_all_masks_with_up_to_four_transitions_replay(self):
        for count in range(5):
            for positions in itertools.combinations((1,32,64,96,128,192,255),count):
                for first in (0,1):
                    mask=[first^(sum(p<=x for p in positions)%2)for x in range(256)]
                    descriptor=compile_mask(mask)
                    self.assertEqual([int(evaluate(descriptor,x))for x in range(256)],mask)
                    self.assertFalse(descriptor['register_timing_admitted'])

    def test_many_alternating_intervals_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError,'NOT_REPRESENTABLE'):compile_mask([x%2 for x in range(256)])

    def test_sparse_source_positions_can_use_inverted_two_windows(self):
        pixels={10:1,20:0,30:1,40:0,50:1}
        descriptor=compile_sparse_mask(pixels)
        self.assertEqual(descriptor['wobjsel_color_bits'],0xf0)
        self.assertEqual(descriptor['wobjlog_color_bits'],4)
        self.assertTrue(all(evaluate(descriptor,x)==bool(v)for x,v in pixels.items()))


if __name__=='__main__':unittest.main()
